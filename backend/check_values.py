import urllib.request, json

# Top value
with urllib.request.urlopen("http://localhost:8000/api/players/top-value?limit=20") as r:
    players = json.load(r)

print("=== TOP VALUE ===")
print(f"{'Player':<26} {'Team':<5} {'Salary':>9} {'MIN':>5} {'GP':>4} {'PTS':>5} {'Value':>8}  Class")
print("-" * 88)
for p in players:
    sal = f"${p['salary']/1e6:.1f}M"
    print(f"{p['full_name']:<26} {p['team_abbr']:<5} {sal:>9} {p['minutes']:>5.1f} {p['games_played']:>4} {p['points']:>5.1f} {p['value_score']:>8.1f}  {p['value_classification']}")

# Check specific known max guys via teams endpoint
print("\n=== CHECKING MAX CONTRACT PLAYERS (OKC) ===")
with urllib.request.urlopen("http://localhost:8000/api/teams/25") as r:  # OKC
    team = json.load(r)

if team.get("players"):
    players_sorted = sorted(team["players"], key=lambda x: x["salary"], reverse=True)
    for p in players_sorted[:8]:
        sal = f"${p['salary']/1e6:.1f}M"
        print(f"{p['full_name']:<26} {sal:>9} {p['minutes']:>5.1f} {p['games_played']:>4} {p['points']:>5.1f} {p['value_score']:>8.1f}  {p['value_classification']}")
else:
    print("no players loaded for OKC yet")
