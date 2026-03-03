import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

interface Props {
  teamId: string;
}

export default function TeamHistory({ teamId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["teamHistory", teamId],
    queryFn: () => api.getTeamHistory(teamId),
  });

  if (isLoading) return <div className="loading">Loading history...</div>;
  if (!data || data.seasons.length === 0) return null;

  const chartData = data.seasons.map((s) => ({
    season: s.season,
    wins: s.wins,
    losses: s.losses,
    winPct: Math.round(s.win_pct * 100),
    confRank: s.conf_rank,
    playoffWins: s.playoff_wins,
  }));

  return (
    <div className="chart-card" style={{ marginTop: "1rem" }}>
      <h3>Historical Record (Last 10 Seasons)</h3>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis
            dataKey="season"
            angle={-40}
            textAnchor="end"
            tick={{ fontSize: 11, fill: "#aaa" }}
          />
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 11, fill: "#aaa" }}
            label={{ value: "Games", angle: -90, position: "insideLeft", fill: "#aaa" }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: "#aaa" }}
            label={{ value: "Win %", angle: 90, position: "insideRight", fill: "#aaa" }}
          />
          <Tooltip
            contentStyle={{ background: "#1e1e2e", border: "1px solid #444", borderRadius: 8 }}
            labelStyle={{ color: "#fff" }}
            formatter={(value: number, name: string) => {
              if (name === "winPct") return [`${value}%`, "Win %"];
              return [value, name.charAt(0).toUpperCase() + name.slice(1)];
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar yAxisId="left" dataKey="wins" fill="#22c55e" name="Wins" radius={[3, 3, 0, 0]} />
          <Bar yAxisId="left" dataKey="losses" fill="#ef4444" name="Losses" radius={[3, 3, 0, 0]} />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="winPct"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={{ r: 3 }}
            name="Win %"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
