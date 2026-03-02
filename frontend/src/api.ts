import axios from "axios";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export interface CapConstants {
  season: string;
  salary_cap: number;
  luxury_tax_threshold: number;
  first_apron: number;
  second_apron: number;
}

export interface Player {
  espn_id: string;
  full_name: string;
  position: string;
  team_abbr: string;
  salary: number;
  salary_year2: number;
  salary_year3: number;
  salary_year4: number;
  age: number;
  points: number;
  rebounds: number;
  assists: number;
  steals: number;
  blocks: number;
  minutes: number;
  games_played: number;
  true_shooting_pct: number;
  per: number;
  value_score: number;
  value_classification: string;
  contract_status: string;
  turnovers: number;
  usg_pct: number;
  ws: number;
  ws_per_48: number;
  bpm: number;
  obpm: number;
  dbpm: number;
  vorp: number;
  ows: number;
  dws: number;
}

export interface TradeRequest {
  team_a_id: string;
  team_b_id: string;
  players_a: string[];
  players_b: string[];
}

export interface TradeResult {
  team_a_salary_out: number;
  team_b_salary_out: number;
  team_a_new_total: number;
  team_b_new_total: number;
  team_a_delta: number;
  team_b_delta: number;
  analysis: string;
}

export interface Team {
  espn_id: string;
  abbreviation: string;
  display_name: string;
  location: string;
  nickname: string;
  logo_url: string;
  wins: number;
  losses: number;
  total_salary: number;
  cap_space: number;
  over_cap: boolean;
  over_luxury_tax: boolean;
  over_first_apron: boolean;
  over_second_apron: boolean;
  wins_per_dollar: number;
  cap_efficiency: number;
  player_count: number;
  is_repeater: boolean;
  tax_bill: number;
  tax_amount_over: number;
  tax_effective_rate: number;
  is_taxpayer: boolean;
  players?: Player[];
}

// ── Cap Projection (Phase 3) ──────────────────────────────────────────────────

export interface SimPlayer {
  full_name: string;
  salary_year1: number;
  salary_year2: number;
  salary_year3: number;
}

export interface ProjectionYearPlayer {
  full_name: string;
  position: string;
  salary: number;
  is_new: boolean;
}

export interface TaxBracket {
  taxable: number;
  rate: number;
  tax: number;
}

export interface ProjectionYear {
  players: ProjectionYearPlayer[];
  total_salary: number;
  cap_space: number;
  over_cap: boolean;
  over_luxury_tax: boolean;
  over_first_apron: boolean;
  over_second_apron: boolean;
  tax_bill: number;
  tax_amount_over: number;
  tax_effective_rate: number;
  is_taxpayer: boolean;
  bracket_breakdown: TaxBracket[];
  player_count: number;
}

export interface ProjectionResult {
  team_id: string;
  team_name: string;
  abbreviation: string;
  is_repeater: boolean;
  cap_constants: CapConstants;
  simulation: { signed: SimPlayer[]; released: string[] };
  years: Record<string, ProjectionYear>;
}

// ── Contract Comparables (Phase 5) ───────────────────────────────────────────

export interface ComparableTarget {
  full_name: string;
  position: string;
  team_abbr: string;
  age: number;
  points: number;
  rebounds: number;
  assists: number;
  bpm: number;
  ws: number;
  salary: number;
  usg_pct: number;
}

export interface ComparablePlayer {
  full_name: string;
  position: string;
  team_abbr: string;
  age: number;
  points: number;
  rebounds: number;
  assists: number;
  steals: number;
  blocks: number;
  minutes: number;
  games_played: number;
  salary: number;
  bpm: number;
  ws: number;
  usg_pct: number;
  similarity: number;
}

export interface ComparablesResult {
  target: ComparableTarget;
  comparables: ComparablePlayer[];
  fair_market_value: number | null;
  current_salary: number;
  pct_diff: number | null;
  verdict: string;
  low_sample: boolean;
  comp_count: number;
}

export const api = {
  getCapConstants: () =>
    axios.get<CapConstants>(`${BASE}/cap-constants`).then((r) => r.data),

  getTeams: () =>
    axios.get<Team[]>(`${BASE}/teams`).then((r) => r.data),

  getTeam: (teamId: string) =>
    axios.get<Team>(`${BASE}/teams/${teamId}`).then((r) => r.data),

  getTopValuePlayers: (limit = 20) =>
    axios.get<Player[]>(`${BASE}/players/top-value?limit=${limit}`).then((r) => r.data),

  refreshData: () =>
    axios.post(`${BASE}/refresh`).then((r) => r.data),

  chatWithAnalyst: (question: string) =>
    axios.post<{ response: string }>(`${BASE}/chat`, { question }).then((r) => r.data),

  getTeamReport: (teamId: string) =>
    axios.get<{ report: string }>(`${BASE}/teams/${teamId}/report`).then((r) => r.data),

  analyzeTrade: (body: TradeRequest) =>
    axios.post<TradeResult>(`${BASE}/trade`, body).then((r) => r.data),

  projectTeam: (teamId: string, body: { sign: SimPlayer[]; release: string[] }) =>
    axios.post<ProjectionResult>(`${BASE}/teams/${teamId}/project`, body).then((r) => r.data),

  getComparables: (playerName: string, limit = 8) =>
    axios
      .get<ComparablesResult>(
        `${BASE}/players/${encodeURIComponent(playerName)}/comparables?limit=${limit}`
      )
      .then((r) => r.data),
};
