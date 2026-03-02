# NBA Salary Cap Analyzer — Architecture & Notes

## Deployment
- **Frontend**: Vercel — `https://nba-cap-analyzer-stoufiles-2252s-projects.vercel.app`
  - Build: `cd frontend && npm install && npm run build`
  - Output: `frontend/dist`
  - Deploy: `cd frontend && npx vercel --prod --yes`
- **Backend**: Railway — `https://nba-salary-cap-api-production.up.railway.app`
  - Deploy: `cd nba-salary-cap-analyzer && railway up --service nba-salary-cap-api`
  - Start: `uvicorn api.index:app --host 0.0.0.0 --port $PORT`
  - Config: `railway.toml` + `Procfile`
- Railway moved backend off Vercel because: serverless 10s timeout, stats.nba.com IP blocks

## Data Sources (all Basketball-Reference)
- **Standings**: `https://www.basketball-reference.com/leagues/NBA_2026_standings.html`
  - `data-stat="team_name"` (full name, not abbr), `data-stat="wins"`, `data-stat="losses"`
  - Teams appear twice (East + West tables) — deduplicate by full name
- **Per-game stats**: `https://www.basketball-reference.com/leagues/NBA_2026_per_game.html`
  - `data-stat="name_display"` (NOT "player"), `data-stat="team_name_abbr"`
  - `data-stat="games"` (NOT "g")
  - Skip TOT/2TM/3TM rows; keep first real-team row per player
- **Contracts/Salaries**: `https://www.basketball-reference.com/contracts/players.html`
  - `data-stat="player"`, `data-stat="team_id"`, `data-stat="y1"` through `data-stat="y4"`
  - Numeric values in `csk="NNNNN"` attribute
  - NO deduplication — traded players appear once per team; handled by `merge_player_data()`

## Key Team Abbreviation Mappings (BBRef → Standard)
```python
BBREF_TEAM_MAP = {"PHO": "PHX", "GOS": "GSW", "SAN": "SAS", "NOR": "NOP", "BRK": "BKN", "CHO": "CHA"}
```

## Traded/Split Contracts (merge_player_data logic)
- BBRef contracts page lists both teams for traded players with same full salary each
- `merge_player_data()` in `data_client.py`:
  1. Groups contracts by normalized name
  2. For players with stats: finds contract entry whose team matches stats team = active
  3. Other entries become `"PlayerName (dead cap)"` with zero stats
  4. For injured (no stats): uses first entry (BBRef lists current team first)
- Future salaries (y2/y3/y4) carried through from matched contract entry

## Player Value Scoring (metrics.py)
- `calc_value_score()`: total season production / tiered salary (floor at $8M)
- Min thresholds: `games >= 10` and `minutes >= 15` (lowered from 25/20)
- `classify_player_value()`: per-salary-tier bands (max/near-max/starter/role/cheap)

## API Endpoints
- `GET /api/cap-constants` — salary cap figures for 2025-26
- `GET /api/teams` — all 30 teams with cap data (no player arrays)
- `GET /api/teams/{team_id}` — single team with full player roster
- `GET /api/players/top-value?limit=100` — top value players league-wide
- `POST /api/refresh` — force refresh cached data
- `GET /api/debug` — test each BBRef scraper individually

## Player Interface (api.ts)
```typescript
export interface Player {
  espn_id, full_name, position, team_abbr,
  salary, salary_year2, salary_year3, salary_year4,
  age, points, rebounds, assists, steals, blocks,
  minutes, games_played, true_shooting_pct, per,
  value_score, value_classification, contract_status
}
```

## Frontend Components
- `App.tsx` — tabs: Teams / Compare / Top Value
- `TeamCard.tsx` — card per team with cap status color
- `TeamDetail.tsx` — team roster + cap breakdown
- `TeamComparison.tsx` — side-by-side team compare
- `PlayerTable.tsx` — sortable table, columns include Y1/Y2/Y3/Y4 salary

## Known Issues / Gotchas
- stats.nba.com blocks all datacenter IPs (Vercel and Railway) — don't use it
- ESPN public API standings `season=2025` returns last year's final records; BBRef is more reliable
- ESPN byathlete player stats endpoint returns 404 — doesn't exist
- HoopsHype is JS-rendered (Next.js), only 20 players in SSR, can't paginate via URL
- In-memory cache (6h TTL) — data is NOT persisted across Railway restarts
