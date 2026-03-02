import { useState } from "react";
import type { Player } from "../api";
import { fmtSalary, fmtPct, valueColor, valueLabel } from "../utils";

interface Props {
  players: Player[];
}

type SortKey = keyof Player;
type ColGroup = "basic" | "advanced" | "contract";

const POSITIONS = ["PG", "SG", "SF", "PF", "C"];

export default function PlayerTable({ players }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("value_score");
  const [asc, setAsc] = useState(false);
  const [filter, setFilter] = useState("");
  const [posFilter, setPosFilter] = useState("All");
  const [visibleGroups, setVisibleGroups] = useState<Set<ColGroup>>(
    new Set(["basic", "advanced", "contract"])
  );

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setAsc((a) => !a);
    else { setSortKey(key); setAsc(false); }
  };

  const toggleGroup = (g: ColGroup) => {
    setVisibleGroups((prev) => {
      const next = new Set(prev);
      if (next.has(g)) next.delete(g);
      else next.add(g);
      return next;
    });
  };

  const show = (g: ColGroup) => visibleGroups.has(g);

  const sorted = [...players]
    .filter((p) => {
      const textMatch =
        filter === "" ||
        p.full_name.toLowerCase().includes(filter.toLowerCase()) ||
        p.position.toLowerCase().includes(filter.toLowerCase());
      const posMatch = posFilter === "All" || p.position === posFilter;
      return textMatch && posMatch;
    })
    .sort((a, b) => {
      const va = a[sortKey] as number | string;
      const vb = b[sortKey] as number | string;
      if (va < vb) return asc ? -1 : 1;
      if (va > vb) return asc ? 1 : -1;
      return 0;
    });

  const col = (label: string, key: SortKey) => (
    <th onClick={() => handleSort(key)} className="sortable-th">
      {label} {sortKey === key ? (asc ? "▲" : "▼") : ""}
    </th>
  );

  return (
    <div className="player-table-container">
      <div className="player-table-controls">
        <input
          className="filter-input"
          placeholder="Filter players..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <select
          className="pos-filter"
          value={posFilter}
          onChange={(e) => setPosFilter(e.target.value)}
        >
          <option value="All">All Positions</option>
          {POSITIONS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <div className="col-toggles">
          {(["basic", "advanced", "contract"] as ColGroup[]).map((g) => (
            <button
              key={g}
              className={`col-toggle-btn ${show(g) ? "active" : ""}`}
              onClick={() => toggleGroup(g)}
            >
              {g.charAt(0).toUpperCase() + g.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="table-scroll">
        <table className="player-table">
          <thead>
            <tr>
              {col("Player", "full_name")}
              {col("Pos", "position")}
              {show("basic") && col("PTS", "points")}
              {show("basic") && col("REB", "rebounds")}
              {show("basic") && col("AST", "assists")}
              {show("basic") && col("TOV", "turnovers")}
              {show("basic") && col("MIN", "minutes")}
              {show("basic") && col("TS%", "true_shooting_pct")}
              {show("advanced") && col("USG%", "usg_pct")}
              {show("advanced") && col("BPM", "bpm")}
              {show("advanced") && col("WS", "ws")}
              {show("advanced") && col("VORP", "vorp")}
              {show("advanced") && col("PER~", "per")}
              {col("Value", "value_score")}
              {show("contract") && col("Salary (Y1)", "salary")}
              {show("contract") && col("Y2", "salary_year2")}
              {show("contract") && col("Y3", "salary_year3")}
              {show("contract") && col("Y4", "salary_year4")}
              {show("contract") && <th>Classification</th>}
              {show("contract") && <th>Contract</th>}
            </tr>
          </thead>
          <tbody>
            {sorted.map((p) => (
              <tr key={p.espn_id}>
                <td className="player-name-cell">{p.full_name}</td>
                <td>{p.position || "—"}</td>
                {show("basic") && <td>{p.points.toFixed(1)}</td>}
                {show("basic") && <td>{p.rebounds.toFixed(1)}</td>}
                {show("basic") && <td>{p.assists.toFixed(1)}</td>}
                {show("basic") && <td>{(p.turnovers ?? 0).toFixed(1)}</td>}
                {show("basic") && <td>{p.minutes.toFixed(1)}</td>}
                {show("basic") && <td>{fmtPct(p.true_shooting_pct)}</td>}
                {show("advanced") && <td>{(p.usg_pct ?? 0).toFixed(1)}%</td>}
                {show("advanced") && <td>{(p.bpm ?? 0).toFixed(1)}</td>}
                {show("advanced") && <td>{(p.ws ?? 0).toFixed(1)}</td>}
                {show("advanced") && <td>{(p.vorp ?? 0).toFixed(1)}</td>}
                {show("advanced") && <td>{p.per.toFixed(1)}</td>}
                <td>
                  <span className="value-badge" style={{ background: valueColor(p.value_classification) }}>
                    {p.value_score.toFixed(2)}
                  </span>
                </td>
                {show("contract") && <td>{fmtSalary(p.salary)}</td>}
                {show("contract") && <td>{p.salary_year2 > 0 ? fmtSalary(p.salary_year2) : "—"}</td>}
                {show("contract") && <td>{p.salary_year3 > 0 ? fmtSalary(p.salary_year3) : "—"}</td>}
                {show("contract") && <td>{p.salary_year4 > 0 ? fmtSalary(p.salary_year4) : "—"}</td>}
                {show("contract") && (
                  <td>
                    <span className="value-label" style={{ color: valueColor(p.value_classification) }}>
                      {valueLabel(p.value_classification)}
                    </span>
                  </td>
                )}
                {show("contract") && (
                  <td className="contract-cell">{p.contract_status.replace("_", " ")}</td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
