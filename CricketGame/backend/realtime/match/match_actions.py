"""
match_actions.py — backward-compatible shim.

All logic has been moved into the `actions/` sub-package:
  actions/timeouts.py   — BALL_PICK_TIMEOUT, CAPTAIN_PICK_TIMEOUT, MAX_AUTO_STRIKES, helpers
  actions/captain.py    — captain pick handlers, auto-strike, captain timeouts
  actions/ball.py       — resolve_pending_ball, game_move, cancel_match, start_ball_countdowns

Imports from this module continue to work unchanged.
"""
from .actions import (
    resolve_pending_ball,
    game_move,
    cancel_match,
    start_ball_countdowns,
    handle_pick_batter,
    handle_pick_bowler,
    _team_for_side,
    BALL_PICK_TIMEOUT,
    CAPTAIN_PICK_TIMEOUT,
    MAX_AUTO_STRIKES,
    _cancel_timeout,
    _start_timeout,
)

__all__ = [
    "resolve_pending_ball", "game_move", "cancel_match", "start_ball_countdowns",
    "handle_pick_batter", "handle_pick_bowler", "_team_for_side",
    "BALL_PICK_TIMEOUT", "CAPTAIN_PICK_TIMEOUT", "MAX_AUTO_STRIKES",
    "_cancel_timeout", "_start_timeout",
]
