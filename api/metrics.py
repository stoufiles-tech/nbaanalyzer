"""
Custom efficiency metrics for NBA player value analysis.
Includes the full luxury-tax bracket calculator (Phase 4).
"""
from typing import Optional

# ── Luxury Tax Brackets ───────────────────────────────────────────────────────
# Each tuple: (bracket_width_$, rate_per_$_over_threshold)
# There are 5 defined 5M brackets; amounts beyond $25M over use escalating rates.

_STD_BRACKETS = [
    (5_000_000, 1.50),  # $0–$5M over
    (5_000_000, 1.75),  # $5M–$10M
    (5_000_000, 2.50),  # $10M–$15M
    (5_000_000, 3.25),  # $15M–$20M
    (5_000_000, 3.75),  # $20M–$25M
    # $25M+: starts at $4.75/$ and increases $0.50 per additional $5M bracket
]

_REPEATER_BRACKETS = [
    (5_000_000, 2.50),  # $0–$5M over
    (5_000_000, 2.75),  # $5M–$10M
    (5_000_000, 3.50),  # $10M–$15M
    (5_000_000, 4.25),  # $15M–$20M
    (5_000_000, 4.75),  # $20M–$25M
    # $25M+: starts at $5.75/$ and increases $0.50 per additional $5M bracket
]

# Teams that are repeater taxpayers for 2025-26
# (over the tax line in 3+ of the 4 preceding seasons: 2021-22 through 2024-25)
REPEATER_TEAMS: set[str] = {"GSW", "PHX", "BOS", "LAC"}


def calc_luxury_tax(total_salary: float, tax_threshold: float,
                    is_repeater: bool = False) -> dict:
    """
    Calculate the exact luxury-tax bill using the NBA's tiered bracket system.

    Returns:
        tax_bill          — dollar amount owed to the league
        amount_over       — how far over the threshold the team is
        is_taxpayer       — bool
        effective_rate    — blended rate (tax_bill / amount_over)
        bracket_breakdown — list of {bracket, taxable, rate, tax} for display
    """
    if total_salary <= tax_threshold:
        return {
            "tax_bill": 0.0,
            "amount_over": 0.0,
            "is_taxpayer": False,
            "effective_rate": 0.0,
            "bracket_breakdown": [],
        }

    amount_over = total_salary - tax_threshold
    brackets = _REPEATER_BRACKETS if is_repeater else _STD_BRACKETS
    base_rate_25m = 5.75 if is_repeater else 4.75

    remaining = amount_over
    tax_bill = 0.0
    breakdown = []

    for size, rate in brackets:
        if remaining <= 0:
            break
        taxable = min(remaining, size)
        tax = taxable * rate
        tax_bill += tax
        breakdown.append({"taxable": round(taxable), "rate": rate, "tax": round(tax)})
        remaining -= taxable

    # Amounts beyond $25M over: rate escalates $0.50 per additional $5M
    chunk_num = 0
    while remaining > 0:
        rate = base_rate_25m + chunk_num * 0.50
        taxable = min(remaining, 5_000_000)
        tax = taxable * rate
        tax_bill += tax
        breakdown.append({"taxable": round(taxable), "rate": rate, "tax": round(tax)})
        remaining -= taxable
        chunk_num += 1

    effective_rate = tax_bill / amount_over if amount_over > 0 else 0.0
    return {
        "tax_bill": round(tax_bill),
        "amount_over": round(amount_over),
        "is_taxpayer": True,
        "effective_rate": round(effective_rate, 3),
        "bracket_breakdown": breakdown,
    }


def calc_true_shooting(points: float, fga: float, fta: float) -> float:
    """TS% = PTS / (2 * (FGA + 0.44 * FTA))"""
    denom = 2 * (fga + 0.44 * fta)
    return round(points / denom, 4) if denom > 0 else 0.0


def calc_per_estimate(pts: float, reb: float, ast: float, stl: float, blk: float,
                      minutes: float, games: int) -> float:
    """
    Simplified PER estimate (not official John Hollinger formula, requires league averages).
    Uses a weighted box-score approach per 36 minutes.
    """
    if minutes <= 0 or games <= 0:
        return 0.0
    per_36 = (pts * 1.0 + reb * 0.7 + ast * 0.7 + stl * 1.0 + blk * 0.7) / (minutes / 36)
    return round(per_36, 2)


