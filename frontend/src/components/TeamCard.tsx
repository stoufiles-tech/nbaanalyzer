import type { Team, CapConstants } from "../api";
import { fmtSalary, capStatusColor, capStatusLabel } from "../utils";
import CapBar from "./CapBar";

interface Props {
  team: Team;
  cap: CapConstants;
  onClick: () => void;
  selected: boolean;
}

export default function TeamCard({ team, cap, onClick, selected }: Props) {
  return (
    <div
      className={`team-card ${selected ? "selected" : ""}`}
      onClick={onClick}
    >
      <div className="team-card-header">
        {team.logo_url && (
          <img src={team.logo_url} alt={team.abbreviation} className="team-logo" />
        )}
        <div>
          <div className="team-name">{team.display_name}</div>
          <div className="team-record">
            {team.wins}-{team.losses}
          </div>
        </div>
        <span
          className="cap-badge"
          style={{ background: capStatusColor(team) }}
        >
          {capStatusLabel(team)}
        </span>
      </div>

      <CapBar team={team} cap={cap} />

      <div className="team-stats-grid">
        <div className="stat-cell">
          <span className="stat-label">Total Salary</span>
          <span className="stat-value">{fmtSalary(team.total_salary)}</span>
        </div>
        <div className="stat-cell">
          <span className="stat-label">Cap Space</span>
          <span className="stat-value">{fmtSalary(team.cap_space)}</span>
        </div>
        <div className="stat-cell">
          <span className="stat-label">Tax Bill</span>
          <span className="stat-value" style={{ color: team.is_taxpayer ? "#f97316" : "#22c55e" }}>
            {team.is_taxpayer ? fmtSalary(team.tax_bill) : "—"}
          </span>
        </div>
        <div className="stat-cell">
          <span className="stat-label">Cap Eff.</span>
          <span className="stat-value">{team.cap_efficiency.toFixed(3)}</span>
        </div>
      </div>
    </div>
  );
}
