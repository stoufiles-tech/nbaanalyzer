import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Team, TradeResult, TradePick, DraftPickDetail } from "../api";
import { fmtSalary } from "../utils";

interface Props {
  teams: Team[];
}

export default function TradeAnalyzer({ teams }: Props) {
  const [teamAId, setTeamAId] = useState("");
  const [teamBId, setTeamBId] = useState("");
  const [selectedA, setSelectedA] = useState<Set<string>>(new Set());
  const [selectedB, setSelectedB] = useState<Set<string>>(new Set());
  const [selectedPicksA, setSelectedPicksA] = useState<Set<string>>(new Set());
  const [selectedPicksB, setSelectedPicksB] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TradeResult | null>(null);
  const [error, setError] = useState("");

  // Fetch full team data (with players) when a team is selected
  const { data: teamAFull, isLoading: loadingA } = useQuery({
    queryKey: ["team", teamAId],
    queryFn: () => api.getTeam(teamAId),
    enabled: !!teamAId,
  });

  const { data: teamBFull, isLoading: loadingB } = useQuery({
    queryKey: ["team", teamBId],
    queryFn: () => api.getTeam(teamBId),
    enabled: !!teamBId,
  });

  // Fetch draft picks for each team
  const { data: picksA } = useQuery({
    queryKey: ["draft-picks", teamAId],
    queryFn: () => api.getTeamDraftPicks(teamAId),
    enabled: !!teamAId,
  });

  const { data: picksB } = useQuery({
    queryKey: ["draft-picks", teamBId],
    queryFn: () => api.getTeamDraftPicks(teamBId),
    enabled: !!teamBId,
  });

  // Use summary team for display (total_salary etc), full team for roster
  const teamA = teams.find((t) => t.espn_id === teamAId);
  const teamB = teams.find((t) => t.espn_id === teamBId);

  const togglePlayer = (
    name: string,
    selected: Set<string>,
    setSelected: (s: Set<string>) => void
  ) => {
    const next = new Set(selected);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setSelected(next);
  };

  const pickKey = (p: DraftPickDetail) => `${p.year}-${p.round}-${p.original_team}`;

  const togglePick = (
    pick: DraftPickDetail,
    selected: Set<string>,
    setSelected: (s: Set<string>) => void
  ) => {
    const key = pickKey(pick);
    const next = new Set(selected);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setSelected(next);
  };

  const salaryOutA = (teamAFull?.players ?? [])
    .filter((p) => selectedA.has(p.full_name))
    .reduce((s, p) => s + p.salary, 0);

  const salaryOutB = (teamBFull?.players ?? [])
    .filter((p) => selectedB.has(p.full_name))
    .reduce((s, p) => s + p.salary, 0);

  const picksValueA = (picksA?.picks ?? [])
    .filter((p) => selectedPicksA.has(pickKey(p)))
    .reduce((s, p) => s + p.estimated_value, 0);

  const picksValueB = (picksB?.picks ?? [])
    .filter((p) => selectedPicksB.has(pickKey(p)))
    .reduce((s, p) => s + p.estimated_value, 0);

  const mismatch =
    salaryOutA > 0 && salaryOutB > 0
      ? Math.abs(salaryOutA - salaryOutB) / Math.max(salaryOutA, salaryOutB)
      : 0;

  const hasPlayersOrPicks = (players: Set<string>, picks: Set<string>) =>
    players.size > 0 || picks.size > 0;

  const canAnalyze =
    hasPlayersOrPicks(selectedA, selectedPicksA) &&
    hasPlayersOrPicks(selectedB, selectedPicksB) &&
    !loading;

  const analyze = async () => {
    if (!canAnalyze) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      // Build picks arrays from selections
      const tradePicksA: TradePick[] = (picksA?.picks ?? [])
        .filter((p) => selectedPicksA.has(pickKey(p)))
        .map((p) => ({ year: p.year, round: p.round, original_team: p.original_team }));

      const tradePicksB: TradePick[] = (picksB?.picks ?? [])
        .filter((p) => selectedPicksB.has(pickKey(p)))
        .map((p) => ({ year: p.year, round: p.round, original_team: p.original_team }));

      const data = await api.analyzeTrade({
        team_a_id: teamAId,
        team_b_id: teamBId,
        players_a: Array.from(selectedA),
        players_b: Array.from(selectedB),
        picks_a: tradePicksA.length > 0 ? tradePicksA : undefined,
        picks_b: tradePicksB.length > 0 ? tradePicksB : undefined,
      });
      setResult(data);
    } catch {
      setError("Failed to analyze trade. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const renderRoster = (
    fullTeam: Team | undefined,
    isLoading: boolean,
    teamId: string,
    selected: Set<string>,
    setSelected: (s: Set<string>) => void,
    label: string,
    teamPicks: DraftPickDetail[] | undefined,
    selectedPicks: Set<string>,
    setSelectedPicks: (s: Set<string>) => void
  ) => {
    if (!teamId) return <div className="trade-roster-empty">Select a team</div>;
    if (isLoading) return <div className="trade-roster-empty">Loading roster...</div>;
    if (!fullTeam) return <div className="trade-roster-empty">No data</div>;

    const sorted = [...(fullTeam.players ?? [])].sort((a, b) => b.salary - a.salary);
    return (
      <div className="trade-roster">
        <div className="trade-roster-header">
          {label}: {fullTeam.display_name}
        </div>
        <div className="trade-roster-list">
          {sorted.map((p) => (
            <label
              key={p.full_name}
              className={`trade-player-row ${selected.has(p.full_name) ? "selected" : ""}`}
            >
              <input
                type="checkbox"
                checked={selected.has(p.full_name)}
                onChange={() => togglePlayer(p.full_name, selected, setSelected)}
              />
              <span className="trade-player-name">{p.full_name}</span>
              <span className="trade-player-pos">{p.position || "—"}</span>
              <span className="trade-player-salary">{fmtSalary(p.salary)}</span>
            </label>
          ))}
        </div>

        {/* Draft Picks Section */}
        {teamPicks && teamPicks.length > 0 && (
          <>
            <div className="trade-roster-header trade-picks-header">Draft Picks</div>
            <div className="trade-picks-list">
              {teamPicks.map((pick) => {
                const key = pickKey(pick);
                return (
                  <label
                    key={key}
                    className={`trade-pick-row ${selectedPicks.has(key) ? "selected" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedPicks.has(key)}
                      onChange={() => togglePick(pick, selectedPicks, setSelectedPicks)}
                    />
                    <span className="trade-pick-label">{pick.label}</span>
                    <span className="trade-pick-value">~{fmtSalary(pick.estimated_value)}</span>
                  </label>
                );
              })}
            </div>
          </>
        )}
      </div>
    );
  };

  const validity = result?.validity;

  return (
    <div className="trade-analyzer">
      <h3>Trade Analyzer</h3>
      <p className="subtitle">Select two teams and players/picks to analyze a potential trade.</p>

      <div className="trade-team-selectors">
        <div className="trade-team-col">
          <select
            className="team-select"
            value={teamAId}
            onChange={(e) => {
              setTeamAId(e.target.value);
              setSelectedA(new Set());
              setSelectedPicksA(new Set());
              setResult(null);
            }}
          >
            <option value="">Select Team A</option>
            {teams
              .filter((t) => t.espn_id !== teamBId)
              .map((t) => (
                <option key={t.espn_id} value={t.espn_id}>
                  {t.display_name}
                </option>
              ))}
          </select>
          {renderRoster(
            teamAFull, loadingA, teamAId,
            selectedA, setSelectedA, "Team A",
            picksA?.picks, selectedPicksA, setSelectedPicksA
          )}
          {(selectedA.size > 0 || selectedPicksA.size > 0) && (
            <div className="trade-salary-summary">
              {selectedA.size > 0 && <>Outgoing: <strong>{fmtSalary(salaryOutA)}</strong></>}
              {selectedPicksA.size > 0 && (
                <span className="trade-picks-summary">
                  {selectedPicksA.size} pick{selectedPicksA.size > 1 ? "s" : ""} (~{fmtSalary(picksValueA)})
                </span>
              )}
            </div>
          )}
        </div>

        <div className="trade-arrow">⇄</div>

        <div className="trade-team-col">
          <select
            className="team-select"
            value={teamBId}
            onChange={(e) => {
              setTeamBId(e.target.value);
              setSelectedB(new Set());
              setSelectedPicksB(new Set());
              setResult(null);
            }}
          >
            <option value="">Select Team B</option>
            {teams
              .filter((t) => t.espn_id !== teamAId)
              .map((t) => (
                <option key={t.espn_id} value={t.espn_id}>
                  {t.display_name}
                </option>
              ))}
          </select>
          {renderRoster(
            teamBFull, loadingB, teamBId,
            selectedB, setSelectedB, "Team B",
            picksB?.picks, selectedPicksB, setSelectedPicksB
          )}
          {(selectedB.size > 0 || selectedPicksB.size > 0) && (
            <div className="trade-salary-summary">
              {selectedB.size > 0 && <>Outgoing: <strong>{fmtSalary(salaryOutB)}</strong></>}
              {selectedPicksB.size > 0 && (
                <span className="trade-picks-summary">
                  {selectedPicksB.size} pick{selectedPicksB.size > 1 ? "s" : ""} (~{fmtSalary(picksValueB)})
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {mismatch > 0.25 && (
        <div className="trade-warning">
          Salary mismatch is {(mismatch * 100).toFixed(0)}% — this trade may not be CBA-compliant.
        </div>
      )}

      <button className="analyze-btn" onClick={analyze} disabled={!canAnalyze}>
        {loading ? "Analyzing..." : "Analyze Trade"}
      </button>

      {error && <div className="trade-error">{error}</div>}

      {result && (
        <div className="trade-result">
          {/* Validity warnings */}
          {validity && !validity.is_valid && (
            <div className="trade-validity-warnings">
              {!validity.team_a_salary_valid && (
                <div className="trade-validity-item">
                  {teamA?.display_name}: {validity.team_a_warnings.join("; ")}
                </div>
              )}
              {!validity.team_b_salary_valid && (
                <div className="trade-validity-item">
                  {teamB?.display_name}: {validity.team_b_warnings.join("; ")}
                </div>
              )}
              {validity.ntc_warnings.map((w, i) => (
                <div key={i} className="trade-validity-item">{w}</div>
              ))}
            </div>
          )}

          <h4>Cap Impact</h4>
          <table className="trade-impact-table">
            <thead>
              <tr>
                <th>Team</th>
                <th>Current Payroll</th>
                <th>New Payroll</th>
                <th>Delta</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{teamA?.display_name}</td>
                <td>{fmtSalary(teamA?.total_salary ?? 0)}</td>
                <td>{fmtSalary(result.team_a_new_total)}</td>
                <td className={result.team_a_delta > 0 ? "delta-up" : "delta-down"}>
                  {result.team_a_delta > 0 ? "+" : ""}{fmtSalary(result.team_a_delta)}
                </td>
              </tr>
              <tr>
                <td>{teamB?.display_name}</td>
                <td>{fmtSalary(teamB?.total_salary ?? 0)}</td>
                <td>{fmtSalary(result.team_b_new_total)}</td>
                <td className={result.team_b_delta > 0 ? "delta-up" : "delta-down"}>
                  {result.team_b_delta > 0 ? "+" : ""}{fmtSalary(result.team_b_delta)}
                </td>
              </tr>
            </tbody>
          </table>

          {/* Draft pick values if present */}
          {((result.picks_a_value ?? 0) > 0 || (result.picks_b_value ?? 0) > 0) && (
            <div className="trade-picks-impact">
              <h4>Draft Capital Impact</h4>
              <div className="trade-picks-values">
                {(result.picks_a_value ?? 0) > 0 && (
                  <div>
                    {teamA?.display_name} sends ~{fmtSalary(result.picks_a_value!)} in draft value
                  </div>
                )}
                {(result.picks_b_value ?? 0) > 0 && (
                  <div>
                    {teamB?.display_name} sends ~{fmtSalary(result.picks_b_value!)} in draft value
                  </div>
                )}
              </div>
            </div>
          )}

          <h4>AI Analysis</h4>
          <div className="trade-analysis-text">{result.analysis}</div>
        </div>
      )}
    </div>
  );
}
