"""
In-memory cache layer (replaces SQLite — works on Vercel serverless).
"""
from datetime import datetime, timedelta
from . import espn_client, metrics

CACHE_TTL = timedelta(hours=6)

# Module-level cache — persists across warm requests on the same function instance
_teams: list[dict] = []
_players: list[dict] = []  # flat list across all teams
_cached_at: datetime | None = None


def _is_stale() -> bool:
    if _cached_at is None:
        return True
    return datetime.utcnow() - _cached_at > CACHE_TTL


async def get_all_teams() -> list[dict]:
    """Return cached teams, refreshing if stale."""
    if not _is_stale() and _teams:
        return _teams
    return await _refresh()


async def _refresh() -> list[dict]:
    global _teams, _players, _cached_at

    raw_teams, raw_stats, salaries = await espn_client.fetch_all_data()
    players_merged = espn_client.merge_player_data(raw_stats, salaries)

    # Group players by team abbreviation
    by_team: dict[str, list[dict]] = {}
    for p in players_merged:
        by_team.setdefault(p["team_abbr"], []).append(p)

    cap = espn_client.get_cap_constants()
    all_players: list[dict] = []
    teams_out: list[dict] = []

    for t in raw_teams:
        abbr = t["abbreviation"]
        team_players_raw = by_team.get(abbr, [])
        team_players = []

        for p in team_players_raw:
            pts  = p["points"];  reb = p["rebounds"]
            ast  = p["assists"]; stl = p["steals"]
            blk  = p["blocks"];  fga = p["fga"]
            fta  = p["fta"];     min_ = p["minutes"]
            gp   = p["games_played"]; salary = p["salary"]

            ts      = metrics.calc_true_shooting(pts, fga, fta)
            per_est = metrics.calc_per_estimate(pts, reb, ast, stl, blk, min_, gp)
            val     = metrics.calc_value_score(pts, reb, ast, stl, blk, ts, salary, min_, gp)
            val_cls = metrics.classify_player_value(val, salary)
            contract = metrics.get_contract_status(salary, cap["salary_cap"])

            player = {
                "espn_id":           p["nba_id"],
                "full_name":         p["full_name"],
                "position":          "",
                "team_abbr":         abbr,
                "salary":            salary,
                "age":               int(p.get("age") or 0),
                "points":            pts,
                "rebounds":          reb,
                "assists":           ast,
                "steals":            stl,
                "blocks":            blk,
                "minutes":           min_,
                "games_played":      gp,
                "field_goal_pct":    p["field_goal_pct"],
                "three_point_pct":   p["three_point_pct"],
                "free_throw_pct":    p["free_throw_pct"],
                "true_shooting_pct": ts,
                "per":               per_est,
                "value_score":       val,
                "value_classification": val_cls,
                "contract_status":   contract,
            }
            team_players.append(player)
            all_players.append(player)

        total_salary = sum(p["salary"] for p in team_players)
        salary_cap   = cap["salary_cap"]

        teams_out.append({
            **t,
            "total_salary":    total_salary,
            "cap_space":       max(0.0, salary_cap - total_salary),
            "over_cap":        total_salary > salary_cap,
            "over_luxury_tax": total_salary > cap["luxury_tax_threshold"],
            "over_first_apron":total_salary > cap["first_apron"],
            "wins_per_dollar": metrics.calc_wins_per_dollar(t["wins"], total_salary),
            "cap_efficiency":  metrics.calc_cap_efficiency(t["wins"], salary_cap, total_salary),
            "player_count":    len(team_players),
            "players":         team_players,
        })

    _teams = teams_out
    _players = all_players
    _cached_at = datetime.utcnow()
    return _teams


def get_team_by_id(espn_id: str) -> dict | None:
    return next((t for t in _teams if t["espn_id"] == espn_id), None)


def get_top_value_players(limit: int = 20) -> list[dict]:
    eligible = [p for p in _players if p["salary"] > 0 and p["value_score"] > 0]
    return sorted(eligible, key=lambda p: p["value_score"], reverse=True)[:limit]
