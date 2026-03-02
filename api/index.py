import sys
import os

# Ensure helper modules in this directory are importable
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from typing import Optional  # noqa: E402
import service  # noqa: E402
import data_client  # noqa: E402
import metrics  # noqa: E402
import ai  # noqa: E402
import db  # noqa: E402
import comparables as comparables_engine  # noqa: E402

app = FastAPI(title="NBA Salary Cap Analyzer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/cap-constants")
async def cap_constants():
    return data_client.get_cap_constants()


@app.get("/api/teams")
async def get_teams():
    teams = await service.get_all_teams()
    return [{k: v for k, v in t.items() if k != "players"} for t in teams]


@app.get("/api/teams/{team_id}")
async def get_team(team_id: str):
    if service._is_stale():
        await service.get_all_teams()
    team = service.get_team_by_id(team_id)
    if not team:
        raise HTTPException(404, f"Team {team_id} not found")
    return team


@app.post("/api/refresh")
async def refresh():
    await service._refresh()
    return {"message": "Data refreshed"}


@app.get("/api/players/{player_name}/comparables")
async def get_player_comparables(player_name: str, limit: int = 8):
    """Find contract comparables and fair market value estimate for a player."""
    if service._is_stale():
        await service.get_all_teams()
    all_players = [p for t in service._teams for p in t.get("players", [])]
    if not all_players:
        raise HTTPException(503, "Player data not yet loaded.")
    limit = max(3, min(limit, 20))
    result = comparables_engine.find_comparables(player_name, all_players, limit)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.get("/api/players/top-value")
async def top_value(limit: int = 100):
    if service._is_stale():
        await service.get_all_teams()
    return service.get_top_value_players(limit)


@app.get("/api/debug")
async def debug():
    import asyncio, traceback
    results = {}

    async def test(name, fn):
        try:
            loop = asyncio.get_event_loop()
            out = await asyncio.wait_for(loop.run_in_executor(None, fn), timeout=90)
            count = len(out) if isinstance(out, (list, dict)) else "ok"
            results[name] = f"ok ({count})"
        except Exception as e:
            results[name] = f"error: {traceback.format_exc()[-300:]}"

    if db.db_exists():
        results["db_status"] = "ok (using SQLite DB)"
        results["db_teams"]   = f"ok ({len(db.load_teams())})"
        results["db_players"] = f"ok ({len(db.load_players())})"
    else:
        await test("standings",     data_client._fetch_bbref_standings_sync)
        await test("player_stats",  data_client._fetch_bbref_player_stats_sync)
        await test("advanced_stats",data_client._fetch_bbref_advanced_sync)
    return results


# ── AI endpoints ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str


class TradeRequest(BaseModel):
    team_a_id: str
    team_b_id: str
    players_a: list[str]  # full_name list
    players_b: list[str]


@app.post("/api/chat")
async def chat(req: ChatRequest):
    teams = await service.get_all_teams()
    all_players = [p for t in teams for p in t.get("players", [])]
    response = ai.chat_with_analyst(req.question, teams, all_players)
    return {"response": response}


@app.get("/api/teams/{team_id}/report")
async def team_report(team_id: str):
    if service._is_stale():
        await service.get_all_teams()
    team = service.get_team_by_id(team_id)
    if not team:
        raise HTTPException(404, f"Team {team_id} not found")
    report = ai.generate_team_report(team)
    return {"report": report}


@app.post("/api/trade")
async def trade_analysis(req: TradeRequest):
    teams = await service.get_all_teams()

    team_a = next((t for t in teams if t["espn_id"] == req.team_a_id), None)
    team_b = next((t for t in teams if t["espn_id"] == req.team_b_id), None)

    if not team_a:
        raise HTTPException(404, f"Team A ({req.team_a_id}) not found")
    if not team_b:
        raise HTTPException(404, f"Team B ({req.team_b_id}) not found")

    def find_players(team: dict, names: list[str]) -> list[dict]:
        roster = {p["full_name"]: p for p in team.get("players", [])}
        return [roster[n] for n in names if n in roster]

    players_a = find_players(team_a, req.players_a)
    players_b = find_players(team_b, req.players_b)
    cap = data_client.get_cap_constants()

    result = ai.analyze_trade(team_a, players_a, team_b, players_b, cap)
    return result


# ── Cap Projection engine ─────────────────────────────────────────────────────

class SimPlayer(BaseModel):
    full_name: str
    salary_year1: float
    salary_year2: float = 0.0
    salary_year3: float = 0.0


class ProjectionRequest(BaseModel):
    sign: list[SimPlayer] = []
    release: list[str] = []  # full_names of current players to remove


SEASONS = ["2025-26", "2026-27", "2027-28"]
SAL_FIELDS = ["salary", "salary_year2", "salary_year3"]


