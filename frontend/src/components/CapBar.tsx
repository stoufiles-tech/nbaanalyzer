import { fmtSalary } from "../utils";
import type { CapConstants, Team } from "../api";

interface Props {
  team: Team;
  cap: CapConstants;
}

export default function CapBar({ team, cap }: Props) {
  const max = cap.second_apron * 1.05;
  const pct = (v: number) => `${Math.min((v / max) * 100, 100).toFixed(2)}%`;

  const markers = [
    { label: "Cap", value: cap.salary_cap, color: "#22c55e" },
    { label: "Tax", value: cap.luxury_tax_threshold, color: "#f97316" },
    { label: "Apron 1", value: cap.first_apron, color: "#ef4444" },
    { label: "Apron 2", value: cap.second_apron, color: "#7c3aed" },
  ];

  return (
    <div className="cap-bar-container">
      <div className="cap-bar-track">
        {/* Filled portion */}
        <div
          className="cap-bar-fill"
          style={{
            width: pct(team.total_salary),
            background: team.over_first_apron
              ? "#ef4444"
              : team.over_luxury_tax
              ? "#f97316"
              : team.over_cap
              ? "#eab308"
              : "#3b82f6",
          }}
        />
        {/* Threshold markers */}
        {markers.map((m) => (
          <div
            key={m.label}
            className="cap-marker"
            style={{ left: pct(m.value), borderColor: m.color }}
            title={`${m.label}: ${fmtSalary(m.value)}`}
          >
            <span className="cap-marker-label" style={{ color: m.color }}>
              {m.label}
            </span>
          </div>
        ))}
      </div>
      <div className="cap-bar-labels">
        <span>{fmtSalary(0)}</span>
        <span style={{ marginLeft: pct(team.total_salary) }}>
          {fmtSalary(team.total_salary)}
        </span>
      </div>
    </div>
  );
}
