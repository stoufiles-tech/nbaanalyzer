import sys
import os

# Ensure helper modules in this directory are importable
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402
import service  # noqa: E402
import data_client  # noqa: E402
import metrics  # noqa: E402
import ai  # noqa: E402
import advisor  # noqa: E402
import draft  # noqa: E402
import comparables as comparables_engine  # noqa: E402

app = FastAPI(title="NBA Salary Cap Analyzer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await service.start_background_scraper()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/cap-constants")
async def cap_constants():
    result = data_client.get_cap_constants()
    # Override data_as_of with live scrape timestamp if available
    last_scrape = service.get_last_scrape_at()
    if last_scrape:
        result["data_as_of"] = last_scrape.strftime("%Y-%m-%d %H:%M UTC")
    elif service._cached_at:
        result["data_as_of"] = service._cached_at.strftime("%Y-%m-%d %H:%M UTC")
    return result


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


@app.get("/api/teams/{team_id}/history")
async def get_team_history(team_id: str):
    """Return historical W-L records for a team (by ESPN ID)."""
    abbr = data_client.ESPN_ID_TO_ABBR.get(team_id)
    if not abbr:
        raise HTTPException(404, f"Unknown team id {team_id}")
    return {"team_id": team_id, "abbreviation": abbr, "seasons": []}


@app.get("/api/teams/{team_id}/draft-picks")
async def get_team_draft_picks(team_id: str):
    """Return draft pick inventory for a team."""
    abbr = data_client.ESPN_ID_TO_ABBR.get(team_id)
    if not abbr:
        raise HTTPException(404, f"Unknown team id {team_id}")
    teams = await service.get_all_teams()
    return draft.get_team_draft_capital_summary(abbr, teams)


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


@app.get("/api/players/all")
async def all_players():
    if service._is_stale():
        await service.get_all_teams()
    return service._players


@app.get("/api/players/top-value")
async def top_value(limit: int = 100):
    if service._is_stale():
        await service.get_all_teams()
    return service.get_top_value_players(limit)


@app.get("/api/debug")
async def debug():
    if service._is_stale():
        await service.get_all_teams()
    last_scrape = service.get_last_scrape_at()
    return {
        "data_source": service.get_data_source(),
        "teams": len(service._teams),
        "players": len(service._players),
        "last_scrape_at": last_scrape.isoformat() if last_scrape else None,
    }


@app.post("/api/admin/refresh-live")
async def admin_refresh_live():
    """Manual trigger for live BBRef scrape."""
    result = await service.refresh_live()
    return result


# ── AI endpoints ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str


class TradePick(BaseModel):
    year: int
    round: int
    original_team: str


class TradeRequest(BaseModel):
    team_a_id: str
    team_b_id: str
    players_a: list[str] = []  # full_name list
    players_b: list[str] = []
    picks_a: list[TradePick] = []  # picks team A sends
    picks_b: list[TradePick] = []  # picks team B sends


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


@app.get("/api/teams/{team_id}/advisor")
async def team_advisor(team_id: str):
    teams = await service.get_all_teams()
    team = service.get_team_by_id(team_id)
    if not team:
        raise HTTPException(404, f"Team {team_id} not found")
    cap = data_client.get_cap_constants()
    result = advisor.generate_recommendations(team, teams, cap)
    # AI summary (graceful fallback)
    try:
        result["ai_summary"] = ai.generate_advisor_summary(team, result)
    except Exception:
        result["ai_summary"] = None
    return result


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

    # Resolve draft picks
    picks_a_resolved = []
    for tp in req.picks_a:
        pick_data = {"year": tp.year, "round": tp.round, "original_team": tp.original_team,
                     "owner": team_a.get("abbreviation", "")}
        pick_data["label"] = draft.format_pick_label(pick_data)
        pick_data["estimated_value"] = draft.estimate_pick_value(pick_data, teams)
        picks_a_resolved.append(pick_data)

    picks_b_resolved = []
    for tp in req.picks_b:
        pick_data = {"year": tp.year, "round": tp.round, "original_team": tp.original_team,
                     "owner": team_b.get("abbreviation", "")}
        pick_data["label"] = draft.format_pick_label(pick_data)
        pick_data["estimated_value"] = draft.estimate_pick_value(pick_data, teams)
        picks_b_resolved.append(pick_data)

    picks_a_value = sum(p["estimated_value"] for p in picks_a_resolved)
    picks_b_value = sum(p["estimated_value"] for p in picks_b_resolved)

    # Pre-validate salary matching (Layer 1)
    sal_a_out = sum(p.get("salary", 0) for p in players_a)
    sal_b_out = sum(p.get("salary", 0) for p in players_b)
    validity_a = advisor.validate_salary_match(sal_b_out, team_a, cap) if sal_b_out > 0 else {"valid": True, "rule_used": "picks_only", "max_incoming": 0, "warnings": []}
    validity_b = advisor.validate_salary_match(sal_a_out, team_b, cap) if sal_a_out > 0 else {"valid": True, "rule_used": "picks_only", "max_incoming": 0, "warnings": []}

    # Check NTC
    ntc_warnings = []
    for p in players_a + players_b:
        if p["full_name"] in advisor.NTC_PLAYERS:
            ntc_warnings.append(f"{p['full_name']} has a {advisor.NTC_PLAYERS[p['full_name']]} no-trade clause")

    result = ai.analyze_trade(
        team_a, players_a, team_b, players_b, cap,
        picks_a=picks_a_resolved if picks_a_resolved else None,
        picks_b=picks_b_resolved if picks_b_resolved else None,
    )
    result["picks_a_value"] = picks_a_value
    result["picks_b_value"] = picks_b_value
    result["validity"] = {
        "team_a_salary_valid": validity_a["valid"],
        "team_a_rule": validity_a["rule_used"],
        "team_a_warnings": validity_a["warnings"],
        "team_b_salary_valid": validity_b["valid"],
        "team_b_rule": validity_b["rule_used"],
        "team_b_warnings": validity_b["warnings"],
        "ntc_warnings": ntc_warnings,
        "is_valid": validity_a["valid"] and validity_b["valid"] and len(ntc_warnings) == 0,
    }
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

