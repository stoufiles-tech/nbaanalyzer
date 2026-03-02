import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Team, TradeResult } from "../api";
import { fmtSalary } from "../utils";

interface Props {
  teams: Team[];
}

export default function TradeAnalyzer({ teams }: Props) {
  const [teamAId, setTeamAId] = useState("");
  const [teamBId, setTeamBId] = useState("");
  const [selectedA, setSelectedA] = useState<Set<string>>(new Set());
  const [selectedB, setSelectedB] = useState<Set<string>>(new Set());
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

  const salaryOutA = (teamAFull?.players ?? [])
    .filter((p) => selectedA.has(p.full_name))
    .reduce((s, p) => s + p.salary, 0);

  const salaryOutB = (teamBFull?.players ?? [])
    .filter((p) => selectedB.has(p.full_name))
    .reduce((s, p) => s + p.salary, 0);

  const mismatch =
    salaryOutA > 0 && salaryOutB > 0
      ? Math.abs(salaryOutA - salaryOutB) / Math.max(salaryOutA, salaryOutB)
      : 0;

  const canAnalyze = selectedA.size > 0 && selectedB.size > 0 && !loading;

  const analyze = async () => {
    if (!canAnalyze) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await api.analyzeTrade({
        team_a_id: teamAId,
        team_b_id: teamBId,
        players_a: Array.from(selectedA),
        players_b: Array.from(selectedB),
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
    label: string
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
      </div>
    );
  };

  return (
    <div className="trade-analyzer">
      <h3>Trade Analyzer</h3>
      <p className="subtitle">Select two teams and players to analyze a potential trade.</p>

      <div className="trade-team-selectors">
        <div className="trade-team-col">
          <select
            className="team-select"
            value={teamAId}
            onChange={(e) => {
              setTeamAId(e.target.value);
              setSelectedA(new Set());
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
          {renderRoster(teamAFull, loadingA, teamAId, selectedA, setSelectedA, "Team A")}
          {selectedA.size > 0 && (
            <div className="trade-salary-summary">
              Outgoing: <strong>{fmtSalary(salaryOutA)}</strong>
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
          {renderRoster(teamBFull, loadingB, teamBId, selectedB, setSelectedB, "Team B")}
          {selectedB.size > 0 && (
            <div className="trade-salary-summary">
              Outgoing: <strong>{fmtSalary(salaryOutB)}</strong>
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

          <h4>AI Analysis</h4>
          <div className="trade-analysis-text">{result.analysis}</div>
        </div>
      )}
    </div>
  );
}
