#!/usr/bin/env python3
"""
Local data fetch + seed script for NBA Salary Cap Analyzer.
Run this on your machine (NOT on Railway) to populate api/nba.db.

Usage:
    cd nba-salary-cap-analyzer
    pip install nba_api
    python scripts/fetch_and_seed.py

Then deploy:
    railway up --service nba-salary-cap-api
"""
import sys
import os
import time

# Allow importing api modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import data_client
import db

try:
    from nba_api.stats.endpoints import leaguedashplayerstats, leaguestandings, teamyearbyyearstats
except ImportError:
    print("ERROR: nba_api not installed. Run:  pip install nba_api")
    sys.exit(1)

SEASON = "2025-26"
_DELAY = 1.0  # seconds between nba_api calls

# Map "TeamCity TeamName" -> abbreviation
_CITY_NAME_TO_ABBR = {
    f"{loc} {full.split()[-1]}": abbr
    for abbr, (loc, full) in data_client.TEAM_FULL.items()
}
# Also map by full display name
_DISPLAY_TO_ABBR = {
    full: abbr for abbr, (loc, full) in data_client.TEAM_FULL.items()
}


def _rows_to_dicts(endpoint_result) -> list:
    raw = endpoint_result.get_dict()
    result_set = raw["resultSets"][0]
    headers = [h.lower() for h in result_set["headers"]]
    return [dict(zip(headers, row)) for row in result_set["rowSet"]]


def fetch_nba_standings() -> list:
    print("  [nba_api] Fetching standings ...")
    resp = leaguestandings.LeagueStandings(season=SEASON, timeout=30)
    time.sleep(_DELAY)
    rows = _rows_to_dicts(resp)

    ESPN_LOGO_ABBR = data_client.ESPN_LOGO_ABBR
    TEAM_FULL = data_client.TEAM_FULL
    ESPN_ID = data_client.ESPN_ID

    teams = []
    for r in rows:
        city = r.get("teamcity", "").strip()
        name = r.get("teamname", "").strip()
        # Try to find abbreviation
        abbr = _CITY_NAME_TO_ABBR.get(f"{city} {name}") or \
               _DISPLAY_TO_ABBR.get(f"{city} {name}")
        if not abbr:
            # Fallback: scan TEAM_FULL by city
            for a, (loc, _) in TEAM_FULL.items():
                if loc.lower() == city.lower():
                    abbr = a
                    break
        if not abbr:
            continue

        wins   = int(r.get("wins") or 0)
        losses = int(r.get("losses") or 0)
        logo_key = ESPN_LOGO_ABBR.get(abbr, abbr.lower())
        loc, disp = TEAM_FULL.get(abbr, (city, f"{city} {name}"))
        teams.append({
            "espn_id":      ESPN_ID.get(abbr, abbr),
            "abbreviation": abbr,
            "display_name": disp,
            "location":     loc,
            "nickname":     name,
            "logo_url":     f"https://a.espncdn.com/i/teamlogos/nba/500/{logo_key}.png",
            "wins":         wins,
            "losses":       losses,
        })
    print(f"     -> {len(teams)} teams")
    return teams


def fetch_nba_per_game() -> list:
    print("  [nba_api] Fetching per-game stats ...")
    resp = leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON,
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base",
        timeout=60,
    )
    time.sleep(_DELAY)
    rows = _rows_to_dicts(resp)

    BBREF_TEAM_MAP = data_client.BBREF_TEAM_MAP
    out = []
    for r in rows:
        abbr_raw = r.get("team_abbreviation", "").upper()
        abbr = BBREF_TEAM_MAP.get(abbr_raw, abbr_raw)
        name = r.get("player_name", "").strip()
        if not name:
            continue
        out.append({
            "nba_id":          str(r.get("player_id", "")),
            "full_name":       name,
            "norm_name":       data_client._normalize_name(name),
            "team_abbr":       abbr,
            "pos":             "",
            "age":             float(r.get("age") or 0),
            "games_played":    int(r.get("gp") or 0),
            "minutes":         float(r.get("min") or 0),
            "points":          float(r.get("pts") or 0),
            "rebounds":        float(r.get("reb") or 0),
            "assists":         float(r.get("ast") or 0),
            "steals":          float(r.get("stl") or 0),
            "blocks":          float(r.get("blk") or 0),
            "fga":             float(r.get("fga") or 0),
            "fta":             float(r.get("fta") or 0),
            "field_goal_pct":  float(r.get("fg_pct") or 0),
            "three_point_pct": float(r.get("fg3_pct") or 0),
            "free_throw_pct":  float(r.get("ft_pct") or 0),
            "tov_per_g":       float(r.get("tov") or 0),
        })
    print(f"     -> {len(out)} players")
    return out


