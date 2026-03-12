"""
Validate data/nba_2025_26.json for integrity.

Checks:
  - All 30 teams present
  - Each team has >= 13 players
  - No player with cap_hit == 0 (unless two-way)
  - Per-team salary totals in reasonable range ($100M-$250M)
  - All required fields present on every player
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "nba_2025_26.json")

REQUIRED_PLAYER_FIELDS = [
    "full_name", "team_abbr", "pos", "age", "games_played", "minutes",
    "points", "rebounds", "assists", "steals", "blocks",
    "salary", "cap_hit",
    "per", "ws", "bpm", "vorp",
]

ALL_TEAMS = {
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
    "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
    "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS",
}


def main():
    if not os.path.exists(DATA_PATH):
        print(f"FAIL: {DATA_PATH} not found")
        sys.exit(1)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = []
    warnings = []

    # ---- Meta ----
    meta = data.get("meta", {})
    if not meta.get("season"):
        errors.append("Missing meta.season")
    if not meta.get("salary_cap"):
        errors.append("Missing meta.salary_cap")

    # ---- Teams ----
    teams = data.get("teams", [])
    team_abbrs = {t["abbreviation"] for t in teams}
    if len(teams) != 30:
        errors.append(f"Expected 30 teams, found {len(teams)}")
    missing_teams = ALL_TEAMS - team_abbrs
    if missing_teams:
        errors.append(f"Missing teams: {missing_teams}")

    # ---- Players ----
    players = data.get("players", [])
    by_team: dict[str, list[dict]] = {}
    for p in players:
        by_team.setdefault(p["team_abbr"], []).append(p)

    for abbr in sorted(team_abbrs):
        roster = by_team.get(abbr, [])
        if len(roster) < 13:
            warnings.append(f"{abbr}: only {len(roster)} players (expected >= 13)")

        total_cap = sum(p.get("cap_hit", 0) or 0 for p in roster)
        if total_cap < 100_000_000:
            warnings.append(f"{abbr}: total cap_hit ${total_cap:,.0f} seems too low (< $100M)")
        if total_cap > 250_000_000:
            warnings.append(f"{abbr}: total cap_hit ${total_cap:,.0f} seems too high (> $250M)")

    for p in players:
        for field in REQUIRED_PLAYER_FIELDS:
            if field not in p:
                errors.append(f"{p.get('full_name','?')}: missing field '{field}'")

        cap_hit = p.get("cap_hit", 0) or 0
        if cap_hit == 0 and (p.get("salary", 0) or 0) > 0:
            warnings.append(f"{p['full_name']} ({p['team_abbr']}): cap_hit is 0 but salary is {p['salary']}")

    # ---- Report ----
    print(f"Teams:   {len(teams)}")
    print(f"Players: {len(players)}")
    print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  [X] {e}")
    else:
        print("No errors.")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  [!] {w}")
    else:
        print("No warnings.")

    print()
    if errors:
        print("RESULT: FAIL")
        sys.exit(1)
    else:
        print("RESULT: PASS")


if __name__ == "__main__":
    main()
