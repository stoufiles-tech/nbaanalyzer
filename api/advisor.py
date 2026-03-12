"""
Roster Advisor engine — analytical recommendations for roster construction.

Pure Python, no network calls. Operates on cached team/player data.
Implements 4-layer CBA validity:
  1. Salary matching (under/over cap, apron rules)
  2. Team context & availability (contender/rebuilder/fringe)
  3. Mutual need scoring (both sides benefit)
  4. No-trade clauses
"""
from __future__ import annotations

import metrics
import draft

# ── Position mapping ─────────────────────────────────────────────────────────

_POS_MAP: dict[str, str] = {
    "PG": "PG", "SG": "SG", "SF": "SF", "PF": "PF", "C": "C",
    "G": "PG", "F": "SF", "G-F": "SG", "F-G": "SF", "F-C": "PF", "C-F": "C",
}
POSITIONS = ["PG", "SG", "SF", "PF", "C"]


def _normalize_pos(pos: str) -> str:
    return _POS_MAP.get(pos.strip(), pos.split("-")[0] if "-" in pos else (pos or "SF"))


# ── Layer 4: No-Trade Clauses ────────────────────────────────────────────────

NTC_PLAYERS: dict[str, str] = {
    "LeBron James": "full",
    "Stephen Curry": "full",
    "Kevin Durant": "full",
    "Bradley Beal": "full",
    "Damian Lillard": "full",
    "Kawhi Leonard": "full",
    "Paul George": "full",
}


# ── Layer 2: Team Context Classification ─────────────────────────────────────

def classify_team_context(team: dict) -> dict:
    """Derive team archetype from record + cap position."""
    wins = team.get("wins", 0)
    losses = team.get("losses", 0)
    total = wins + losses
    win_pct = wins / total if total > 0 else 0.5

    if win_pct >= 0.600:
        label = "contender"
    elif win_pct >= 0.450:
        label = "fringe"
    elif win_pct < 0.350:
        label = "rebuilder"
    else:
        label = "neutral"

    return {
        "label": label,
        "win_pct": round(win_pct, 3),
        "wins": wins,
        "losses": losses,
        "over_luxury_tax": team.get("over_luxury_tax", False),
        "over_first_apron": team.get("over_first_apron", False),
        "over_second_apron": team.get("over_second_apron", False),
    }


def estimate_availability(player: dict, team_context: dict,
                          team_players: list[dict]) -> dict:
    """Estimate whether a player is available for trade/FA."""
    name = player.get("full_name", "")
    label = team_context.get("label", "neutral")
    age = player.get("age", 27)
    bpm = player.get("bpm", 0.0)

    # NTC check
    if name in NTC_PLAYERS:
        return {
            "availability": "ntc_blocked",
            "reason": f"Has {NTC_PLAYERS[name]} no-trade clause",
        }

    # Rank player within their team by BPM (for determining core status)
    qualified = [p for p in team_players
                 if p.get("minutes", 0) >= 15 and p.get("games_played", 0) >= 20]
    by_bpm = sorted(qualified, key=lambda p: p.get("bpm", 0), reverse=True)
    player_rank = next(
        (i for i, p in enumerate(by_bpm) if p.get("full_name") == name), len(by_bpm)
    )

    if label == "contender":
        # Top 3 players on a contender are untouchable
        if player_rank < 3:
            return {
                "availability": "untouchable",
                "reason": f"Core player on a contender (#{player_rank + 1} by BPM)",
            }
        return {
            "availability": "available",
            "reason": "Role player on contender — available in trade",
        }

    elif label == "rebuilder":
        # Young talent on rebuilders is untouchable
        if age < 24 and bpm > 0:
            return {
                "availability": "untouchable",
                "reason": f"Young asset on rebuilder (age {age}, BPM {bpm:+.1f})",
            }
        # Veterans on long contracts are available (salary dump candidates)
        if age >= 28 and player.get("salary_year2", 0):
            return {
                "availability": "available",
                "reason": "Veteran on multi-year deal — salary dump candidate",
            }
        return {
            "availability": "available",
            "reason": "Available from rebuilding team",
        }

    else:  # fringe or neutral
        # Only the franchise cornerstone (#1 by BPM) is untouchable
        if player_rank == 0:
            return {
                "availability": "unlikely",
                "reason": f"Franchise cornerstone (#{player_rank + 1} by BPM)",
            }
        return {
            "availability": "available",
            "reason": "Available from fringe/neutral team",
        }


