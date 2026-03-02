"""
Contract comparables engine.
Computes multi-dimensional player similarity using weighted normalized stats,
then estimates Fair Market Value from the salary distribution of top comps.
"""
from __future__ import annotations
import math
import re

# ── Feature weights (must sum to 1.0) ────────────────────────────────────────
WEIGHTS: dict[str, float] = {
    "bpm":      0.22,
    "ws":       0.18,
    "points":   0.16,
    "usg_pct":  0.14,
    "assists":  0.12,
    "rebounds": 0.08,
    "steals":   0.05,
    "blocks":   0.05,
}

# ── Position ordering for adjacency bonus ────────────────────────────────────
_POS_ORDER: dict[str, int] = {
    "PG": 0, "SG": 1, "SF": 2, "PF": 3, "C": 4,
}

# ── Qualifying thresholds ────────────────────────────────────────────────────
MIN_GAMES   = 20
MIN_MINUTES = 15.0

LEAGUE_MINIMUM = 1_160_094  # 2025-26 rookie minimum salary


def _normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z ]", "", name)
    return re.sub(r"\s+", " ", name)


def _primary_pos(pos: str) -> str:
    """Return the first position listed (handles 'PG-SG', 'SF', etc.)."""
    if not pos:
        return ""
    return re.split(r"[-/,]", pos.strip())[0].upper()


def _pos_bonus(pos_a: str, pos_b: str) -> float:
    """
    Additive bonus/penalty based on positional proximity.
    Same: +0.08, adjacent: +0.04, two apart: 0.0, three+ apart: -0.04
    """
    a = _POS_ORDER.get(pos_a, -1)
    b = _POS_ORDER.get(pos_b, -1)
    if a == -1 or b == -1:
        return 0.0  # unknown position — neutral
    dist = abs(a - b)
    if dist == 0: return  0.08
    if dist == 1: return  0.04
    if dist == 2: return  0.00
    return -0.04


def _age_multiplier(age_target: float, age_comp: float) -> float:
    """
    Multiplicative penalty for age gap.
    4% reduction per year of difference, capped at 8 years (max 32% penalty).
    """
    gap = min(abs(age_target - age_comp), 8)
    return 1.0 - 0.04 * gap


def _compute_ranges(players: list[dict]) -> dict[str, tuple[float, float]]:
    ranges: dict[str, tuple[float, float]] = {}
    for feat in WEIGHTS:
        vals = [p.get(feat, 0.0) or 0.0 for p in players]
        lo, hi = min(vals), max(vals)
        ranges[feat] = (lo, hi if hi > lo else lo + 1e-9)
    return ranges


def _normalize_vec(player: dict, ranges: dict[str, tuple[float, float]]) -> dict[str, float]:
    return {
        feat: ((player.get(feat, 0.0) or 0.0) - lo) / (hi - lo)
        for feat, (lo, hi) in ranges.items()
    }


def _euclidean_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """
    Weighted Euclidean distance → similarity score in (0, 1].
    similarity = 1 / (1 + weighted_distance)
    """
    dist_sq = sum(
        WEIGHTS[feat] * (vec_a[feat] - vec_b[feat]) ** 2
        for feat in WEIGHTS
    )
    return 1.0 / (1.0 + math.sqrt(dist_sq))


def _fmv_from_comps(comps: list[dict]) -> float | None:
    """
    Similarity-weighted average salary, trimming outliers when N >= 6.
    Returns None if no comps have salary data.
    """
    salaried = [c for c in comps if (c.get("salary") or 0) > 0]
    if not salaried:
        return None

    # Trim highest + lowest salary when enough comps exist
    if len(salaried) >= 6:
        salaried = sorted(salaried, key=lambda c: c["salary"])[1:-1]

    total_w = sum(c["similarity"] for c in salaried)
    if total_w == 0:
        return None

    fmv = sum(c["salary"] * c["similarity"] for c in salaried) / total_w
    return max(fmv, float(LEAGUE_MINIMUM))


