"""
BBRef HTML scraper — live data updates from Basketball Reference.

Uses httpx (already in requirements) + re (stdlib). No new dependencies.
Parses HTML tables using data-stat attributes. BBRef wraps some tables
in <!-- --> comments which we handle by stripping comment markers.
"""
import asyncio
import logging
import re
from typing import Optional

import httpx

from data_client import BBREF_TEAM_MAP, BBREF_NAME_TO_ABBR, _normalize_name

logger = logging.getLogger("scraper")

_BBREF_BASE = "https://www.basketball-reference.com"
_SEASON_YEAR = 2026  # NBA_2025-26 season uses 2026 on BBRef
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
_TIMEOUT = 30.0


def _strip_comments(html: str) -> str:
    """Remove HTML comment markers so commented-out tables become parseable."""
    return html.replace("<!--", "").replace("-->", "")


def _parse_rows(html: str, table_id: str) -> list[dict[str, str]]:
    """
    Extract rows from a BBRef table by id. Each <td>/<th> has a data-stat attr.
    Returns list of dicts: {data_stat_value: cell_text}.
    """
    # Find the table
    pattern = rf'<table[^>]*id="{table_id}"[^>]*>.*?</table>'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return []
    table_html = match.group(0)

    rows: list[dict[str, str]] = []
    # Find all <tr> in <tbody>, or fall back to entire table if no tbody
    tbody = re.search(r'<tbody>(.*?)</tbody>', table_html, re.DOTALL)
    search_area = tbody.group(1) if tbody else table_html

    for tr_match in re.finditer(r'<tr[^>]*>(.*?)</tr>', search_area, re.DOTALL):
        tr = tr_match.group(1)
        # Skip header/separator rows
        if 'class="thead"' in tr or 'class="over_header"' in tr or 'scope="col"' in tr:
            continue
        row: dict[str, str] = {}
        for cell in re.finditer(
            r'data-stat="([^"]+)"[^>]*>(.*?)</t[dh]>',
            tr, re.DOTALL
        ):
            stat_name = cell.group(1)
            # Strip HTML tags and clean entities
            value = re.sub(r'<[^>]+>', '', cell.group(2))
            value = value.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&mdash;', '-').strip()
            row[stat_name] = value
        if row:
            rows.append(row)
    return rows


def _safe_float(val: str, default: float = 0.0) -> float:
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default


def _safe_int(val: str, default: int = 0) -> int:
    try:
        return int(val) if val else default
    except (ValueError, TypeError):
        return default


def _resolve_team_abbr(raw: str) -> str:
    """Normalize BBRef team abbreviation to our standard."""
    raw = raw.strip().upper()
    return BBREF_TEAM_MAP.get(raw, raw)


async def scrape_standings() -> Optional[list[dict]]:
    """
    Scrape current W-L standings from BBRef.
    Returns list of {abbreviation, wins, losses}.
    """
    url = f"{_BBREF_BASE}/leagues/NBA_{_SEASON_YEAR}_standings.html"
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch standings: {e}")
        return None

    html = _strip_comments(resp.text)
    teams: dict[str, dict] = {}

    # BBRef has two tables: confs_standings_E and confs_standings_W
    for table_id in ["confs_standings_E", "confs_standings_W"]:
        rows = _parse_rows(html, table_id)
        for row in rows:
            team_name = row.get("team_name", "")
            if not team_name:
                continue
            # Clean team name (remove asterisks, seed numbers, nbsp)
            team_name = re.sub(r'\(\d+\)', '', team_name)  # remove (1), (2), etc.
            team_name = team_name.replace("*", "").strip()
            abbr = BBREF_NAME_TO_ABBR.get(team_name)
            if not abbr:
                continue
            teams[abbr] = {
                "abbreviation": abbr,
                "wins": _safe_int(row.get("wins", "0")),
                "losses": _safe_int(row.get("losses", "0")),
            }

    if not teams:
        # Try expanded standings table
        rows = _parse_rows(html, "expanded_standings")
        for row in rows:
            team_name = row.get("team_name", "")
            if not team_name:
                continue
            team_name = team_name.replace("*", "").strip()
            abbr = BBREF_NAME_TO_ABBR.get(team_name)
            if not abbr:
                continue
            teams[abbr] = {
                "abbreviation": abbr,
                "wins": _safe_int(row.get("wins", "0")),
                "losses": _safe_int(row.get("losses", "0")),
            }

    return list(teams.values()) if teams else None