# ── Layer 1: CBA Salary Matching ─────────────────────────────────────────────

def validate_salary_match(incoming_salary: float, team: dict, cap: dict) -> dict:
    """
    Validate CBA salary matching rules for an acquisition.

    2025-26 CBA rules:
    - Under cap: absorb up to cap_space without matching
    - Over cap, under 1st apron: send back 125% + $250K
    - Over 1st apron: send back 110% + $250K
    - Over 2nd apron: same as 1st apron + no salary aggregation (max 2 out for 1 in)
    """
    if incoming_salary <= 0:
        return {"valid": False, "rule_used": "invalid", "max_incoming": 0, "warnings": ["No salary"]}

    salary_cap = cap.get("salary_cap", 154_600_000)
    total_salary = team.get("total_salary", 0)
    cap_space = max(0, salary_cap - total_salary)
    over_cap = total_salary > salary_cap
    over_first = team.get("over_first_apron", False)
    over_second = team.get("over_second_apron", False)

    warnings: list[str] = []

    if not over_cap:
        # Under cap — can absorb up to cap space without matching
        if incoming_salary <= cap_space:
            return {
                "valid": True,
                "rule_used": "cap_space",
                "max_incoming": cap_space,
                "warnings": [],
            }
        else:
            # Need to match the overage
            overage = incoming_salary - cap_space
            return {
                "valid": True,
                "rule_used": "cap_space_partial",
                "max_incoming": cap_space,
                "warnings": [f"Exceeds cap space by {_fmt_sal(overage)} — need salary match for overage"],
            }

    if over_second:
        # Over 2nd apron: 110% + $250K, no aggregation
        max_incoming = incoming_salary * 1.10 + 250_000
        warnings.append("2nd apron: cannot aggregate salaries (max 2 players out)")
        return {
            "valid": True,
            "rule_used": "110%+250K (2nd apron)",
            "max_incoming": round(max_incoming),
            "warnings": warnings,
        }

    if over_first:
        # Over 1st apron: 110% + $250K
        max_incoming = incoming_salary * 1.10 + 250_000
        return {
            "valid": True,
            "rule_used": "110%+250K (1st apron)",
            "max_incoming": round(max_incoming),
            "warnings": warnings,
        }

    # Over cap, under 1st apron: 125% + $250K
    max_incoming = incoming_salary * 1.25 + 250_000
    return {
        "valid": True,
        "rule_used": "125%+250K",
        "max_incoming": round(max_incoming),
        "warnings": warnings,
    }


def _fmt_sal(n: float) -> str:
    if abs(n) >= 1_000_000:
        return f"${abs(n)/1_000_000:.1f}M"
    return f"${abs(n):,.0f}"


def _team_tradeable_salary(team: dict) -> float:
    """Estimate tradeable outgoing salary: non-star expiring + mid-tier contracts."""
    players = team.get("players", [])
    by_bpm = sorted(
        [p for p in players if p.get("minutes", 0) >= 15],
        key=lambda p: p.get("bpm", 0), reverse=True,
    )
    # Exclude top 2 players (stars the team wouldn't trade)
    star_names = {p["full_name"] for p in by_bpm[:2]}
    tradeable = 0.0
    for p in players:
        if p["full_name"] in star_names:
            continue
        if p.get("salary", 0) > 0:
            tradeable += p["salary"]
    return tradeable


