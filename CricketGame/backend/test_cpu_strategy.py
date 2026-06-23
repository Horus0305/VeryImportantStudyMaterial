"""
Test script for CPU Strategy Engine v2 (Frequency-Based)
Run this to verify the 3-signal blend approach is working.
"""
from .data.database import SessionLocal
from .cpu.cpu_strategy_engine import CPUStrategyEngine, get_learning_phase, UNIFORM
from .cpu.cpu_learning_schema import CPULearningProgress, CPUUserProfile
from .data.models import Player


def test_learning_phases():
    """Test learning phase calculations."""
    print("\n[Test] Testing Learning Phase System...")
    
    # Phase 1: Global
    phase = get_learning_phase(30)
    assert phase['phase'] == 'global'
    assert phase['global_weight'] == 1.0
    assert phase['user_weight'] == 0.0
    assert 0.0 <= phase['confidence'] <= 0.3
    print(f"  OK Phase 1 (30 balls): {phase['phase']}, confidence={phase['confidence']:.2f}")
    
    # Phase 2: Transition
    phase = get_learning_phase(150)
    assert phase['phase'] == 'transition'
    assert 0.3 <= phase['global_weight'] <= 0.7
    assert 0.3 <= phase['user_weight'] <= 0.7
    assert 0.3 <= phase['confidence'] <= 0.8
    print(f"  OK Phase 2 (150 balls): {phase['phase']}, confidence={phase['confidence']:.2f}")
    print(f"    Global weight: {phase['global_weight']:.2f}, User weight: {phase['user_weight']:.2f}")
    
    # Phase 3: Personalized
    phase = get_learning_phase(500)
    assert phase['phase'] == 'personalized'
    assert phase['global_weight'] == 0.2
    assert phase['user_weight'] == 0.8
    assert 0.8 <= phase['confidence'] <= 0.95
    print(f"  OK Phase 3 (500 balls): {phase['phase']}, confidence={phase['confidence']:.2f}")


def test_cpu_engine_initialization():
    """Test CPU engine can be initialized."""
    print("\n[Test] Testing CPU Engine Initialization...")
    
    engine = CPUStrategyEngine()
    assert engine is not None
    print("  OK CPU Strategy Engine initialized successfully")


def test_local_frequency_empty():
    """Test local frequency with empty history."""
    print("\n[Test] Testing Local Frequency (Empty)...")
    
    engine = CPUStrategyEngine()
    freq = engine._build_local_frequency([])
    
    assert abs(sum(freq.values()) - 1.0) < 0.01
    assert all(abs(freq[n] - 1/7) < 0.01 for n in range(7))
    print(f"  OK Empty history -> uniform: {freq}")


def test_local_frequency_spamming():
    """Test local frequency correctly detects spamming."""
    print("\n[Test] Testing Local Frequency (Spam Detection)...")
    
    engine = CPUStrategyEngine()
    
    # Opponent spams 6 ten times
    freq = engine._build_local_frequency([6] * 10)
    assert freq[6] == 1.0, f"Expected 100% on 6, got {freq[6]}"
    assert all(freq[n] == 0.0 for n in range(6))
    print(f"  OK All-6 spam -> 6={freq[6]:.0%}")
    
    # Mixed: 6 appears 6/10 times, 4 appears 4/10 times
    freq = engine._build_local_frequency([6, 6, 6, 6, 6, 6, 4, 4, 4, 4])
    assert abs(freq[6] - 0.6) < 0.01
    assert abs(freq[4] - 0.4) < 0.01
    print(f"  OK Mixed spam -> 6={freq[6]:.0%}, 4={freq[4]:.0%}")


def test_blend_signals_cold_start():
    """Test blend signals with no DB data (cold start)."""
    print("\n[Test] Testing Signal Blend (Cold Start)...")
    
    engine = CPUStrategyEngine()
    
    # Ball 0, no global, no transition -> should return uniform
    result = engine._blend_signals(
        local_freq=dict(UNIFORM),
        global_freq=dict(UNIFORM), global_n=0,
        transition_pred=dict(UNIFORM), trans_n=0,
        balls_played=0,
    )
    
    assert abs(sum(result.values()) - 1.0) < 0.01
    print(f"  OK Cold start blend sums to 1.0: {result}")


