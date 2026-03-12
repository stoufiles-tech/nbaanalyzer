import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { Player } from "./api";
import TeamCard from "./components/TeamCard";
import TeamComparison from "./components/TeamComparison";
import TeamDetail from "./components/TeamDetail";
import PlayerTable from "./components/PlayerTable";
import PlayerComparables from "./components/PlayerComparables";
import PlayerVsPlayer from "./components/PlayerVsPlayer";
import ExpiringContracts from "./components/ExpiringContracts";
import AIChat from "./components/AIChat";
import TradeAnalyzer from "./components/TradeAnalyzer";
import { fmtSalary } from "./utils";

type Tab = "overview" | "comparison" | "top-value" | "comparables" | "expiring" | "ai";

const TAB_LABELS: Record<Tab, string> = {
  overview: "Teams",
  comparison: "Compare",
  "top-value": "Top Value",
  comparables: "Valuations",
  expiring: "Free Agents",
  ai: "AI Analyst",
};

function computePositionAverages(players: Player[]) {
  const byPos: Record<string, { total: number; count: number }> = {};
  for (const p of players) {
    const pos = p.position || "??";
    if (p.salary <= 0) continue;
    if (!byPos[pos]) byPos[pos] = { total: 0, count: 0 };
    byPos[pos].total += p.salary;
    byPos[pos].count += 1;
  }
  return Object.entries(byPos)
    .filter(([, v]) => v.count >= 3)
    .map(([pos, v]) => ({ pos, avg: v.total / v.count, count: v.count }))
    .sort((a, b) => b.avg - a.avg);
}

type CompareSubTab = "teams" | "players";

export default function App() {
  const [tab, setTab] = useState<Tab>("overview");
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const [compsPlayer, setCompsPlayer] = useState<string | null>(null);
  const [compareSubTab, setCompareSubTab] = useState<CompareSubTab>("teams");

  const { data: cap, isLoading: capLoading } = useQuery({
    queryKey: ["cap-constants"],
    queryFn: api.getCapConstants,
  });

  const { data: teams, isLoading: teamsLoading } = useQuery({
    queryKey: ["teams"],
    queryFn: api.getTeams,
  });

  const { data: topPlayers, isLoading: topLoading } = useQuery({
    queryKey: ["top-value"],
    queryFn: () => api.getTopValuePlayers(100),
    enabled: tab === "top-value",
  });

  const handlePlayerClick = (name: string) => {
    setCompsPlayer(name);
    setTab("comparables");
  };

  const positionBenchmarks = useMemo(
    () => (topPlayers ? computePositionAverages(topPlayers) : []),
    [topPlayers]
  );

  const isLoading = capLoading || teamsLoading;

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <div className="logo">NBA Cap Analyzer</div>
          {cap && (
            <div className="cap-pill">
              {cap.season} · Cap: {fmtSalary(cap.salary_cap)} · Tax: {fmtSalary(cap.luxury_tax_threshold)}
              {cap.data_as_of ? ` · Data: ${cap.data_as_of}` : ""}
            </div>
          )}
        </div>
        <div className="header-right">
          <nav className="tab-nav">
            {(Object.keys(TAB_LABELS) as Tab[]).map((t) => (
              <button
                key={t}
                className={`tab-btn ${tab === t ? "active" : ""}`}
                onClick={() => { setTab(t); setSelectedTeamId(null); }}
              >
                {TAB_LABELS[t]}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="app-main">
        {isLoading && <div className="loading-overlay">Loading NBA data...</div>}

        {!isLoading && cap && teams && (
          <>
            {tab === "overview" && !selectedTeamId && (
              <div>
                <div className="section-header">
                  <h2>All Teams ({teams.length})</h2>
                  <div className="legend">
                    <span className="legend-dot" style={{ background: "#22c55e" }} /> Under Cap
                    <span className="legend-dot" style={{ background: "#eab308" }} /> Over Cap
                    <span className="legend-dot" style={{ background: "#f97316" }} /> Luxury Tax
                    <span className="legend-dot" style={{ background: "#ef4444" }} /> Over Apron
                  </div>
                </div>
                <div className="teams-grid">
                  {teams.map((t) => (
                    <TeamCard
                      key={t.espn_id}
                      team={t}
                      cap={cap}
                      onClick={() => setSelectedTeamId(t.espn_id)}
                      selected={selectedTeamId === t.espn_id}
                    />
                  ))}
                </div>
              </div>
            )}

            {tab === "overview" && selectedTeamId && (
              <div>
                <button className="back-btn" onClick={() => setSelectedTeamId(null)}>
                  ← Back to Teams
                </button>
                <TeamDetail teamId={selectedTeamId} cap={cap} onPlayerClick={handlePlayerClick} />
              </div>
            )}

            {tab === "comparison" && (
              <div>
                <div className="detail-tab-bar">
                  <button
                    className={`detail-tab-btn ${compareSubTab === "teams" ? "active" : ""}`}
                    onClick={() => setCompareSubTab("teams")}
                  >
                    Teams
                  </button>
                  <button
                    className={`detail-tab-btn ${compareSubTab === "players" ? "active" : ""}`}
                    onClick={() => setCompareSubTab("players")}
                  >
                    Players
                  </button>
                </div>
                {compareSubTab === "teams" && (
                  <>
                    <h2>Team Comparisons</h2>
                    <TeamComparison teams={teams} cap={cap} onTeamClick={(id) => { setSelectedTeamId(id); setTab("overview"); }} />
                  </>
                )}
                {compareSubTab === "players" && (
                  <>
                    <h2>Head-to-Head Player Comparison</h2>
                    <p className="subtitle">Pick any two players and compare their stats side-by-side.</p>
                    <PlayerVsPlayer />
                  </>
                )}
              </div>
            )}

            {tab === "top-value" && (
              <div>
                <h2>Top Value Players (League-Wide)</h2>
                <p className="subtitle">
                  Ranked by value score — production per $M of salary. Higher = better value.
                </p>
                {positionBenchmarks.length > 0 && (
                  <div className="benchmark-chips">
                    <span className="benchmark-label">Avg Salary by Position:</span>
                    {positionBenchmarks.map((b) => (
                      <span key={b.pos} className="benchmark-chip">
                        {b.pos}: {fmtSalary(b.avg)}
                      </span>
                    ))}
                  </div>
                )}
                {topLoading ? (
                  <div className="loading">Loading top value players...</div>
                ) : topPlayers ? (
                  <PlayerTable players={topPlayers} onPlayerClick={handlePlayerClick} />
                ) : null}
              </div>
            )}

            {tab === "comparables" && (
              <div>
                <h2>Contract Comparables</h2>
                <p className="subtitle">
                  Find players with similar production profiles and compare salaries to estimate fair market value.
                </p>
                <PlayerComparables initialPlayer={compsPlayer} />
              </div>
            )}

            {tab === "expiring" && (
              <div>
                <h2>Expiring Contracts & Free Agents</h2>
                <p className="subtitle">
                  Players with no guaranteed salary beyond this season — potential free agents or trade targets.
                </p>
                <ExpiringContracts onPlayerClick={handlePlayerClick} />
              </div>
            )}

            {tab === "ai" && (
              <div className="ai-tab">
                <div className="ai-tab-split">
                  <div className="ai-chat-section">
                    <h2>AI Analyst</h2>
                    <p className="subtitle">Ask questions about the 2025-26 season, cap situations, and player values.</p>
                    <AIChat />
                  </div>
                  <div className="ai-trade-section">
                    <TradeAnalyzer teams={teams} />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
