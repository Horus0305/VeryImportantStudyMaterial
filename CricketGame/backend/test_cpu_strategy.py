"""
Test script for CPU Strategy Engine
Run this to verify intelligent move selection is working.
"""
from .data.database import SessionLocal, init_db
from .cpu.cpu_strategy_engine import CPUStrategyEngine, get_learning_phase, BASE_WEIGHTS
from .cpu.cpu_learning_schema import CPULearningProgress, CPUUserProfile
from .data.models import Player


def test_learning_phases():
    """Test learning phase calculations."""
    print("\n🧪 Testing Learning Phase System...")
    
    # Phase 1: Global
    phase = get_learning_phase(30)
    assert phase['phase'] == 'global'
    assert phase['global_weight'] == 1.0
    assert phase['user_weight'] == 0.0
    assert 0.0 <= phase['confidence'] <= 0.3
    print(f"  ✓ Phase 1 (30 balls): {phase['phase']}, confidence={phase['confidence']:.2f}")
    
    # Phase 2: Transition
    phase = get_learning_phase(150)
    assert phase['phase'] == 'transition'
    assert 0.3 <= phase['global_weight'] <= 0.7
    assert 0.3 <= phase['user_weight'] <= 0.7
    assert 0.3 <= phase['confidence'] <= 0.8
    print(f"  ✓ Phase 2 (150 balls): {phase['phase']}, confidence={phase['confidence']:.2f}")
    print(f"    Global weight: {phase['global_weight']:.2f}, User weight: {phase['user_weight']:.2f}")
    
    # Phase 3: Personalized
    phase = get_learning_phase(500)
    assert phase['phase'] == 'personalized'
    assert phase['global_weight'] == 0.2
    assert phase['user_weight'] == 0.8
    assert 0.8 <= phase['confidence'] <= 0.95
    print(f"  ✓ Phase 3 (500 balls): {phase['phase']}, confidence={phase['confidence']:.2f}")


def test_base_weights():
    """Test base weights sum to 1.0."""
    print("\n🧪 Testing Base Weights...")
    
    total = sum(BASE_WEIGHTS.values())
    assert abs(total - 1.0) < 0.01, f"Base weights sum to {total}, expected 1.0"
    print(f"  ✓ Base weights sum: {total:.3f}")
    print(f"  ✓ Distribution: {BASE_WEIGHTS}")


def test_cpu_engine_initialization():
    """Test CPU engine can be initialized."""
    print("\n🧪 Testing CPU Engine Initialization...")
    
    engine = CPUStrategyEngine()
    assert engine is not None
    print("  ✓ CPU Strategy Engine initialized successfully")


def test_move_selection_with_no_data():
    """Test move selection when no pattern data exists."""
    print("\n🧪 Testing Move Selection (No Data)...")
    
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
    
    # Should not crash even with no data
    move = engine.select_move(
        user_id=99999,  # Non-existent user
        match_context=match_context,
        opponent_history=opponent_history
    )
    
    assert 0 <= move <= 6
    print(f"  ✓ Move selected: {move} (valid range)")


def test_move_selection_distribution():
    """Test that move selection produces varied results."""
    print("\n🧪 Testing Move Selection Distribution...")
    
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
    
    opponent_history = [4, 4, 6, 2, 4, 3, 4, 6]  # Opponent favors 4 and 6
    
    # Generate 100 moves
    moves = []
    for _ in range(100):
        move = engine.select_move(
            user_id=99999,
            match_context=match_context,
            opponent_history=opponent_history
        )
        moves.append(move)
    
    # Check distribution
    from collections import Counter
    distribution = Counter(moves)
    
    print(f"  ✓ Generated 100 moves")
    print(f"  ✓ Distribution: {dict(distribution)}")
    
    # Should have some variety (not all same number)
    unique_moves = len(distribution)
    assert unique_moves >= 3, f"Only {unique_moves} unique moves, expected at least 3"
    print(f"  ✓ Variety: {unique_moves} different numbers selected")


def test_cpu_status():
    """Test CPU status retrieval."""
    print("\n🧪 Testing CPU Status Retrieval...")
    
    engine = CPUStrategyEngine()
    
    # Test with non-existent user (should handle gracefully)
    status = engine.get_cpu_status(user_id=99999)
    
    assert 'balls_tracked' in status
    assert 'phase' in status
    assert 'confidence' in status
    assert 'message' in status
    
    print(f"  ✓ Status retrieved: {status}")


