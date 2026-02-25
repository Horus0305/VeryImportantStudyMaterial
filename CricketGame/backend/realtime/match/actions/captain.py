"""Captain selection — PICK_BATTER / PICK_BOWLER handlers and timeout logic."""
import asyncio

from ....game.game_engine import compute_potm
from ..match_persistence import save_match_history, save_match_stats
from .timeouts import (
    CAPTAIN_PICK_TIMEOUT, MAX_AUTO_STRIKES,
    _cancel_timeout, _start_timeout,
)


# ─── Team helper ──────────────────────────────────────────────────────────────

def _team_for_side(room, side: list) -> str | None:
    """Return the team key whose member list overlaps with *side*."""
    if not side:
        return None
    for key, members in room.teams.items():
        if any(p in members for p in side):
            return key
    return None


# ─── Auto-strike recording ────────────────────────────────────────────────────

def _build_match_over_payload(match) -> dict:
    payload = {
        "winner": match.winner,
        "result_text": match.result_text,
        "scorecard_1": match.innings_1.get_scorecard() if getattr(match, "innings_1", None) else {},
        "scorecard_2": match.innings_2.get_scorecard() if getattr(match, "innings_2", None) else {},
        "side_a": match.side_a,
        "side_b": match.side_b,
        "bat_team_1": match.batting_first,
        "bat_team_2": match.bowling_first,
    }
    if match.is_super_over:
        payload["scorecard_3"] = match.innings_3.get_scorecard() if getattr(match, "innings_3", None) else {}
        payload["scorecard_4"] = match.innings_4.get_scorecard() if getattr(match, "innings_4", None) else {}
        payload["bat_team_3"] = match.bowling_first
        payload["bat_team_4"] = match.batting_first
        payload["super_over_timeline"] = match.get_super_over_timeline() if hasattr(match, "get_super_over_timeline") else []
    return payload


async def _forfeit_match_for_non_response(manager, room, offender: str) -> None:
    match = room.match
    if not match or match.is_finished:
        return

    if offender in match.side_a:
        winning_side = match.side_b
    elif offender in match.side_b:
        winning_side = match.side_a
    else:
        return

    winner_label = ", ".join(winning_side)
    match.winner = winner_label
    match.result_text = f"{winner_label} won by forfeit ({offender} reached 3/3 auto-move warnings)"
    match.is_finished = True
    # Forced outcomes should not affect tournament NRR tables.
    match.nrr_locked = True

    for key in list(room.pending_timeouts.keys()):
        _cancel_timeout(room, key)
    room.pending_moves = {}

    final = _build_match_over_payload(match)
    potm_data = compute_potm(match)
    final["potm"] = potm_data

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


async def _handle_auto_strike(manager, room, username: str, role: str) -> None:
    """
    Record an auto-move strike for a human player.
    Broadcasts AUTO_MOVE_WARNING; on MAX_AUTO_STRIKES in ball-pick flow,
    the non-responsive player forfeits the match.
    """
    strikes = room.auto_move_strikes.get(username, 0) + 1
    room.auto_move_strikes[username] = strikes
    await manager.broadcast(room, {
        "type": "AUTO_MOVE_WARNING",
        "player": username,
        "strikes": strikes,
        "max": MAX_AUTO_STRIKES,
    })
    if strikes < MAX_AUTO_STRIKES:
        return  # Warning only, not yet forceful

    innings = room.match.active_innings if room.match else None
    if not innings:
        return

    # Captain timeout should not force-dismiss players; warning-only behavior.
    if role in ("captain_bat", "captain_bowl"):
        return

    if role in ("bat", "bowl"):
        await _forfeit_match_for_non_response(manager, room, username)


# ─── Captain timeout callbacks ────────────────────────────────────────────────

async def _captain_batter_timeout(manager, room, innings, captain: str) -> None:
    """5-second timeout: auto-pick the first enabled batter for the captain."""
    await asyncio.sleep(CAPTAIN_PICK_TIMEOUT)
    if not room.match or not innings.needs_batter_choice:
        return
    options = innings.available_next_batters()
    enabled = [o for o in options if not o["disabled"]]
    choice = enabled or options
    if not choice:
        return
    innings.apply_batter_choice(choice[0]["player"])
    await _handle_auto_strike(manager, room, captain, "captain_bat")
    await manager._send_match_state(room)
    from .ball import start_ball_countdowns
    start_ball_countdowns(manager, room, innings)
    await manager._maybe_cpu_move(room, innings)
    await manager._auto_play_cpu_match(room)


async def _captain_bowler_timeout(manager, room, innings, captain: str) -> None:
    """5-second timeout: auto-pick the first enabled bowler for the captain."""
    await asyncio.sleep(CAPTAIN_PICK_TIMEOUT)
    if not room.match or not innings.needs_bowler_choice:
        return
    options = innings.available_next_bowlers()
    enabled = [o for o in options if not o["disabled"]]
    choice = enabled or options
    if not choice:
        return
    innings.apply_bowler_choice(choice[0]["player"])
    await _handle_auto_strike(manager, room, captain, "captain_bowl")
    await manager._send_match_state(room)
    from .ball import start_ball_countdowns
    start_ball_countdowns(manager, room, innings)
    await manager._maybe_cpu_move(room, innings)
    await manager._auto_play_cpu_match(room)


# ─── Captain pick initiators ──────────────────────────────────────────────────

async def _trigger_captain_picks_if_needed(manager, room, innings) -> bool:
    """Check if the innings starts with a captain pick and trigger it."""
    started_pick = False
    if innings.needs_batter_choice:
        await _start_captain_batter_pick(manager, room, innings)
        started_pick = True
    if innings.needs_bowler_choice:
        await _start_captain_bowler_pick(manager, room, innings)
        started_pick = True
    return started_pick

