import urllib.request
import json

base = "http://localhost:8000/api/leaderboard"

for s in ["2", "1", "all"]:
    url = f"{base}?season={s}&limit=5"
    try:
        res = urllib.request.urlopen(url)
        data = json.loads(res.read())
        lb = data.get("leaderboard", [])
        print(f"--- Season {s} Leaderboard (top 3) ---")
        for x in lb[:3]:
            print(f"{x['username']}: won={x['tournaments_won']}, played={x['tournaments_played']}, runs={x['total_runs']}")
    except Exception as e:
        print(f"Error fetching season {s}: {e}")
