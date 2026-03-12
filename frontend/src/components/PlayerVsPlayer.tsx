import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Player } from "../api";
import { fmtSalary } from "../utils";

const SUGGESTED_MATCHUPS = [
  ["Shai Gilgeous-Alexander", "Luka Doncic"],
  ["Jayson Tatum", "Kevin Durant"],
  ["Nikola Jokic", "Joel Embiid"],
  ["Anthony Edwards", "Jaylen Brown"],
];

interface StatDef {
  key: string;
  label: string;
  fmt: (v: number) => string;
  invert?: boolean; // lower = better (salary)
  getA: (p: Player) => number;
  getB: (p: Player) => number;
}

function pct(v: number) { return (v * 100).toFixed(1) + "%"; }
function dec1(v: number) { return v.toFixed(1); }
function dec2(v: number) { return v.toFixed(2); }

const STATS: StatDef[] = [
  { key: "pts",    label: "PTS",       fmt: dec1, getA: p => p.points,  getB: p => p.points },
  { key: "reb",    label: "REB",       fmt: dec1, getA: p => p.rebounds, getB: p => p.rebounds },
  { key: "ast",    label: "AST",       fmt: dec1, getA: p => p.assists,  getB: p => p.assists },
  { key: "stl",    label: "STL",       fmt: dec1, getA: p => p.steals,   getB: p => p.steals },
  { key: "blk",    label: "BLK",       fmt: dec1, getA: p => p.blocks,   getB: p => p.blocks },
  { key: "min",    label: "MIN",       fmt: dec1, getA: p => p.minutes,  getB: p => p.minutes },
  { key: "ts",     label: "TS%",       fmt: pct,  getA: p => p.true_shooting_pct, getB: p => p.true_shooting_pct },
  { key: "per",    label: "PER",       fmt: dec1, getA: p => p.per,      getB: p => p.per },
  { key: "bpm",    label: "BPM",       fmt: dec1, getA: p => p.bpm,      getB: p => p.bpm },
  { key: "ws",     label: "WS",        fmt: dec1, getA: p => p.ws,       getB: p => p.ws },
  { key: "vorp",   label: "VORP",      fmt: dec2, getA: p => p.vorp,     getB: p => p.vorp },
  { key: "usg",    label: "USG%",      fmt: pct,  getA: p => p.usg_pct,  getB: p => p.usg_pct },
  { key: "salary", label: "Salary",    fmt: v => fmtSalary(v), invert: true, getA: p => p.salary, getB: p => p.salary },
  { key: "value",  label: "Value Score", fmt: dec1, getA: p => p.value_score, getB: p => p.value_score },
];

function valueBadgeColor(cls: string): string {
  switch (cls) {
    case "elite": return "#16a34a";
    case "great": return "#22c55e";
    case "good":  return "#84cc16";
    case "fair":  return "#eab308";
    case "overpaid": return "#f97316";
    case "bad":   return "#ef4444";
    default:      return "#94a3b8";
  }
}

