"""
Claude-powered NBA analyst functions.
"""
import os
import anthropic

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are an expert NBA salary cap analyst with deep knowledge of the CBA,
player evaluation, and roster construction. You have access to real 2025-26 season data
provided in the user message. Be concise, specific, and cite actual numbers from the data.

IMPORTANT DATA NOTE: All salary figures are BASE SALARY from Basketball-Reference, not
official cap hits. Actual cap charges may differ due to trade bonuses, likely/unlikely
incentives, and structured deal adjustments. Factor this caveat into your analysis when
discussing cap implications."""


def _fmt_salary(n: float) -> str:
    abs_n = abs(n)
    sign = "-" if n < 0 else ""
    if abs_n >= 1_000_000:
        return f"{sign}${abs_n/1_000_000:.1f}M"
    return f"{sign}${abs_n:,.0f}"


def build_league_context(teams: list[dict], players: list[dict]) -> str:
    """Build compact context string from all teams + top players."""
    # Top 150 players by value_score
    top_players = sorted(
        [p for p in players if p.get("salary", 0) > 0],
        key=lambda p: p.get("value_score", 0),
        reverse=True
    )[:150]

    lines = ["=== TOP 150 PLAYERS BY VALUE SCORE ==="]
    lines.append("Name,Team,Pos,Salary,PTS,REB,AST,BPM,VORP,WS,USG%,Value,Classification")
    for p in top_players:
        lines.append(
            f"{p['full_name']},{p['team_abbr']},{p.get('position','')},{_fmt_salary(p['salary'])},"
            f"{p.get('points',0):.1f},{p.get('rebounds',0):.1f},{p.get('assists',0):.1f},"
            f"{p.get('bpm',0):.1f},{p.get('vorp',0):.1f},{p.get('ws',0):.1f},"
            f"{p.get('usg_pct',0):.1f},{p.get('value_score',0):.2f},{p.get('value_classification','')}"
        )

    lines.append("\n=== ALL 30 TEAMS ===")
    lines.append("Team,Record,TotalSalary,CapSpace,CapEfficiency,OverTax,OverApron")
    for t in teams:
        lines.append(
            f"{t['display_name']},{t['wins']}-{t['losses']},"
            f"{_fmt_salary(t['total_salary'])},{_fmt_salary(t['cap_space'])},"
            f"{t.get('cap_efficiency',0):.3f},"
            f"{'Yes' if t.get('over_luxury_tax') else 'No'},"
            f"{'Yes' if t.get('over_first_apron') else 'No'}"
        )

    lines.append("\n=== CAP CONSTANTS (2025-26) ===")
    lines.append("Salary Cap: $154.6M | Luxury Tax: $187.9M | First Apron: $195M | Second Apron: $207M")

    return "\n".join(lines)


def chat_with_analyst(question: str, teams: list, players: list) -> str:
    """Answer a free-form question about the league."""
    context = build_league_context(teams, players)
    message = _client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Here is the current NBA data:\n\n{context}\n\nQuestion: {question}"
        }]
    )
    return message.content[0].text


def generate_team_report(team: dict) -> str:
    """Generate a cap analysis paragraph for a specific team."""
    players = sorted(team.get("players", []), key=lambda p: p.get("salary", 0), reverse=True)

    roster_lines = []
    for p in players[:15]:
        roster_lines.append(
            f"  {p['full_name']} ({p.get('position','?')}): {_fmt_salary(p['salary'])} | "
            f"{p.get('points',0):.1f}pts {p.get('rebounds',0):.1f}reb {p.get('assists',0):.1f}ast | "
            f"BPM: {p.get('bpm',0):.1f} | VORP: {p.get('vorp',0):.1f} | "
            f"Value: {p.get('value_classification','').replace('_',' ')}"
        )

    prompt = f"""Analyze the {team['display_name']} cap situation for 2025-26.

Record: {team['wins']}-{team['losses']}
Total Payroll: {_fmt_salary(team['total_salary'])}
Cap Space: {_fmt_salary(team['cap_space'])}
Over Luxury Tax: {'Yes' if team.get('over_luxury_tax') else 'No'}
Over First Apron: {'Yes' if team.get('over_first_apron') else 'No'}
Cap Efficiency Score: {team.get('cap_efficiency', 0):.3f}