async def scrape_per_game_stats() -> Optional[list[dict]]:
    """
    Scrape per-game player stats from BBRef.
    Returns list of dicts matching the shape data_client produces for stats.
    """
    url = f"{_BBREF_BASE}/leagues/NBA_{_SEASON_YEAR}_per_game.html"
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch per-game stats: {e}")
        return None

    html = _strip_comments(resp.text)
    rows = _parse_rows(html, "per_game_stats")
    if not rows:
        return None

    # Deduplicate: keep only TOT row for traded players, else last entry
    seen: dict[str, dict] = {}
    for row in rows:
        name = row.get("player", "")
        if not name:
            continue
        team_raw = row.get("team_id", "")
        # If player has TOT (total for traded players), prefer that row
        if team_raw == "TOT":
            # We'll need to figure out current team from a non-TOT row
            seen[name] = {**row, "_is_tot": True}
        elif name in seen and seen[name].get("_is_tot"):
            # This is the team-specific row after TOT — record current team
            seen[name]["_current_team"] = team_raw
        else:
            seen[name] = row

    players: list[dict] = []
    for name, row in seen.items():
        team_raw = row.get("_current_team", row.get("team_id", ""))
        team_abbr = _resolve_team_abbr(team_raw)

        players.append({
            "nba_id": name,
            "full_name": name,
            "team_abbr": team_abbr,
            "pos": row.get("pos", ""),
            "age": _safe_float(row.get("age", "0")),
            "games_played": _safe_int(row.get("g", "0")),
            "minutes": _safe_float(row.get("mp_per_g", "0")),
            "points": _safe_float(row.get("pts_per_g", "0")),
            "rebounds": _safe_float(row.get("trb_per_g", "0")),
            "assists": _safe_float(row.get("ast_per_g", "0")),
            "steals": _safe_float(row.get("stl_per_g", "0")),
            "blocks": _safe_float(row.get("blk_per_g", "0")),
            "fga": _safe_float(row.get("fga_per_g", "0")),
            "fta": _safe_float(row.get("fta_per_g", "0")),
            "field_goal_pct": _safe_float(row.get("fg_pct", "0")),
            "three_point_pct": _safe_float(row.get("fg3_pct", "0")),
            "free_throw_pct": _safe_float(row.get("ft_pct", "0")),
            "tov_per_g": _safe_float(row.get("tov_per_g", "0")),
            "cap_hit": None,
        })

    return players if players else None


async def scrape_advanced_stats() -> Optional[dict[str, dict]]:
    """
    Scrape advanced stats (BPM, VORP, WS) from BBRef.
    Returns dict keyed by normalized name.
    """
    url = f"{_BBREF_BASE}/leagues/NBA_{_SEASON_YEAR}_advanced.html"
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch advanced stats: {e}")
        return None

    html = _strip_comments(resp.text)
    rows = _parse_rows(html, "advanced_stats")
    if not rows:
        return None

    advanced: dict[str, dict] = {}
    for row in rows:
        name = row.get("player", "")
        if not name:
            continue
        team_raw = row.get("team_id", "")
        # Skip TOT rows for advanced — keep per-team
        if team_raw == "TOT":
            continue

        norm = _normalize_name(name)
        # Only keep first (or overwrite with latest team)
        advanced[norm] = {
            "per": _safe_float(row.get("per", "0")),
            "usg_pct": _safe_float(row.get("usg_pct", "0")),
            "ws": _safe_float(row.get("ws", "0")),
            "ws_per_48": _safe_float(row.get("ws_48", "0")),
            "bpm": _safe_float(row.get("bpm", "0")),
            "obpm": _safe_float(row.get("obpm", "0")),
            "dbpm": _safe_float(row.get("dbpm", "0")),
            "vorp": _safe_float(row.get("vorp", "0")),
            "ows": _safe_float(row.get("ows", "0")),
            "dws": _safe_float(row.get("dws", "0")),
        }

    return advanced if advanced else None


async def scrape_contracts() -> Optional[list[dict]]:
    """
    Scrape player contracts/salaries from BBRef contracts page.
    Returns list of dicts matching the shape data_client produces for contracts.
    """
    url = f"{_BBREF_BASE}/contracts/players.html"
    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch contracts: {e}")
        return None

    html = _strip_comments(resp.text)
    rows = _parse_rows(html, "player-contracts")
    if not rows:
        return None

    def _parse_salary(val: str) -> float:
        """Parse '$12,345,678' format to float."""
        if not val:
            return 0.0
        cleaned = val.replace("$", "").replace(",", "").strip()
        return _safe_float(cleaned)

    contracts: list[dict] = []
    for row in rows:
        name = row.get("player", "")
        if not name:
            continue
        team_raw = row.get("team_id", "")
        team_abbr = _resolve_team_abbr(team_raw)
        norm = _normalize_name(name)

        # BBRef contract columns: y1, y2, y3, y4, y5, y6
        contracts.append({
            "full_name": name,
            "norm_name": norm,
            "team_abbr": team_abbr,
            "salary": _parse_salary(row.get("y1", "")),
            "salary_year2": _parse_salary(row.get("y2", "")),
            "salary_year3": _parse_salary(row.get("y3", "")),
            "salary_year4": _parse_salary(row.get("y4", "")),
        })

    return contracts if contracts else None


async def scrape_all() -> Optional[tuple[list[dict], list[dict], dict[str, dict], list[dict]]]:
    """
    Orchestrator: scrape all four data sources with delays between requests.
    Returns (standings, per_game_stats, advanced_stats, contracts) or None on failure.
    """
    logger.info("Starting full BBRef scrape...")

    standings = await scrape_standings()
    if standings is None:
        logger.warning("Standings scrape failed")
        return None

    await asyncio.sleep(3)

    per_game = await scrape_per_game_stats()
    if per_game is None:
        logger.warning("Per-game stats scrape failed")
        return None

    await asyncio.sleep(3)

    advanced = await scrape_advanced_stats()
    if advanced is None:
        logger.warning("Advanced stats scrape failed")
        return None

    await asyncio.sleep(3)

    contracts = await scrape_contracts()
    if contracts is None:
        logger.warning("Contracts scrape failed")
        return None

    logger.info(
        f"Scrape complete: {len(standings)} teams, {len(per_game)} players, "
        f"{len(advanced)} advanced, {len(contracts)} contracts"
    )
    return standings, per_game, advanced, contracts
