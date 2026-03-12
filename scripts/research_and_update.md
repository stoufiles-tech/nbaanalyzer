# Daily NBA Trades & Free Agency Research — Task Prompt

Use this prompt with Cowork or Claude Code to run the daily update.

---

Research today's NBA trades, signings, waivers, and free agency moves, then update the website data file.

## Objective
Search the web for any NBA transactions (trades, signings, waivers, two-way contracts, 10-day contracts) that occurred since the last update, and apply them to the project's data file.

## Steps

1. **Read the current data timestamp**: Open `data/nba_2025_26.json` and check `meta.data_as_of` to know the last update date.

2. **Research recent transactions**: Use web search for "NBA trades today", "NBA transactions today", "NBA signings waivers". Also search "NBA trade rumors confirmed" for breaking news. Focus on CONFIRMED transactions only — not rumors or speculation. Look at sources like ESPN, The Athletic, NBA.com official transactions page.

3. **For each confirmed transaction found**, extract:
   - **Trades**: player name, from_team (3-letter abbr), to_team (3-letter abbr)
   - **Signings**: player name, team (3-letter abbr), salary if reported
   - **Waivers**: player name, team (3-letter abbr)

   Standard NBA abbreviations: ATL, BOS, BKN, CHA, CHI, CLE, DAL, DEN, DET, GSW, HOU, IND, LAC, LAL, MEM, MIA, MIL, MIN, NOP, NYK, OKC, ORL, PHI, PHX, POR, SAC, SAS, TOR, UTA, WAS.

4. **Update the data file** using the helper script at `scripts/daily_trades_research.py`:
   ```python
   import sys, os
   sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
   from daily_trades_research import load_data, save_data, apply_transactions

   data = load_data()
   transactions = [
       {"type": "trade", "player": "John Doe", "from": "LAL", "to": "BOS"},
       {"type": "signing", "player": "Jane Smith", "team": "MIA", "salary": 5000000},
       {"type": "waiver", "player": "Bob Jones", "team": "CHI"},
   ]
   count = apply_transactions(data, transactions)
   save_data(data)
   ```

5. **Update standings** if any win/loss records are found — modify team entries in `data["teams"]` where `abbreviation` matches.

6. **Write a brief summary** of what was updated (or note "No new transactions found").

## Constraints
- Only apply CONFIRMED transactions — never rumors
- If unsure, skip rather than apply incorrect data
- The `norm_name` field is lowercase — match against that
