"""
Multi-source NBA data client (pure urllib + stdlib — no pandas).

Data source priority:
  1. api/nba.db  (SQLite — populated by scripts/fetch_and_seed.py run locally)
  2. Basketball-Reference live scrape (fallback when DB not present)
"""
import re
import json
import ssl
import gzip
import urllib.request
import urllib.error
import asyncio
from concurrent.futures import ThreadPoolExecutor

SEASON = "2025-26"

SALARY_CAP           = 154_647_000
LUXURY_TAX_THRESHOLD = 187_931_000
FIRST_APRON          = 195_000_000
SECOND_APRON         = 207_000_000

_executor = ThreadPoolExecutor(max_workers=4)

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

BBREF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

ESPN_LOGO_ABBR = {
    "ATL": "atl", "BOS": "bos", "BKN": "bkn", "CHA": "cha", "CHI": "chi",
    "CLE": "cle", "DAL": "dal", "DEN": "den", "DET": "det", "GSW": "gs",
    "HOU": "hou", "IND": "ind", "LAC": "lac", "LAL": "lal", "MEM": "mem",
    "MIA": "mia", "MIL": "mil", "MIN": "min", "NOP": "no",  "NYK": "ny",
    "OKC": "okc", "ORL": "orl", "PHI": "phi", "PHX": "phx", "POR": "por",
    "SAC": "sac", "SAS": "sa",  "TOR": "tor", "UTA": "utah","WAS": "wsh",
}

TEAM_FULL = {
    "ATL": ("Atlanta",       "Atlanta Hawks"),
    "BOS": ("Boston",        "Boston Celtics"),
    "BKN": ("Brooklyn",      "Brooklyn Nets"),
    "CHA": ("Charlotte",     "Charlotte Hornets"),
    "CHI": ("Chicago",       "Chicago Bulls"),
    "CLE": ("Cleveland",     "Cleveland Cavaliers"),
    "DAL": ("Dallas",        "Dallas Mavericks"),
    "DEN": ("Denver",        "Denver Nuggets"),
    "DET": ("Detroit",       "Detroit Pistons"),
    "GSW": ("Golden State",  "Golden State Warriors"),
    "HOU": ("Houston",       "Houston Rockets"),
    "IND": ("Indiana",       "Indiana Pacers"),
    "LAC": ("LA",            "LA Clippers"),
    "LAL": ("Los Angeles",   "Los Angeles Lakers"),
    "MEM": ("Memphis",       "Memphis Grizzlies"),
    "MIA": ("Miami",         "Miami Heat"),
    "MIL": ("Milwaukee",     "Milwaukee Bucks"),
    "MIN": ("Minnesota",     "Minnesota Timberwolves"),
    "NOP": ("New Orleans",   "New Orleans Pelicans"),
    "NYK": ("New York",      "New York Knicks"),
    "OKC": ("Oklahoma City", "Oklahoma City Thunder"),
    "ORL": ("Orlando",       "Orlando Magic"),
    "PHI": ("Philadelphia",  "Philadelphia 76ers"),
    "PHX": ("Phoenix",       "Phoenix Suns"),
    "POR": ("Portland",      "Portland Trail Blazers"),
    "SAC": ("Sacramento",    "Sacramento Kings"),
    "SAS": ("San Antonio",   "San Antonio Spurs"),
    "TOR": ("Toronto",       "Toronto Raptors"),
    "UTA": ("Utah",          "Utah Jazz"),
    "WAS": ("Washington",    "Washington Wizards"),
}

BBREF_TEAM_MAP = {
    "PHO": "PHX", "GOS": "GSW", "SAN": "SAS", "NOR": "NOP",
    "BRK": "BKN", "CHO": "CHA", "WSB": "WAS", "NOH": "NOP",
}

