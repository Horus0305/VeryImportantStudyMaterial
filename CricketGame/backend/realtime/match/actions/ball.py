"""Core ball resolution, game_move, cancel_match, and countdown starters."""
import asyncio
import random

from ....game.game_engine import compute_potm
from ..match_logging import record_cpu_history, log_ball_for_learning
from ..match_persistence import save_match_stats, save_match_history
from .timeouts import BALL_PICK_TIMEOUT, _cancel_timeout, _start_timeout
from .captain import _start_captain_batter_pick, _start_captain_bowler_pick


# ─── Ball-pick countdown tasks ────────────────────────────────────────────────

async def _bat_countdown(manager, room, username: str) -> None:
    """10-second deadline for batter. On expire: CPU picks, strikes recorded."""
    await asyncio.sleep(BALL_PICK_TIMEOUT)
    match = room.match
    if not match or "bat" in room.pending_moves:
        return
    innings = match.active_innings
    if not innings or innings.striker != username:
        return

    room.pending_moves["bat"] = random.randint(0, 6)
    from .captain import _handle_auto_strike
    await _handle_auto_strike(manager, room, username, "bat")
    innings = match.active_innings  # re-fetch in case it changed
    if innings:
        await resolve_pending_ball(manager, room, innings)


async def _bowl_countdown(manager, room, username: str) -> None:
    """10-second deadline for bowler. On expire: CPU picks, strikes recorded."""
    await asyncio.sleep(BALL_PICK_TIMEOUT)
    match = room.match
    if not match or "bowl" in room.pending_moves:
        return
    innings = match.active_innings
    if not innings or innings.current_bowler != username:
        return

    room.pending_moves["bowl"] = random.randint(0, 6)
    from .captain import _handle_auto_strike
    await _handle_auto_strike(manager, room, username, "bowl")
    innings = match.active_innings
    if innings:
        await resolve_pending_ball(manager, room, innings)


def start_ball_countdowns(manager, room, innings) -> None:
    """Start 10-second timers for the active human batter and/or bowler."""
    # Never start countdowns while captain selection is pending
    if innings.needs_batter_choice or innings.needs_bowler_choice:
        return

    striker = innings.striker
    bowler = innings.current_bowler

    if not manager._is_cpu(room, striker) and "bat" not in room.pending_moves:
        _start_timeout(room, "bat", _bat_countdown(manager, room, striker))
        # Notify the batter's client to start their countdown timer
        p = room.players.get(striker)
        if p:
            import asyncio
            asyncio.create_task(manager.send(p, {"type": "COUNTDOWN", "role": "bat", "seconds": BALL_PICK_TIMEOUT}))

    if not manager._is_cpu(room, bowler) and "bowl" not in room.pending_moves:
        _start_timeout(room, "bowl", _bowl_countdown(manager, room, bowler))
        # Notify the bowler's client to start their countdown timer
        p = room.players.get(bowler)
        if p:
            import asyncio
            asyncio.create_task(manager.send(p, {"type": "COUNTDOWN", "role": "bowl", "seconds": BALL_PICK_TIMEOUT}))


# ─── Core ball resolution ─────────────────────────────────────────────────────

