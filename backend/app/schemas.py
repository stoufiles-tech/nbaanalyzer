from pydantic import BaseModel
from typing import Optional


class PlayerOut(BaseModel):
    espn_id: str
    full_name: str
    position: str
    team_abbr: str
    salary: float
    age: int
    points: float
    rebounds: float
    assists: float
    steals: float
    blocks: float
    minutes: float
    games_played: int
    true_shooting_pct: float
    per: float
    value_score: float
    value_classification: str
    contract_status: str

    model_config = {"from_attributes": True}


class TeamOut(BaseModel):
    espn_id: str
    abbreviation: str
    display_name: str
    location: str
    nickname: str
    logo_url: str
    wins: int
    losses: int
    total_salary: float
    cap_space: float
    over_cap: bool
    over_luxury_tax: bool
    over_first_apron: bool
    wins_per_dollar: float
    cap_efficiency: float
    player_count: int

    model_config = {"from_attributes": True}


class CapConstantsOut(BaseModel):
    season: str
    salary_cap: float
    luxury_tax_threshold: float
    first_apron: float
    second_apron: float


class TeamDetailOut(TeamOut):
    players: list[PlayerOut] = []


class LeagueOverviewOut(BaseModel):
    cap_constants: CapConstantsOut
    teams: list[TeamOut]