ESPN_ID = {
    "ATL": "1",  "BOS": "2",  "BKN": "17", "CHA": "30", "CHI": "4",
    "CLE": "5",  "DAL": "6",  "DEN": "7",  "DET": "8",  "GSW": "9",
    "HOU": "10", "IND": "11", "LAC": "12", "LAL": "13", "MEM": "29",
    "MIA": "14", "MIL": "15", "MIN": "16", "NOP": "3",  "NYK": "18",
    "OKC": "25", "ORL": "19", "PHI": "20", "PHX": "21", "POR": "22",
    "SAC": "23", "SAS": "24", "TOR": "28", "UTA": "26", "WAS": "27",
}

BBREF_NAME_TO_ABBR = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM", "Miami Heat": "MIA", "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR", "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}


def _normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z ]", "", name)
    return re.sub(r"\s+", " ", name)


def _fetch_html(url: str, headers: dict, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=_ssl_ctx, timeout=timeout) as r:
        raw = r.read()
    if r.headers.get("Content-Encoding") == "gzip":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", errors="replace")


def _gstat(row: str, stat: str) -> float:
    m = re.search(r'data-stat="' + stat + r'"[^>]*csk="([\d.+-]+)"', row)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    m = re.search(r'data-stat="' + stat + r'"[^>]*>([\d.+-]+)', row)
    try:
        return float(m.group(1)) if m else 0.0
    except ValueError:
        return 0.0


def _fetch_bbref_player_stats_sync() -> list[dict]:
    url = "https://www.basketball-reference.com/leagues/NBA_2026_per_game.html"
    html = _fetch_html(url, BBREF_HEADERS, timeout=25)
    players: list[dict] = []
    seen: set[str] = set()

    for m in re.finditer(r"<tr\b([^>]*)>(.*?)</tr>", html, re.DOTALL):
        content = m.group(2)
        if 'name_display' not in content or 'pts_per_g' not in content:
            continue
        name_m = re.search(r'data-stat="name_display"[^>]*>.*?href="[^"]+">([^<]+)</a>', content, re.DOTALL)
        team_m = re.search(r'data-stat="team_name_abbr"[^>]*>(?:<a[^>]*>)?([A-Z0-9]+)', content, re.DOTALL)
        if not name_m:
            continue
        name = name_m.group(1).strip()
        team_raw = team_m.group(1).strip() if team_m else ""
        team = BBREF_TEAM_MAP.get(team_raw, team_raw)
        if team_raw in ("TOT", "2TM", "3TM", "4TM", "5TM") or name in seen:
            continue
        seen.add(name)

        pos_m = re.search(r'data-stat="pos"[^>]*>([^<]*)', content)
        pos = pos_m.group(1).strip() if pos_m else ""

        players.append({
            "nba_id":          name,
            "full_name":       name,
            "team_abbr":       team,
            "pos":             pos,
            "age":             _gstat(content, "age"),
            "games_played":    int(_gstat(content, "games") or 0),
            "minutes":         _gstat(content, "mp_per_g"),
            "points":          _gstat(content, "pts_per_g"),
            "rebounds":        _gstat(content, "trb_per_g"),
            "assists":         _gstat(content, "ast_per_g"),
            "steals":          _gstat(content, "stl_per_g"),
            "blocks":          _gstat(content, "blk_per_g"),
            "fga":             _gstat(content, "fga_per_g"),
            "fta":             _gstat(content, "fta_per_g"),
            "field_goal_pct":  _gstat(content, "fg_pct"),
            "three_point_pct": _gstat(content, "fg3_pct"),
            "free_throw_pct":  _gstat(content, "ft_pct"),
            "tov_per_g":       _gstat(content, "tov_per_g"),
        })

    return players