def _can_salary_match(target_salary: float, team: dict, cap: dict) -> dict:
    """Check if team has enough tradeable salary to match the incoming player."""
    validity = validate_salary_match(target_salary, team, cap)
    if not validity["valid"]:
        return validity

    rule = validity["rule_used"]
    tradeable = _team_tradeable_salary(team)

    if rule == "cap_space":
        # No matching needed
        return validity

    if rule == "cap_space_partial":
        overage = target_salary - max(0, cap.get("salary_cap", 0) - team.get("total_salary", 0))
        if tradeable >= overage:
            return validity
        validity["warnings"].append(f"Only {_fmt_sal(tradeable)} tradeable salary for {_fmt_sal(overage)} needed")
        validity["valid"] = False
        return validity

    # Over cap: need to send back enough
    needed_outgoing = target_salary  # They need to match our incoming
    if "125%" in rule:
        needed_outgoing = target_salary / 1.25
    elif "110%" in rule:
        needed_outgoing = target_salary / 1.10

    if tradeable >= needed_outgoing:
        return validity

    validity["warnings"].append(
        f"Need {_fmt_sal(needed_outgoing)} outgoing salary, only {_fmt_sal(tradeable)} tradeable"
    )
    validity["valid"] = False
    return validity


# ── Roster Analysis ──────────────────────────────────────────────────────────

def _league_avg_bpm_by_pos(all_teams: list[dict]) -> dict[str, float]:
    """Compute league-wide average BPM per position (min 15 mpg, 20+ games)."""
    totals: dict[str, list[float]] = {p: [] for p in POSITIONS}
    for t in all_teams:
        for p in t.get("players", []):
            if p.get("minutes", 0) < 15 or p.get("games_played", 0) < 20:
                continue
            npos = _normalize_pos(p.get("position", ""))
            if npos in totals:
                totals[npos].append(p.get("bpm", 0.0))
    return {pos: (sum(v) / len(v) if v else 0.0) for pos, v in totals.items()}


def analyze_roster(team: dict, all_teams: list[dict], cap: dict) -> dict:
    """Analyze a team's roster: cap situation, positional depth, needs."""
    players = team.get("players", [])
    league_avg = _league_avg_bpm_by_pos(all_teams)

    # Positional depth: minutes-weighted avg BPM per position
    pos_minutes: dict[str, float] = {p: 0.0 for p in POSITIONS}
    pos_bpm_weighted: dict[str, float] = {p: 0.0 for p in POSITIONS}
    pos_players: dict[str, list[dict]] = {p: [] for p in POSITIONS}

    for p in players:
        npos = _normalize_pos(p.get("position", ""))
        if npos not in pos_minutes:
            continue
        mins = p.get("minutes", 0.0)
        bpm = p.get("bpm", 0.0)
        pos_minutes[npos] += mins
        pos_bpm_weighted[npos] += bpm * mins
        pos_players[npos].append(p)

    positional_depth: dict[str, dict] = {}
    positional_needs: list[dict] = []

    for pos in POSITIONS:
        avg_bpm = (pos_bpm_weighted[pos] / pos_minutes[pos]) if pos_minutes[pos] > 0 else -5.0
        lg_avg = league_avg.get(pos, 0.0)
        gap = avg_bpm - lg_avg
        if gap < -1.5:
            priority = "HIGH"
        elif gap < -0.5:
            priority = "MED"
        else:
            priority = "LOW"

        positional_depth[pos] = {
            "count": len(pos_players[pos]),
            "avg_bpm": round(avg_bpm, 2),
            "league_avg_bpm": round(lg_avg, 2),
            "gap": round(gap, 2),
        }
        positional_needs.append({
            "position": pos,
            "team_bpm": round(avg_bpm, 2),
            "league_avg_bpm": round(lg_avg, 2),
            "gap": round(gap, 2),
            "priority": priority,
            "player_count": len(pos_players[pos]),
        })

    # Expiring contracts (salary_year2 == 0 means no guaranteed money next year)
    expiring = [p for p in players if p.get("salary", 0) > 0 and (p.get("salary_year2", 0) or 0) == 0]
    expiring_salary = sum(p["salary"] for p in expiring)

    # Contract timeline: biggest commitments
    committed = [p for p in players if (p.get("salary_year2", 0) or 0) > 0]
    committed.sort(key=lambda p: p.get("salary", 0), reverse=True)
    biggest_contracts = [{
        "full_name": p["full_name"],
        "position": p.get("position", ""),
        "salary": p["salary"],
        "salary_year2": p.get("salary_year2", 0) or 0,
        "salary_year3": p.get("salary_year3", 0) or 0,
        "years_remaining": sum(1 for s in ["salary", "salary_year2", "salary_year3"] if (p.get(s, 0) or 0) > 0),
    } for p in committed[:8]]

    return {
        "cap_space": team.get("cap_space", 0),
        "total_salary": team.get("total_salary", 0),
        "tax_bill": team.get("tax_bill", 0),
        "over_luxury_tax": team.get("over_luxury_tax", False),
        "over_first_apron": team.get("over_first_apron", False),
        "over_second_apron": team.get("over_second_apron", False),
        "is_taxpayer": team.get("is_taxpayer", False),
        "expiring_count": len(expiring),
        "expiring_salary": expiring_salary,
        "positional_needs": positional_needs,
        "positional_depth": positional_depth,
        "biggest_contracts": biggest_contracts,
    }


