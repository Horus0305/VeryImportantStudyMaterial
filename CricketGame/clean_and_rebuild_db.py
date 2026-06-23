"""
clean_and_rebuild_db.py
======================
Database cleanup and statistics rebuild script.
Purges excluded players, matches, tournaments, and learning logs, and recalculates
format_stats from scratch to resolve all discrepancies.
"""
import sqlite3
import json
import shutil
import os
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ALLOWED_PLAYERS = {"AniketKS", "Yash", "Atharva", "hetvig04", "Meet", "Atharva Kolekar", "Sahil"}
CPU_BOTS = {"CPU", "CPU Bot", "CPU Bot 2", "CPU Bot 3", "CPU Bot 4", "CPU Bot 5"}
ALLOWED_AND_CPU = ALLOWED_PLAYERS.union(CPU_BOTS)

def rebuild_database(db_path):
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Skipping.")
        return

    print(f"\n=============================================================")
    print(f"CLEANING AND REBUILDING: {db_path}")
    print(f"=============================================================")

    # 1. Create a backup
    backup_path = db_path + ".bak"
    shutil.copyfile(db_path, backup_path)
    print(f"Created backup: {backup_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Check if this is an initialized database containing the players table
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players'")
    if not cur.fetchone():
        print(f"Table 'players' not found in {db_path}. Skipping.")
        conn.close()
        return

    # 2. Get allowed and excluded players
    cur.execute("SELECT id, username FROM players")
    all_players = {r['id']: r['username'] for r in cur.fetchall()}
    
    allowed_ids = {pid for pid, uname in all_players.items() if uname in ALLOWED_PLAYERS}
    excluded_ids = {pid for pid in all_players if pid not in allowed_ids}
    excluded_usernames = {all_players[pid] for pid in excluded_ids}

    print(f"Allowed Player IDs: {allowed_ids}")
    print(f"Excluded Players ({len(excluded_usernames)}): {', '.join(sorted(list(excluded_usernames)))}")

    # 3. Purge Excluded Players
    if excluded_ids:
        placeholders = ",".join("?" * len(excluded_ids))
        cur.execute(f"DELETE FROM players WHERE id IN ({placeholders})", tuple(excluded_ids))
        print(f"Deleted {len(excluded_ids)} players from 'players' table.")

    # 4. Purge Match History
    cur.execute("SELECT * FROM match_history")
    matches = [dict(r) for r in cur.fetchall()]
    deleted_matches_count = 0
    deleted_match_ids = []

    for m in matches:
        try:
            side_a = json.loads(m['side_a']) if m['side_a'] else []
            side_b = json.loads(m['side_b']) if m['side_b'] else []
        except Exception:
            side_a, side_b = [], []
        
        all_participants = set(side_a + side_b)
        has_excluded = any(p in excluded_usernames for p in all_participants)
        
        if has_excluded:
            cur.execute("DELETE FROM match_history WHERE id = ?", (m['id'],))
            deleted_matches_count += 1
            deleted_match_ids.append(m['match_id'])

    print(f"Deleted {deleted_matches_count} matches from 'match_history'.")

    # 5. Purge Tournament History
    cur.execute("SELECT * FROM tournament_history")
    tournaments = [dict(r) for r in cur.fetchall()]
    deleted_tournaments_count = 0

    for t in tournaments:
        try:
            t_players = json.loads(t['players']) if t['players'] else []
        except Exception:
            t_players = []
        
        has_excluded = any(p in excluded_usernames for p in t_players)
        
        if has_excluded:
            cur.execute("DELETE FROM tournament_history WHERE id = ?", (t['id'],))
            deleted_tournaments_count += 1

    print(f"Deleted {deleted_tournaments_count} tournaments from 'tournament_history'.")

    # 6. Purge Learning Logs
    # Purge match_ball_log for any deleted matches
    if deleted_match_ids:
        # Delete in chunks to avoid SQL limit constraints if list is large
        chunk_size = 500
        for i in range(0, len(deleted_match_ids), chunk_size):
            chunk = deleted_match_ids[i:i + chunk_size]
            placeholders = ",".join("?" * len(chunk))
            cur.execute(f"DELETE FROM match_ball_log WHERE match_id IN ({placeholders})", tuple(chunk))
    
    # Also delete logs containing any excluded player IDs
    if excluded_ids:
        placeholders = ",".join("?" * len(excluded_ids))
        cur.execute(f"DELETE FROM match_ball_log WHERE batter_user_id IN ({placeholders}) OR bowler_user_id IN ({placeholders})", tuple(excluded_ids) + tuple(excluded_ids))
    
    cur.execute("SELECT COUNT(*) FROM match_ball_log")
    remaining_balls = cur.fetchone()[0]
    print(f"Cleaned 'match_ball_log'. Remaining ball logs: {remaining_balls}")

    # Purge other pattern/progress tables
    if excluded_ids:
        placeholders = ",".join("?" * len(excluded_ids))
        for table in ['cpu_user_profiles', 'cpu_situational_patterns', 'cpu_sequence_patterns', 'cpu_learning_progress']:
            cur.execute(f"DELETE FROM {table} WHERE user_id IN ({placeholders})", tuple(excluded_ids))
            print(f"Cleaned table '{table}'.")

    # 7. Rebuild Format Stats Cache for Allowed Players
    print("\nRebuilding format_stats cache...")
    
    # Delete stats for excluded players
    if excluded_ids:
        placeholders = ",".join("?" * len(excluded_ids))
        cur.execute(f"DELETE FROM format_stats WHERE player_id IN ({placeholders})", tuple(excluded_ids))

    # Initialize stats for allowed players to default values
    for pid in allowed_ids:
        # Verify rows exist for all 4 formats
        for fmt in ["1v1", "tournament", "team", "cpu"]:
            cur.execute("SELECT id FROM format_stats WHERE player_id = ? AND format = ?", (pid, fmt))
            if not cur.fetchone():
                cur.execute("INSERT INTO format_stats (player_id, format) VALUES (?, ?)", (pid, fmt))
            
            # Reset values to default
            cur.execute("""
                UPDATE format_stats 
                SET matches_played = 0, matches_won = 0, total_runs = 0, total_balls_faced = 0,
                    highest_score = 0, fours = 0, sixes = 0, fifties = 0, hundreds = 0,
                    innings_batted = 0, wickets_taken = 0, best_bowling_wickets = 0, best_bowling_runs = 999,
                    runs_conceded = 0, overs_bowled = 0.0, innings_bowled = 0,
                    tournaments_played = 0, tournaments_won = 0, potm_count = 0, player_of_tournament_count = 0
                WHERE player_id = ? AND format = ?
            """, (pid, fmt))

    conn.commit()

    # Let's read all active players mapped by username
    cur.execute("SELECT id, username FROM players")
    active_players = {r['username']: r['id'] for r in cur.fetchall()}

    # Helper function to convert overs string or float to balls
    def to_balls(overs_val):
        if not overs_val:
            return 0
        try:
            val_str = str(overs_val).strip()
            if not val_str:
                return 0
            if '.' in val_str:
                parts = val_str.split('.')
                return int(parts[0]) * 6 + int(parts[1]) if parts[1] else int(parts[0]) * 6
            return int(val_str) * 6
        except Exception:
            return 0

    # Process Matches for Matches Played, Matches Won, Batting, Bowling, and POTM
    cur.execute("SELECT * FROM match_history")
    matches_left = [dict(r) for r in cur.fetchall()]
    
    # Store accumulated stats in memory first
    # Structure: (player_id, format) -> dict
    stats_map = {}
    def get_stats_dict(pid, fmt):
        key = (pid, fmt)
        if key not in stats_map:
            stats_map[key] = {
                "matches_played": 0, "matches_won": 0, "total_runs": 0, "total_balls_faced": 0,
                "highest_score": 0, "fours": 0, "sixes": 0, "fifties": 0, "hundreds": 0,
                "innings_batted": 0, "wickets_taken": 0, "best_bowling_wickets": 0, "best_bowling_runs": 999,
                "runs_conceded": 0, "total_balls_bowled": 0, "innings_bowled": 0,
                "tournaments_played": 0, "tournaments_won": 0, "potm_count": 0, "player_of_tournament_count": 0
            }
        return stats_map[key]

    def is_player_winner(winner_field, username):
        if not winner_field or winner_field == "TIE":
            return False
        winners = [w.strip() for w in winner_field.split(",") if w.strip()]
        return username in winners

    print(f"Processing {len(matches_left)} matches...")
    for m in matches_left:
        # Determine format
        mode = m['mode']
        fmt = "team" if mode in ("team", "2v2") else mode
        
        try:
            side_a = json.loads(m['side_a']) if m['side_a'] else []
            side_b = json.loads(m['side_b']) if m['side_b'] else []
        except Exception:
            side_a, side_b = [], []
            
        all_m_players = side_a + side_b

        # Matches Played & Won
        for username in all_m_players:
            if username in active_players:
                pid = active_players[username]
                ps = get_stats_dict(pid, fmt)
                ps["matches_played"] += 1
                if is_player_winner(m['winner'], username):
                    ps["matches_won"] += 1

        # Match POTM count
        potm = m['potm']
        if potm and potm in active_players:
            pid = active_players[potm]
            ps = get_stats_dict(pid, fmt)
            ps["potm_count"] += 1

        # Scorecard data
        for sc_col in ['scorecard_1', 'scorecard_2']:
            sc_raw = m[sc_col]
            if not sc_raw:
                continue
            try:
                sc = json.loads(sc_raw) if isinstance(sc_raw, str) else sc_raw
            except Exception:
                continue
            
            # Batting stats
            for bat in sc.get("batting", []):
                name = bat.get("name")
                if name in active_players:
                    pid = active_players[name]
                    ps = get_stats_dict(pid, fmt)
                    runs = bat.get("runs", 0)
                    balls = bat.get("balls", 0)
                    ps["total_runs"] += runs
                    ps["total_balls_faced"] += balls
                    ps["fours"] += bat.get("fours", 0)
                    ps["sixes"] += bat.get("sixes", 0)
                    ps["innings_batted"] += 1
                    
                    if runs > ps["highest_score"]:
                        ps["highest_score"] = runs
                    if runs >= 100:
                        ps["hundreds"] += 1
                    elif runs >= 50:
                        ps["fifties"] += 1

            # Bowling stats
            for bowl in sc.get("bowling", []):
                name = bowl.get("name")
                if name in active_players:
                    pid = active_players[name]
                    ps = get_stats_dict(pid, fmt)
                    wkts = bowl.get("wickets", 0)
                    runs_c = bowl.get("runs", 0)
                    balls_bowled = to_balls(bowl.get("overs", 0))
                    
                    ps["wickets_taken"] += wkts
                    ps["runs_conceded"] += runs_c
                    ps["total_balls_bowled"] += balls_bowled
                    ps["innings_bowled"] += 1
                    
                    # Best bowling
                    bbw = ps["best_bowling_wickets"]
                    bbr = ps["best_bowling_runs"]
                    if wkts > bbw or (wkts == bbw and runs_c < bbr):
                        ps["best_bowling_wickets"] = wkts
                        ps["best_bowling_runs"] = runs_c

    # Process Tournaments for Tournaments Played, Won, and Player of Tournament
    cur.execute("SELECT * FROM tournament_history")
    tournaments_left = [dict(r) for r in cur.fetchall()]
    print(f"Processing {len(tournaments_left)} tournaments...")

    for t in tournaments_left:
        try:
            t_players = json.loads(t['players']) if t['players'] else []
        except Exception:
            t_players = []
            
        # Tournaments played
        for name in t_players:
            if name in active_players:
                pid = active_players[name]
                ps = get_stats_dict(pid, "tournament")
                ps["tournaments_played"] += 1

        # Tournaments won
        champ = t['champion']
        if champ and champ in active_players:
            pid = active_players[champ]
            ps = get_stats_dict(pid, "tournament")
            ps["tournaments_won"] += 1

        # Player of the tournament award
        pot = t['player_of_tournament']
        if pot:
            try:
                pot_data = json.loads(pot) if isinstance(pot, str) else pot
                pot_player = pot_data.get("player")
                if pot_player and pot_player in active_players:
                    pid = active_players[pot_player]
                    ps = get_stats_dict(pid, "tournament")
                    ps["player_of_tournament_count"] += 1
            except Exception:
                pass

    # Save all accumulated stats back to the database format_stats table
    print("Writing rebuilt stats to 'format_stats'...")
    for (pid, fmt), ps in stats_map.items():
        # Convert total balls bowled to fractional overs (e.g. 19 balls -> 3.1 overs)
        total_balls = ps["total_balls_bowled"]
        overs_f = (total_balls // 6) + (total_balls % 6) / 10.0
        
        cur.execute("""
            UPDATE format_stats
            SET matches_played = ?, matches_won = ?, total_runs = ?, total_balls_faced = ?,
                highest_score = ?, fours = ?, sixes = ?, fifties = ?, hundreds = ?,
                innings_batted = ?, wickets_taken = ?, best_bowling_wickets = ?, best_bowling_runs = ?,
                runs_conceded = ?, overs_bowled = ?, innings_bowled = ?,
                tournaments_played = ?, tournaments_won = ?, potm_count = ?, player_of_tournament_count = ?
            WHERE player_id = ? AND format = ?
        """, (
            ps["matches_played"], ps["matches_won"], ps["total_runs"], ps["total_balls_faced"],
            ps["highest_score"], ps["fours"], ps["sixes"], ps["fifties"], ps["hundreds"],
            ps["innings_batted"], ps["wickets_taken"], ps["best_bowling_wickets"], ps["best_bowling_runs"],
            ps["runs_conceded"], overs_f, ps["innings_bowled"],
            ps["tournaments_played"], ps["tournaments_won"], ps["potm_count"], ps["player_of_tournament_count"],
            pid, fmt
        ))

    conn.commit()
    conn.close()
    print("Database rebuild complete!")

if __name__ == '__main__':
    # Resolve database path dynamically
    db_url = os.environ.get("DATABASE_URL")
    db_path = None
    if db_url and db_url.startswith("sqlite://"):
        db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    
    candidates = [
        db_path,
        os.path.expanduser("~/data/cricket.db"),
        "/home/ecricket2026/data/cricket.db",
        "cricket_prod.db",
        "cricket.db"
    ]
    
    processed = set()
    for path in candidates:
        if path and os.path.exists(path):
            abs_path = os.path.abspath(path)
            if abs_path not in processed:
                rebuild_database(abs_path)
                processed.add(abs_path)
                
    if not processed:
        print("No database files found to clean up.")