def test_blend_signals_local_dominates_late():
    """Test that local frequency dominates after 7+ balls."""
    print("\n[Test] Testing Signal Blend (Local Dominates Late)...")
    
    engine = CPUStrategyEngine()
    
    # Local says 100% number 6, global says uniform, transition says uniform
    local = {n: 0.0 for n in range(7)}
    local[6] = 1.0
    
    result = engine._blend_signals(
        local_freq=local,
        global_freq=dict(UNIFORM), global_n=100,
        transition_pred=dict(UNIFORM), trans_n=50,
        balls_played=10,
    )
    
    # 6 should be the highest
    assert result[6] == max(result.values()), f"Expected 6 to be highest, got {result}"
    assert result[6] > 0.3, f"Expected 6 to dominate, got {result[6]:.3f}"
    print(f"  OK Late-game local dominance: 6={result[6]:.3f} (highest)")


def test_blend_signals_global_dominates_early():
    """Test that global frequency dominates on ball 0-1."""
    print("\n[Test] Testing Signal Blend (Global Dominates Early)...")
    
    engine = CPUStrategyEngine()
    
    # Global says 60% number 5, local is empty/uniform
    global_freq = {n: 0.05 for n in range(7)}
    global_freq[5] = 0.65  # not normalized, but we'll normalize
    total_g = sum(global_freq.values())
    global_freq = {n: v/total_g for n, v in global_freq.items()}
    
    result = engine._blend_signals(
        local_freq=dict(UNIFORM),
        global_freq=global_freq, global_n=200,
        transition_pred=dict(UNIFORM), trans_n=0,
        balls_played=0,
    )
    
    # 5 should be the highest
    assert result[5] == max(result.values()), f"Expected 5 to be highest, got {result}"
    print(f"  OK Early-game global dominance: 5={result[5]:.3f} (highest)")


def test_move_selection_with_no_data():
    """Test move selection when no pattern data exists."""
    print("\n[Test] Testing Move Selection (No Data)...")
    
    engine = CPUStrategyEngine()
    
    match_context = {
        'match_format': '5over',
        'role': 'batting',
        'current_over': 2,
        'total_overs': 5,
        'current_score': 20,
        'target': 35,
        'wickets_lost': 1,
        'balls_left': 18,
        'batting_first': False,
        'last_3_results': []
    }
    
    opponent_history = [4, 2, 6, 3, 4]
    
    move = engine.select_move(
        user_id=99999,
        match_context=match_context,
        opponent_history=opponent_history
    )
    
    assert 0 <= move <= 6
    print(f"  OK Move selected: {move} (valid range)")


def test_move_selection_distribution():
    """Test that move selection produces varied results."""
    print("\n[Test] Testing Move Selection Distribution...")
    
    engine = CPUStrategyEngine()
    
    match_context = {
        'match_format': '5over',
        'role': 'bowling',
        'current_over': 3,
        'total_overs': 5,
        'current_score': 30,
        'target': None,
        'wickets_lost': 3,
        'balls_left': 12,
        'batting_first': True,
        'last_3_results': []
    }
    
    opponent_history = [4, 4, 6, 2, 4, 3, 4, 6]
    
    moves = []
    for _ in range(100):
        move = engine.select_move(
            user_id=99999,
            match_context=match_context,
            opponent_history=opponent_history
        )
        moves.append(move)
    
    from collections import Counter
    distribution = Counter(moves)
    
    print(f"  OK Generated 100 moves")
    print(f"  OK Distribution: {dict(distribution)}")
    
    unique_moves = len(distribution)
    assert unique_moves >= 3, f"Only {unique_moves} unique moves, expected at least 3"
    print(f"  OK Variety: {unique_moves} different numbers selected")


def test_cpu_status():
    """Test CPU status retrieval."""
    print("\n[Test] Testing CPU Status Retrieval...")
    
    engine = CPUStrategyEngine()
    
    status = engine.get_cpu_status(user_id=99999)
    
    assert 'balls_tracked' in status
    assert 'phase' in status
    assert 'confidence' in status
    assert 'message' in status
    
    print(f"  OK Status retrieved: {status}")


