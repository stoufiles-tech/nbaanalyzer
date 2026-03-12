"""
Static NBA data client — loads from data/nba_2025_26.json.

No scraping, no database, no network calls. All data is compiled
from Spotrac cap hits and Basketball-Reference stats.
"""
import re
import json
import os

_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "nba_2025_26.json",
)

_cached_data: dict | None = None

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

ESPN_ID_TO_ABBR = {v: k for k, v in ESPN_ID.items()}

NBA_TEAM_ID = {
    "ATL": 1610612737, "BOS": 1610612738, "BKN": 1610612751, "CHA": 1610612766,
    "CHI": 1610612741, "CLE": 1610612739, "DAL": 1610612742, "DEN": 1610612743,
    "DET": 1610612765, "GSW": 1610612744, "HOU": 1610612745, "IND": 1610612754,
    "LAC": 1610612746, "LAL": 1610612747, "MEM": 1610612763, "MIA": 1610612748,
    "MIL": 1610612749, "MIN": 1610612750, "NOP": 1610612740, "NYK": 1610612752,
    "OKC": 1610612760, "ORL": 1610612753, "PHI": 1610612755, "PHX": 1610612756,
    "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "TOR": 1610612761,
    "UTA": 1610612762, "WAS": 1610612764,
}

NBA_TEAM_ID_TO_ABBR = {v: k for k, v in NBA_TEAM_ID.items()}

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

SEASON = "2025-26"

SALARY_CAP           = 154_647_000
LUXURY_TAX_THRESHOLD = 187_931_000
FIRST_APRON          = 195_000_000
SECOND_APRON         = 207_000_000


def _normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z ]", "", name)
    return re.sub(r"\s+", " ", name)


def _load_json() -> dict:
    global _cached_data
    if _cached_data is not None:
        return _cached_data
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        _cached_data = json.load(f)
    return _cached_data


async def fetch_all_data() -> tuple[list[dict], list[dict], list[dict], dict[str, dict]]:
    """
    Returns (teams, per_game_stats, contracts, advanced_stats)
    from the static JSON file. Same tuple shape as the old scraper.
    """
    data = _load_json()

    teams = data["teams"]

    stats: list[dict] = []
    contracts: list[dict] = []
    advanced: dict[str, dict] = {}

    for p in data["players"]:
        norm = p.get("norm_name") or _normalize_name(p["full_name"])

        stats.append({
            "nba_id":          p["full_name"],
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
            "cap_hit":         p.get("cap_hit"),
        })

        contracts.append({
            "full_name":    p["full_name"],
            "norm_name":    norm,
            "team_abbr":    p["team_abbr"],
            "salary":       p.get("salary", 0),
            "salary_year2": p.get("salary_year2", 0),
            "salary_year3": p.get("salary_year3", 0),
            "salary_year4": p.get("salary_year4", 0),
        })

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
            "cap_hit":         None,
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
    data = _load_json()
    meta = data["meta"]
    return {
        "season":               meta["season"],
        "salary_cap":           meta["salary_cap"],
        "luxury_tax_threshold": meta["luxury_tax_threshold"],
        "first_apron":          meta["first_apron"],
        "second_apron":         meta["second_apron"],
        "data_as_of":           meta.get("data_as_of", ""),
    }
