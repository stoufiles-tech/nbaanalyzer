"""
Draft pick tracking and valuation module.

Loads picks from data/nba_2025_26.json, estimates dollar-equivalent values,
and provides team draft capital summaries.
"""
import json
import os
from typing import Optional

_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "nba_2025_26.json",
)


def _load_picks() -> list[dict]:
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("draft_picks", [])


def get_all_picks() -> list[dict]:
    """Return all draft picks."""
    return _load_picks()


def get_team_picks(abbr: str) -> list[dict]:
    """Return all draft picks owned by a team."""
    abbr = abbr.upper()
    return [p for p in _load_picks() if p["owner"] == abbr]


def _estimate_pick_position(original_team: str, teams: list[dict]) -> Optional[int]:
    """
    Estimate where a pick will land based on the original team's current record.
    Lower wins = higher (better) pick. Returns estimated overall pick number (1-30).
    """
    # Sort teams by wins ascending (worst teams pick first)
    sorted_teams = sorted(teams, key=lambda t: (t.get("wins", 0), -t.get("losses", 0)))
    for i, t in enumerate(sorted_teams):
        if t.get("abbreviation") == original_team:
            return i + 1  # 1-indexed
    return 15  # default to mid-round


def estimate_pick_value(pick: dict, teams: list[dict]) -> float:
    """
    Estimate the dollar-equivalent value of a draft pick.

    Heuristics:
    - R1 lottery (1-14): ~$15-30M depending on position
    - R1 mid (15-22): ~$8-15M
    - R1 late (23-30): ~$4-8M
    - R2: ~$1-3.5M
    - Future year discount: 0.85 per year out
    - Protection discount: 0.7x (protected picks are less valuable)
    """
    year = pick.get("year", 2026)
    round_num = pick.get("round", 1)
    original_team = pick.get("original_team", "")
    protections = pick.get("protections", "")
    is_swap = pick.get("swap_rights", False)

    # Estimate position
    pos = _estimate_pick_position(original_team, teams)
    if pos is None:
        pos = 15

    # Base value by round and estimated position
    if round_num == 1:
        if pos <= 5:
            base_value = 30_000_000 - (pos - 1) * 3_000_000  # $18-30M
        elif pos <= 14:
            base_value = 18_000_000 - (pos - 5) * 1_000_000  # $9-18M
        elif pos <= 22:
            base_value = 12_000_000 - (pos - 14) * 500_000   # $8-12M
        else:
            base_value = 8_000_000 - (pos - 22) * 500_000    # $4-8M
    else:
        # Round 2
        if pos <= 5:
            base_value = 3_500_000
        elif pos <= 15:
            base_value = 2_500_000
        else:
            base_value = 1_500_000

    # Swap rights are worth ~40% of a pick
    if is_swap:
        base_value *= 0.4

    # Future year discount: 0.85 per year
    years_out = max(0, year - 2026)
    future_discount = 0.85 ** years_out

    # Protection discount
    protection_discount = 1.0
    if protections:
        if "top-1" in protections:
            protection_discount = 0.95
        elif "top-4" in protections:
            protection_discount = 0.75
        elif "top-5" in protections:
            protection_discount = 0.70
        elif "top-6" in protections:
            protection_discount = 0.65
        elif "top-10" in protections:
            protection_discount = 0.50
        elif "top-14" in protections:
            protection_discount = 0.35
        else:
            protection_discount = 0.70  # generic protection

    value = base_value * future_discount * protection_discount
    return round(value)


def format_pick_label(pick: dict) -> str:
    """
    Format a human-readable pick label.
    E.g.: "2026 1st round (via HOU) [top-4 protected]"
    """
    year = pick.get("year", "")
    round_num = pick.get("round", 1)
    original_team = pick.get("original_team", "")
    owner = pick.get("owner", "")
    protections = pick.get("protections", "")
    via_trade = pick.get("via_trade", "")
    is_swap = pick.get("swap_rights", False)

    round_str = "1st round" if round_num == 1 else "2nd round"

    parts = [f"{year} {round_str}"]

    if is_swap:
        parts.append(f"(swap with {original_team})")
    elif original_team != owner:
        if via_trade:
            parts.append(f"({via_trade})")
        else:
            parts.append(f"(via {original_team})")

    if protections:
        parts.append(f"[{protections}]")

    return " ".join(parts)


def get_team_draft_capital_summary(abbr: str, teams: list[dict]) -> dict:
    """
    Full draft capital inventory for a team with estimated values.
    """
    abbr = abbr.upper()
    picks = get_team_picks(abbr)

    pick_details = []
    total_value = 0.0

    for pick in sorted(picks, key=lambda p: (p["year"], p["round"])):
        value = estimate_pick_value(pick, teams)
        total_value += value
        pick_details.append({
            **pick,
            "label": format_pick_label(pick),
            "estimated_value": value,
        })

    # Count by category
    r1_count = sum(1 for p in picks if p["round"] == 1)
    r2_count = sum(1 for p in picks if p["round"] == 2)
    own_picks = sum(1 for p in picks if p["original_team"] == abbr)
    acquired = len(picks) - own_picks

    return {
        "team": abbr,
        "total_picks": len(picks),
        "first_round": r1_count,
        "second_round": r2_count,
        "own_picks": own_picks,
        "acquired_picks": acquired,
        "total_estimated_value": round(total_value),
        "picks": pick_details,
    }