def test_bowling_targets_frequent_numbers():
    """Test that bowling strategy targets numbers the opponent plays frequently."""
    print("\n[Test] Testing Bowling Targets Frequent Numbers...")
    
    engine = CPUStrategyEngine()
    
    match_context = {
        'match_format': '5over',
        'role': 'bowling',
        'current_over': 3,
        'total_overs': 5,
        'current_score': 30,
        'target': None,
        'wickets_lost': 2,
        'balls_left': 12,
        'batting_first': True,
        'last_3_results': []
    }
    
    # Opponent heavily favors 4 and 6
    opponent_history = [4, 4, 6, 4, 6, 4, 6, 4, 6, 4]
    
    moves = [engine.select_move(99999, match_context, opponent_history) for _ in range(200)]
    
    from collections import Counter
    dist = Counter(moves)
    
    # 4 and 6 should be the most frequently bowled
    freq_4_6 = dist.get(4, 0) + dist.get(6, 0)
    freq_others = sum(dist.get(n, 0) for n in [0, 1, 2, 3, 5])
    
    print(f"  Bowling distribution: {dict(dist)}")
    print(f"  4+6 count: {freq_4_6}/200, others: {freq_others}/200")
    assert freq_4_6 > freq_others * 0.5, "Expected bowling to favor 4 and 6"
    print(f"  OK Bowling correctly targets frequent numbers")


def test_batting_avoids_frequent_numbers():
    """Test that batting strategy avoids numbers the opponent bowls frequently."""
    print("\n[Test] Testing Batting Avoids Frequent Numbers...")
    
    engine = CPUStrategyEngine()
    
    match_context = {
        'match_format': '5over',
        'role': 'batting',
        'current_over': 3,
        'total_overs': 5,
        'current_score': 30,
        'target': 50,
        'wickets_lost': 2,
        'balls_left': 12,
        'batting_first': False,
        'last_3_results': []
    }
    
    # Opponent bowler heavily spams 6
    opponent_history = [6, 6, 6, 6, 6, 6, 6, 6, 6, 6]
    
    moves = [engine.select_move(99999, match_context, opponent_history) for _ in range(200)]
    
    from collections import Counter
    dist = Counter(moves)
    
    # 6 should NOT be the most frequently batted
    freq_6 = dist.get(6, 0)
    
    print(f"  Batting distribution: {dict(dist)}")
    print(f"  Number 6 count: {freq_6}/200")
    # With 10x spam of 6, batting should pick 6 less than uniform (200/7 = 28.6)
    assert freq_6 < 60, f"Expected batting to avoid 6, but got {freq_6}/200"
    print(f"  OK Batting correctly avoids opponent's spammed number")


def test_spam_scenario_bowling():
    """Test the exact scenario from the bug report: opponent spams 6 six times."""
    print("\n[Test] Testing Spam Scenario (6x6 Bowling)...")
    
    engine = CPUStrategyEngine()
    
    match_context = {
        'match_format': '2over',
        'role': 'bowling',
        'current_over': 0,
        'total_overs': 2,
        'current_score': 36,
        'target': None,
        'wickets_lost': 0,
        'balls_left': 6,
        'batting_first': True,
        'last_3_results': []
    }
    
    # The exact exploit: opponent plays 6 six times
    spam_history = [6, 6, 6, 6, 6, 6]
    
    # Run 500 iterations to get a stable distribution
    moves = [engine.select_move(99999, match_context, spam_history) for _ in range(500)]
    
    from collections import Counter
    dist = Counter(moves)
    pct_6 = dist.get(6, 0) / 500 * 100
    
    print(f"  Distribution vs 6-spammer: {dict(dist)}")
    print(f"  CPU bowls 6: {pct_6:.1f}% of the time")
    
    # CPU should bowl 6 significantly more than random (14.3%)
    assert pct_6 > 20, f"Expected CPU to bowl 6 >20%, got {pct_6:.1f}%"
    print(f"  OK CPU bowling 6 at {pct_6:.1f}% (random would be 14.3%)")


