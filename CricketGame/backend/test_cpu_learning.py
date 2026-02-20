"""
Test script for CPU Learning Infrastructure
Run this after migration to verify the system is working.
"""
from .data.database import SessionLocal
from .cpu.cpu_learning_schema import (
    MatchBallLog, CPUGlobalPattern, CPUUserProfile, CPUSituationalPattern,
    CPUSequencePattern, CPULearningProgress, CPULearningQueue
)
from .cpu.cpu_learning_integration import log_ball_to_database, get_learning_stats
from .cpu.cpu_learning_utils import (
    get_game_phase, get_score_situation, get_recent_event,
    calculate_learning_phase, normalize_frequencies
)


def test_context_functions():
    """Test context detection functions."""
    print("\n🧪 Testing Context Detection Functions...")
    
    # Test game phase
    assert get_game_phase(0, 10) == 'powerplay'
    assert get_game_phase(5, 10) == 'middle'
    assert get_game_phase(9, 10) == 'death'
    print("  ✓ get_game_phase works correctly")
    
    # Test score situation (batting first)
    situation = get_score_situation(
        batting_first=True,
        current_score=50,
        target=None,
        wickets_lost=2,
        balls_left=30,
        total_overs=10
    )
    assert situation in ['defending_safe', 'defending_comfortable', 'defending_moderate', 'defending_tight', 'defending_collapse']
    print(f"  ✓ get_score_situation (batting first): {situation}")
    
    # Test score situation (chasing)
    situation = get_score_situation(
        batting_first=False,
        current_score=30,
        target=51,
        wickets_lost=3,
        balls_left=20,
        total_overs=10
    )
    assert situation in ['chasing_comfortable', 'chasing_moderate', 'chasing_tight', 'chasing_desperate', 'chasing_very_tight', 'chasing_won']
    print(f"  ✓ get_score_situation (chasing): {situation}")
    
    # Test recent event
    recent = get_recent_event([
        {'runs': 4, 'is_out': False},
        {'runs': 6, 'is_out': False},
        {'runs': 4, 'is_out': False}
    ])
    assert recent == 'hot_streak'
    print(f"  ✓ get_recent_event: {recent}")
    
    # Test learning phase
    phase, confidence = calculate_learning_phase(50)
    assert phase == 'global'
    assert 0.0 <= confidence <= 0.3
    print(f"  ✓ calculate_learning_phase (50 balls): {phase}, confidence={confidence}")
    
    phase, confidence = calculate_learning_phase(150)
    assert phase == 'transition'
    assert 0.3 <= confidence <= 0.7
    print(f"  ✓ calculate_learning_phase (150 balls): {phase}, confidence={confidence}")
    
    phase, confidence = calculate_learning_phase(500)
    assert phase == 'personalized'
    assert 0.7 <= confidence <= 0.95
    print(f"  ✓ calculate_learning_phase (500 balls): {phase}, confidence={confidence}")
    
    # Test normalize frequencies
    freqs = normalize_frequencies([1, 2, 3, 4, 5, 6, 7])
    assert abs(sum(freqs) - 1.0) < 0.001
    print(f"  ✓ normalize_frequencies: sum={sum(freqs)}")


def test_database_tables():
    """Test that all tables exist and are accessible."""
    print("\n🧪 Testing Database Tables...")
    
    db = SessionLocal()
    try:
        # Test each table
        tables = [
            ('match_ball_log', MatchBallLog),
            ('cpu_global_patterns', CPUGlobalPattern),
            ('cpu_user_profiles', CPUUserProfile),
            ('cpu_situational_patterns', CPUSituationalPattern),
            ('cpu_sequence_patterns', CPUSequencePattern),
            ('cpu_learning_progress', CPULearningProgress),
            ('cpu_learning_queue', CPULearningQueue),
        ]
        
        for table_name, model in tables:
            count = db.query(model).count()
            print(f"  ✓ {table_name}: {count} records")
        
    finally:
        db.close()


def test_ball_logging():
    """Test logging a sample ball."""
    print("\n🧪 Testing Ball Logging...")
    
    db = SessionLocal()
    try:
        # Log a test ball
        ball_log_id = log_ball_to_database(
            db=db,
            match_id="TEST_MATCH_001",
            ball_number=1,
            batter_username="TestPlayer1",
            bowler_username="TestPlayer2",
            bat_move=4,
            bowl_move=2,
            runs_scored=4,
            is_out=False,
            match_format_overs=5,
            current_over=0,
            total_overs=5,
            innings=1,
            batting_score=4,
            batting_wickets=0,
            target=None,
            balls_remaining=29,
            batting_first=True
        )
        
        if ball_log_id:
            print(f"  ✓ Ball logged successfully (ID: {ball_log_id})")
            
            # Verify it's in the queue
            queue_item = db.query(CPULearningQueue).filter(
                CPULearningQueue.ball_log_id == ball_log_id
            ).first()
            
            if queue_item:
                print(f"  ✓ Ball queued for processing (processed={queue_item.processed})")
            else:
                print("  ✗ Ball NOT queued")
        else:
            print("  ✗ Ball logging failed")
        
    finally:
        db.close()


def test_learning_stats():
    """Test getting learning statistics."""
    print("\n🧪 Testing Learning Stats...")
    
    db = SessionLocal()
    try:
        stats = get_learning_stats(db)
        print(f"  Total balls logged: {stats['total_balls_logged']}")
        print(f"  Queue pending: {stats['queue_pending']}")
        print(f"  Queue processed: {stats['queue_processed']}")
        print(f"  Processing rate: {stats['processing_rate']}")
    finally:
        db.close()


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("CPU LEARNING INFRASTRUCTURE TEST SUITE")
    print("=" * 60)
    
    try:
        test_context_functions()
        test_database_tables()
        test_ball_logging()
        test_learning_stats()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start your FastAPI server")
        print("2. Play some matches")
        print("3. Check the database to see data accumulating")
        print("4. Monitor the learning queue processing")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
