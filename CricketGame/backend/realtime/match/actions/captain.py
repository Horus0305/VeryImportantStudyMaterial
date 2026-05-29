"""Captain selection — PICK_BATTER / PICK_BOWLER handlers."""
import asyncio

from .timeouts import _cancel_timeout


# ─── Team helper ──────────────────────────────────────────────────────────────

def _team_for_side(room, side: list) -> str | None:
    if not side:
        return None
    for key, members in room.teams.items():
        if any(p in members for p in side):
            return key
    return None


# ─── Captain pick initiators ──────────────────────────────────────────────────

async def _trigger_captain_picks_if_needed(manager, room, innings) -> bool:
    started_pick = False
    if innings.needs_batter_choice:
        await _start_captain_batter_pick(manager, room, innings)
        started_pick = True
    if innings.needs_bowler_choice:
        await _start_captain_bowler_pick(manager, room, innings)
        started_pick = True
    return started_pick


async def _start_captain_batter_pick(manager, room, innings) -> None:
    """Notify batting captain to pick next batter. No timeout — captain must choose."""
    batting_team = _team_for_side(room, innings.batting_side)
    captain = room.captains.get(batting_team) if batting_team else None
    if not captain:
        # No captain (1v1 / CPU) — auto-pick first available
        options = innings.available_next_batters()
        enabled = [o for o in options if not o["disabled"]]
        choice = enabled or options
        if choice:
            innings.apply_batter_choice(choice[0]["player"])
        await manager._send_match_state(room)
        from .ball import resolve_pending_ball
        await manager._maybe_cpu_move(room, innings)
        await manager._auto_play_cpu_match(room)
        return

    options = innings.available_next_batters()
    await manager.broadcast(room, {
        "type": "CHOOSE_BATTER",
        "captain": captain,
        "options": options,
    })

    if manager._is_cpu(room, captain):
        enabled = [o for o in options if not o["disabled"]]
        chosen_list = enabled or options
        if chosen_list:
            innings.apply_batter_choice(chosen_list[0]["player"])
            await manager._send_match_state(room)
            await manager._maybe_cpu_move(room, innings)
            await manager._auto_play_cpu_match(room)


async def _start_captain_bowler_pick(manager, room, innings) -> None:
    """Notify bowling captain to pick next bowler. No timeout — captain must choose."""
    bowling_team = _team_for_side(room, innings.bowling_side)
    captain = room.captains.get(bowling_team) if bowling_team else None
    if not captain:
        options = innings.available_next_bowlers()
        enabled = [o for o in options if not o["disabled"]]
        choice = enabled or options
        if choice:
            innings.apply_bowler_choice(choice[0]["player"])
        await manager._send_match_state(room)
        await manager._maybe_cpu_move(room, innings)
        await manager._auto_play_cpu_match(room)
        return

    options = innings.available_next_bowlers()
    await manager.broadcast(room, {
        "type": "CHOOSE_BOWLER",
        "captain": captain,
        "options": options,
    })

    if manager._is_cpu(room, captain):
        enabled = [o for o in options if not o["disabled"]]
        chosen_list = enabled or options
        if chosen_list:
            innings.apply_bowler_choice(chosen_list[0]["player"])
            await manager._send_match_state(room)
            await manager._maybe_cpu_move(room, innings)
            await manager._auto_play_cpu_match(room)


# ─── Public handlers (called from manager.py) ─────────────────────────────────

async def handle_pick_batter(manager, room, player, msg: dict) -> None:
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

    innings.apply_batter_choice(chosen)
    await manager._send_match_state(room)
    await manager._maybe_cpu_move(room, innings)
    await manager._auto_play_cpu_match(room)


async def handle_pick_bowler(manager, room, player, msg: dict) -> None:
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

    innings.apply_bowler_choice(chosen)
    await manager._send_match_state(room)
    await manager._maybe_cpu_move(room, innings)
    await manager._auto_play_cpu_match(room)