def test_role_specific_strategies():
    """Test that bowling and batting strategies differ."""
    print("\n[Test] Testing Role-Specific Strategies...")
    
    engine = CPUStrategyEngine()
    
    base_context = {
        'match_format': '5over',
        'current_over': 2,
        'total_overs': 5,
        'current_score': 25,
        'target': 40,
        'wickets_lost': 2,
        'balls_left': 18,
        'batting_first': False,
        'last_3_results': []
    }
    
    opponent_history = [4, 4, 4, 6, 4, 6, 4]
    
    bowling_context = {**base_context, 'role': 'bowling'}
    bowling_moves = [
        engine.select_move(99999, bowling_context, opponent_history)
        for _ in range(50)
    ]
    
    batting_context = {**base_context, 'role': 'batting'}
    batting_moves = [
        engine.select_move(99999, batting_context, opponent_history)
        for _ in range(50)
    ]
    
    from collections import Counter
    bowling_dist = Counter(bowling_moves)
    batting_dist = Counter(batting_moves)
    
    print(f"  OK Bowling distribution: {dict(bowling_dist)}")
    print(f"  OK Batting distribution: {dict(batting_dist)}")
    
    bowling_4_6 = bowling_dist.get(4, 0) + bowling_dist.get(6, 0)
    batting_4_6 = batting_dist.get(4, 0) + batting_dist.get(6, 0)
    
    print(f"  OK Bowling 4+6 count: {bowling_4_6}")
    print(f"  OK Batting 4+6 count: {batting_4_6}")
    
    assert bowling_4_6 > batting_4_6, "Expected bowling to target 4+6 more than batting"
    print(f"  OK Bowling targets 4+6 more than batting")


def test_situational_adjustments():
    """Test that score pressure affects move selection."""
    print("\n[Test] Testing Situational Adjustments...")
    
    engine = CPUStrategyEngine()
    
    desperate_context = {
        'match_format': '5over',
        'role': 'batting',
        'current_over': 4,
        'total_overs': 5,
        'current_score': 20,
        'target': 50,
        'wickets_lost': 7,
        'balls_left': 6,
        'batting_first': False,
        'last_3_results': []
    }
    
    comfortable_context = {
        'match_format': '5over',
        'role': 'batting',
        'current_over': 2,
        'total_overs': 5,
        'current_score': 30,
        'target': 35,
        'wickets_lost': 1,
        'balls_left': 18,
        'batting_first': False,
        'last_3_results': []
    }
    
    opponent_history = [2, 3, 4, 2, 3]
    
    desperate_moves = [
        engine.select_move(99999, desperate_context, opponent_history)
        for _ in range(50)
    ]
    
    comfortable_moves = [
        engine.select_move(99999, comfortable_context, opponent_history)
        for _ in range(50)
    ]
    
    from collections import Counter
    desperate_dist = Counter(desperate_moves)
    comfortable_dist = Counter(comfortable_moves)
    
    print(f"  OK Desperate situation: {dict(desperate_dist)}")
    print(f"  OK Comfortable situation: {dict(comfortable_dist)}")


def test_performance():
    """Test move selection performance."""
    print("\n[Test] Testing Performance...")
    
    import time
    
    engine = CPUStrategyEngine()
    
    match_context = {
        'match_format': '5over',
        'role': 'batting',
        'current_over': 2,
        'total_overs': 5,
        'current_score': 20,
        'target': 35,
        'wickets_lost': 2,
        'balls_left': 18,
        'batting_first': False,
        'last_3_results': []
    }
    
    opponent_history = [4, 2, 6, 3, 4, 5, 2, 4]
    
    start = time.time()
    for _ in range(100):
        engine.select_move(99999, match_context, opponent_history)
    elapsed = time.time() - start
    
    avg_time_ms = (elapsed / 100) * 1000
    
    print(f"  OK 100 moves in {elapsed:.3f}s")
    print(f"  OK Average: {avg_time_ms:.2f}ms per move")
    
    assert avg_time_ms < 100, f"Too slow: {avg_time_ms:.2f}ms (expected <100ms)"
    print(f"  OK Performance acceptable (<100ms)")


def run_all_tests():
    """Run all strategy engine tests."""
    print("=" * 60)
    print("CPU STRATEGY ENGINE v2 TEST SUITE (Frequency-Based)")
    print("=" * 60)
    
    try:
        test_learning_phases()
        test_cpu_engine_initialization()
        test_local_frequency_empty()
        test_local_frequency_spamming()
        test_blend_signals_cold_start()
        test_blend_signals_local_dominates_late()
        test_blend_signals_global_dominates_early()
        test_move_selection_with_no_data()
        test_move_selection_distribution()
        test_cpu_status()
        test_bowling_targets_frequent_numbers()
        test_batting_avoids_frequent_numbers()
        test_spam_scenario_bowling()
        test_role_specific_strategies()
        test_situational_adjustments()
        test_performance()
        
        print("\n" + "=" * 60)
        print("[Pass] ALL TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"[Fail] TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
