export const fmtSalary = (n: number): string => {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
};

export const fmtPct = (n: number): string => `${(n * 100).toFixed(1)}%`;

export const valueColor = (cls: string): string => {
  const map: Record<string, string> = {
    severely_underpaid: "#22c55e",
    underpaid: "#86efac",
    fair_value: "#94a3b8",
    overpaid: "#fca5a5",
    severely_overpaid: "#ef4444",
    unknown: "#64748b",
  };
  return map[cls] ?? "#64748b";
};

export const valueLabel = (cls: string): string => {
  const map: Record<string, string> = {
    severely_underpaid: "Severely Underpaid",
    underpaid: "Underpaid",
    fair_value: "Fair Value",
    overpaid: "Overpaid",
    severely_overpaid: "Severely Overpaid",
    unknown: "Unknown",
  };
  return map[cls] ?? cls;
};

export const capStatusColor = (team: { over_luxury_tax: boolean; over_first_apron: boolean; over_cap: boolean }): string => {
  if (team.over_first_apron) return "#ef4444";
  if (team.over_luxury_tax) return "#f97316";
  if (team.over_cap) return "#eab308";
  return "#22c55e";
};

export const capStatusLabel = (team: { over_luxury_tax: boolean; over_first_apron: boolean; over_cap: boolean }): string => {
  if (team.over_first_apron) return "Over Apron";
  if (team.over_luxury_tax) return "Luxury Tax";
  if (team.over_cap) return "Over Cap";
  return "Under Cap";
};