async def resolve_pending_ball(manager, room, innings) -> bool:
    """Resolve the ball if both bat and bowl moves are present."""
    match = room.match
    if not match:
        return False
    pending = room.pending_moves
    if "bat" not in pending or "bowl" not in pending:
        return False

    # Cancel any running ball-pick countdowns before processing
    _cancel_timeout(room, "bat")
    _cancel_timeout(room, "bowl")

    bat_move = pending["bat"]
    bowl_move = pending["bowl"]
    result = innings.resolve_ball(bat_move, bowl_move)
    record_cpu_history(manager, room, innings, bat_move, bowl_move)
    log_ball_for_learning(manager, room, match, innings, bat_move, bowl_move, result)
    room.pending_moves = {}

    await manager.broadcast(room, {"type": "BALL_RESULT", **result})

    # ── Innings complete ──────────────────────────────────────────────────────
    if result.get("innings_complete"):
        if match.current_innings == 1:
            scorecard = innings.get_scorecard()
            target = innings.total_runs + 1
            await manager.broadcast(room, {
                "type": "INNINGS_BREAK",
                "scorecard": scorecard,
                "target": target,
            })
            room.auto_move_strikes = {}   # reset strikes for innings 2
            match.start_innings_2()
            await asyncio.sleep(2)
            new_innings = match.active_innings
            await manager._send_match_state(room)
            if new_innings:
                from .captain import _trigger_captain_picks_if_needed
                await _trigger_captain_picks_if_needed(manager, room, new_innings)
                start_ball_countdowns(manager, room, new_innings)
            await manager._maybe_cpu_move(room, new_innings)
            await manager._auto_play_cpu_match(room)
            return True

        if (
            match.current_innings == 2
            and match.innings_1.total_runs == innings.total_runs
            and room.tournament
            and room.tournament.phase != "group"
        ):
            scorecard = innings.get_scorecard()
            target = innings.total_runs + 1
            await manager.broadcast(room, {
                "type": "INNINGS_BREAK",
                "scorecard": scorecard,
                "target": target,
                "msg": "SUPER OVER: INNINGS 1",
            })
            room.auto_move_strikes = {}
            match.start_innings_3()
            await asyncio.sleep(2)
            new_innings = match.active_innings
            await manager._send_match_state(room)
            if new_innings:
                from .captain import _trigger_captain_picks_if_needed
                await _trigger_captain_picks_if_needed(manager, room, new_innings)
                start_ball_countdowns(manager, room, new_innings)
            await manager._maybe_cpu_move(room, new_innings)
            await manager._auto_play_cpu_match(room)
            return True

        if match.current_innings == 3:
            scorecard = innings.get_scorecard()
            target = innings.total_runs + 1
            await manager.broadcast(room, {
                "type": "INNINGS_BREAK",
                "scorecard": scorecard,
                "target": target,
                "msg": "SUPER OVER: INNINGS 2",
            })
            room.auto_move_strikes = {}
            match.start_innings_4()
            await asyncio.sleep(2)
            new_innings = match.active_innings
            await manager._send_match_state(room)
            if new_innings:
                from .captain import _trigger_captain_picks_if_needed
                await _trigger_captain_picks_if_needed(manager, room, new_innings)
                start_ball_countdowns(manager, room, new_innings)
            await manager._maybe_cpu_move(room, new_innings)
            await manager._auto_play_cpu_match(room)
            return True

        # ── Match over ───────────────────────────────────────────────────────
        if match.current_innings == 4:
            match.snapshot_super_over_round()

        if (
            match.current_innings == 4
            and room.tournament
            and room.tournament.phase != "group"
            and getattr(match, "innings_3", None)
            and match.innings_3.total_runs == innings.total_runs
        ):
            scorecard = innings.get_scorecard()
            await manager.broadcast(room, {
                "type": "INNINGS_BREAK",
                "scorecard": scorecard,
                "target": None,
                "msg": "SUPER OVER TIED - ANOTHER SUPER OVER",
            })
            room.auto_move_strikes = {}
            match.start_innings_3()
            await asyncio.sleep(2)
            new_innings = match.active_innings
            await manager._send_match_state(room)
            if new_innings:
                from .captain import _trigger_captain_picks_if_needed
                await _trigger_captain_picks_if_needed(manager, room, new_innings)
                start_ball_countdowns(manager, room, new_innings)
            await manager._maybe_cpu_move(room, new_innings)
            await manager._auto_play_cpu_match(room)
            return True

        final = match.determine_result()
        potm_data = compute_potm(match)
        final["potm"] = potm_data

        # Cancel all pending timeouts before match teardown
        for key in list(room.pending_timeouts.keys()):
            _cancel_timeout(room, key)

        if room.tournament:
            tournament_payload = manager._apply_tournament_result(room, match)
            await manager.broadcast(room, {"type": "MATCH_OVER", **final, "tournament": tournament_payload})
            await manager.broadcast(room, {"type": "TOURNAMENT_STANDINGS", **tournament_payload})
        else:
            await manager.broadcast(room, {"type": "MATCH_OVER", **final})

        save_match_stats(manager, room, match)
        tournament_id = room.tournament_id if room.tournament else None
        save_match_history(manager, room, match, potm_data, tournament_id)

        room.match = None
        room.pending_moves = {}

        if room.tournament:
            await asyncio.sleep(3)
            await manager._start_next_tournament_match(room)
        else:
            await manager.broadcast_lobby(room)
        return True

    # ── Wicket or Over ended → captain picks OR auto-rotate ────────────────────
    started_pick = False
    if result.get("needs_batter_choice"):
        await _start_captain_batter_pick(manager, room, innings)
        started_pick = True
    if result.get("needs_bowler_choice"):
        await _start_captain_bowler_pick(manager, room, innings)
        started_pick = True
        
    if started_pick:
        return True

    # ── Normal ball — send state and arm next countdown ───────────────────────
    await manager._send_match_state(room)
    start_ball_countdowns(manager, room, innings)
    await manager._maybe_cpu_move(room, innings)
    await manager._auto_play_cpu_match(room)
    return True


