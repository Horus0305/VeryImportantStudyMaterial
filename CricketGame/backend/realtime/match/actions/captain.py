"""Captain selection — PICK_BATTER / PICK_BOWLER handlers and timeout logic."""
import asyncio

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

async def _handle_auto_strike(manager, room, username: str, role: str) -> None:
    """
    Record an auto-move strike for a human player.
    Broadcasts AUTO_MOVE_WARNING; on MAX_AUTO_STRIKES forces the relevant
    game action (wicket for batter, over-end for bowler).
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

    if role == "bat":
        bat_card = innings.batting_cards.get(username)
        if bat_card and not bat_card.is_out:
            bat_card.is_out = True
            bat_card.dismissal = "retired hurt (timeout)"
            innings.wickets_fallen += 1
            result_stub = {
                "striker": username,
                "bowler": innings.current_bowler,
                "is_out": True,
                "runs": 0,
                "milestone": None,
                "hat_trick": False,
            }
            innings._handle_wicket_fall(result_stub)
        room.pending_moves.pop("bat", None)
        await manager._send_match_state(room)
        if not innings.needs_batter_choice:
            # Import lazily to avoid circular dependency
            from .ball import start_ball_countdowns
            start_ball_countdowns(manager, room, innings)
            await manager._maybe_cpu_move(room, innings)

    elif role == "bowl":
        room.pending_moves.pop("bowl", None)
        bowl_card = innings.bowling_cards.get(innings.current_bowler)
        if bowl_card:
            bowl_card.overs_completed += 1
            bowl_card.balls_bowled_in_over = 0
        innings.balls_in_over = 0
        innings.overs_completed += 1
        innings._rotate_strike()
        innings._next_bowler({})
        await manager._send_match_state(room)
        if innings.needs_bowler_choice:
            await _start_captain_bowler_pick(manager, room, innings)
        else:
            from .ball import start_ball_countdowns
            start_ball_countdowns(manager, room, innings)
            await manager._maybe_cpu_move(room, innings)


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
    await _handle_auto_strike(manager, room, captain, "bat")
    await manager._send_match_state(room)
    from .ball import start_ball_countdowns
    start_ball_countdowns(manager, room, innings)
    await manager._maybe_cpu_move(room, innings)


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
    await _handle_auto_strike(manager, room, captain, "bowl")
    await manager._send_match_state(room)
    from .ball import start_ball_countdowns
    start_ball_countdowns(manager, room, innings)
    await manager._maybe_cpu_move(room, innings)


# ─── Captain pick initiators ──────────────────────────────────────────────────

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