Top 15 players by salary:
{chr(10).join(roster_lines)}

Provide a concise 3-4 paragraph analysis covering: cap situation, key contracts (good/bad values),
roster construction strengths/weaknesses, and offseason flexibility."""

    message = _client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def analyze_trade(
    team_a: dict,
    players_out_a: list[dict],
    team_b: dict,
    players_out_b: list[dict],
    cap: dict,
) -> dict:
    """Analyze a proposed trade between two teams."""
    sal_a_out = sum(p.get("salary", 0) for p in players_out_a)
    sal_b_out = sum(p.get("salary", 0) for p in players_out_b)

    new_total_a = team_a["total_salary"] - sal_a_out + sal_b_out
    new_total_b = team_b["total_salary"] - sal_b_out + sal_a_out

    def player_summary(p: dict) -> str:
        return (
            f"{p['full_name']} ({p.get('position','?')}) | "
            f"Salary: {_fmt_salary(p.get('salary',0))} | "
            f"{p.get('points',0):.1f}pts {p.get('rebounds',0):.1f}reb {p.get('assists',0):.1f}ast | "
            f"BPM: {p.get('bpm',0):.1f} | VORP: {p.get('vorp',0):.1f} | WS: {p.get('ws',0):.1f} | "
            f"Value Score: {p.get('value_score',0):.1f} ({p.get('value_classification','unknown').replace('_',' ')})"
        )

    players_a_str = "\n".join(player_summary(p) for p in players_out_a) or "None"
    players_b_str = "\n".join(player_summary(p) for p in players_out_b) or "None"

    val_a_out = sum(p.get("value_score", 0) for p in players_out_a)
    val_b_out = sum(p.get("value_score", 0) for p in players_out_b)

    prompt = f"""Evaluate this proposed NBA trade.

TRADE DETAILS:
{team_a['display_name']} ({team_a['wins']}-{team_a['losses']}, Payroll: {_fmt_salary(team_a['total_salary'])})
  Sends: {players_a_str}
  Receives: {players_b_str}

{team_b['display_name']} ({team_b['wins']}-{team_b['losses']}, Payroll: {_fmt_salary(team_b['total_salary'])})
  Sends: {players_b_str}
  Receives: {players_a_str}

VALUE COMPARISON:
- {team_a['display_name']} gives up {val_a_out:.1f} total value score, receives {val_b_out:.1f} (net: {val_b_out - val_a_out:+.1f})
- {team_b['display_name']} gives up {val_b_out:.1f} total value score, receives {val_a_out:.1f} (net: {val_a_out - val_b_out:+.1f})

CAP IMPACT:
- {team_a['display_name']}: {_fmt_salary(team_a['total_salary'])} → {_fmt_salary(new_total_a)} ({_fmt_salary(new_total_a - team_a['total_salary'])})
- {team_b['display_name']}: {_fmt_salary(team_b['total_salary'])} → {_fmt_salary(new_total_b)} ({_fmt_salary(new_total_b - team_b['total_salary'])})
- Salary Cap: {_fmt_salary(cap.get('salary_cap', 0))} | Luxury Tax: {_fmt_salary(cap.get('luxury_tax_threshold', 0))}

NOTE: Salary figures shown are base salary from Basketball-Reference, not official cap hits.
Actual cap charges may differ due to trade bonuses, incentives, or structured deals.

Provide your analysis in exactly this structure:
1. **{team_a['display_name']} perspective**: What they gain and lose (on-court + cap).
2. **{team_b['display_name']} perspective**: What they gain and lose (on-court + cap).
3. **Verdict**: State ONE clear winner (or declare it even) and explain why in 1-2 sentences. Do not contradict the reasoning above."""

    message = _client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "team_a_salary_out": sal_a_out,
        "team_b_salary_out": sal_b_out,
        "team_a_new_total": new_total_a,
        "team_b_new_total": new_total_b,
        "team_a_delta": new_total_a - team_a["total_salary"],
        "team_b_delta": new_total_b - team_b["total_salary"],
        "analysis": message.content[0].text,
    }
