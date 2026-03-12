import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { FitScoredPlayer, PositionalNeed, CapOutlookYear, DraftCapitalSummary } from "../api";
import { fmtSalary } from "../utils";

interface Props {
  teamId: string;
  onPlayerClick?: (name: string) => void;
}

const PRIORITY_COLOR: Record<string, string> = {
  HIGH: "#ef4444",
  MED: "#f59e0b",
  LOW: "#22c55e",
};

function FitScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, score);
  const color = pct >= 70 ? "#22c55e" : pct >= 50 ? "#f59e0b" : "#94a3b8";
  return (
    <div className="advisor-fit-bar-wrap">
      <div className="advisor-fit-bar-track">
        <div className="advisor-fit-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="advisor-fit-bar-label">{score.toFixed(0)}</span>
    </div>
  );
}

function NeedRow({ need }: { need: PositionalNeed }) {
  const maxBpm = 6;
  const teamPct = Math.max(0, Math.min(100, ((need.team_bpm + maxBpm) / (2 * maxBpm)) * 100));
  const leaguePct = Math.max(0, Math.min(100, ((need.league_avg_bpm + maxBpm) / (2 * maxBpm)) * 100));

  return (
    <div className="advisor-need-row">
      <span className="advisor-need-pos">{need.position}</span>
      <div className="advisor-need-bars">
        <div className="advisor-need-bar-group">
          <div className="advisor-need-bar-track">
            <div
              className="advisor-need-bar-fill advisor-need-bar-team"
              style={{ width: `${teamPct}%` }}
            />
            <div
              className="advisor-need-bar-fill advisor-need-bar-league"
              style={{ width: `${leaguePct}%` }}
            />
          </div>
          <div className="advisor-need-values">
            <span>Team: {need.team_bpm.toFixed(1)}</span>
            <span>Lg Avg: {need.league_avg_bpm.toFixed(1)}</span>
          </div>
        </div>
      </div>
      <span
        className="advisor-need-badge"
        style={{ background: PRIORITY_COLOR[need.priority] }}
      >
        {need.priority}
      </span>
    </div>
  );
}

const AVAIL_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  available: { bg: "#dcfce7", color: "#166534", label: "Available" },
  unlikely: { bg: "#fef9c3", color: "#854d0e", label: "Unlikely" },
  untouchable: { bg: "#fee2e2", color: "#991b1b", label: "Untouchable" },
  ntc_blocked: { bg: "#fee2e2", color: "#991b1b", label: "NTC" },
};

const CTX_STYLE: Record<string, { bg: string; color: string }> = {
  contender: { bg: "#dbeafe", color: "#1e40af" },
  fringe: { bg: "#fef9c3", color: "#854d0e" },
  rebuilder: { bg: "#fce7f3", color: "#9d174d" },
  neutral: { bg: "#f1f5f9", color: "#64748b" },
};