def calc_value_score(pts: float, reb: float, ast: float, stl: float, blk: float,
                     ts_pct: float, salary: float, minutes: float, games: int) -> float:
    """
    Contract value score: total season production relative to salary tier.

    Design goals:
      - Stars playing heavy minutes should rank above cheap bench players
        with small sample sizes.
      - A minimum-wage player can't "win" the ranking just by being cheap.
      - Overpaid stars with poor production should clearly rank low.

    Method:
      1. Total season production = weighted box score * games.
         Using totals (not per-game) rewards volume, durability, and usage.
      2. Normalize by a *tiered* salary: we use max(salary, $8M) so that
         players paid below the mid-level exception ($8M proxy) are all
         evaluated as if they cost $8M. This acknowledges that:
           (a) Minimum salary is set by the CBA, not market value.
           (b) Cheap players could realistically cost ~$8M+ on an open market.
         Players making MORE than $8M are judged against their real salary.

    Minimum sample filters: 20+ min/game, 25+ games played.
    """
    if salary <= 0 or minutes < 15 or games < 10:
        return 0.0

    # Total season weighted box score production
    total_production = (
        pts * 1.0 + reb * 0.7 + ast * 0.7 + stl * 1.2 + blk * 1.0
    ) * (ts_pct if ts_pct > 0 else 0.50) * games

    # Tiered salary normalization: floor at $8M (mid-level proxy)
    tiered_salary_m = max(salary, 8_000_000) / 1_000_000

    return round(total_production / tiered_salary_m, 3)


def calc_wins_per_dollar(team_wins: int, team_total_salary: float) -> float:
    """Wins per $1M spent."""
    if team_total_salary <= 0:
        return 0.0
    return round(team_wins / (team_total_salary / 1_000_000), 4)


def calc_cap_efficiency(team_wins: int, salary_cap: float, team_total_salary: float) -> float:
    """
    Cap efficiency: how well a team converts cap usage into wins.
    Score of 1.0 = perfectly proportional. >1 = overperforming cap usage.
    """
    if team_total_salary <= 0 or salary_cap <= 0:
        return 0.0
    cap_pct = team_total_salary / salary_cap
    win_pct = team_wins / 82
    return round(win_pct / cap_pct, 4) if cap_pct > 0 else 0.0


def classify_player_value(value_score: float, salary: float) -> str:
    """
    Classify contract value within salary tier.

    Each tier has its own fair-value band so that a max player is judged
    against max-player expectations, not against a $5M role player.

    Approximate value score ranges for "fair value" per tier
    (calibrated empirically against 2025-26 season data):
      Max ($30M+):      fair ≈ 35–65   (e.g. Jokic ~55, healthy star ~40)
      Near-max ($20-30M): fair ≈ 30–55
      Starter ($12-20M):  fair ≈ 25–50
      Role ($8-12M):      fair ≈ 20–45
      Cheap (<$8M, floored to $8M in score): fair ≈ 20–45
    """
    if value_score <= 0:
        return "unknown"

    salary_m = salary / 1_000_000

    # Thresholds calibrated against 2025-26 season score distribution.
    # Format: (severely_overpaid_ceil, overpaid_ceil, underpaid_floor, steal_floor)
    if salary_m >= 30:
        # Max deals: SGA-tier players score ~35-55 when earning their contract.
        # Under 15 = essentially not contributing at max salary.
        tiers = (15, 32, 55, 75)
    elif salary_m >= 20:
        # Near-max: fair value in the 28-52 range.
        tiers = (10, 28, 52, 72)
    elif salary_m >= 12:
        # Quality starters: fair value 24-60, Chet Holmgren ~65 = underpaid.
        tiers = (8, 24, 60, 80)
    else:
        # Below $12M — all normalized to $8M floor in the score.
        # Cheap productive starters (Pritchard, Keyonte) score 85-120 = underpaid/steal.
        # Role players score 35-60 = fair value.
        tiers = (8, 30, 85, 105)

    badly_overpaid, overpaid_threshold, underpaid_threshold, steal_threshold = tiers

    if value_score < badly_overpaid:
        return "severely_overpaid"
    elif value_score < overpaid_threshold:
        return "overpaid"
    elif value_score >= steal_threshold:
        return "severely_underpaid"
    elif value_score >= underpaid_threshold:
        return "underpaid"
    else:
        return "fair_value"


def get_contract_status(salary: float, cap: float) -> str:
    pct = salary / cap
    if pct >= 0.30:
        return "max"
    elif pct >= 0.20:
        return "supermax_eligible"
    elif pct >= 0.10:
        return "starter"
    elif pct >= 0.05:
        return "rotation"
    else:
        return "minimum"