@app.post("/api/teams/{team_id}/project")
async def project_team(team_id: str, req: ProjectionRequest):
    """
    Simulate a free-agent signing and/or player release and return a
    3-year cap projection for the team.
    """
    if service._is_stale():
        await service.get_all_teams()
    team = service.get_team_by_id(team_id)
    if not team:
        raise HTTPException(404, f"Team {team_id} not found")

    released = set(req.release)
    current_players = [p for p in team.get("players", []) if p["full_name"] not in released]
    cap = data_client.get_cap_constants()
    is_repeater = team.get("is_repeater", False)

    years: dict[str, dict] = {}
    for i, season in enumerate(SEASONS):
        sal_key = SAL_FIELDS[i]
        year_players = []

        for p in current_players:
            sal = p.get(sal_key, 0) or 0
            if sal > 0:
                year_players.append({
                    "full_name": p["full_name"],
                    "position":  p.get("position", ""),
                    "salary":    sal,
                    "is_new":    False,
                })

        sim_sal_attrs = ["salary_year1", "salary_year2", "salary_year3"]
        for sp in req.sign:
            sal = getattr(sp, sim_sal_attrs[i])
            if sal > 0:
                year_players.append({
                    "full_name": sp.full_name,
                    "position":  "FA",
                    "salary":    sal,
                    "is_new":    True,
                })

        year_players.sort(key=lambda p: p["salary"], reverse=True)
        total_salary = sum(p["salary"] for p in year_players)
        tax_info = metrics.calc_luxury_tax(total_salary, cap["luxury_tax_threshold"], is_repeater)

        years[season] = {
            "players":            year_players,
            "total_salary":       total_salary,
            "cap_space":          max(0.0, cap["salary_cap"] - total_salary),
            "over_cap":           total_salary > cap["salary_cap"],
            "over_luxury_tax":    total_salary > cap["luxury_tax_threshold"],
            "over_first_apron":   total_salary > cap["first_apron"],
            "over_second_apron":  total_salary > cap["second_apron"],
            "tax_bill":           tax_info["tax_bill"],
            "tax_amount_over":    tax_info["amount_over"],
            "tax_effective_rate": tax_info["effective_rate"],
            "is_taxpayer":        tax_info["is_taxpayer"],
            "bracket_breakdown":  tax_info["bracket_breakdown"],
            "player_count":       len(year_players),
        }

    return {
        "team_id":      team_id,
        "team_name":    team["display_name"],
        "abbreviation": team["abbreviation"],
        "is_repeater":  is_repeater,
        "cap_constants": cap,
        "simulation": {
            "signed":   [s.model_dump() for s in req.sign],
            "released": list(released),
        },
        "years": years,
    }


# ── Salary / DB CRUD endpoints ────────────────────────────────────────────────

class SalaryUpdate(BaseModel):
    salary: float
    salary_year2: Optional[float] = None
    salary_year3: Optional[float] = None
    salary_year4: Optional[float] = None


class PlayerCreate(BaseModel):
    full_name: str
    team_abbr: str
    pos: Optional[str] = ""
    age: Optional[float] = 0
    salary: Optional[float] = 0
    salary_year2: Optional[float] = 0
    salary_year3: Optional[float] = 0
    salary_year4: Optional[float] = 0


@app.get("/api/db/status")
async def db_status():
    """Check whether the SQLite DB exists and how many rows it has."""
    if not db.db_exists():
        return {"seeded": False, "db_path": db.DB_PATH}
    teams   = db.load_teams()
    players = db.load_players()
    timestamps = [p.get("updated_at", "") for p in players] + \
                 [t.get("updated_at", "") for t in teams]
    last_updated = max((t for t in timestamps if t), default="unknown")
    return {
        "seeded":       True,
        "teams":        len(teams),
        "players":      len(players),
        "last_updated": last_updated,
        "db_path":      db.DB_PATH,
    }


@app.get("/api/db/players")
async def list_db_players(team: Optional[str] = None, q: Optional[str] = None):
    """List all players stored in the SQLite DB.
    Optional filters: ?team=BOS  or  ?q=lebron
    """
    if not db.db_exists():
        raise HTTPException(503, "Database not seeded yet. Run scripts/fetch_and_seed.py locally.")
    players = db.load_players()
    if team:
        players = [p for p in players if p.get("team_abbr", "").upper() == team.upper()]
    if q:
        ql = q.lower()
        players = [p for p in players if ql in p.get("full_name", "").lower()]
    return players


@app.get("/api/db/players/{player_id}")
async def get_db_player(player_id: int):
    if not db.db_exists():
        raise HTTPException(503, "Database not seeded yet.")
    player = db.get_player_by_id(player_id)
    if not player:
        raise HTTPException(404, f"Player {player_id} not found")
    return player


@app.patch("/api/db/players/{player_id}/salary")
async def update_salary(player_id: int, req: SalaryUpdate):
    """Update salary fields for a player. Invalidates the in-memory cache."""
    if not db.db_exists():
        raise HTTPException(503, "Database not seeded yet.")
    updated = db.update_player_salary(
        player_id,
        req.salary,
        req.salary_year2,
        req.salary_year3,
        req.salary_year4,
    )
    if not updated:
        raise HTTPException(404, f"Player {player_id} not found")
    service._cached_at = None
    return {"message": "Salary updated", "player_id": player_id, "salary": req.salary}


@app.post("/api/db/players", status_code=201)
async def create_player(req: PlayerCreate):
    """Manually add a player (two-way / G League / missing players)."""
    player = {
        "full_name":    req.full_name,
        "norm_name":    data_client._normalize_name(req.full_name),
        "team_abbr":    req.team_abbr.upper(),
        "pos":          req.pos or "",
        "age":          req.age or 0,
        "salary":       req.salary or 0,
        "salary_year2": req.salary_year2 or 0,
        "salary_year3": req.salary_year3 or 0,
        "salary_year4": req.salary_year4 or 0,
    }
    db.init_db()
    new_id = db.insert_player(player)
    service._cached_at = None
    return {"message": "Player created", "player_id": new_id}


@app.delete("/api/db/players/{player_id}")
async def delete_player(player_id: int):
    """Remove a player from the DB."""
    if not db.db_exists():
        raise HTTPException(503, "Database not seeded yet.")
    deleted = db.delete_player(player_id)
    if not deleted:
        raise HTTPException(404, f"Player {player_id} not found")
    service._cached_at = None
    return {"message": "Player deleted", "player_id": player_id}
