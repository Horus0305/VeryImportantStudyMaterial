"""Shared timeout constants and low-level asyncio task wrappers."""
import asyncio

BALL_PICK_TIMEOUT = 10      # seconds a human has to pick their number
CAPTAIN_PICK_TIMEOUT = 5    # seconds captain has to pick next batter/bowler
MAX_AUTO_STRIKES = 3        # auto-plays before the player forfeits


def _cancel_timeout(room, key: str) -> None:
    """Cancel a pending timeout task if it exists and is still running."""
    task = room.pending_timeouts.pop(key, None)
    if task and not task.done():
        task.cancel()


def _start_timeout(room, key: str, coro) -> None:
    """Start an asyncio task for a timeout, storing it for later cancellation."""
    _cancel_timeout(room, key)
    room.pending_timeouts[key] = asyncio.create_task(coro)