function PlayerSearch({ label, players, selected, onSelect }: {
  label: string;
  players: Player[];
  selected: Player | null;
  onSelect: (p: Player | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const filtered = query.length >= 2
    ? players.filter(p => p.full_name.toLowerCase().includes(query.toLowerCase())).slice(0, 12)
    : [];

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="h2h-picker" ref={ref}>
      <span className="h2h-picker-label">{label}</span>
      {selected ? (
        <div className="h2h-selected">
          <span>{selected.full_name}</span>
          <button className="h2h-clear" onClick={() => { onSelect(null); setQuery(""); }}>x</button>
        </div>
      ) : (
        <input
          className="h2h-search-input"
          placeholder="Search player..."
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => { if (query.length >= 2) setOpen(true); }}
        />
      )}
      {open && filtered.length > 0 && (
        <div className="h2h-dropdown">
          {filtered.map(p => (
            <div key={p.espn_id} className="h2h-dropdown-item" onClick={() => { onSelect(p); setOpen(false); setQuery(""); }}>
              <span className="h2h-dd-name">{p.full_name}</span>
              <span className="h2h-dd-meta">{p.team_abbr} · {p.position} · {fmtSalary(p.salary)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PlayerVsPlayer() {
  const { data: allPlayers } = useQuery({
    queryKey: ["all-players"],
    queryFn: api.getAllPlayers,
    staleTime: 5 * 60_000,
  });

  const players = allPlayers ?? [];

  const [playerA, setPlayerA] = useState<Player | null>(null);
  const [playerB, setPlayerB] = useState<Player | null>(null);

  const findPlayer = useCallback((name: string) => players.find(p => p.full_name === name) ?? null, [players]);

  const loadMatchup = (a: string, b: string) => {
    setPlayerA(findPlayer(a));
    setPlayerB(findPlayer(b));
  };

  if (!allPlayers) return <div className="loading">Loading players...</div>;

  const hasComparison = playerA && playerB;

  // Compute stat maxes and winners
  let winsA = 0, winsB = 0;
  const statRows = hasComparison ? STATS.map(s => {
    const valA = s.getA(playerA);
    const valB = s.getB(playerB);
    const max = Math.max(Math.abs(valA), Math.abs(valB), 0.001);
    let winner: "a" | "b" | "tie" = "tie";
    if (s.invert) {
      if (valA < valB) winner = "a";
      else if (valB < valA) winner = "b";
    } else {
      if (valA > valB) winner = "a";
      else if (valB > valA) winner = "b";
    }
    if (winner === "a") winsA++;
    else if (winner === "b") winsB++;
    return { ...s, valA, valB, max, winner };
  }) : [];

  return (
    <div className="h2h-container">
      {/* Search row */}
      <div className="h2h-search-row">
        <PlayerSearch label="Player A" players={players} selected={playerA} onSelect={setPlayerA} />
        <span className="h2h-vs">VS</span>
        <PlayerSearch label="Player B" players={players} selected={playerB} onSelect={setPlayerB} />
      </div>

      {/* Quick matchups */}
      <div className="h2h-chips">
        <span className="h2h-chips-label">Quick matchups:</span>
        {SUGGESTED_MATCHUPS.map(([a, b]) => (
          <button key={a+b} className="h2h-chip" onClick={() => loadMatchup(a, b)}>
            {a.split(" ").pop()} vs {b.split(" ").pop()}
          </button>
        ))}
      </div>

      {/* Comparison */}
      {hasComparison ? (
        <div className="h2h-result">
          {/* Header cards */}
          <div className="h2h-header">
            <div className="h2h-header-card h2h-left">
              <div className="h2h-player-name">{playerA.full_name}</div>
              <div className="h2h-player-meta">{playerA.team_abbr} · {playerA.position} · {fmtSalary(playerA.salary)}</div>
              <span className="value-badge" style={{ background: valueBadgeColor(playerA.value_classification) }}>
                {playerA.value_classification}
              </span>
            </div>
            <div className="h2h-header-card h2h-right">
              <div className="h2h-player-name">{playerB.full_name}</div>
              <div className="h2h-player-meta">{playerB.team_abbr} · {playerB.position} · {fmtSalary(playerB.salary)}</div>
              <span className="value-badge" style={{ background: valueBadgeColor(playerB.value_classification) }}>
                {playerB.value_classification}
              </span>
            </div>
          </div>

          {/* Stat rows */}
          <div className="h2h-stats">
            {statRows.map(row => {
              const pctA = (Math.abs(row.valA) / row.max) * 100;
              const pctB = (Math.abs(row.valB) / row.max) * 100;
              return (
                <div key={row.key} className="h2h-stat-row">
                  <div className={`h2h-val h2h-val-a ${row.winner === "a" ? "h2h-winner" : ""}`}>
                    {row.fmt(row.valA)}
                  </div>
                  <div className="h2h-bar-group">
                    <div className="h2h-bar h2h-bar-a">
                      <div
                        className={`h2h-bar-fill ${row.winner === "a" ? "h2h-bar-win" : ""}`}
                        style={{ width: `${pctA}%` }}
                      />
                    </div>
                    <div className="h2h-bar-label">{row.label}</div>
                    <div className="h2h-bar h2h-bar-b">
                      <div
                        className={`h2h-bar-fill ${row.winner === "b" ? "h2h-bar-win" : ""}`}
                        style={{ width: `${pctB}%` }}
                      />
                    </div>
                  </div>
                  <div className={`h2h-val h2h-val-b ${row.winner === "b" ? "h2h-winner" : ""}`}>
                    {row.fmt(row.valB)}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary */}
          <div className="h2h-summary">
            <span className={winsA > winsB ? "h2h-winner" : ""}>{playerA.full_name.split(" ").pop()}: {winsA}</span>
            <span className="h2h-summary-sep">categories won</span>
            <span className={winsB > winsA ? "h2h-winner" : ""}>{playerB.full_name.split(" ").pop()}: {winsB}</span>
          </div>
        </div>
      ) : (
        <div className="h2h-empty">
          <div className="h2h-empty-icon">1v1</div>
          <div className="h2h-empty-title">Pick two players to compare</div>
          <div className="h2h-empty-text">Search above or click a quick matchup to get started.</div>
        </div>
      )}
    </div>
  );
}
