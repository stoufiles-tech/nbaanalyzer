"""
Multi-source NBA data client (no pandas / nba_api — pure httpx + stdlib).
  - NBA Stats API: player stats + team standings
  - Basketball-Reference: real player salaries (scraped)
  - ESPN CDN: team logos
"""
import re
import ssl
import urllib.request
import asyncio
import httpx
from concurrent.futures import ThreadPoolExecutor

SEASON = "2025-26"

SALARY_CAP         = 154_647_000
LUXURY_TAX_THRESHOLD = 187_931_000
FIRST_APRON        = 195_000_000
SECOND_APRON       = 207_000_000

_executor = ThreadPoolExecutor(max_workers=4)

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

NBA_HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
    "Connection": "keep-alive",
    "Referer": "https://www.nba.com/",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

BBREF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
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

# NBA.com team ID → abbreviation
NBA_TEAM_ID_TO_ABBR = {
    1610612737: "ATL", 1610612738: "BOS", 1610612751: "BKN",
    1610612766: "CHA", 1610612741: "CHI", 1610612739: "CLE",
    1610612742: "DAL", 1610612743: "DEN", 1610612765: "DET",
    1610612744: "GSW", 1610612745: "HOU", 1610612754: "IND",
    1610612746: "LAC", 1610612747: "LAL", 1610612763: "MEM",
    1610612748: "MIA", 1610612749: "MIL", 1610612750: "MIN",
    1610612740: "NOP", 1610612752: "NYK", 1610612760: "OKC",
    1610612753: "ORL", 1610612755: "PHI", 1610612756: "PHX",
    1610612757: "POR", 1610612758: "SAC", 1610612759: "SAS",
    1610612761: "TOR", 1610612762: "UTA", 1610612764: "WAS",
}

ESPN_ID = {
    "ATL": "1",  "BOS": "2",  "BKN": "17", "CHA": "30", "CHI": "4",
    "CLE": "5",  "DAL": "6",  "DEN": "7",  "DET": "8",  "GSW": "9",
    "HOU": "10", "IND": "11", "LAC": "12", "LAL": "13", "MEM": "29",
    "MIA": "14", "MIL": "15", "MIN": "16", "NOP": "3",  "NYK": "18",
    "OKC": "25", "ORL": "19", "PHI": "20", "PHX": "21", "POR": "22",
    "SAC": "23", "SAS": "24", "TOR": "28", "UTA": "26", "WAS": "27",
}


def _normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z ]", "", name)
    return re.sub(r"\s+", " ", name)


def _fetch_nba_stats_sync() -> list[dict]:
    url = (
        "https://stats.nba.com/stats/leaguedashplayerstats"
        "?Season=2025-26&SeasonType=Regular+Season&PerMode=Totals"
        "&MeasureType=Base&LastNGames=0&Month=0&OpponentTeamID=0"
        "&PaceAdjust=N&PlusMinus=N&Rank=N"
    )
    req = urllib.request.Request(url, headers=NBA_HEADERS)
    with urllib.request.urlopen(req, context=_ssl_ctx, timeout=25) as r:
        import json
        data = json.loads(r.read())

    rs = data["resultSets"][0]
    headers = rs["headers"]
    idx = {h: i for i, h in enumerate(headers)}

    players = []
    for row in rs["rowSet"]:
        gp  = int(row[idx["GP"]]  or 0)
        min_total = float(row[idx["MIN"]] or 0)
        min_pg = round(min_total / gp, 2) if gp > 0 else 0.0
        pts = float(row[idx["PTS"]] or 0)
        reb = float(row[idx["REB"]] or 0)
        ast = float(row[idx["AST"]] or 0)
        stl = float(row[idx["STL"]] or 0)
        blk = float(row[idx["BLK"]] or 0)
        fgm = float(row[idx["FGM"]] or 0)
        fga = float(row[idx["FGA"]] or 0)
        fg3m = float(row[idx["FG3M"]] or 0)
        fg3a = float(row[idx["FG3A"]] or 0)
        ftm = float(row[idx["FTM"]] or 0)
        fta = float(row[idx["FTA"]] or 0)
        team_id = int(row[idx["TEAM_ID"]] or 0)
        abbr = NBA_TEAM_ID_TO_ABBR.get(team_id, str(row[idx["TEAM_ABBREVIATION"]]))

        pts_pg = round(pts / gp, 2) if gp > 0 else 0.0
        reb_pg = round(reb / gp, 2) if gp > 0 else 0.0
        ast_pg = round(ast / gp, 2) if gp > 0 else 0.0
        stl_pg = round(stl / gp, 2) if gp > 0 else 0.0
        blk_pg = round(blk / gp, 2) if gp > 0 else 0.0
        fga_pg = round(fga / gp, 2) if gp > 0 else 0.0
        fta_pg = round(fta / gp, 2) if gp > 0 else 0.0

        players.append({
            "nba_id": str(row[idx["PLAYER_ID"]]),
            "full_name": str(row[idx["PLAYER_NAME"]]),
            "team_abbr": abbr,
            "age": float(row[idx.get("AGE", -1)] or 0) if "AGE" in idx else 0.0,
            "games_played": gp,
            "minutes": min_pg,
            "points": pts_pg,
            "rebounds": reb_pg,
            "assists": ast_pg,
            "steals": stl_pg,
            "blocks": blk_pg,
            "field_goal_pct": round(fgm / fga, 4) if fga > 0 else 0.0,
            "three_point_pct": round(fg3m / fg3a, 4) if fg3a > 0 else 0.0,
            "free_throw_pct": round(ftm / fta, 4) if fta > 0 else 0.0,
            "fga": fga_pg,
            "fta": fta_pg,
        })
    return players


