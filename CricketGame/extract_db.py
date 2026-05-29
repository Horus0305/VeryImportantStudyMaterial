"""
Cricket Game — full database extractor.

Usage:
    python extract_db.py --url https://your-api.alwaysdata.net --seed yourUsername

The script crawls the live API (no auth required for read endpoints) using
a BFS over the player graph: starting from seed usernames it finds every
match, reads side_a / side_b to discover new players, then fetches stats,
full match scorecards, and tournament records for the whole graph.

Output: cricket_data_export.json  (and optionally a CSV summary)
"""

import argparse
import json
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import urllib.request
import urllib.error


# ── HTTP helpers ────────────────────────────────────────────────────────────

def get(base_url: str, path: str, retries: int = 3) -> dict | list | None:
    # URL-encode each path segment (handles spaces and special chars in usernames)
    segments = path.lstrip('/').split('/')
    encoded_segments = []
    for seg in segments:
        # Split off query string if present
        if '?' in seg:
            part, qs = seg.split('?', 1)
            encoded_segments.append(f"{quote(part, safe='')}?{qs}")
        else:
            encoded_segments.append(quote(seg, safe=''))
    url = f"{base_url.rstrip('/')}/{'/'.join(encoded_segments)}"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            print(f"  [HTTP {e.code}] {url}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            print(f"  [ERR] {url}: {e}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    return None


# ── BFS extraction ──────────────────────────────────────────────────────────

def extract(base_url: str, seed_users: list[str]) -> dict:
    seen_players: set[str] = set()
    seen_matches: set[str] = set()
    seen_tournaments: set[str] = set()

    queue: deque[str] = deque(seed_users)
    for u in seed_users:
        seen_players.add(u)

    all_players: dict[str, dict] = {}
    all_matches: dict[str, dict] = {}
    all_tournaments: dict[str, dict] = {}

    while queue:
        username = queue.popleft()
        print(f"\n[player] {username}")

        # ── Player stats ──────────────────────────────────────────────────
        stats = get(base_url, f"/auth/stats/{username}")
        if stats is None:
            print(f"  stats: not found (player may not exist or API path differs)")
        all_players[username] = {"stats": stats, "matches": [], "tournaments": []}

        # ── Matches ───────────────────────────────────────────────────────
        matches = get(base_url, f"/api/matches/{username}?limit=500")
        if not matches:
            matches = []
        print(f"  matches: {len(matches)}")

        for m in matches:
            mid = m.get("match_id")
            if not mid:
                continue
            all_players[username]["matches"].append(mid)

            if mid not in seen_matches:
                seen_matches.add(mid)
                all_matches[mid] = m

                # Discover new players from this match
                for side_key in ("side_a", "side_b"):
                    side = m.get(side_key) or []
                    if isinstance(side, str):
                        try:
                            side = json.loads(side)
                        except Exception:
                            side = []
                    for player in side:
                        if player and player not in seen_players:
                            seen_players.add(player)
                            queue.append(player)
                            print(f"  discovered: {player}")

                # Discover tournament IDs
                tid = m.get("tournament_id")
                if tid and tid not in seen_tournaments:
                    seen_tournaments.add(tid)

        # ── Tournaments ───────────────────────────────────────────────────
        tournaments = get(base_url, f"/api/tournaments/{username}?limit=500")
        if not tournaments:
            tournaments = []
        print(f"  tournaments: {len(tournaments)}")

        for t in tournaments:
            tid = t.get("tournament_id")
            if not tid:
                continue
            all_players[username]["tournaments"].append(tid)
            if tid not in seen_tournaments:
                seen_tournaments.add(tid)

    # ── Fetch full tournament details (with embedded match list) ──────────
    print(f"\n[tournaments] fetching {len(seen_tournaments)} tournament(s)…")
    for tid in seen_tournaments:
        if tid in all_tournaments:
            continue
        t = get(base_url, f"/api/tournament/{tid}")
        if t:
            all_tournaments[tid] = t
            print(f"  {tid}: {t.get('champion', '?')} won")
            # Also pull any matches inside the tournament that we might have missed
            for m in t.get("matches", []):
                mid = m.get("match_id")
                if mid and mid not in all_matches:
                    all_matches[mid] = m

    return {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "api_base": base_url,
        "summary": {
            "players": len(all_players),
            "matches": len(all_matches),
            "tournaments": len(all_tournaments),
        },
        "players": all_players,
        "matches": all_matches,
        "tournaments": all_tournaments,
    }


# ── CSV helper ───────────────────────────────────────────────────────────────

def write_csv_summary(data: dict, path: Path) -> None:
    import csv

    FORMATS = ["1v1", "tournament", "team", "cpu"]
    rows = []
    for username, info in data["players"].items():
        raw_stats = info.get("stats") or {}
        for fmt in FORMATS:
            fmt_data = raw_stats.get(fmt)
            if not fmt_data:
                continue
            rows.append({
                "username": username,
                "format": fmt,
                "matches_played": fmt_data.get("matches_played", 0),
                "matches_won": fmt_data.get("matches_won", 0),
                "total_runs": fmt_data.get("total_runs", 0),
                "highest_score": fmt_data.get("highest_score", 0),
                "avg_runs": fmt_data.get("avg_runs", 0.0),
                "avg_strike_rate": fmt_data.get("avg_strike_rate", 0.0),
                "fours": fmt_data.get("fours", 0),
                "sixes": fmt_data.get("sixes", 0),
                "fifties": fmt_data.get("fifties", 0),
                "hundreds": fmt_data.get("hundreds", 0),
                "wickets_taken": fmt_data.get("wickets_taken", 0),
                "best_bowling": fmt_data.get("best_bowling", "0/0"),
                "bowling_average": fmt_data.get("bowling_average", 0.0),
                "tournaments_played": fmt_data.get("tournaments_played", 0),
                "tournaments_won": fmt_data.get("tournaments_won", 0),
                "potm_count": fmt_data.get("potm_count", 0),
                "player_of_tournament_count": fmt_data.get("player_of_tournament_count", 0),
            })

    if not rows:
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV summary -> {path}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract all Cricket Game data from a live API.")
    parser.add_argument("--url", required=True,
                        help="Base URL of the API, e.g. https://myapp.alwaysdata.net")
    parser.add_argument("--seed", required=True, nargs="+",
                        help="One or more known usernames to seed the crawl")
    parser.add_argument("--out", default="cricket_data_export.json",
                        help="Output JSON file path (default: cricket_data_export.json)")
    parser.add_argument("--csv", default="cricket_stats_summary.csv",
                        help="Output CSV file path for player stats (default: cricket_stats_summary.csv)")
    args = parser.parse_args()

    print(f"Starting extraction from {args.url}")
    print(f"Seed players: {', '.join(args.seed)}\n")

    data = extract(args.url, args.seed)

    out_path = Path(args.out)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nJSON dump -> {out_path}")
    print(f"  Players:     {data['summary']['players']}")
    print(f"  Matches:     {data['summary']['matches']}")
    print(f"  Tournaments: {data['summary']['tournaments']}")

    write_csv_summary(data, Path(args.csv))
    print("\nDone.")


if __name__ == "__main__":
    main()