def fetch_nba_advanced() -> dict:
    print("  [nba_api] Fetching advanced stats (USG%) ...")
    resp = leaguedashplayerstats.LeagueDashPlayerStats(
        season=SEASON,
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Advanced",
        timeout=60,
    )
    time.sleep(_DELAY)
    rows = _rows_to_dicts(resp)
    out = {}
    for r in rows:
        name = r.get("player_name", "").strip()
        if not name:
            continue
        norm = data_client._normalize_name(name)
        if norm not in out:
            out[norm] = {"usg_pct": float(r.get("usg_pct") or 0)}
    print(f"     -> {len(out)} records")
    return out


def fetch_bbref_salaries() -> list:
    print("  [bbref] Fetching salary/contract data ...")
    rows = data_client._fetch_bbref_contracts_sync()
    print(f"     -> {len(rows)} salary records")
    return rows


def fetch_bbref_advanced() -> dict:
    print("  [bbref] Fetching WS / BPM / VORP ...")
    result = data_client._fetch_bbref_advanced_sync()
    print(f"     -> {len(result)} advanced records")
    return result


def fetch_positions() -> dict:
    print("  [bbref] Fetching player positions ...")
    rows = data_client._fetch_bbref_player_stats_sync()
    result = {data_client._normalize_name(p["full_name"]): p.get("pos", "") for p in rows}
    print(f"     -> {len(result)} position records")
    return result


def fetch_team_histories() -> list[dict]:
    """Fetch last 10 seasons of W-L records for all 30 teams via nba_api."""
    print("  [nba_api] Fetching team year-by-year histories ...")
    current_year = int(SEASON.split("-")[0])
    min_year = current_year - 10  # last 10 seasons

    records: list[dict] = []
    for abbr, team_id in data_client.NBA_TEAM_ID.items():
        try:
            resp = teamyearbyyearstats.TeamYearByYearStats(
                team_id=str(team_id),
                per_mode_simple="Totals",
                season_type_all_star="Regular Season",
                timeout=30,
            )
            time.sleep(_DELAY)
            raw = resp.get_dict()
            result_set = raw["resultSets"][0]
            headers = [h.lower() for h in result_set["headers"]]
            rows = [dict(zip(headers, row)) for row in result_set["rowSet"]]

            for r in rows:
                # season field is like "2024-25"
                season_str = str(r.get("year", ""))
                try:
                    season_year = int(season_str.split("-")[0])
                except (ValueError, IndexError):
                    continue
                if season_year < min_year:
                    continue

                wins = int(r.get("wins", 0) or 0)
                losses = int(r.get("losses", 0) or 0)
                total = wins + losses
                win_pct = round(wins / total, 3) if total > 0 else 0.0
                conf_rank = int(r.get("conf_rank", 0) or 0)
                div_rank = int(r.get("div_rank", 0) or 0)
                po_wins = int(r.get("po_wins", 0) or 0)
                po_losses = int(r.get("po_losses", 0) or 0)

                records.append({
                    "team_abbr": abbr,
                    "season": season_str,
                    "wins": wins,
                    "losses": losses,
                    "win_pct": win_pct,
                    "conf_rank": conf_rank,
                    "div_rank": div_rank,
                    "playoff_wins": po_wins,
                    "playoff_losses": po_losses,
                })
        except Exception as e:
            print(f"     WARNING: Failed to fetch history for {abbr}: {e}")
            continue

    print(f"     -> {len(records)} team_history records")
    return records