function TargetCard({
  player,
  rank,
  type,
  onPlayerClick,
}: {
  player: FitScoredPlayer;
  rank: number;
  type: "fa" | "trade";
  onPlayerClick?: (name: string) => void;
}) {
  const avail = player.availability ?? "available";
  const availInfo = AVAIL_STYLE[avail] ?? AVAIL_STYLE.available;
  const ctx = player.source_team_context ?? "";
  const ctxInfo = CTX_STYLE[ctx];
  const tradeWarnings = player.trade_validity?.warnings ?? [];
  const srcNeeds = player.source_team_needs ?? [];

  return (
    <div className="advisor-target-card">
      <div className="advisor-target-rank">#{rank}</div>
      <div className="advisor-target-info">
        <div className="advisor-target-name-row">
          {onPlayerClick ? (
            <button className="clickable-name" onClick={() => onPlayerClick(player.full_name)}>
              {player.full_name}
            </button>
          ) : (
            <span className="advisor-target-name">{player.full_name}</span>
          )}
          <span
            className="advisor-availability-badge"
            style={{ background: availInfo.bg, color: availInfo.color }}
            title={player.availability_reason ?? ""}
          >
            {availInfo.label}
          </span>
          <span className="advisor-target-meta">
            {player.position} | {player.team_abbr}
            {ctxInfo && (
              <span
                className="advisor-context-chip"
                style={{ background: ctxInfo.bg, color: ctxInfo.color }}
              >
                {ctx.charAt(0).toUpperCase() + ctx.slice(1)}
              </span>
            )}
            {" "}| Age {player.age}
          </span>
        </div>
        <div className="advisor-target-stats">
          <span>{player.points.toFixed(1)} pts</span>
          <span>{player.rebounds.toFixed(1)} reb</span>
          <span>{player.assists.toFixed(1)} ast</span>
          <span>BPM {player.bpm.toFixed(1)}</span>
        </div>
        <div className="advisor-target-salary-row">
          <span className="advisor-target-salary">{fmtSalary(player.salary)}</span>
          {type === "fa" && <span className="advisor-target-tag advisor-tag-fa">Expiring</span>}
          {type === "trade" && <span className="advisor-target-tag advisor-tag-trade">Trade Target</span>}
          {player.has_ntc && <span className="advisor-target-tag" style={{ background: "#fee2e2", color: "#991b1b" }}>NTC</span>}
        </div>
        {type === "trade" && srcNeeds.length > 0 && (
          <div className="advisor-mutual-needs">
            {player.team_abbr} needs: {srcNeeds.join(", ")}
          </div>
        )}
        {tradeWarnings.length > 0 && (
          <div className="advisor-trade-warning">
            {tradeWarnings.map((w, i) => <div key={i}>{w}</div>)}
          </div>
        )}
      </div>
      <div className="advisor-target-score">
        <FitScoreBar score={player.fit_score} />
        <div className="advisor-fit-breakdown">
          <span title="Positional need">N:{player.fit_breakdown.need_bonus.toFixed(0)}</span>
          <span title="Value efficiency">V:{player.fit_breakdown.value_efficiency.toFixed(0)}</span>
          <span title="Age curve">A:{player.fit_breakdown.age_curve.toFixed(0)}</span>
          <span title="Cap feasibility">C:{player.fit_breakdown.cap_feasibility.toFixed(0)}</span>
          <span title="Mutual need">M:{(player.fit_breakdown.mutual_need ?? 0).toFixed(0)}</span>
        </div>
      </div>
    </div>
  );
}

