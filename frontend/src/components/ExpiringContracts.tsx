import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Player } from "../api";
import { fmtSalary } from "../utils";

interface Props {
  onPlayerClick?: (name: string) => void;
}

interface TeamGroup {
  abbr: string;
  players: Player[];
  totalExpiring: number;
}

export default function ExpiringContracts({ onPlayerClick }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const { data: allPlayers, isLoading } = useQuery({
    queryKey: ["all-players"],
    queryFn: api.getAllPlayers,
  });

  if (isLoading) return <div className="loading">Loading player data...</div>;
  if (!allPlayers) return null;

  const expiring = allPlayers.filter(
    (p) => p.salary > 0 && p.salary_year2 === 0
  );

  // Flat list sorted by salary for the top contracts table
  const topExpiring = [...expiring].sort((a, b) => b.salary - a.salary);

  const byTeam = new Map<string, Player[]>();
  for (const p of expiring) {
    const list = byTeam.get(p.team_abbr) || [];
    list.push(p);
    byTeam.set(p.team_abbr, list);
  }

  const groups: TeamGroup[] = Array.from(byTeam.entries())
    .map(([abbr, players]) => ({
      abbr,
      players: players.sort((a, b) => b.salary - a.salary),
      totalExpiring: players.reduce((s, p) => s + p.salary, 0),
    }))
    .sort((a, b) => b.totalExpiring - a.totalExpiring);

  const totalSalary = expiring.reduce((s, p) => s + p.salary, 0);
  const maxTeamExpiring = groups[0]?.totalExpiring || 1;

  const toggle = (abbr: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(abbr)) next.delete(abbr);
      else next.add(abbr);
      return next;
    });
  };

  return (
    <div className="expiring-container">
      <div className="expiring-banner">
        <div className="expiring-banner-stat">
          <span className="expiring-banner-value">{expiring.length}</span>
          <span className="expiring-banner-label">Expiring Contracts</span>
        </div>
        <div className="expiring-banner-stat">
          <span className="expiring-banner-value">{fmtSalary(totalSalary)}</span>
          <span className="expiring-banner-label">Total Expiring Salary</span>
        </div>
        <div className="expiring-banner-stat">
          <span className="expiring-banner-value">{groups.length}</span>
          <span className="expiring-banner-label">Teams with Expiring</span>
        </div>
      </div>

      {/* Top expiring contracts — visible immediately */}
      <div className="expiring-top-table">
        <h3>Top Expiring Contracts</h3>
        <div className="player-table-container">
          <div className="table-scroll">
            <table className="player-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Player</th>
                  <th>Team</th>
                  <th>Pos</th>
                  <th>Age</th>
                  <th>Salary</th>
                  <th>PTS</th>
                  <th>REB</th>
                  <th>AST</th>
                  <th>BPM</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {topExpiring.slice(0, 30).map((p, i) => (
                  <tr key={p.espn_id}>
                    <td style={{ color: "var(--text-muted)" }}>{i + 1}</td>
                    <td className="player-name-cell">
                      {onPlayerClick ? (
                        <button className="clickable-name" onClick={() => onPlayerClick(p.full_name)}>
                          {p.full_name}
                        </button>
                      ) : (
                        p.full_name
                      )}
                    </td>
                    <td>{p.team_abbr}</td>
                    <td>{p.position || "—"}</td>
                    <td>{p.age}</td>
                    <td style={{ fontWeight: 600, color: "var(--accent)" }}>{fmtSalary(p.salary)}</td>
                    <td>{p.points.toFixed(1)}</td>
                    <td>{p.rebounds.toFixed(1)}</td>
                    <td>{p.assists.toFixed(1)}</td>
                    <td>{p.bpm.toFixed(1)}</td>
                    <td>{p.value_score.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="expiring-chart-card">
        <h3>Expiring Salary by Team</h3>
        <div className="expiring-bars">
          {groups.map((g) => (
            <div key={g.abbr} className="expiring-bar-row">
              <span className="expiring-bar-label">{g.abbr}</span>
              <div className="expiring-bar-track">
                <div
                  className="expiring-bar-fill"
                  style={{ width: `${(g.totalExpiring / maxTeamExpiring) * 100}%` }}
                />
              </div>
              <span className="expiring-bar-value">{fmtSalary(g.totalExpiring)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="expiring-teams">
        {groups.map((g) => (
          <div key={g.abbr} className="expiring-team-card">
            <button className="expiring-team-header" onClick={() => toggle(g.abbr)}>
              <span className="expiring-team-abbr">{g.abbr}</span>
              <span className="expiring-team-count">{g.players.length} player{g.players.length !== 1 ? "s" : ""}</span>
              <span className="expiring-team-total">{fmtSalary(g.totalExpiring)}</span>
              <span className="expiring-chevron">{expanded.has(g.abbr) ? "▲" : "▼"}</span>
            </button>
            {expanded.has(g.abbr) && (
              <div className="expiring-player-list">
                {g.players.map((p) => (
                  <div key={p.espn_id} className="expiring-player-row">
                    <span
                      className={`expiring-player-name${onPlayerClick ? " clickable-name" : ""}`}
                      onClick={() => onPlayerClick?.(p.full_name)}
                    >
                      {p.full_name}
                    </span>
                    <span className="expiring-player-pos">{p.position || "—"}</span>
                    <span className="expiring-player-stats">
                      {p.points.toFixed(1)} / {p.rebounds.toFixed(1)} / {p.assists.toFixed(1)}
                    </span>
                    <span className="expiring-player-salary">{fmtSalary(p.salary)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