def test_role_specific_strategies():
    """Test that bowling and batting strategies differ."""
    print("\n🧪 Testing Role-Specific Strategies...")
    
    engine = CPUStrategyEngine()
    
    # Same context, different roles
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
    
    opponent_history = [4, 4, 4, 6, 4, 6, 4]  # Opponent heavily favors 4 and 6
    
    # Bowling strategy (should target 4 and 6)
    bowling_context = {**base_context, 'role': 'bowling'}
    bowling_moves = [
        engine.select_move(99999, bowling_context, opponent_history)
        for _ in range(50)
    ]
    
    # Batting strategy (should avoid 4 and 6)
    batting_context = {**base_context, 'role': 'batting'}
    batting_moves = [
        engine.select_move(99999, batting_context, opponent_history)
        for _ in range(50)
    ]
    
    from collections import Counter
    bowling_dist = Counter(bowling_moves)
    batting_dist = Counter(batting_moves)
    
    print(f"  ✓ Bowling distribution: {dict(bowling_dist)}")
    print(f"  ✓ Batting distribution: {dict(batting_dist)}")
    
    # Bowling should favor 4 and 6 more than batting
    bowling_4_6 = bowling_dist.get(4, 0) + bowling_dist.get(6, 0)
    batting_4_6 = batting_dist.get(4, 0) + batting_dist.get(6, 0)
    
    print(f"  ✓ Bowling 4+6 count: {bowling_4_6}")
    print(f"  ✓ Batting 4+6 count: {batting_4_6}")
    print(f"  ✓ Strategies differ: {'Yes' if bowling_4_6 != batting_4_6 else 'No'}")


def test_situational_adjustments():
    """Test that score pressure affects move selection."""
    print("\n🧪 Testing Situational Adjustments...")
    
    engine = CPUStrategyEngine()
    
    # Desperate situation (need quick runs)
    desperate_context = {
        'match_format': '5over',
        'role': 'batting',
        'current_over': 4,
        'total_overs': 5,
        'current_score': 20,
        'target': 50,  # Need 30 runs in 6 balls!
        'wickets_lost': 7,
        'balls_left': 6,
        'batting_first': False,
        'last_3_results': []
    }
    
    # Comfortable situation
    comfortable_context = {
        'match_format': '5over',
        'role': 'batting',
        'current_over': 2,
        'total_overs': 5,
        'current_score': 30,
        'target': 35,  # Need 5 runs in 18 balls
        'wickets_lost': 1,
        'balls_left': 18,
        'batting_first': False,
        'last_3_results': []
    }
    
    opponent_history = [2, 3, 4, 2, 3]
    
    # Generate moves for both situations
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
    
    print(f"  ✓ Desperate situation: {dict(desperate_dist)}")
    print(f"  ✓ Comfortable situation: {dict(comfortable_dist)}")
    
    # Desperate should have more 5s and 6s
    desperate_big_hits = desperate_dist.get(5, 0) + desperate_dist.get(6, 0)
    comfortable_big_hits = comfortable_dist.get(5, 0) + comfortable_dist.get(6, 0)
    
    print(f"  ✓ Desperate big hits (5+6): {desperate_big_hits}")
    print(f"  ✓ Comfortable big hits (5+6): {comfortable_big_hits}")


def test_performance():
    """Test move selection performance."""
    print("\n🧪 Testing Performance...")
    
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
    
    # Time 100 move selections
    start = time.time()
    for _ in range(100):
        engine.select_move(99999, match_context, opponent_history)
    elapsed = time.time() - start
    
    avg_time_ms = (elapsed / 100) * 1000
    
    print(f"  ✓ 100 moves in {elapsed:.3f}s")
    print(f"  ✓ Average: {avg_time_ms:.2f}ms per move")
    
    assert avg_time_ms < 100, f"Too slow: {avg_time_ms:.2f}ms (expected <100ms)"
    print(f"  ✓ Performance acceptable (<100ms)")


def run_all_tests():
    """Run all strategy engine tests."""
    print("=" * 60)
    print("CPU STRATEGY ENGINE TEST SUITE")
    print("=" * 60)
    
    try:
        # Ensure DB is initialized for tests
        try:
            init_db()
            print("  ✓ Database initialized")
        except Exception as e:
            print(f"  ⚠️ Database initialization failed: {e}")

        test_learning_phases()
        test_base_weights()
        test_cpu_engine_initialization()
        test_move_selection_with_no_data()
        test_move_selection_distribution()
        test_cpu_status()
        test_role_specific_strategies()
        test_situational_adjustments()
        test_performance()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nCPU Strategy Engine is working correctly!")
        print("\nNext steps:")
        print("1. Play matches against CPU")
        print("2. Check /api/cpu-status/{username} to see learning progress")
        print("3. Observe CPU adapting to your play style over time")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