async def _start_captain_batter_pick(manager, room, innings) -> None:
    """Notify batting captain to pick next batter; start 5-second timeout."""
    batting_team = _team_for_side(room, innings.batting_side)
    captain = room.captains.get(batting_team) if batting_team else None
    if not captain:
        # No captain assigned (1v1 / CPU mode) → auto-pick and resume play
        options = innings.available_next_batters()
        enabled = [o for o in options if not o["disabled"]]
        choice = enabled or options
        if choice:
            innings.apply_batter_choice(choice[0]["player"])
        await manager._send_match_state(room)
        from .ball import start_ball_countdowns
        start_ball_countdowns(manager, room, innings)
        await manager._maybe_cpu_move(room, innings)
        await manager._auto_play_cpu_match(room)
        return

    options = innings.available_next_batters()
    await manager.broadcast(room, {
        "type": "CHOOSE_BATTER",
        "captain": captain,
        "options": options,
        "timeout": CAPTAIN_PICK_TIMEOUT,
    })

    if manager._is_cpu(room, captain):
        enabled = [o for o in options if not o["disabled"]]
        chosen_list = enabled or options
        if chosen_list:
            innings.apply_batter_choice(chosen_list[0]["player"])
            await manager._send_match_state(room)
            from .ball import start_ball_countdowns
            start_ball_countdowns(manager, room, innings)
            await manager._maybe_cpu_move(room, innings)
            await manager._auto_play_cpu_match(room)
    else:
        _start_timeout(room, "captain_bat",
                       _captain_batter_timeout(manager, room, innings, captain))
        # Notify captain to start their countdown timer
        p = room.players.get(captain)
        if p:
            import asyncio
            asyncio.create_task(manager.send(p, {"type": "COUNTDOWN", "role": "captain", "seconds": CAPTAIN_PICK_TIMEOUT}))


async def _start_captain_bowler_pick(manager, room, innings) -> None:
    """Notify bowling captain to pick next bowler; start 5-second timeout."""
    bowling_team = _team_for_side(room, innings.bowling_side)
    captain = room.captains.get(bowling_team) if bowling_team else None
    if not captain:
        # No captain assigned (1v1 / CPU mode) → auto-pick and resume play
        options = innings.available_next_bowlers()
        enabled = [o for o in options if not o["disabled"]]
        choice = enabled or options
        if choice:
            innings.apply_bowler_choice(choice[0]["player"])
        await manager._send_match_state(room)
        from .ball import start_ball_countdowns
        start_ball_countdowns(manager, room, innings)
        await manager._maybe_cpu_move(room, innings)
        await manager._auto_play_cpu_match(room)
        return

    options = innings.available_next_bowlers()
    await manager.broadcast(room, {
        "type": "CHOOSE_BOWLER",
        "captain": captain,
        "options": options,
        "timeout": CAPTAIN_PICK_TIMEOUT,
    })

    if manager._is_cpu(room, captain):
        enabled = [o for o in options if not o["disabled"]]
        chosen_list = enabled or options
        if chosen_list:
            innings.apply_bowler_choice(chosen_list[0]["player"])
            await manager._send_match_state(room)
            from .ball import start_ball_countdowns
            start_ball_countdowns(manager, room, innings)
            await manager._maybe_cpu_move(room, innings)
            await manager._auto_play_cpu_match(room)
    else:
        _start_timeout(room, "captain_bowl",
                       _captain_bowler_timeout(manager, room, innings, captain))
        # Notify captain to start their countdown timer
        p = room.players.get(captain)
        if p:
            import asyncio
            asyncio.create_task(manager.send(p, {"type": "COUNTDOWN", "role": "captain", "seconds": CAPTAIN_PICK_TIMEOUT}))


# ─── Public handlers (called from manager.py) ─────────────────────────────────

async def handle_pick_batter(manager, room, player, msg: dict) -> None:
    """Batting captain submitted their next batter choice."""
    match = room.match
    if not match:
        return
    innings = match.active_innings
    if not innings or not innings.needs_batter_choice:
        return

    batting_team = _team_for_side(room, innings.batting_side)
    captain = room.captains.get(batting_team) if batting_team else None
    if player.username != captain:
        return

    chosen = msg.get("player")
    options = innings.available_next_batters()
    valid_names = [o["player"] for o in options if not o["disabled"]] or \
                  [o["player"] for o in options]
    if chosen not in valid_names:
        return

    _cancel_timeout(room, "captain_bat")
    innings.apply_batter_choice(chosen)
    await manager._send_match_state(room)
    from .ball import start_ball_countdowns
    start_ball_countdowns(manager, room, innings)
    await manager._maybe_cpu_move(room, innings)
    await manager._auto_play_cpu_match(room)


async def handle_pick_bowler(manager, room, player, msg: dict) -> None:
    """Bowling captain submitted their next bowler choice."""
    match = room.match
    if not match:
        return
    innings = match.active_innings
    if not innings or not innings.needs_bowler_choice:
        return

    bowling_team = _team_for_side(room, innings.bowling_side)
    captain = room.captains.get(bowling_team) if bowling_team else None
    if player.username != captain:
        return

    chosen = msg.get("player")
    options = innings.available_next_bowlers()
    valid_names = [o["player"] for o in options if not o["disabled"]] or \
                  [o["player"] for o in options]
    if chosen not in valid_names:
        return

    _cancel_timeout(room, "captain_bowl")
    innings.apply_bowler_choice(chosen)
    await manager._send_match_state(room)
    from .ball import start_ball_countdowns
    start_ball_countdowns(manager, room, innings)
    await manager._maybe_cpu_move(room, innings)
    await manager._auto_play_cpu_match(room)