def _fetch_bbref_contracts_sync() -> list[dict]:
    url = "https://www.basketball-reference.com/contracts/players.html"
    html = _fetch_html(url, BBREF_HEADERS, timeout=25)
    players: list[dict] = []

    for m in re.finditer(r"<tr\b([^>]*)>(.*?)</tr>", html, re.DOTALL):
        content = m.group(2)
        name_m = re.search(r'data-stat="player"[^>]*>.*?<a[^>]*>([^<]+)</a>', content, re.DOTALL)
        team_m = re.search(r'data-stat="team_id"[^>]*>(?:<a[^>]*>)?([A-Z0-9]+)', content, re.DOTALL)
        sal_m  = re.search(r'data-stat="y1"[^>]*csk="(\d+)"', content)
        if not (name_m and sal_m):
            continue
        name   = name_m.group(1).strip()
        raw_tm = team_m.group(1).strip() if team_m else ""
        team   = BBREF_TEAM_MAP.get(raw_tm, raw_tm)
        salary = float(sal_m.group(1))
        if salary <= 0:
            continue

        def _yr(stat: str) -> float:
            mm = re.search(r'data-stat="' + stat + r'"[^>]*csk="(\d+)"', content)
            return float(mm.group(1)) if mm else 0.0

        players.append({
            "full_name":    name,
            "norm_name":    _normalize_name(name),
            "team_abbr":    team,
            "salary":       salary,
            "salary_year2": _yr("y2"),
            "salary_year3": _yr("y3"),
            "salary_year4": _yr("y4"),
        })

    return players


def _fetch_bbref_standings_sync() -> list[dict]:
    url = "https://www.basketball-reference.com/leagues/NBA_2026_standings.html"
    html = _fetch_html(url, BBREF_HEADERS, timeout=20)
    teams: list[dict] = []
    seen: set[str] = set()

    for m in re.finditer(r"<tr\b([^>]*)>(.*?)</tr>", html, re.DOTALL):
        content = m.group(2)
        team_m = re.search(r'data-stat="team_name"[^>]*>.*?href="[^"]+">([^<]+)</a>', content, re.DOTALL)
        w_m = re.search(r'data-stat="wins"[^>]*>(\d+)', content)
        l_m = re.search(r'data-stat="losses"[^>]*>(\d+)', content)
        if not (team_m and w_m and l_m):
            continue
        full_name = team_m.group(1).strip()
        if full_name in seen:
            continue
        seen.add(full_name)
        abbr = BBREF_NAME_TO_ABBR.get(full_name, "")
        if not abbr:
            continue
        wins   = int(w_m.group(1))
        losses = int(l_m.group(1))
        logo_key = ESPN_LOGO_ABBR.get(abbr, abbr.lower())
        logo = f"https://a.espncdn.com/i/teamlogos/nba/500/{logo_key}.png"
        loc, disp = TEAM_FULL.get(abbr, (abbr, full_name))
        teams.append({
            "espn_id":      ESPN_ID.get(abbr, abbr),
            "abbreviation": abbr,
            "display_name": disp,
            "location":     loc,
            "nickname":     disp.replace(loc, "").strip(),
            "logo_url":     logo,
            "wins":         wins,
            "losses":       losses,
        })

    return teams


def _fetch_bbref_advanced_sync() -> dict[str, dict]:
    url = "https://www.basketball-reference.com/leagues/NBA_2026_advanced.html"
    html = _fetch_html(url, BBREF_HEADERS, timeout=25)
    result: dict[str, dict] = {}

    for m in re.finditer(r"<tr\b([^>]*)>(.*?)</tr>", html, re.DOTALL):
        content = m.group(2)
        if 'name_display' not in content or 'per' not in content:
            continue
        name_m = re.search(r'data-stat="name_display"[^>]*>.*?href="[^"]+">([^<]+)</a>', content, re.DOTALL)
        team_m = re.search(r'data-stat="team_name_abbr"[^>]*>(?:<a[^>]*>)?([A-Z0-9]+)', content, re.DOTALL)
        if not name_m:
            continue
        name = name_m.group(1).strip()
        team_raw = team_m.group(1).strip() if team_m else ""
        if team_raw in ("TOT", "2TM", "3TM", "4TM", "5TM"):
            continue
        norm = _normalize_name(name)
        if norm in result:
            continue
        result[norm] = {
            "per":       _gstat(content, "per"),
            "usg_pct":   _gstat(content, "usg_pct"),
            "ws":        _gstat(content, "ws"),
            "ws_per_48": _gstat(content, "ws_per_48"),
            "bpm":       _gstat(content, "bpm"),
            "obpm":      _gstat(content, "obpm"),
            "dbpm":      _gstat(content, "dbpm"),
            "vorp":      _gstat(content, "vorp"),
            "ows":       _gstat(content, "ows"),
            "dws":       _gstat(content, "dws"),
        }

    return result