# ── Layer 3: Mutual Need Scoring ─────────────────────────────────────────────

def _compute_needs_map(team: dict, all_teams: list[dict]) -> dict[str, str]:
    """Return {position: priority} for a team."""
    analysis = analyze_roster(team, all_teams, {})
    return {n["position"]: n["priority"] for n in analysis["positional_needs"]}


def _team_surplus_positions(team: dict, all_teams: list[dict]) -> list[str]:
    """Positions where team is at LOW need (surplus)."""
    needs = _compute_needs_map(team, all_teams)
    return [pos for pos, pri in needs.items() if pri == "LOW"]


def score_mutual_fit(player: dict, source_team: dict, dest_team: dict,
                     all_teams: list[dict]) -> dict:
    """Score how well a trade works for the source team (0-15 bonus)."""
    source_needs = _compute_needs_map(source_team, all_teams)
    dest_surplus = _team_surplus_positions(dest_team, all_teams)

    # Find highest source need that matches a dest surplus position
    best_bonus = 0.0
    matched_positions: list[str] = []

    for pos in dest_surplus:
        src_need = source_needs.get(pos, "LOW")
        if src_need == "HIGH":
            best_bonus = max(best_bonus, 15.0)
            matched_positions.append(pos)
        elif src_need == "MED":
            best_bonus = max(best_bonus, 8.0)
            matched_positions.append(pos)

    source_need_positions = [
        pos for pos, pri in source_needs.items() if pri in ("HIGH", "MED")
    ]

    return {
        "mutual_need_score": round(best_bonus, 1),
        "source_team_needs": source_need_positions,
        "matched_positions": matched_positions,
    }


# ── Player Fit Scoring ───────────────────────────────────────────────────────

def _candidate_pool(team_abbr: str, all_teams: list[dict]) -> list[dict]:
    """All players NOT on the given team, min 15 mpg and 20+ games.
    Attaches NTC, team context, and availability info."""
    pool = []
    for t in all_teams:
        if t["abbreviation"] == team_abbr:
            continue
        team_ctx = classify_team_context(t)
        team_players = t.get("players", [])
        for p in team_players:
            if p.get("minutes", 0) >= 15 and p.get("games_played", 0) >= 20 and p.get("salary", 0) > 0:
                avail = estimate_availability(p, team_ctx, team_players)
                pool.append({
                    **p,
                    "team_name": t.get("display_name", t["abbreviation"]),
                    "has_ntc": p["full_name"] in NTC_PLAYERS,
                    "source_team_context": team_ctx["label"],
                    "availability": avail["availability"],
                    "availability_reason": avail["reason"],
                    "_source_team": t,  # internal ref for mutual need
                })
    return pool


