"""
One-time export: read api/nba.db and write data/nba_2025_26.json.

Produces a static JSON file with all teams and players.
cap_hit defaults to the base salary from BBRef — update manually from Spotrac.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "api", "nba.db")
OUT_PATH = os.path.join(ROOT, "data", "nba_2025_26.json")


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: {DB_PATH} not found. Run fetch_and_seed.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # ── Teams ────────────────────────────────────────────────────────────────
    teams_raw = conn.execute("SELECT * FROM teams").fetchall()
    teams = []
    for t in teams_raw:
        teams.append({
            "espn_id":      t["espn_id"],
            "abbreviation": t["abbreviation"],
            "display_name": t["display_name"],
            "location":     t["location"],
            "nickname":     t["nickname"],
            "logo_url":     t["logo_url"],
            "wins":         t["wins"],
            "losses":       t["losses"],
        })

    # ── Players ──────────────────────────────────────────────────────────────
    players_raw = conn.execute("SELECT * FROM players").fetchall()
    players = []
    for p in players_raw:
        d = dict(p)
        salary = d.get("salary", 0) or 0
        players.append({
            "full_name":       d["full_name"],
            "norm_name":       d.get("norm_name", d["full_name"].lower().strip()),
            "team_abbr":       d["team_abbr"],
            "pos":             d.get("pos", ""),
            "age":             d.get("age", 0),
            "games_played":    d.get("games_played", 0),
            "minutes":         d.get("minutes", 0),
            "points":          d.get("points", 0),
            "rebounds":        d.get("rebounds", 0),
            "assists":         d.get("assists", 0),
            "steals":          d.get("steals", 0),
            "blocks":          d.get("blocks", 0),
            "fga":             d.get("fga", 0),
            "fta":             d.get("fta", 0),
            "field_goal_pct":  d.get("field_goal_pct", 0),
            "three_point_pct": d.get("three_point_pct", 0),
            "free_throw_pct":  d.get("free_throw_pct", 0),
            "tov_per_g":       d.get("tov_per_g", 0),
            "salary":          salary,
            "cap_hit":         salary,  # default to base salary; update from Spotrac
            "salary_year2":    d.get("salary_year2", 0),
            "salary_year3":    d.get("salary_year3", 0),
            "salary_year4":    d.get("salary_year4", 0),
            "per":             d.get("per", 0),
            "usg_pct":         d.get("usg_pct", 0),
            "ws":              d.get("ws", 0),
            "ws_per_48":       d.get("ws_per_48", 0),
            "bpm":             d.get("bpm", 0),
            "obpm":            d.get("obpm", 0),
            "dbpm":            d.get("dbpm", 0),
            "vorp":            d.get("vorp", 0),
            "ows":             d.get("ows", 0),
            "dws":             d.get("dws", 0),
        })

    conn.close()

    data = {
        "meta": {
            "season": "2025-26",
            "salary_cap": 154_647_000,
            "luxury_tax_threshold": 187_931_000,
            "first_apron": 195_000_000,
            "second_apron": 207_000_000,
            "data_as_of": datetime.now().strftime("%Y-%m-%d"),
            "salary_source": "Spotrac cap hits (default: BBRef base salary)",
        },
        "teams": teams,
        "players": players,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(teams)} teams, {len(players)} players -> {OUT_PATH}")


if __name__ == "__main__":
    main()