async def fetch_all_data() -> tuple[list[dict], list[dict], list[dict], dict[str, dict]]:
    """
    Returns (teams, per_game_stats, contracts, advanced_stats).

    If api/nba.db exists, reads from it directly (fast, no network calls).
    Otherwise falls back to live Basketball-Reference scraping.
    """
    try:
        import db as _db
        if _db.db_exists():
            return _load_from_db(_db)
    except Exception:
        pass  # DB module or file unavailable — fall through to scraping

    # ── Live BBRef scrape (fallback) ─────────────────────────────────────────
    loop = asyncio.get_event_loop()
    teams, stats, contracts, advanced = await asyncio.gather(
        loop.run_in_executor(_executor, _fetch_bbref_standings_sync),
        loop.run_in_executor(_executor, _fetch_bbref_player_stats_sync),
        loop.run_in_executor(_executor, _fetch_bbref_contracts_sync),
        loop.run_in_executor(_executor, _fetch_bbref_advanced_sync),
    )
    return teams, stats, contracts, advanced


def _load_from_db(_db) -> tuple[list[dict], list[dict], list[dict], dict[str, dict]]:
    """
    Convert SQLite rows into the same shape that the BBRef scrapers return
    so that service.py / merge_player_data() need zero changes.
    """
    teams = _db.load_teams()  # already in the right shape

    db_players = _db.load_players()

    # Build per-game stats list (same shape as _fetch_bbref_player_stats_sync)
    stats: list[dict] = []
    for p in db_players:
        stats.append({
            "nba_id":          str(p.get("id", "")),
            "full_name":       p["full_name"],
            "team_abbr":       p["team_abbr"],
            "pos":             p.get("pos", ""),
            "age":             p.get("age", 0),
            "games_played":    p.get("games_played", 0),
            "minutes":         p.get("minutes", 0),
            "points":          p.get("points", 0),
            "rebounds":        p.get("rebounds", 0),
            "assists":         p.get("assists", 0),
            "steals":          p.get("steals", 0),
            "blocks":          p.get("blocks", 0),
            "fga":             p.get("fga", 0),
            "fta":             p.get("fta", 0),
            "field_goal_pct":  p.get("field_goal_pct", 0),
            "three_point_pct": p.get("three_point_pct", 0),
            "free_throw_pct":  p.get("free_throw_pct", 0),
            "tov_per_g":       p.get("tov_per_g", 0),
        })

    # Build contracts list (same shape as _fetch_bbref_contracts_sync)
    contracts: list[dict] = []
    for p in db_players:
        contracts.append({
            "full_name":    p["full_name"],
            "norm_name":    p.get("norm_name", _normalize_name(p["full_name"])),
            "team_abbr":    p["team_abbr"],
            "salary":       p.get("salary", 0),
            "salary_year2": p.get("salary_year2", 0),
            "salary_year3": p.get("salary_year3", 0),
            "salary_year4": p.get("salary_year4", 0),
        })

    # Build advanced stats dict keyed by norm_name
    advanced: dict[str, dict] = {}
    for p in db_players:
        norm = p.get("norm_name") or _normalize_name(p["full_name"])
        advanced[norm] = {
            "per":       p.get("per", 0),
            "usg_pct":   p.get("usg_pct", 0),
            "ws":        p.get("ws", 0),
            "ws_per_48": p.get("ws_per_48", 0),
            "bpm":       p.get("bpm", 0),
            "obpm":      p.get("obpm", 0),
            "dbpm":      p.get("dbpm", 0),
            "vorp":      p.get("vorp", 0),
            "ows":       p.get("ows", 0),
            "dws":       p.get("dws", 0),
        }

    return teams, stats, contracts, advanced


