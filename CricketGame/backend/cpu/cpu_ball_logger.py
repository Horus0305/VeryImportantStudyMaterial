"""
CPU Ball Logger - Helper to log balls from ws_manager without blocking match flow.
"""
import asyncio
from typing import Optional

from ..data.database import SessionLocal
from .cpu_learning_integration import log_ball_to_database


def _log_ball_sync(payload: dict) -> None:
    db = SessionLocal()
    try:
        log_ball_to_database(db=db, **payload)
    except Exception as e:
        print(f"[CPU] Error in log_ball_async: {e}")
    finally:
        db.close()


def log_ball_async(
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
) -> None:
    """
    Queue ball logging work in a background thread so gameplay stays responsive.
    """
    payload = {
        "match_id": match_id,
        "ball_number": ball_number,
        "batter_username": batter_username,
        "bowler_username": bowler_username,
        "bat_move": bat_move,
        "bowl_move": bowl_move,
        "runs_scored": runs_scored,
        "is_out": is_out,
        "match_format_overs": match_format_overs,
        "current_over": current_over,
        "total_overs": total_overs,
        "innings": innings,
        "batting_score": batting_score,
        "batting_wickets": batting_wickets,
        "target": target,
        "balls_remaining": balls_remaining,
        "batting_first": batting_first,
    }

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(asyncio.to_thread(_log_ball_sync, payload))
    except RuntimeError:
        # Fallback for non-async contexts.
        _log_ball_sync(payload)
