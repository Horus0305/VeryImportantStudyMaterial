import sqlite3

def main():
    conn = sqlite3.connect('cricket.db')
    c = conn.cursor()

    # Find all tournaments in Season 2 (after 2026-07-20)
    c.execute("""
        SELECT tournament_id, timestamp, champion 
        FROM tournament_history 
        WHERE timestamp >= '2026-07-20' 
        ORDER BY timestamp ASC
    """)
    rows = c.fetchall()

    if not rows:
        print("No tournaments found in Season 2 (on or after 2026-07-20).")
        conn.close()
        return

    print("Season 2 tournaments found:")
    for idx, (tid, ts, champ) in enumerate(rows, 1):
        print(f"{idx}. ID: {tid} | Time: {ts} | Champion: {champ}")

    # The first tournament of Season 2 is the oldest one (index 0)
    target_tid, target_ts, target_champ = rows[0]
    print(f"\nTargeting first Season 2 tournament for deletion:")
    print(f"ID: {target_tid} | Time: {target_ts} | Champion: {target_champ}")

    # Delete matches of this tournament
    c.execute("DELETE FROM match_history WHERE tournament_id = ?", (target_tid,))
    matches_deleted = c.rowcount
    print(f"Deleted {matches_deleted} matches from match_history.")

    # Delete the tournament itself
    c.execute("DELETE FROM tournament_history WHERE tournament_id = ?", (target_tid,))
    print(f"Deleted tournament {target_tid} from tournament_history.")

    conn.commit()
    conn.close()
    print("Database commit successful. Done!")

if __name__ == '__main__':
    main()