def merge_player_data(
    stats: list[dict],
    contracts: list[dict],
    advanced_stats: dict[str, dict] | None = None,
) -> list[dict]:
    from collections import defaultdict

    contracts_by_norm: dict[str, list[dict]] = defaultdict(list)
    for c in contracts:
        contracts_by_norm[c["norm_name"]].append(c)

    stats_by_name: dict[str, dict] = {}
    for p in stats:
        k = _normalize_name(p["full_name"])
        if k not in stats_by_name:
            stats_by_name[k] = p

    def _fuzzy_stat(norm: str) -> dict | None:
        for sname, sv in stats_by_name.items():
            if norm in sname or sname in norm:
                return sv
        return None

    _adv = advanced_stats or {}
    _ZERO_ADV = {
        "per": 0.0, "usg_pct": 0.0, "ws": 0.0, "ws_per_48": 0.0,
        "bpm": 0.0, "obpm": 0.0, "dbpm": 0.0, "vorp": 0.0, "ows": 0.0, "dws": 0.0,
    }

    def _adv_for(norm: str) -> dict:
        return _adv.get(norm, _ZERO_ADV)

    def _zero_stats(contract: dict) -> dict:
        norm = _normalize_name(contract["full_name"])
        return {
            "nba_id":          contract["full_name"],
            "full_name":       contract["full_name"],
            "team_abbr":       contract["team_abbr"],
            "pos":             "",
            "age":             0.0, "games_played": 0, "minutes": 0.0,
            "points": 0.0, "rebounds": 0.0, "assists": 0.0,
            "steals": 0.0, "blocks": 0.0, "fga": 0.0, "fta": 0.0,
            "field_goal_pct": 0.0, "three_point_pct": 0.0, "free_throw_pct": 0.0,
            "tov_per_g": 0.0,
            "salary":          contract["salary"],
            "salary_year2":    contract["salary_year2"],
            "salary_year3":    contract["salary_year3"],
            "salary_year4":    contract["salary_year4"],
            **_adv_for(norm),
        }

    def _with_stats(contract: dict, stat: dict) -> dict:
        norm = _normalize_name(contract["full_name"])
        return {
            **stat,
            "full_name":    contract["full_name"],
            "team_abbr":    contract["team_abbr"],
            "salary":       contract["salary"],
            "salary_year2": contract["salary_year2"],
            "salary_year3": contract["salary_year3"],
            "salary_year4": contract["salary_year4"],
            **_adv_for(norm),
        }

    merged: list[dict] = []
    for norm, entries in contracts_by_norm.items():
        stat = stats_by_name.get(norm) or _fuzzy_stat(norm)
        if len(entries) == 1:
            c = entries[0]
            merged.append(_with_stats(c, stat) if stat else _zero_stats(c))
        else:
            if stat:
                stat_team = stat.get("team_abbr", "")
                active = next((c for c in entries if c["team_abbr"] == stat_team), entries[0])
            else:
                active = entries[0]
            merged.append(_with_stats(active, stat) if stat else _zero_stats(active))
            for c in entries:
                if c is active:
                    continue
                dead = _zero_stats(c)
                dead["full_name"] = f"{c['full_name']} (dead cap)"
                merged.append(dead)

    return merged


def get_cap_constants() -> dict:
    return {
        "season":               SEASON,
        "salary_cap":           SALARY_CAP,
        "luxury_tax_threshold": LUXURY_TAX_THRESHOLD,
        "first_apron":          FIRST_APRON,
        "second_apron":         SECOND_APRON,
    }