function DraftAssetsSection({ capital }: { capital: DraftCapitalSummary }) {
  return (
    <div className="advisor-draft-section">
      <div className="advisor-draft-summary">
        <span>{capital.total_picks} picks</span>
        <span>{capital.first_round} 1st round</span>
        <span>{capital.second_round} 2nd round</span>
        <span>{capital.acquired_picks} acquired</span>
        <span>~{fmtSalary(capital.total_estimated_value)} est. value</span>
      </div>
      <div className="advisor-draft-list">
        {capital.picks.map((pick) => (
          <div key={`${pick.year}-${pick.round}-${pick.original_team}`} className="advisor-draft-pick">
            <span className="advisor-draft-pick-label">{pick.label}</span>
            <span className="advisor-draft-pick-value">~{fmtSalary(pick.estimated_value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function OutlookGrid({ outlook }: { outlook: CapOutlookYear[] }) {
  return (
    <div className="advisor-outlook-grid">
      {outlook.map((yr) => (
        <div key={yr.season} className="advisor-outlook-col">
          <div className="advisor-outlook-header">{yr.season}</div>
          <div className="advisor-outlook-body">
            <div className="advisor-outlook-stat">
              <span className="advisor-outlook-label">Committed</span>
              <span className="advisor-outlook-value">{fmtSalary(yr.committed_salary)}</span>
            </div>
            <div className="advisor-outlook-stat">
              <span className="advisor-outlook-label">Proj. Cap</span>
              <span className="advisor-outlook-value">{fmtSalary(yr.projected_cap)}</span>
            </div>
            <div className="advisor-outlook-stat">
              <span className="advisor-outlook-label">Proj. Space</span>
              <span className="advisor-outlook-value" style={{ color: yr.projected_space > 0 ? "#22c55e" : "#ef4444" }}>
                {fmtSalary(yr.projected_space)}
              </span>
            </div>
            <div className="advisor-outlook-stat">
              <span className="advisor-outlook-label">Players</span>
              <span className="advisor-outlook-value">{yr.committed_players}</span>
            </div>
            <div className="advisor-outlook-contracts">
              {yr.biggest_contracts.slice(0, 3).map((c) => (
                <div key={c.full_name} className="advisor-outlook-contract-row">
                  <span>{c.full_name}</span>
                  <span>{fmtSalary(c.salary)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function RosterAdvisor({ teamId, onPlayerClick }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["team-advisor", teamId],
    queryFn: () => api.getTeamAdvisor(teamId),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="loading">
        Analyzing roster... this may take a moment
      </div>
    );
  }
  if (error || !data) {
    return <div className="error">Failed to load roster analysis</div>;
  }

  const { roster_analysis: ra, fa_targets, trade_targets, cap_outlook, ai_summary, draft_capital } = data;

  return (
    <div className="advisor-container">
      {/* Cap Situation */}
      <div className="advisor-section">
        <h3 className="advisor-section-title">Cap Situation</h3>
        <div className="detail-stats-row">
          <div className="stat-box">
            <div className="stat-box-label">Cap Space</div>
            <div className="stat-box-value">{fmtSalary(ra.cap_space)}</div>
          </div>
          <div className="stat-box">
            <div className="stat-box-label">Tax Bill</div>
            <div className="stat-box-value">{fmtSalary(ra.tax_bill)}</div>
          </div>
          <div className="stat-box">
            <div className="stat-box-label">Expiring Salary</div>
            <div className="stat-box-value">{fmtSalary(ra.expiring_salary)}</div>
          </div>
          <div className="stat-box">
            <div className="stat-box-label">Expiring Players</div>
            <div className="stat-box-value">{ra.expiring_count}</div>
          </div>
        </div>
      </div>

      {/* Positional Needs */}
      <div className="advisor-section">
        <h3 className="advisor-section-title">Positional Needs</h3>
        <div className="advisor-need-legend">
          <span><span className="advisor-need-dot" style={{ background: "#3b82f6" }} /> Team BPM</span>
          <span><span className="advisor-need-dot" style={{ background: "#94a3b8" }} /> League Avg</span>
        </div>
        {ra.positional_needs.map((n) => (
          <NeedRow key={n.position} need={n} />
        ))}
      </div>

      {/* FA Targets */}
      {fa_targets.length > 0 && (
        <div className="advisor-section">
          <h3 className="advisor-section-title">Free Agent Targets</h3>
          <p className="advisor-section-subtitle">Top expiring-contract players ranked by team fit</p>
          {fa_targets.map((p, i) => (
            <TargetCard key={p.full_name} player={p} rank={i + 1} type="fa" onPlayerClick={onPlayerClick} />
          ))}
        </div>
      )}

      {/* Trade Targets */}
      {trade_targets.length > 0 && (
        <div className="advisor-section">
          <h3 className="advisor-section-title">Trade Targets</h3>
          <p className="advisor-section-subtitle">Under-contract players where salary matching is feasible</p>
          {trade_targets.map((p, i) => (
            <TargetCard key={p.full_name} player={p} rank={i + 1} type="trade" onPlayerClick={onPlayerClick} />
          ))}
        </div>
      )}

      {/* Cap Outlook */}
      <div className="advisor-section">
        <h3 className="advisor-section-title">3-Year Cap Outlook</h3>
        <OutlookGrid outlook={cap_outlook} />
      </div>

      {/* Draft Assets */}
      {draft_capital && draft_capital.total_picks > 0 && (
        <div className="advisor-section">
          <h3 className="advisor-section-title">Draft Assets</h3>
          <DraftAssetsSection capital={draft_capital} />
        </div>
      )}

      {/* AI Summary */}
      {ai_summary && (
        <div className="advisor-section">
          <div className="ai-report-card">
            <h3>AI Roster Advisor</h3>
            <p>{ai_summary}</p>
          </div>
        </div>
      )}
    </div>
  );
}
