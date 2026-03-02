import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import TeamCard from "./components/TeamCard";
import TeamComparison from "./components/TeamComparison";
import TeamDetail from "./components/TeamDetail";
import PlayerTable from "./components/PlayerTable";
import AIChat from "./components/AIChat";
import TradeAnalyzer from "./components/TradeAnalyzer";
import { fmtSalary } from "./utils";

type Tab = "overview" | "comparison" | "top-value" | "ai";

export default function App() {
  const [tab, setTab] = useState<Tab>("overview");
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const qc = useQueryClient();

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

  const refreshMutation = useMutation({
    mutationFn: api.refreshData,
    onSuccess: () => {
      qc.invalidateQueries();
    },
  });

  const isLoading = capLoading || teamsLoading;

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <div className="logo">NBA Cap Analyzer</div>
          {cap && (
            <div className="cap-pill">
              {cap.season} · Cap: {fmtSalary(cap.salary_cap)} · Tax: {fmtSalary(cap.luxury_tax_threshold)}
            </div>
          )}
        </div>
        <div className="header-right">
          <nav className="tab-nav">
            {(["overview", "comparison", "top-value", "ai"] as Tab[]).map((t) => (
              <button
                key={t}
                className={`tab-btn ${tab === t ? "active" : ""}`}
                onClick={() => { setTab(t); setSelectedTeamId(null); }}
              >
                {t === "overview" ? "Teams" : t === "comparison" ? "Compare" : t === "top-value" ? "Top Value" : "AI Analyst"}
              </button>
            ))}
          </nav>
          <button
            className="refresh-btn"
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
          >
            {refreshMutation.isPending ? "Refreshing..." : "Refresh Data"}
          </button>
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
                <TeamDetail teamId={selectedTeamId} cap={cap} />
              </div>
            )}

            {tab === "comparison" && (
              <div>
                <h2>Team Comparisons</h2>
                <TeamComparison teams={teams} cap={cap} />
              </div>
            )}

            {tab === "top-value" && (
              <div>
                <h2>Top Value Players (League-Wide)</h2>
                <p className="subtitle">
                  Ranked by value score — production per $M of salary. Higher = better value.
                </p>
                {topLoading ? (
                  <div className="loading">Loading top value players...</div>
                ) : topPlayers ? (
                  <PlayerTable players={topPlayers} />
                ) : null}
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
