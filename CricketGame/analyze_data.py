"""Analyze ball-by-ball data from production database with player names."""
import sqlite3
import sys
import io
from collections import Counter, defaultdict

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

for db_name in ['cricket_prod.db', 'cricket.db']:
    print(f"\n{'='*70}")
    print(f"DATABASE: {db_name}")
    print(f"{'='*70}")
    try:
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as e:
        print(f"  Could not open: {e}")
        continue

    # Check tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    if 'match_ball_log' not in tables or 'players' not in tables:
        print("  Missing required tables")
        conn.close()
        continue

    # Build player name map
    cur.execute("SELECT id, username FROM players")
    name_map = {r[0]: r[1] for r in cur.fetchall()}
    name_map[-1] = "CPU"
    def pname(uid):
        return name_map.get(uid, f"Unknown({uid})")

    cur.execute("SELECT COUNT(*) FROM match_ball_log")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT match_id) FROM match_ball_log")
    total_matches = cur.fetchone()[0]
    print(f"\nTotal balls: {total} | Total matches: {total_matches}")

    # Unique human players
    cur.execute("SELECT DISTINCT batter_user_id FROM match_ball_log WHERE batter_user_id != -1 UNION SELECT DISTINCT bowler_user_id FROM match_ball_log WHERE bowler_user_id != -1")
    all_humans = sorted([r[0] for r in cur.fetchall()])
    print(f"Players: {', '.join(pname(uid) for uid in all_humans)}")

    # ── BATTING DISTRIBUTIONS ────────────────────────────────────────────
    print(f"\n--- BATTING MOVE DISTRIBUTIONS ---")
    print(f"{'Player':<16} {'Balls':>5}  {'0':>5} {'1':>5} {'2':>5} {'3':>5} {'4':>5} {'5':>5} {'6':>5}  Style")
    cur.execute("""
        SELECT batter_user_id, bat_move, COUNT(*) as cnt
        FROM match_ball_log WHERE batter_user_id != -1
        GROUP BY batter_user_id, bat_move ORDER BY batter_user_id, bat_move
    """)
    user_bat = defaultdict(lambda: {i: 0 for i in range(7)})
    for row in cur.fetchall():
        user_bat[row[0]][row[1]] = row[2]
    for uid in sorted(user_bat.keys()):
        dist = user_bat[uid]
        total_moves = sum(dist.values())
        pcts = {k: v/total_moves*100 for k, v in dist.items()}
        # Determine style
        high_pct = pcts[4] + pcts[5] + pcts[6]
        top_num = max(pcts, key=pcts.get)
        if high_pct > 75:
            style = "Pure aggro"
        elif high_pct > 60:
            style = f"High-heavy ({top_num}-lover)"
        elif pcts[0] > 20:
            style = "0-mixer"
        else:
            style = "Balanced"
        print(f"{pname(uid):<16} {total_moves:>5}  {pcts[0]:>4.0f}% {pcts[1]:>4.0f}% {pcts[2]:>4.0f}% {pcts[3]:>4.0f}% {pcts[4]:>4.0f}% {pcts[5]:>4.0f}% {pcts[6]:>4.0f}%  {style}")

    # ── BOWLING DISTRIBUTIONS ────────────────────────────────────────────
    print(f"\n--- BOWLING MOVE DISTRIBUTIONS ---")
    print(f"{'Player':<16} {'Balls':>5}  {'0':>5} {'1':>5} {'2':>5} {'3':>5} {'4':>5} {'5':>5} {'6':>5}")
    cur.execute("""
        SELECT bowler_user_id, bowl_move, COUNT(*) as cnt
        FROM match_ball_log WHERE bowler_user_id != -1
        GROUP BY bowler_user_id, bowl_move ORDER BY bowler_user_id, bowl_move
    """)
    user_bowl = defaultdict(lambda: {i: 0 for i in range(7)})
    for row in cur.fetchall():
        user_bowl[row[0]][row[1]] = row[2]
    for uid in sorted(user_bowl.keys()):
        dist = user_bowl[uid]
        total_moves = sum(dist.values())
        pcts = {k: v/total_moves*100 for k, v in dist.items()}
        print(f"{pname(uid):<16} {total_moves:>5}  {pcts[0]:>4.0f}% {pcts[1]:>4.0f}% {pcts[2]:>4.0f}% {pcts[3]:>4.0f}% {pcts[4]:>4.0f}% {pcts[5]:>4.0f}% {pcts[6]:>4.0f}%")

    # ── STREAKS ──────────────────────────────────────────────────────────
    print(f"\n--- STREAK ANALYSIS (consecutive same number, batting) ---")
    cur.execute("""
        SELECT match_id, batter_user_id, bat_move, ball_number
        FROM match_ball_log WHERE batter_user_id != -1
        ORDER BY match_id, ball_number
    """)
    rows = cur.fetchall()
    streaks = []
    prev_match, prev_user, prev_move, streak_len = None, None, None, 0
    for r in rows:
        mid, uid, move, bnum = r
        if mid == prev_match and uid == prev_user and move == prev_move:
            streak_len += 1
        else:
            if streak_len >= 3:
                streaks.append((prev_match, prev_user, prev_move, streak_len))
            streak_len = 1
        prev_match, prev_user, prev_move = mid, uid, move
    if streak_len >= 3:
        streaks.append((prev_match, prev_user, prev_move, streak_len))

    if streaks:
        for s in sorted(streaks, key=lambda x: -x[3]):
            print(f"  {pname(s[1]):<14} played {s[2]} x{s[3]} in a row (match {s[0][:8]})")
    else:
        print(f"  None found")

    # ── STREAKS (BOWLING) ────────────────────────────────────────────────
    print(f"\n--- STREAK ANALYSIS (consecutive same number, bowling) ---")
    cur.execute("""
        SELECT match_id, bowler_user_id, bowl_move, ball_number
        FROM match_ball_log WHERE bowler_user_id != -1
        ORDER BY match_id, ball_number
    """)
    rows = cur.fetchall()
    streaks_b = []
    prev_match, prev_user, prev_move, streak_len = None, None, None, 0
    for r in rows:
        mid, uid, move, bnum = r
        if mid == prev_match and uid == prev_user and move == prev_move:
            streak_len += 1
        else:
            if streak_len >= 3:
                streaks_b.append((prev_match, prev_user, prev_move, streak_len))
            streak_len = 1
        prev_match, prev_user, prev_move = mid, uid, move
    if streak_len >= 3:
        streaks_b.append((prev_match, prev_user, prev_move, streak_len))

    if streaks_b:
        for s in sorted(streaks_b, key=lambda x: -x[3]):
            print(f"  {pname(s[1]):<14} bowled {s[2]} x{s[3]} in a row (match {s[0][:8]})")
    else:
        print(f"  None found")

    # ── PATTERN ANALYSIS ─────────────────────────────────────────────────
    print(f"\n--- REPEATING PATTERNS (batting) ---")
    cur.execute("""
        SELECT match_id, batter_user_id, bat_move
        FROM match_ball_log WHERE batter_user_id != -1
        ORDER BY match_id, ball_number
    """)
    rows = cur.fetchall()
    match_seqs = defaultdict(list)
    for r in rows:
        match_seqs[(r[0], r[1])].append(r[2])

    pattern_examples = defaultdict(list)  # pattern -> [(match, player)]
    for (mid, uid), seq in match_seqs.items():
        if len(seq) < 4:
            continue
        for i in range(len(seq) - 3):
            p = (seq[i], seq[i+1])
            if seq[i+2] == p[0] and seq[i+3] == p[1]:
                pattern_examples[p].append((mid[:8], pname(uid)))
        for i in range(len(seq) - 5):
            p = (seq[i], seq[i+1], seq[i+2])
            if seq[i+3] == p[0] and seq[i+4] == p[1] and seq[i+5] == p[2]:
                pattern_examples[p].append((mid[:8], pname(uid)))

    if pattern_examples:
        for pat, examples in sorted(pattern_examples.items(), key=lambda x: -len(x[1]))[:15]:
            who = ", ".join(f"{e[1]}" for e in examples[:3])
            print(f"  {str(pat):<20} x{len(examples)}  by {who}")
    else:
        print(f"  No repeating patterns found")

    # ── CPU EFFECTIVENESS ────────────────────────────────────────────────
    print(f"\n--- CPU EFFECTIVENESS ---")
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN is_out=1 THEN 1 ELSE 0 END) FROM match_ball_log WHERE bowler_user_id=-1")
    row = cur.fetchone()
    if row and row[0] > 0:
        print(f"  CPU bowling: {row[0]} balls, {row[1]} wickets ({row[1]/row[0]*100:.1f}% wicket rate)")
        print(f"  Random baseline: 14.3% (1/7)")
        print(f"  CPU advantage: {row[1]/row[0]*100 - 14.3:+.1f}%")
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN is_out=1 THEN 1 ELSE 0 END) FROM match_ball_log WHERE batter_user_id=-1")
    row = cur.fetchone()
    if row and row[0] > 0:
        print(f"  CPU batting: {row[0]} balls, {row[1]} outs ({row[1]/row[0]*100:.1f}% out rate)")
        print(f"  Random baseline: 14.3%")
        print(f"  CPU advantage: {14.3 - row[1]/row[0]*100:+.1f}% (lower is better)")

    # ── CPU MOVE DISTRIBUTIONS ───────────────────────────────────────────
    print(f"\n--- CPU MOVE DISTRIBUTIONS ---")
    cur.execute("SELECT bowl_move, COUNT(*) FROM match_ball_log WHERE bowler_user_id=-1 GROUP BY bowl_move ORDER BY bowl_move")
    rows = cur.fetchall()
    if rows:
        total_cpu = sum(r[1] for r in rows)
        print(f"  CPU bowling ({total_cpu} balls): {', '.join(f'{r[0]}={r[1]/total_cpu*100:.0f}%' for r in rows)}")
    cur.execute("SELECT bat_move, COUNT(*) FROM match_ball_log WHERE batter_user_id=-1 GROUP BY bat_move ORDER BY bat_move")
    rows = cur.fetchall()
    if rows:
        total_cpu = sum(r[1] for r in rows)
        print(f"  CPU batting ({total_cpu} balls): {', '.join(f'{r[0]}={r[1]/total_cpu*100:.0f}%' for r in rows)}")

    # ── TRANSITION MATRIX ────────────────────────────────────────────────
    print(f"\n--- TRANSITION MATRIX (after X, what do players bat next?) ---")
    print(f"{'After':<7} {'->0':>5} {'->1':>5} {'->2':>5} {'->3':>5} {'->4':>5} {'->5':>5} {'->6':>5}")
    cur.execute("""
        SELECT match_id, batter_user_id, bat_move
        FROM match_ball_log WHERE batter_user_id != -1
        ORDER BY match_id, ball_number
    """)
    rows = cur.fetchall()
    transitions = defaultdict(lambda: defaultdict(int))
    prev_match2, prev_user2, prev_move2 = None, None, None
    for r in rows:
        mid, uid, move = r
        if mid == prev_match2 and uid == prev_user2 and prev_move2 is not None:
            transitions[prev_move2][move] += 1
        prev_match2, prev_user2, prev_move2 = mid, uid, move

    for from_move in range(7):
        if from_move in transitions:
            total_t = sum(transitions[from_move].values())
            pcts = [f"{transitions[from_move].get(to, 0)/total_t*100:>4.0f}%" for to in range(7)]
            print(f"  {from_move:<7} {' '.join(pcts)}")

    # ── PER-PLAYER TRANSITION (top players) ──────────────────────────────
    print(f"\n--- PER-PLAYER TRANSITIONS (batting, after 6 -> what?) ---")
    cur.execute("""
        SELECT match_id, batter_user_id, bat_move
        FROM match_ball_log WHERE batter_user_id != -1
        ORDER BY batter_user_id, match_id, ball_number
    """)
    rows = cur.fetchall()
    player_trans = defaultdict(lambda: defaultdict(int))
    prev_uid, prev_mid, prev_mv = None, None, None
    for r in rows:
        mid, uid, move = r
        if uid == prev_uid and mid == prev_mid and prev_mv == 6:
            player_trans[uid][move] += 1
        prev_uid, prev_mid, prev_mv = uid, mid, move

    for uid in sorted(player_trans.keys()):
        total_t = sum(player_trans[uid].values())
        if total_t < 3:
            continue
        pcts = [f"{player_trans[uid].get(to, 0)/total_t*100:.0f}%" for to in range(7)]
        print(f"  {pname(uid):<14} after 6 -> {', '.join(f'{to}:{p}' for to, p in zip(range(7), pcts))}  (n={total_t})")

    # ── WICKET ANALYSIS: what numbers get players out most? ──────────────
    print(f"\n--- WHAT NUMBERS GET PLAYERS OUT? (batting) ---")
    print(f"{'Player':<16} {'Balls':>5} {'Outs':>4}  Most deadly numbers")
    cur.execute("""
        SELECT batter_user_id, bat_move, COUNT(*) as cnt
        FROM match_ball_log
        WHERE batter_user_id != -1 AND is_out = 1
        GROUP BY batter_user_id, bat_move
        ORDER BY batter_user_id, cnt DESC
    """)
    out_by_num = defaultdict(lambda: defaultdict(int))
    for row in cur.fetchall():
        out_by_num[row[0]][row[1]] = row[2]

    for uid in sorted(out_by_num.keys()):
        total_outs = sum(out_by_num[uid].values())
        total_balls = sum(user_bat.get(uid, {}).values())
        deadly = sorted(out_by_num[uid].items(), key=lambda x: -x[1])[:3]
        deadly_str = ", ".join(f"{n}(x{c})" for n, c in deadly)
        print(f"  {pname(uid):<14} {total_balls:>5} {total_outs:>4}  {deadly_str}")

    conn.close()

print("\nDone.")
