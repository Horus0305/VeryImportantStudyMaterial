"""
Backtesting script for CPU Strategy Engine v2.
Replays matches from the database ball-by-ball and calculates the expected
hit/out rates of the new frequency-based blend engine vs the actual historical CPU performance.
"""
import sqlite3
import os
from collections import defaultdict
from backend.cpu.cpu_strategy_engine import CPUStrategyEngine

def run_backtest(db_path):
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist.")
        return

    print(f"\n=============================================================")
    print(f"RUNNING BACKTEST ON DATABASE: {db_path}")
    print(f"=============================================================")

    # Initialize CPU strategy engine
    # We will bypass the database Session during select_move by mocking the db loaders
    # to avoid needing a live SQLAlchemy transaction for every single ball.
    engine = CPUStrategyEngine()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Load all user profiles from the database to use as the global frequency signal.
    # User profiles map: (user_id, match_format) -> profile_dict
    user_profiles = {}
    try:
        cur.execute("SELECT * FROM cpu_user_profiles")
        for row in cur.fetchall():
            user_profiles[(row['user_id'], row['match_format'])] = dict(row)
    except sqlite3.OperationalError:
        print("cpu_user_profiles table not found or empty.")

    # Load all sequence patterns from the database to use as the transition prediction signal.
    # Sequence patterns map: (user_id, match_format, role, previous_move) -> pattern_dict
    seq_patterns = {}
    try:
        cur.execute("SELECT * FROM cpu_sequence_patterns WHERE previous_result = 'scored'")
        for row in cur.fetchall():
            key = (row['user_id'], row['match_format'], row['role'], row['previous_move'])
            seq_patterns[key] = dict(row)
    except sqlite3.OperationalError:
        print("cpu_sequence_patterns table not found or empty.")

    # Load all learning progress to know total balls tracked per user
    learning_progress = {}
    try:
        cur.execute("SELECT * FROM cpu_learning_progress")
        for row in cur.fetchall():
            learning_progress[row['user_id']] = row['total_balls_tracked']
    except sqlite3.OperationalError:
        pass

    # Mock DB loaders on our engine instance to use these in-memory dicts
    # This prevents SQLAlchemy session overhead and speeds up the backtest 100x.
    def mock_load_user_patterns(db, user_id, context):
        if user_id == -1:
            return {i: 1.0/7 for i in range(7)}, 0
        profile = user_profiles.get((user_id, context['match_format']))
        if not profile:
            return {i: 1.0/7 for i in range(7)}, 0
        
        if context['role'] == 'bowling':
            if profile.get('total_balls_faced', 0) < 10:
                return {i: 1.0/7 for i in range(7)}, 0
            return {
                0: profile.get('bat_num_0_freq', 0.0),
                1: profile.get('bat_num_1_freq', 0.0),
                2: profile.get('bat_num_2_freq', 0.0),
                3: profile.get('bat_num_3_freq', 0.0),
                4: profile.get('bat_num_4_freq', 0.0),
                5: profile.get('bat_num_5_freq', 0.0),
                6: profile.get('bat_num_6_freq', 0.0),
            }, profile.get('total_balls_faced', 0)
        else:
            if profile.get('total_balls_bowled', 0) < 10:
                return {i: 1.0/7 for i in range(7)}, 0
            return {
                0: profile.get('bowl_num_0_freq', 0.0),
                1: profile.get('bowl_num_1_freq', 0.0),
                2: profile.get('bowl_num_2_freq', 0.0),
                3: profile.get('bowl_num_3_freq', 0.0),
                4: profile.get('bowl_num_4_freq', 0.0),
                5: profile.get('bowl_num_5_freq', 0.0),
                6: profile.get('bowl_num_6_freq', 0.0),
            }, profile.get('total_balls_bowled', 0)

    def mock_load_sequence_patterns(db, user_id, context, opponent_history):
        if user_id == -1 or not opponent_history:
            return {i: 1.0/7 for i in range(7)}, 0
        last_move = opponent_history[-1]
        opponent_role = 'batting' if context['role'] == 'bowling' else 'bowling'
        pattern = seq_patterns.get((user_id, context['match_format'], opponent_role, last_move))
        if pattern and pattern.get('sample_count', 0) > 3:
            return {
                0: pattern.get('next_0_freq', 0.0),
                1: pattern.get('next_1_freq', 0.0),
                2: pattern.get('next_2_freq', 0.0),
                3: pattern.get('next_3_freq', 0.0),
                4: pattern.get('next_4_freq', 0.0),
                5: pattern.get('next_5_freq', 0.0),
                6: pattern.get('next_6_freq', 0.0),
            }, pattern.get('sample_count', 0)
        return {i: 1.0/7 for i in range(7)}, 0

    def mock_get_total_balls_tracked(db, user_id):
        return learning_progress.get(user_id, 0)

    engine._load_user_patterns = mock_load_user_patterns
    engine._load_sequence_patterns = mock_load_sequence_patterns
    engine._get_total_balls_tracked = mock_get_total_balls_tracked

    # Fetch all balls log involving the CPU
    cur.execute("""
        SELECT * FROM match_ball_log 
        WHERE (batter_user_id = -1 AND bowler_user_id != -1)
           OR (bowler_user_id = -1 AND batter_user_id != -1)
        ORDER BY match_id, innings, ball_number
    """)
    all_balls = [dict(row) for row in cur.fetchall()]
    conn.close()

    if not all_balls:
        print("No CPU vs Human balls found in database.")
        return

    # Group balls by match_id + innings to reconstruct local histories correctly
    match_innings_groups = defaultdict(list)
    for ball in all_balls:
        match_innings_groups[(ball['match_id'], ball['innings'])].append(ball)

    bowl_balls_count = 0
    bowl_wickets_actual = 0
    bowl_expected_wickets_new = 0.0

    bat_balls_count = 0
    bat_outs_actual = 0
    bat_expected_outs_new = 0.0

    for (match_id, innings), balls in match_innings_groups.items():
        # Reconstruct histories for this innings
        # Opponent batting moves seen by CPU bowler
        opponent_bat_history = []
        # Opponent bowling moves seen by CPU batter
        opponent_bowl_history = []

        for ball in balls:
            # Reconstruct match context
            match_format = ball['match_format']
            is_out = ball['is_out']
            bat_move = ball['bat_move']
            bowl_move = ball['bowl_move']

            # Context dict needed by engine
            context = {
                'match_format': match_format,
                'current_over': ball['current_over'],
                'total_overs': ball['total_overs'],
                'current_score': ball['batting_score'],
                'target': ball['target'],
                'wickets_lost': ball['batting_wickets'],
                'balls_left': ball['balls_remaining'],
                'batting_first': ball['target'] is None,
                'last_3_results': []
            }

            if ball['bowler_user_id'] == -1:
                # CPU is BOWLING, opponent is BATTING
                opponent_id = ball['batter_user_id']
                context['role'] = 'bowling'

                # Calculate CPU strategy distribution
                # Bypass DB sessions
                local_freq = engine._build_local_frequency(opponent_bat_history)
                global_freq, global_n = engine._load_user_patterns(None, opponent_id, context)
                transition_pred, trans_n = engine._load_sequence_patterns(None, opponent_id, context, opponent_bat_history)
                total_balls = engine._get_total_balls_tracked(None, opponent_id)
                from backend.cpu.cpu_strategy_engine import get_learning_phase, MAX_CONF
                phase_info = get_learning_phase(total_balls)
                confidence = min(phase_info['confidence'], MAX_CONF)

                prediction = engine._blend_signals(
                    local_freq, global_freq, global_n,
                    transition_pred, trans_n, len(opponent_bat_history)
                )
                # Get CPU's target distribution
                cpu_bowl_dist = engine._bowling_strategy(prediction, context, confidence)

                # Wicket happens if CPU bowl_move matches batter's bat_move
                # Expected probability of taking wicket:
                prob_wicket = cpu_bowl_dist.get(bat_move, 1.0/7)
                bowl_expected_wickets_new += prob_wicket
                bowl_balls_count += 1
                if is_out:
                    bowl_wickets_actual += 1

                # Update local history
                opponent_bat_history.append(bat_move)

            elif ball['batter_user_id'] == -1:
                # CPU is BATTING, opponent is BOWLING
                opponent_id = ball['bowler_user_id']
                context['role'] = 'batting'

                # Calculate CPU strategy distribution
                local_freq = engine._build_local_frequency(opponent_bowl_history)
                global_freq, global_n = engine._load_user_patterns(None, opponent_id, context)
                transition_pred, trans_n = engine._load_sequence_patterns(None, opponent_id, context, opponent_bowl_history)
                total_balls = engine._get_total_balls_tracked(None, opponent_id)
                from backend.cpu.cpu_strategy_engine import get_learning_phase, MAX_CONF
                phase_info = get_learning_phase(total_balls)
                confidence = min(phase_info['confidence'], MAX_CONF)

                prediction = engine._blend_signals(
                    local_freq, global_freq, global_n,
                    transition_pred, trans_n, len(opponent_bowl_history)
                )
                # Get CPU's avoidance distribution
                cpu_bat_dist = engine._batting_strategy(prediction, context, confidence)

                # Out happens if CPU bat_move matches bowler's bowl_move
                # Expected probability of getting out:
                prob_out = cpu_bat_dist.get(bowl_move, 1.0/7)
                bat_expected_outs_new += prob_out
                bat_balls_count += 1
                if is_out:
                    bat_outs_actual += 1

                # Update local history
                opponent_bowl_history.append(bowl_move)

    print(f"Results for CPU BOWLING (Total balls = {bowl_balls_count}):")
    actual_bowl_rate = (bowl_wickets_actual / bowl_balls_count) * 100 if bowl_balls_count > 0 else 0
    expected_bowl_rate = (bowl_expected_wickets_new / bowl_balls_count) * 100 if bowl_balls_count > 0 else 0
    print(f"  Actual wicket rate (Old Engine): {actual_bowl_rate:.2f}%")
    print(f"  Expected wicket rate (New Engine v2): {expected_bowl_rate:.2f}%")
    print(f"  Random baseline: 14.29%")
    print(f"  New Engine Improvement vs Random: {expected_bowl_rate - 14.29:+.2f}%")
    print(f"  New Engine Improvement vs Old: {expected_bowl_rate - actual_bowl_rate:+.2f}%")

    print(f"\nResults for CPU BATTING (Total balls = {bat_balls_count}):")
    actual_bat_rate = (bat_outs_actual / bat_balls_count) * 100 if bat_balls_count > 0 else 0
    expected_bat_rate = (bat_expected_outs_new / bat_balls_count) * 100 if bat_balls_count > 0 else 0
    print(f"  Actual out rate (Old Engine): {actual_bat_rate:.2f}%")
    print(f"  Expected out rate (New Engine v2): {expected_bat_rate:.2f}% (lower is better)")
    print(f"  Random baseline: 14.29%")
    print(f"  New Engine Improvement vs Random: {14.29 - expected_bat_rate:+.2f}%")
    print(f"  New Engine Improvement vs Old: {actual_bat_rate - expected_bat_rate:+.2f}%")

if __name__ == "__main__":
    run_backtest("cricket_prod.db")
    run_backtest("cricket.db")
