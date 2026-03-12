import { useState, useEffect, useRef } from "react";
import { api } from "../api";
import type { ComparablesResult, ComparablePlayer } from "../api";
import { fmtSalary } from "../utils";

const fmtBpm = (n: number) => (n >= 0 ? `+${n.toFixed(1)}` : n.toFixed(1));

const fmvBadgeStyle = (pctDiff: number | null): React.CSSProperties => {
  if (pctDiff === null) return { background: "#64748b" };
  if (pctDiff < -0.05)  return { background: "#16a34a" };  // underpaid — green
  if (pctDiff >  0.05)  return { background: "#dc2626" };  // overpaid  — red
  return { background: "#2563eb" };                         // fair      — blue
};

const verdictColor = (verdict: string) => {
  if (verdict.startsWith("Underpaid")) return "#16a34a";
  if (verdict.startsWith("Overpaid"))  return "#dc2626";
  if (verdict === "Fairly priced")     return "#2563eb";
  return "#64748b";
};

const SUGGESTIONS = [
  "Shai Gilgeous-Alexander",
  "Nikola Jokic",
  "Anthony Edwards",
  "Jayson Tatum",
  "Karl-Anthony Towns",
];

interface Props {
  initialPlayer?: string | null;
}

export default function PlayerComparables({ initialPlayer }: Props) {
  const [query, setQuery]     = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<ComparablesResult | null>(null);
  const [error, setError]     = useState("");

  const lastInitial = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    if (initialPlayer && initialPlayer !== lastInitial.current) {
      lastInitial.current = initialPlayer;
      search(initialPlayer);
    }
  }, [initialPlayer]); // eslint-disable-line react-hooks/exhaustive-deps

  const search = async (name?: string) => {
    const q = (name ?? query).trim();
    if (!q) return;
    if (name) setQuery(name);
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await api.getComparables(q, 8);
      setResult(data);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail;
      setError(detail ?? "Player not found. Check the spelling and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="comps-container">
      {/* ── Search ──────────────────────────────────────────────────── */}
      <div className="comps-search-row">
        <input
          className="comps-search-input"
          placeholder="Enter any player name (e.g. Jayson Tatum)…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
        />
        <button
          className="comps-search-btn"
          onClick={() => search()}
          disabled={loading || !query.trim()}
        >
          {loading ? "Searching…" : "Find Comps"}
        </button>
      </div>

      {/* Suggestions */}
      {!result && !loading && (
        <div className="comps-suggestions">
          <span className="comps-suggestions-label">Try:</span>
          {SUGGESTIONS.map((s) => (
            <button key={s} className="comps-suggestion-chip" onClick={() => search(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      {error && <div className="comps-error">{error}</div>}

      {result && (
        <>
          {result.low_sample && (
            <div className="comps-warning">
              Fewer than 3 comparable players have salary data — FMV estimate may be unreliable.
            </div>
          )}

          {/* ── Player card + FMV badge ──────────────────────────────── */}
          <div className="comps-header-grid">
            <div className="comps-player-card">
              <div className="comps-player-name">{result.target.full_name}</div>
              <div className="comps-player-meta">
                {result.target.team_abbr}
                {result.target.position ? ` · ${result.target.position}` : ""}
                {result.target.age > 0   ? ` · Age ${result.target.age}` : ""}
              </div>
              <div className="comps-stat-row">
                {[
                  ["PTS",  result.target.points.toFixed(1)],
                  ["REB",  result.target.rebounds.toFixed(1)],
                  ["AST",  result.target.assists.toFixed(1)],
                  ["BPM",  fmtBpm(result.target.bpm)],
                  ["WS",   result.target.ws.toFixed(1)],
                  ["USG%", result.target.usg_pct > 0
                             ? `${(result.target.usg_pct * 100).toFixed(1)}%`
                             : `${result.target.usg_pct.toFixed(1)}%`],
                ].map(([label, val]) => (
                  <div className="comps-stat" key={label}>
                    <span className="comps-stat-label">{label}</span>
                    <span className="comps-stat-value">{val}</span>
                  </div>
                ))}
              </div>
              <div className="comps-current-salary">
                Current contract:{" "}
                <strong>
                  {result.current_salary > 0
                    ? fmtSalary(result.current_salary)
                    : "No active contract"}
                </strong>
              </div>
            </div>

            <div className="comps-fmv-card">
              <div className="comps-fmv-label">Fair Market Value</div>
              <div className="comps-fmv-badge" style={fmvBadgeStyle(result.pct_diff)}>
                {result.fair_market_value != null
                  ? fmtSalary(result.fair_market_value)
                  : "N/A"}
              </div>
              <div className="comps-verdict" style={{ color: verdictColor(result.verdict) }}>
                {result.verdict}
              </div>
              {result.pct_diff != null && (
                <div className="comps-pct-diff">
                  {result.pct_diff >= 0 ? "+" : ""}
                  {(result.pct_diff * 100).toFixed(1)}% vs. FMV
                </div>
              )}
              <div className="comps-fmv-note">
                Based on {result.comp_count} comparable contracts
              </div>
            </div>
          </div>

          {/* ── Comparables table ────────────────────────────────────── */}
          <div className="comps-table-wrap">
            <div className="comps-table-title">Contract Comparables</div>
            <div className="table-scroll">
              <table className="player-table comps-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Player</th>
                    <th>Team</th>
                    <th>Pos</th>
                    <th>Age</th>
                    <th>PTS</th>
                    <th>REB</th>
                    <th>AST</th>
                    <th>BPM</th>
                    <th>WS</th>
                    <th>Salary</th>
                    <th>Match</th>
                  </tr>
                </thead>
                <tbody>
                  {result.comparables.map((comp: ComparablePlayer, i: number) => (
                    <tr key={comp.full_name}>
                      <td className="comps-rank">{i + 1}</td>
                      <td className="player-name-cell">{comp.full_name}</td>
                      <td>{comp.team_abbr}</td>
                      <td>{comp.position || "—"}</td>
                      <td>{comp.age > 0 ? comp.age : "—"}</td>
                      <td>{comp.points.toFixed(1)}</td>
                      <td>{comp.rebounds.toFixed(1)}</td>
                      <td>{comp.assists.toFixed(1)}</td>
                      <td>{fmtBpm(comp.bpm)}</td>
                      <td>{comp.ws.toFixed(1)}</td>
                      <td>{comp.salary > 0 ? fmtSalary(comp.salary) : "—"}</td>
                      <td>
                        <div className="comps-sim-bar-wrap">
                          <div
                            className="comps-sim-bar"
                            style={{ width: `${(comp.similarity * 100).toFixed(0)}%` }}
                          />
                          <span className="comps-sim-pct">
                            {(comp.similarity * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {!result && !loading && !error && (
        <div className="comps-empty-state">
          <div className="comps-empty-icon">$</div>
          <div className="comps-empty-title">Contract Comparables</div>
          <div className="comps-empty-text">
            Search any player to find similar contracts and estimate their fair market value.
          </div>
        </div>
      )}
    </div>
  );
}
