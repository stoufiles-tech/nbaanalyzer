import axios from "axios";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export interface CapConstants {
  season: string;
  salary_cap: number;
  luxury_tax_threshold: number;
  first_apron: number;
  second_apron: number;
  data_as_of?: string;
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
  cap_hit: number | null;
  effective_salary: number;
  salary_source: string;
  has_cap_hit_override: boolean;
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

export interface TradePick {
  year: number;
  round: number;
  original_team: string;
}

export interface TradeRequest {
  team_a_id: string;
  team_b_id: string;
  players_a: string[];
  players_b: string[];
  picks_a?: TradePick[];
  picks_b?: TradePick[];
}

export interface TradeValidityResult {
  team_a_salary_valid: boolean;
  team_a_rule: string;
  team_a_warnings: string[];
  team_b_salary_valid: boolean;
  team_b_rule: string;
  team_b_warnings: string[];
  ntc_warnings: string[];
  is_valid: boolean;
}

export interface TradeResult {
  team_a_salary_out: number;
  team_b_salary_out: number;
  team_a_new_total: number;
  team_b_new_total: number;
  team_a_delta: number;
  team_b_delta: number;
  analysis: string;
  validity?: TradeValidityResult;
  picks_a_value?: number;
  picks_b_value?: number;
}

export interface DraftPickDetail {
  owner: string;
  year: number;
  round: number;
  original_team: string;
  protections: string;
  swap_rights: boolean;
  via_trade: string;
  notes: string;
  label: string;
  estimated_value: number;
}

export interface DraftCapitalSummary {
  team: string;
  total_picks: number;
  first_round: number;
  second_round: number;
  own_picks: number;
  acquired_picks: number;
  total_estimated_value: number;
  picks: DraftPickDetail[];
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

// ── Team History ─────────────────────────────────────────────────────────────

export interface TeamHistorySeason {
  team_abbr: string;
  season: string;
  wins: number;
  losses: number;
  win_pct: number;
  conf_rank: number;
  div_rank: number;
  playoff_wins: number;
  playoff_losses: number;
}

export interface TeamHistoryResult {
  team_id: string;
  abbreviation: string;
  seasons: TeamHistorySeason[];
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

// ── Roster Advisor ──────────────────────────────────────────────────────────

export interface PositionalNeed {
  position: string;
  team_bpm: number;
  league_avg_bpm: number;
  gap: number;
  priority: "HIGH" | "MED" | "LOW";
  player_count: number;
}

export interface FitBreakdown {
  need_bonus: number;
  value_efficiency: number;
  age_curve: number;
  cap_feasibility: number;
  mutual_need: number;
}

export interface TradeValidity {
  valid: boolean;
  rule_used: string;
  max_incoming: number;
  warnings: string[];
}

export interface FitScoredPlayer {
  full_name: string;
  team_abbr: string;
  team_name: string;
  position: string;
  age: number;
  salary: number;
  salary_year2: number;
  points: number;
  rebounds: number;
  assists: number;
  bpm: number;
  vorp: number;
  ws: number;
  value_score: number;
  fit_score: number;
  fit_breakdown: FitBreakdown;
  trade_validity?: TradeValidity;
  availability?: string;
  availability_reason?: string;
  has_ntc?: boolean;
  source_team_context?: string;
  source_team_needs?: string[];
  mutual_need_score?: number;
}

export interface BiggestContract {
  full_name: string;
  salary: number;
}

export interface CapOutlookYear {
  season: string;
  committed_salary: number;
  projected_cap: number;
  projected_space: number;
  committed_players: number;
  biggest_contracts: BiggestContract[];
}

export interface RosterAnalysis {
  cap_space: number;
  total_salary: number;
  tax_bill: number;
  over_luxury_tax: boolean;
  over_first_apron: boolean;
  over_second_apron: boolean;
  is_taxpayer: boolean;
  expiring_count: number;
  expiring_salary: number;
  positional_needs: PositionalNeed[];
  biggest_contracts: {
    full_name: string;
    position: string;
    salary: number;
    salary_year2: number;
    salary_year3: number;
    years_remaining: number;
  }[];
}

export interface AdvisorResult {
  team_id: string;
  team_name: string;
  abbreviation: string;
  team_context?: string;
  roster_analysis: RosterAnalysis;
  fa_targets: FitScoredPlayer[];
  trade_targets: FitScoredPlayer[];
  cap_outlook: CapOutlookYear[];
  ai_summary: string | null;
  draft_capital?: DraftCapitalSummary;
}

export const api = {
  getCapConstants: () =>
    axios.get<CapConstants>(`${BASE}/cap-constants`).then((r) => r.data),

  getTeams: () =>
    axios.get<Team[]>(`${BASE}/teams`).then((r) => r.data),

  getTeam: (teamId: string) =>
    axios.get<Team>(`${BASE}/teams/${teamId}`).then((r) => r.data),

  getTeamHistory: (teamId: string) =>
    axios.get<TeamHistoryResult>(`${BASE}/teams/${teamId}/history`).then((r) => r.data),

  getAllPlayers: () =>
    axios.get<Player[]>(`${BASE}/players/all`).then((r) => r.data),

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

  getTeamAdvisor: (teamId: string) =>
    axios.get<AdvisorResult>(`${BASE}/teams/${teamId}/advisor`).then((r) => r.data),

  getTeamDraftPicks: (teamId: string) =>
    axios.get<DraftCapitalSummary>(`${BASE}/teams/${teamId}/draft-picks`).then((r) => r.data),
};