# ─── Human move handler ───────────────────────────────────────────────────────

async def game_move(manager, room, player, msg: dict) -> None:
    """Process a GAME_MOVE from a human player."""
    match = room.match
    if not match or match.is_finished:
        return
    innings = match.active_innings
    if not innings:
        return

    # Ignore ball moves while captain selection is pending
    if innings.needs_batter_choice or innings.needs_bowler_choice:
        return

    move = msg.get("move")
    if not isinstance(move, int) or move < 0 or move > 6:
        return

    is_batting = player.username in innings.batting_side
    is_bowling = player.username in innings.bowling_side
    pending = room.pending_moves
    updated = False

    if is_batting and player.username == innings.striker and "bat" not in pending:
        pending["bat"] = move
        _cancel_timeout(room, "bat")
        updated = True
    elif is_bowling and player.username == innings.current_bowler and "bowl" not in pending:
        pending["bowl"] = move
        _cancel_timeout(room, "bowl")
        updated = True
    elif match.mode == "1v1":
        if is_batting and "bat" not in pending:
            pending["bat"] = move
            _cancel_timeout(room, "bat")
            updated = True
        elif is_bowling and "bowl" not in pending:
            pending["bowl"] = move
            _cancel_timeout(room, "bowl")
            updated = True

    if updated:
        await manager._send_match_state(room)
        await manager._maybe_cpu_move(room, innings)
        if await resolve_pending_ball(manager, room, innings):
            return

    await resolve_pending_ball(manager, room, innings)


# ─── Match cancellation ───────────────────────────────────────────────────────

async def cancel_match(manager, room, player) -> None:
    """Host cancels the current match."""
    if player.username != room.host:
        return
    match = room.match
    if not match or match.is_finished:
        return

    for key in list(room.pending_timeouts.keys()):
        _cancel_timeout(room, key)

    match.result_text = "Match Cancelled by Host"
    match.winner = None
    match.is_finished = True

    if room.tournament:
        tournament_payload = manager._apply_tournament_cancellation(room, match)
        await manager.broadcast(room, {
            "type": "MATCH_CANCELLED",
            "msg": "Match Cancelled by Host",
            "tournament": tournament_payload,
        })
        await manager.broadcast(room, {"type": "TOURNAMENT_STANDINGS", **tournament_payload})
        save_match_history(manager, room, match, None, room.tournament_id)
        room.match = None
        room.pending_moves = {}
        await asyncio.sleep(3)
        await manager._start_next_tournament_match(room)
    else:
        await manager.broadcast(room, {"type": "MATCH_CANCELLED", "msg": "Match Cancelled by Host"})
        save_match_history(manager, room, match, None, None)
        room.match = None
        room.pending_moves = {}
        await manager.broadcast_lobby(room)

