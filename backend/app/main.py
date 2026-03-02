from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from . import service, espn_client

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
    return espn_client.get_cap_constants()


@app.get("/api/teams")
async def get_teams():
    teams = await service.get_all_teams()
    # Strip player detail for the list view to keep response size small
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


@app.get("/api/players/top-value")
async def top_value(limit: int = 20):
    if service._is_stale():
        await service.get_all_teams()
    return service.get_top_value_players(limit)
