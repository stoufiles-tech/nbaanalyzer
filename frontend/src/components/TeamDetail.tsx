import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { CapConstants } from "../api";
import CapBar from "./CapBar";
import PlayerTable from "./PlayerTable";
import CapProjection from "./CapProjection";
import TeamHistory from "./TeamHistory";
import DataQualityBanner from "./DataQualityBanner";
import { fmtSalary, capStatusLabel, capStatusColor } from "../utils";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
} from "recharts";
import { valueColor } from "../utils";

interface Props {
  teamId: string;
  cap: CapConstants;
}

const POSITIONS = ["PG", "SG", "SF", "PF", "C"];
const COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#6366f1", "#14b8a6"];

type DetailTab = "overview" | "projections";

export default function TeamDetail({ teamId, cap }: Props) {
  const [report, setReport] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [detailTab, setDetailTab] = useState<DetailTab>("overview");

  const { data: team, isLoading } = useQuery({
    queryKey: ["team", teamId],
    queryFn: () => api.getTeam(teamId),
  });

  const fetchReport = async () => {
    setReportLoading(true);
    try {
      const data = await api.getTeamReport(teamId);
      setReport(data.report);
    } finally {
      setReportLoading(false);
    }
  };

  if (isLoading) return <div className="loading">Loading roster...</div>;
  if (!team) return <div className="error">Team not found</div>;

  const players = team.players ?? [];

  // Salary by player (top 10)
  const salaryData = [...players]
    .sort((a, b) => b.salary - a.salary)
    .slice(0, 12)
    .map((p) => ({ name: p.full_name.split(" ").slice(-1)[0], salary: p.salary }));

  // Value distribution pie
  const valueCounts: Record<string, number> = {};
  players.forEach((p) => {
    valueCounts[p.value_classification] = (valueCounts[p.value_classification] ?? 0) + 1;
  });
  const pieData = Object.entries(valueCounts).map(([k, v]) => ({ name: k, value: v, fill: valueColor(k) }));

  return (
    <div className="team-detail">
      {/* ── Inner tab bar ── */}
      <div className="detail-tab-bar">
        {(["overview", "projections"] as DetailTab[]).map((t) => (
          <button
            key={t}
            className={`detail-tab-btn ${detailTab === t ? "active" : ""}`}
            onClick={() => setDetailTab(t)}
          >
            {t === "overview" ? "Overview" : "Cap Projections"}
          </button>
        ))}
      </div>

      {detailTab === "projections" && team && (
        <CapProjection teamId={teamId} players={team.players ?? []} />
      )}

      {detailTab === "overview" && (<>
      <DataQualityBanner />
      <div className="team-detail-header">
        {team.logo_url && <img src={team.logo_url} alt={team.abbreviation} className="team-logo-lg" />}
        <div>
          <h2>{team.display_name}</h2>
          <div className="team-record-lg">{team.wins}-{team.losses}</div>
          <span className="cap-badge" style={{ background: capStatusColor(team) }}>
            {capStatusLabel(team)}
          </span>
        </div>
        <div className="ai-report-btn-wrap">
          <button
            className="ai-report-btn"
            onClick={fetchReport}
            disabled={reportLoading}
          >
            {reportLoading ? "Generating analysis..." : report ? "Refresh AI Report" : "AI Report"}
          </button>
        </div>
      </div>

      {report && (
        <div className="ai-report-card">
          <h3>AI Cap Analysis</h3>
          <p>{report}</p>
        </div>
      )}

      <div className="detail-stats-row">
        <div className="stat-box">
          <div className="stat-box-label">Total Payroll</div>
          <div className="stat-box-value">{fmtSalary(team.total_salary)}</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Cap Space</div>
          <div className="stat-box-value">{fmtSalary(team.cap_space)}</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Wins / $M</div>
          <div className="stat-box-value">{team.wins_per_dollar.toFixed(3)}</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Cap Efficiency</div>
          <div className="stat-box-value">{team.cap_efficiency.toFixed(3)}</div>
        </div>
        <div className="stat-box">
          <div className="stat-box-label">Roster Size</div>
          <div className="stat-box-value">{team.player_count}</div>
        </div>
      </div>

      <div className="cap-section">
        <h3>Salary Cap Usage</h3>
        <CapBar team={team} cap={cap} />
        <div className="cap-legend">
          <span style={{ color: "#22c55e" }}>Salary Cap: {fmtSalary(cap.salary_cap)}</span>
          <span style={{ color: "#f97316" }}>Luxury Tax: {fmtSalary(cap.luxury_tax_threshold)}</span>
          <span style={{ color: "#ef4444" }}>First Apron: {fmtSalary(cap.first_apron)}</span>
          <span style={{ color: "#7c3aed" }}>Second Apron: {fmtSalary(cap.second_apron)}</span>
        </div>
      </div>

      <div className="detail-charts-row">
        <div className="chart-card">
          <h3>Salary Distribution (Top 12)</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={salaryData} margin={{ top: 5, right: 10, left: 10, bottom: 40 }}>
              <XAxis dataKey="name" angle={-40} textAnchor="end" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(v) => `$${(v / 1e6).toFixed(0)}M`} />
              <Tooltip formatter={(v: number) => fmtSalary(v)} />
              <Bar dataKey="salary" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                {salaryData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Player Value Classification</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name.replace("_", " ")} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {pieData.map((d, i) => (
                  <Cell key={i} fill={d.fill} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <TeamHistory teamId={teamId} />

      <div className="roster-section">
        <h3>Full Roster</h3>
        <PlayerTable players={players} />
      </div>
      </>)} {/* end overview tab */}
    </div>
  );
}