def score_player_fit(player: dict, needs: list[dict], cap_space: float,
                     value_scores: list[float], dest_team: dict,
                     all_teams: list[dict], cap: dict) -> dict:
    """Score a single player's fit for a team (0-115, normalized to 0-100 for display)."""
    npos = _normalize_pos(player.get("position", ""))

    # 1. Need bonus (0-30): how badly does the team need this position?
    need_bonus = 0.0
    for n in needs:
        if n["position"] == npos:
            if n["priority"] == "HIGH":
                need_bonus = 20.0 + min(10.0, abs(n["gap"]) * 3)
            elif n["priority"] == "MED":
                need_bonus = 10.0 + min(10.0, abs(n["gap"]) * 4)
            else:
                need_bonus = 5.0
            break

    # 2. Value efficiency (0-30): normalized value_score
    vs = player.get("value_score", 0)
    if value_scores:
        max_vs = max(value_scores) if value_scores else 1
        min_vs = min(value_scores) if value_scores else 0
        rng = max_vs - min_vs if max_vs > min_vs else 1
        value_eff = ((vs - min_vs) / rng) * 30.0
    else:
        value_eff = 0.0

    # 3. Age curve (0-20): peak 24-28
    age = player.get("age", 27)
    if 24 <= age <= 28:
        age_score = 20.0
    else:
        dist = min(abs(age - 24), abs(age - 28))
        age_score = max(0.0, 20.0 - dist * 3.0)

    # 4. Cap feasibility (0-20)
    salary = player.get("salary", 0)
    if salary <= cap_space:
        cap_score = 20.0
    elif salary <= cap_space + 13_000_000:
        cap_score = 12.0
    elif salary <= cap_space + 30_000_000:
        cap_score = 6.0
    else:
        cap_score = 2.0

    # 5. Mutual need bonus (0-15) — Layer 3
    source_team = player.get("_source_team", {})
    mutual = score_mutual_fit(player, source_team, dest_team, all_teams)
    mutual_bonus = mutual["mutual_need_score"]

    # Raw score out of 115
    raw_score = need_bonus + value_eff + age_score + cap_score + mutual_bonus

    # Availability penalty — Layer 2
    availability = player.get("availability", "available")
    if availability == "unlikely":
        raw_score = max(0, raw_score - 15)

    # Normalize 0-115 to 0-100 for display
    fit_score = round((raw_score / 115.0) * 100.0, 1)

    # Trade validity — Layer 1 (only for non-expiring / trade targets)
    is_expiring = (player.get("salary_year2", 0) or 0) == 0
    if not is_expiring:
        trade_validity = _can_salary_match(salary, dest_team, cap)
    else:
        trade_validity = {"valid": True, "rule_used": "fa_target", "max_incoming": 0, "warnings": []}

    return {
        "full_name": player["full_name"],
        "team_abbr": player.get("team_abbr", ""),
        "team_name": player.get("team_name", ""),
        "position": player.get("position", ""),
        "age": age,
        "salary": salary,
        "salary_year2": player.get("salary_year2", 0) or 0,
        "points": player.get("points", 0),
        "rebounds": player.get("rebounds", 0),
        "assists": player.get("assists", 0),
        "bpm": player.get("bpm", 0),
        "vorp": player.get("vorp", 0),
        "ws": player.get("ws", 0),
        "value_score": player.get("value_score", 0),
        "fit_score": fit_score,
        "fit_breakdown": {
            "need_bonus": round(need_bonus, 1),
            "value_efficiency": round(value_eff, 1),
            "age_curve": round(age_score, 1),
            "cap_feasibility": round(cap_score, 1),
            "mutual_need": round(mutual_bonus, 1),
        },
        # New CBA validity fields
        "trade_validity": trade_validity,
        "availability": availability,
        "availability_reason": player.get("availability_reason", ""),
        "has_ntc": player.get("has_ntc", False),
        "source_team_context": player.get("source_team_context", ""),
        "source_team_needs": mutual["source_team_needs"],
        "mutual_need_score": mutual["mutual_need_score"],
    }


