"""
Daily NBA Trades & Free Agency Research Script

Searches the web for recent NBA transactions (trades, signings, waivers,
two-way deals) and updates data/nba_2025_26.json accordingly.

Designed to be run by Cowork's scheduled task system.
"""

import json
import os
import sys
from datetime import datetime

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "nba_2025_26.json",
)

CHANGELOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "transactions_log.json",
)


def load_data():
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def save_data(data):
    data["meta"]["data_as_of"] = datetime.now().strftime("%Y-%m-%d")
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[OK] Saved updated data to {DATA_PATH}")


def load_changelog():
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r") as f:
            return json.load(f)
    return {"transactions": []}


def save_changelog(log):
    with open(CHANGELOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def apply_trade(data, player_name, from_team, to_team):
    """Move a player from one team to another in the dataset."""
    norm = player_name.strip().lower()
    for p in data["players"]:
        if p["norm_name"] == norm and p["team_abbr"] == from_team:
            p["team_abbr"] = to_team
            print(f"  Traded: {player_name} from {from_team} → {to_team}")
            return True
    # Try partial match
    for p in data["players"]:
        if norm in p["norm_name"] and p["team_abbr"] == from_team:
            p["team_abbr"] = to_team
            print(f"  Traded (fuzzy): {p['full_name']} from {from_team} → {to_team}")
            return True
    print(f"  [WARN] Could not find {player_name} on {from_team}")
    return False


def apply_signing(data, player_name, team, salary=0):
    """Add a new player (free agent signing) to the dataset."""
    norm = player_name.strip().lower()
    # Check if already exists
    for p in data["players"]:
        if p["norm_name"] == norm:
            p["team_abbr"] = team
            if salary:
                p["salary"] = salary
                p["cap_hit"] = salary
            print(f"  Signed (updated existing): {player_name} → {team}")
            return True
    # Add new entry
    data["players"].append({
        "full_name": player_name,
        "norm_name": norm,
        "team_abbr": team,
        "pos": "??",
        "age": 0,
        "games_played": 0, "minutes": 0, "points": 0,
        "rebounds": 0, "assists": 0, "steals": 0, "blocks": 0,
        "fga": 0, "fta": 0,
        "field_goal_pct": 0, "three_point_pct": 0, "free_throw_pct": 0,
        "tov_per_g": 0,
        "salary": salary, "cap_hit": salary,
        "salary_year2": 0, "salary_year3": 0, "salary_year4": 0,
        "per": 0, "usg_pct": 0, "ws": 0, "ws_per_48": 0,
        "bpm": 0, "obpm": 0, "dbpm": 0, "vorp": 0, "ows": 0, "dws": 0,
    })
    print(f"  Signed (new): {player_name} → {team}")
    return True


def apply_waiver(data, player_name, team):
    """Mark a player as waived (set team to FA)."""
    norm = player_name.strip().lower()
    for p in data["players"]:
        if p["norm_name"] == norm and p["team_abbr"] == team:
            p["team_abbr"] = "FA"
            print(f"  Waived: {player_name} from {team}")
            return True
    print(f"  [WARN] Could not find {player_name} on {team} for waiver")
    return False


def apply_transactions(data, transactions):
    """Apply a list of transaction dicts to the data."""
    changelog = load_changelog()
    applied = 0
    for tx in transactions:
        tx_type = tx.get("type", "").lower()
        if tx_type == "trade":
            if apply_trade(data, tx["player"], tx["from"], tx["to"]):
                applied += 1
        elif tx_type == "signing":
            if apply_signing(data, tx["player"], tx["team"], tx.get("salary", 0)):
                applied += 1
        elif tx_type == "waiver":
            if apply_waiver(data, tx["player"], tx["team"]):
                applied += 1
        tx["applied_at"] = datetime.now().isoformat()
        changelog["transactions"].append(tx)
    save_changelog(changelog)
    return applied


if __name__ == "__main__":
    # When run directly, this is a utility. The actual web research
    # is done by the Cowork scheduled task which calls WebSearch,
    # parses results, builds transaction dicts, and calls this module.
    print("NBA Trades & Free Agency Updater")
    print(f"Data file: {DATA_PATH}")
    data = load_data()
    print(f"Current players: {len(data['players'])}")
    print(f"Data as of: {data['meta']['data_as_of']}")
    print("Ready for transactions. Use apply_transactions(data, [...]) programmatically.")
