# NBA Salary Cap Analyzer

Interactive web app for analyzing NBA team salary cap situations and player value.

## Features

- **Team Cap Overview** — Visual cap bar showing payroll vs. salary cap, luxury tax, and apron thresholds
- **Player Value Analysis** — Overpaid/underpaid/fair-value classification per player based on stats vs. salary
- **Custom Efficiency Metrics** — Wins per $M spent, cap efficiency score, simplified PER, True Shooting %
- **Team Comparisons** — Bar + scatter charts comparing all 30 teams
- **Top Value Players** — League-wide leaderboard sorted by value score
- **SQLite caching** — ESPN data cached for 6 hours, auto-refreshes

## Quick Start

```
start.bat
```

Or manually:

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

## Data Sources

- Player/team data: ESPN public API
- Salaries: Estimated by experience tier (ESPN doesn't expose contract data publicly)
- Cap figures: 2024-25 official NBA figures (hardcoded constants)

## Salary Note

ESPN's public API does not expose actual contract salaries. The app uses
experience-based estimates. For real salary data, integrate Spotrac or
Basketball-Reference (requires scraping or paid API).