def _is_expiring(player: dict) -> bool:
    return (player.get("salary_year2", 0) or 0) == 0


# ── Cap Outlook ──────────────────────────────────────────────────────────────

def _cap_outlook(team: dict, cap: dict) -> list[dict]:
    """3-year committed salary projection."""
    players = team.get("players", [])
    sal_fields = ["salary", "salary_year2", "salary_year3"]
    seasons = ["2025-26", "2026-27", "2027-28"]
    outlook = []

    for i, season in enumerate(seasons):
        field = sal_fields[i]
        committed = []
        total = 0.0
        for p in players:
            sal = p.get(field, 0) or 0
            if sal > 0:
                committed.append({
                    "full_name": p["full_name"],
                    "salary": sal,
                })
                total += sal
        committed.sort(key=lambda x: x["salary"], reverse=True)
        projected_cap = cap["salary_cap"] * (1.10 ** i)
        outlook.append({
            "season": season,
            "committed_salary": round(total),
            "projected_cap": round(projected_cap),
            "projected_space": round(max(0, projected_cap - total)),
            "committed_players": len(committed),
            "biggest_contracts": committed[:5],
        })

    return outlook


# ── Main Entry Point ─────────────────────────────────────────────────────────

def generate_recommendations(team: dict, all_teams: list[dict], cap: dict) -> dict:
    """
    Full roster advisor analysis with 4-layer CBA validity:
    positional needs, FA targets, trade targets, and 3-year cap outlook.
    """
    team_abbr = team["abbreviation"]
    roster_analysis = analyze_roster(team, all_teams, cap)

    # Build candidate pool (with NTC, context, availability pre-attached)
    pool = _candidate_pool(team_abbr, all_teams)
    value_scores = [p.get("value_score", 0) for p in pool]
    cap_space = roster_analysis["cap_space"]
    needs = roster_analysis["positional_needs"]

    # Score all players with full 4-layer logic
    scored = [
        score_player_fit(p, needs, cap_space, value_scores, team, all_teams, cap)
        for p in pool
    ]
    scored.sort(key=lambda x: x["fit_score"], reverse=True)

    # Build lookup for pool player data (expiring check, availability filter)
    pool_lookup = {p["full_name"]: p for p in pool}

    # Filter: remove untouchable and NTC-blocked from trade targets
    def _trade_eligible(s: dict) -> bool:
        if s["availability"] in ("untouchable", "ntc_blocked"):
            return False
        if not _is_expiring(pool_lookup.get(s["full_name"], {})):
            return True
        return False

    def _fa_eligible(s: dict) -> bool:
        if s["availability"] == "untouchable":
            return False
        if _is_expiring(pool_lookup.get(s["full_name"], {})):
            return True
        return False

    # Split: FA targets vs trade targets
    fa_targets = [s for s in scored if _fa_eligible(s)]

    # For trade targets: must also pass salary matching
    trade_targets = []
    for s in scored:
        if not _trade_eligible(s):
            continue
        if s["trade_validity"]["valid"]:
            trade_targets.append(s)
        if len(trade_targets) >= 5:
            break

    cap_outlook = _cap_outlook(team, cap)

    # Add team context for the requesting team
    team_context = classify_team_context(team)

    # Draft capital summary
    draft_capital = draft.get_team_draft_capital_summary(team_abbr, all_teams)

    return {
        "team_id": team.get("espn_id", ""),
        "team_name": team.get("display_name", ""),
        "abbreviation": team_abbr,
        "team_context": team_context["label"],
        "roster_analysis": roster_analysis,
        "fa_targets": fa_targets[:5],
        "trade_targets": trade_targets[:5],
        "cap_outlook": cap_outlook,
        "draft_capital": draft_capital,
    }