def find_comparables(
    target_name: str,
    all_players: list[dict],
    limit: int = 8,
) -> dict:
    """
    Find the most statistically similar players to `target_name` and estimate
    their fair market contract value.

    Returns dict with keys:
      target, comparables, fair_market_value, current_salary,
      pct_diff, verdict, low_sample, comp_count
    """
    # ── 1. Locate target player ───────────────────────────────────────────────
    target = next(
        (p for p in all_players if p["full_name"].lower() == target_name.lower()),
        None,
    )
    if target is None:
        target_norm = _normalize_name(target_name)
        target = next(
            (p for p in all_players
             if target_norm in _normalize_name(p["full_name"])
             or _normalize_name(p["full_name"]) in target_norm),
            None,
        )
    if target is None:
        return {"error": f"Player '{target_name}' not found", "comparables": []}

    # ── 2. Build eligible pool ────────────────────────────────────────────────
    pool = [
        p for p in all_players
        if p["full_name"] != target["full_name"]
        and (p.get("games_played") or 0) >= MIN_GAMES
        and (p.get("minutes") or 0.0) >= MIN_MINUTES
    ]

    # ── 3. Normalize across pool + target ────────────────────────────────────
    ranges = _compute_ranges(pool + [target])
    target_vec = _normalize_vec(target, ranges)
    target_pos = _primary_pos(target.get("position") or target.get("pos", ""))
    target_age = float(target.get("age") or 0)

    # ── 4. Score every player ─────────────────────────────────────────────────
    scored: list[dict] = []
    for p in pool:
        base_sim = _euclidean_similarity(target_vec, _normalize_vec(p, ranges))
        pos_adj  = _pos_bonus(target_pos, _primary_pos(p.get("position") or p.get("pos", "")))
        age_mult = _age_multiplier(target_age, float(p.get("age") or 0))
        final    = max(0.0, min(1.0, (base_sim + pos_adj) * age_mult))
        scored.append({**p, "similarity": round(final, 4)})

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    top = scored[:limit]

    # ── 5. FMV + verdict ─────────────────────────────────────────────────────
    fmv           = _fmv_from_comps(top)
    current_sal   = float(target.get("salary") or 0)
    salaried_cnt  = sum(1 for c in top if (c.get("salary") or 0) > 0)
    low_sample    = salaried_cnt < 3

    if current_sal <= 0:
        pct_diff, verdict = None, "No active contract"
    elif fmv is None or fmv <= 0:
        pct_diff, verdict = None, "Insufficient comp data"
    else:
        pct_diff  = (current_sal - fmv) / fmv
        abs_pct   = abs(pct_diff) * 100
        if abs_pct < 5.0:
            verdict = "Fairly priced"
        elif pct_diff > 0:
            verdict = f"Overpaid by ~{abs_pct:.0f}%"
        else:
            verdict = f"Underpaid by ~{abs_pct:.0f}%"

    # ── 6. Clean output ───────────────────────────────────────────────────────
    COMP_KEYS = [
        "full_name", "position", "team_abbr", "age",
        "points", "rebounds", "assists", "steals", "blocks",
        "minutes", "games_played", "salary",
        "bpm", "ws", "usg_pct", "similarity",
    ]
    comparables_out = [{k: c.get(k) for k in COMP_KEYS} for c in top]

    return {
        "target": {
            "full_name": target["full_name"],
            "position":  target.get("position") or target.get("pos", ""),
            "team_abbr": target.get("team_abbr", ""),
            "age":       target_age,
            "points":    target.get("points", 0),
            "rebounds":  target.get("rebounds", 0),
            "assists":   target.get("assists", 0),
            "bpm":       target.get("bpm", 0),
            "ws":        target.get("ws", 0),
            "salary":    current_sal,
            "usg_pct":   target.get("usg_pct", 0),
        },
        "comparables":       comparables_out,
        "fair_market_value": round(fmv) if fmv is not None else None,
        "current_salary":    round(current_sal),
        "pct_diff":          round(pct_diff, 4) if pct_diff is not None else None,
        "verdict":           verdict,
        "low_sample":        low_sample,
        "comp_count":        len(comparables_out),
    }
