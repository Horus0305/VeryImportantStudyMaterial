import json

data = json.loads(open('cricket_data_export.json', encoding='utf-8').read())
print('=== EXTRACTION SUMMARY ===')
print(f"Players:     {data['summary']['players']}")
print(f"Matches:     {data['summary']['matches']}")
print(f"Tournaments: {data['summary']['tournaments']}")
print()
print('=== TOURNAMENT FORMAT LEADERBOARD ===')
players = [(u, i) for u, i in data['players'].items() if (i.get('stats') or {}).get('tournament')]
players.sort(key=lambda x: x[1]['stats']['tournament']['total_runs'], reverse=True)
print(f"{'Player':<18} {'Matches':>8} {'Wins':>6} {'Runs':>7} {'HS':>5} {'SR%':>7} {'Wkts':>6} {'POTM':>6} {'TourWin':>8}")
print('-' * 80)
for u, info in players:
    t = info['stats']['tournament']
    print(f"{u:<18} {t['matches_played']:>8} {t['matches_won']:>6} {t['total_runs']:>7} {t['highest_score']:>5} {t['avg_strike_rate']:>7.1f} {t['wickets_taken']:>6} {t['potm_count']:>6} {t['tournaments_won']:>8}")
