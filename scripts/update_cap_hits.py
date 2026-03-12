"""
Scrape Spotrac cap hits for all 30 NBA teams and update data/nba_2025_26.json.

Usage:  python scripts/update_cap_hits.py
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "nba_2025_26.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
}

# Map team abbreviation -> Spotrac URL slug
TEAM_SLUGS = {
    "ATL": "atlanta-hawks",
    "BOS": "boston-celtics",
    "BKN": "brooklyn-nets",
    "CHA": "charlotte-hornets",
    "CHI": "chicago-bulls",
    "CLE": "cleveland-cavaliers",
    "DAL": "dallas-mavericks",
    "DEN": "denver-nuggets",
    "DET": "detroit-pistons",
    "GSW": "golden-state-warriors",
    "HOU": "houston-rockets",
    "IND": "indiana-pacers",
    "LAC": "la-clippers",
    "LAL": "los-angeles-lakers",
    "MEM": "memphis-grizzlies",
    "MIA": "miami-heat",
    "MIL": "milwaukee-bucks",
    "MIN": "minnesota-timberwolves",
    "NOP": "new-orleans-pelicans",
    "NYK": "new-york-knicks",
    "OKC": "oklahoma-city-thunder",
    "ORL": "orlando-magic",
    "PHI": "philadelphia-76ers",
    "PHX": "phoenix-suns",
    "POR": "portland-trail-blazers",
    "SAC": "sacramento-kings",
    "SAS": "san-antonio-spurs",
    "TOR": "toronto-raptors",
    "UTA": "utah-jazz",
    "WAS": "washington-wizards",
}


def _normalize(name: str) -> str:
    """Normalize a player name for fuzzy matching."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z ]", "", name)
    return re.sub(r"\s+", " ", name)


def fetch_team_cap_hits(abbr: str, slug: str) -> dict[str, int]:
    """Scrape Spotrac and return {normalized_name: cap_hit} for one team."""
    url = f"https://www.spotrac.com/nba/{slug}/cap/_/year/2025"
    req = urllib.request.Request(url, headers=HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  [{abbr}] HTTP {e.code} - skipping")
        return {}
    except Exception as e:
        print(f"  [{abbr}] Error: {e} - skipping")
        return {}

    # Find the active roster table
    table_match = re.search(
        r'<table[^>]*id="table_active"[^>]*>(.*?)</table>',
        html, re.DOTALL
    )
    if not table_match:
        print(f"  [{abbr}] Could not find table_active - skipping")
        return {}

    table_html = table_match.group(1)

    # Find tbody
    tbody_match = re.search(r'<tbody[^>]*>(.*?)</tbody>', table_html, re.DOTALL)
    if not tbody_match:
        print(f"  [{abbr}] Could not find tbody - skipping")
        return {}

    tbody = tbody_match.group(1)
    results: dict[str, int] = {}

    # Parse each row
    for row_match in re.finditer(r'<tr[^>]*>(.*?)</tr>', tbody, re.DOTALL):
        row = row_match.group(1)

        # Extract player name from <a class="link...">Name</a>
        name_match = re.search(r'<a[^>]*class="link[^"]*"[^>]*>([^<]+)</a>', row)
        if not name_match:
            continue
        player_name = name_match.group(1).strip()

        # Extract all td data-sort values
        cells = re.findall(r'<td[^>]*(?:data-sort="([^"]*)")?[^>]*>', row)

        # Alternative: find all data-sort values in order
        data_sorts = re.findall(r'data-sort="([^"]*)"', row)

        # Cap hit is typically the 3rd data-sort value (after pos, age, type comes cap_hit)
        # But let's be more robust: find the first data-sort that looks like a large dollar amount
        cap_hit = 0
        for i, ds in enumerate(data_sorts):
            try:
                val = int(ds)
                # Cap hits are typically > 500,000 and < 100,000,000
                # The first large integer after position/age is cap hit
                if val > 100000:
                    cap_hit = val
                    break
            except (ValueError, TypeError):
                continue

        if cap_hit > 0:
            norm = _normalize(player_name)
            results[norm] = cap_hit

    return results


def main():
    if not os.path.exists(DATA_PATH):
        print(f"ERROR: {DATA_PATH} not found. Run export_db_to_json.py first.")
        sys.exit(1)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    players = data["players"]
    total_updated = 0
    total_not_found = 0

    for abbr in sorted(TEAM_SLUGS.keys()):
        slug = TEAM_SLUGS[abbr]
        print(f"Fetching {abbr} ({slug})...")

        cap_hits = fetch_team_cap_hits(abbr, slug)
        if not cap_hits:
            print(f"  [{abbr}] No cap hits found")
            continue

        team_players = [p for p in players if p["team_abbr"] == abbr]
        matched = 0
        unmatched = []

        for p in team_players:
            norm = _normalize(p["full_name"])
            if norm in cap_hits:
                p["cap_hit"] = cap_hits[norm]
                matched += 1
            else:
                # Try fuzzy: check if any Spotrac name contains or is contained by our name
                found = False
                for sname, sval in cap_hits.items():
                    if norm in sname or sname in norm:
                        p["cap_hit"] = sval
                        matched += 1
                        found = True
                        break
                if not found:
                    unmatched.append(p["full_name"])

        total_updated += matched
        total_not_found += len(unmatched)
        print(f"  [{abbr}] {matched}/{len(team_players)} matched, "
              f"{len(cap_hits)} on Spotrac")
        if unmatched:
            safe_names = [n.encode("ascii", "replace").decode() for n in unmatched[:5]]
            print(f"  [{abbr}] Not found on Spotrac: {', '.join(safe_names)}"
                  + (f" (+{len(unmatched)-5} more)" if len(unmatched) > 5 else ""))

        # Save progress after each team
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Be polite to Spotrac
        time.sleep(2)

    print(f"\nDone! Updated {total_updated} players. "
          f"{total_not_found} not found on Spotrac.")
    print(f"Saved to {DATA_PATH}")


if __name__ == "__main__":
    main()