def _fetch_standings_sync() -> list[dict]:
    url = (
        "https://stats.nba.com/stats/leaguestandingsv3"
        "?Season=2025-26&SeasonType=Regular+Season&LeagueID=00"
    )
    req = urllib.request.Request(url, headers=NBA_HEADERS)
    with urllib.request.urlopen(req, context=_ssl_ctx, timeout=20) as r:
        import json
        data = json.loads(r.read())

    rs = data["resultSets"][0]
    headers = rs["headers"]
    idx = {h: i for i, h in enumerate(headers)}

    teams = []
    for row in rs["rowSet"]:
        team_id = int(row[idx["TeamID"]])
        abbr = NBA_TEAM_ID_TO_ABBR.get(team_id, "???")
        logo = f"https://a.espncdn.com/i/teamlogos/nba/500/{ESPN_LOGO_ABBR.get(abbr, abbr.lower())}.png"
        loc, full = TEAM_FULL.get(abbr, (abbr, abbr))
        teams.append({
            "espn_id": ESPN_ID.get(abbr, abbr),
            "abbreviation": abbr,
            "display_name": full,
            "location": loc,
            "nickname": full.replace(loc, "").strip(),
            "logo_url": logo,
            "wins": int(row[idx["WINS"]]),
            "losses": int(row[idx["LOSSES"]]),
        })
    return teams


def _fetch_bbref_salaries_sync() -> dict[str, float]:
    url = "https://www.basketball-reference.com/contracts/players.html"
    req = urllib.request.Request(url, headers=BBREF_HEADERS)
    with urllib.request.urlopen(req, context=_ssl_ctx, timeout=20) as r:
        html = r.read().decode("utf-8")

    salaries: dict[str, float] = {}
    rows = re.findall(
        r'data-stat="player"[^>]*>.*?<a[^>]*>([^<]+)</a>.*?data-stat="y1"[^>]*csk="(\d+)"',
        html,
        re.DOTALL,
    )
    for name, sal in rows:
        salaries[_normalize_name(name)] = float(sal)
    return salaries


async def fetch_all_data() -> tuple[list[dict], list[dict], dict[str, float]]:
    loop = asyncio.get_event_loop()
    teams, stats, salaries = await asyncio.gather(
        loop.run_in_executor(_executor, _fetch_standings_sync),
        loop.run_in_executor(_executor, _fetch_nba_stats_sync),
        loop.run_in_executor(_executor, _fetch_bbref_salaries_sync),
    )
    return teams, stats, salaries


def merge_player_data(stats: list[dict], salaries: dict[str, float]) -> list[dict]:
    merged = []
    for p in stats:
        key = _normalize_name(p["full_name"])
        salary = salaries.get(key, 0.0)
        if salary == 0.0:
            for sname, sval in salaries.items():
                if key in sname or sname in key:
                    salary = sval
                    break
        merged.append({**p, "salary": salary})
    return merged


def get_cap_constants() -> dict:
    return {
        "season": SEASON,
        "salary_cap": SALARY_CAP,
        "luxury_tax_threshold": LUXURY_TAX_THRESHOLD,
        "first_apron": FIRST_APRON,
        "second_apron": SECOND_APRON,
    }
