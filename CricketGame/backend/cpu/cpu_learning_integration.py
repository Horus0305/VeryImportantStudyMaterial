"""
CPU Learning Integration - Functions to integrate learning into match flow
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from .cpu_learning_schema import MatchBallLog, CPULearningQueue
from .cpu_learning_utils import (
    get_game_phase, get_score_situation, get_match_format_key, get_user_id_from_username
)


def log_ball_to_database(
    db: Session,
    match_id: str,
    ball_number: int,
    batter_username: str,
    bowler_username: str,
    bat_move: int,
    bowl_move: int,
    runs_scored: int,
    is_out: bool,
    match_format_overs: int,
    current_over: int,
    total_overs: int,
    innings: int,
    batting_score: int,
    batting_wickets: int,
    target: Optional[int],
    balls_remaining: int,
    batting_first: bool
) -> Optional[int]:
    """
    Log a single ball to the match_ball_log table.
    
    Returns:
        The ball_log_id if successful, None otherwise
    """
    try:
        # Get user IDs
        batter_user_id = get_user_id_from_username(batter_username, db)
        bowler_user_id = get_user_id_from_username(bowler_username, db)
        
        # Compute context
        match_format = get_match_format_key(match_format_overs)
        game_phase = get_game_phase(current_over, total_overs)
        score_pressure = get_score_situation(
            batting_first=batting_first,
            current_score=batting_score,
            target=target,
            wickets_lost=batting_wickets,
            balls_left=balls_remaining,
            total_overs=total_overs
        )
        
        # Create ball log entry
        ball_log = MatchBallLog(
            match_id=match_id,
            ball_number=ball_number,
            batter_user_id=batter_user_id,
            bowler_user_id=bowler_user_id,
            bat_move=bat_move,
            bowl_move=bowl_move,
            runs_scored=runs_scored,
            is_out=is_out,
            match_format=match_format,
            current_over=current_over,
            total_overs=total_overs,
            innings=innings,
            batting_score=batting_score,
            batting_wickets=batting_wickets,
            target=target,
            balls_remaining=balls_remaining,
            game_phase=game_phase,
            score_pressure=score_pressure
        )
        
        db.add(ball_log)
        db.flush()  # Get the ID without committing
        
        ball_log_id = ball_log.id
        
        # Add to processing queue
        queue_item = CPULearningQueue(
            ball_log_id=ball_log_id,
            processed=False
        )
        db.add(queue_item)
        
        db.commit()
        
        return ball_log_id
        
    except Exception as e:
        print(f"⚠ Error logging ball to database: {e}")
        db.rollback()
        return None


def queue_ball_for_learning(db: Session, ball_log_id: int) -> bool:
    """
    Add a ball to the learning queue for async processing.
    
    Args:
        db: Database session
        ball_log_id: ID of the ball log entry
        
    Returns:
        True if successful, False otherwise
    """
    try:
        queue_item = CPULearningQueue(
            ball_log_id=ball_log_id,
            processed=False
        )
        db.add(queue_item)
        db.commit()
        return True
    except Exception as e:
        print(f"⚠ Error queueing ball for learning: {e}")
        db.rollback()
        return False


def get_learning_stats(db: Session) -> dict:
    """
    Get statistics about the learning system.
    
    Returns:
        Dict with queue size, total balls logged, etc.
    """
    try:
        total_balls = db.query(MatchBallLog).count()
        queue_pending = db.query(CPULearningQueue).filter(
            CPULearningQueue.processed == False
        ).count()
        queue_processed = db.query(CPULearningQueue).filter(
            CPULearningQueue.processed == True
        ).count()
        
        return {
            'total_balls_logged': total_balls,
            'queue_pending': queue_pending,
            'queue_processed': queue_processed,
            'processing_rate': f"{queue_processed}/{total_balls}" if total_balls > 0 else "0/0"
        }
    except Exception as e:
        print(f"⚠ Error getting learning stats: {e}")
        return {
            'total_balls_logged': 0,
            'queue_pending': 0,
            'queue_processed': 0,
            'processing_rate': 'error'
        }