def build_player_rows(nba_stats, nba_advanced, bbref_salaries, bbref_advanced, positions) -> list:
    from collections import defaultdict

    sal_by_norm = defaultdict(list)
    for s in bbref_salaries:
        sal_by_norm[s["norm_name"]].append(s)

    _ZERO_ADV = {
        "per": 0.0, "usg_pct": 0.0, "ws": 0.0, "ws_per_48": 0.0,
        "bpm": 0.0, "obpm": 0.0, "dbpm": 0.0, "vorp": 0.0, "ows": 0.0, "dws": 0.0,
    }

    rows = []
    for p in nba_stats:
        norm = p["norm_name"]
        sal_entries = sal_by_norm.get(norm, [])

        if sal_entries:
            sal = next((s for s in sal_entries if s["team_abbr"] == p["team_abbr"]),
                       sal_entries[0])
            salary       = sal["salary"]
            salary_year2 = sal["salary_year2"]
            salary_year3 = sal["salary_year3"]
            salary_year4 = sal["salary_year4"]
        else:
            salary = salary_year2 = salary_year3 = salary_year4 = 0.0

        adv_bbref = bbref_advanced.get(norm, _ZERO_ADV)
        adv_nba   = nba_advanced.get(norm, {})

        rows.append({
            "full_name":       p["full_name"],
            "norm_name":       norm,
            "team_abbr":       p["team_abbr"],
            "pos":             positions.get(norm, ""),
            "age":             p["age"],
            "games_played":    p["games_played"],
            "minutes":         p["minutes"],
            "points":          p["points"],
            "rebounds":        p["rebounds"],
            "assists":         p["assists"],
            "steals":          p["steals"],
            "blocks":          p["blocks"],
            "fga":             p["fga"],
            "fta":             p["fta"],
            "field_goal_pct":  p["field_goal_pct"],
            "three_point_pct": p["three_point_pct"],
            "free_throw_pct":  p["free_throw_pct"],
            "tov_per_g":       p["tov_per_g"],
            "salary":          salary,
            "salary_year2":    salary_year2,
            "salary_year3":    salary_year3,
            "salary_year4":    salary_year4,
            "per":             adv_bbref.get("per", 0.0),
            "usg_pct":         adv_nba.get("usg_pct") or adv_bbref.get("usg_pct", 0.0),
            "ws":              adv_bbref.get("ws", 0.0),
            "ws_per_48":       adv_bbref.get("ws_per_48", 0.0),
            "bpm":             adv_bbref.get("bpm", 0.0),
            "obpm":            adv_bbref.get("obpm", 0.0),
            "dbpm":            adv_bbref.get("dbpm", 0.0),
            "vorp":            adv_bbref.get("vorp", 0.0),
            "ows":             adv_bbref.get("ows", 0.0),
            "dws":             adv_bbref.get("dws", 0.0),
        })

    return rows


def main():
    print("=== NBA Salary Cap Analyzer - Local Data Seed ===\n")

    print("Fetching data ...")
    teams       = fetch_nba_standings()
    nba_stats   = fetch_nba_per_game()
    nba_adv     = fetch_nba_advanced()
    bbref_sal   = fetch_bbref_salaries()
    bbref_adv   = fetch_bbref_advanced()
    positions   = fetch_positions()

    print("\nMerging data ...")
    player_rows = build_player_rows(nba_stats, nba_adv, bbref_sal, bbref_adv, positions)
    print(f"  -> {len(player_rows)} players after merge")

    print("\nFetching team histories ...")
    team_history = fetch_team_histories()

    print("\nWriting to database ...")
    db.init_db()
    db.upsert_teams(teams)
    db.upsert_players(player_rows)
    db.upsert_team_history(team_history)

    from datetime import datetime
    print(f"\nDone! {db.DB_PATH}")
    print(f"  Teams:        {len(teams)}")
    print(f"  Players:      {len(player_rows)}")
    print(f"  Team History: {len(team_history)}")
    print(f"  Seeded:  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("\nNext steps:")
    print("  railway up --service nba-salary-cap-api")


if __name__ == "__main__":
    main()
