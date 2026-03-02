import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  ScatterChart,
  Scatter,
  CartesianGrid,
  Legend,
} from "recharts";
import type { Team, CapConstants } from "../api";
import { fmtSalary, capStatusColor } from "../utils";

interface Props {
  teams: Team[];
  cap: CapConstants;
}

export default function TeamComparison({ teams, cap }: Props) {
  const sorted = [...teams].sort((a, b) => b.total_salary - a.total_salary);

  const scatterData = teams.map((t) => ({
    name: t.abbreviation,
    salary_m: t.total_salary / 1_000_000,
    wins: t.wins,
    fill: capStatusColor(t),
  }));

  const effData = [...teams]
    .sort((a, b) => b.cap_efficiency - a.cap_efficiency)
    .slice(0, 15)
    .map((t) => ({
      name: t.abbreviation,
      cap_efficiency: t.cap_efficiency,
      wins_per_dollar: t.wins_per_dollar,
      fill: capStatusColor(t),
    }));

  return (
    <div className="comparison-grid">
      {/* Salary Bar Chart */}
      <div className="chart-card">
        <h3>Team Payrolls vs Thresholds</h3>
        <ResponsiveContainer width="100%" height={340}>
          <BarChart data={sorted} margin={{ top: 10, right: 20, left: 20, bottom: 60 }}>
            <XAxis dataKey="abbreviation" angle={-45} textAnchor="end" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => `$${(v / 1e6).toFixed(0)}M`} />
            <Tooltip formatter={(v: number) => fmtSalary(v)} />
            <ReferenceLine y={cap.salary_cap} stroke="#22c55e" strokeDasharray="4 2" label={{ value: "Cap", fill: "#22c55e", fontSize: 11 }} />
            <ReferenceLine y={cap.luxury_tax_threshold} stroke="#f97316" strokeDasharray="4 2" label={{ value: "Tax", fill: "#f97316", fontSize: 11 }} />
            <ReferenceLine y={cap.first_apron} stroke="#ef4444" strokeDasharray="4 2" label={{ value: "Apron", fill: "#ef4444", fontSize: 11 }} />
            <Bar dataKey="total_salary" radius={[4, 4, 0, 0]}>
              {sorted.map((t) => (
                <Cell key={t.espn_id} fill={capStatusColor(t)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Wins vs Salary Scatter */}
      <div className="chart-card">
        <h3>Wins vs. Total Salary</h3>
        <ResponsiveContainer width="100%" height={340}>
          <ScatterChart margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              dataKey="salary_m"
              name="Salary ($M)"
              type="number"
              tickFormatter={(v) => `$${v.toFixed(0)}M`}
              label={{ value: "Total Salary ($M)", position: "insideBottom", offset: -10, fill: "#94a3b8" }}
            />
            <YAxis
              dataKey="wins"
              name="Wins"
              label={{ value: "Wins", angle: -90, position: "insideLeft", fill: "#94a3b8" }}
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ payload }) => {
                if (!payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="custom-tooltip">
                    <strong>{d.name}</strong>
                    <div>${d.salary_m.toFixed(1)}M — {d.wins} wins</div>
                  </div>
                );
              }}
            />
            <Scatter data={scatterData} fill="#3b82f6">
              {scatterData.map((d, i) => (
                <Cell key={i} fill={d.fill} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Cap Efficiency Bar */}
      <div className="chart-card full-width">
        <h3>Cap Efficiency (Top 15) — Wins per $ Spent</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={effData} margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis />
            <Tooltip formatter={(v: number) => v.toFixed(4)} />
            <Legend />
            <Bar dataKey="cap_efficiency" name="Cap Efficiency" radius={[4, 4, 0, 0]}>
              {effData.map((d, i) => (
                <Cell key={i} fill={d.fill} />
              ))}
            </Bar>
            <Bar dataKey="wins_per_dollar" name="Wins/$M" radius={[4, 4, 0, 0]} fill="#818cf8" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
