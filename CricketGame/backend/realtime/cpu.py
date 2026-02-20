import asyncio
import random

from ..data.database import SessionLocal
from ..cpu.cpu_learning_utils import get_user_id_from_username


def cpu_pick_move(manager, room, role: str, cpu_name: str) -> int:
    match = room.match
    if not match:
        return random.randint(0, 6)

    innings = match.active_innings
    if not innings:
        return random.randint(0, 6)

    if role == "bat":
        opponent_username = innings.current_bowler if innings.current_bowler != cpu_name else None
        opponent_role_history = "bowl"
    else:
        opponent_username = innings.striker if innings.striker != cpu_name else None
        opponent_role_history = "bat"

    if not opponent_username:
        return cpu_pick_move_simple(manager, room, role, cpu_name)

    db = SessionLocal()
    try:
        opponent_user_id = get_user_id_from_username(opponent_username, db)
    finally:
        db.close()

    if opponent_user_id == -1:
        return cpu_pick_move_simple(manager, room, role, cpu_name)

    balls_bowled = innings.overs_completed * 6 + innings.balls_in_over
    total_balls = innings.total_overs * 6
    balls_remaining = total_balls - balls_bowled

    last_3_results = []
    if len(innings.ball_log) >= 3:
        for ball_result in innings.ball_log[-3:]:
            last_3_results.append({
                "runs": ball_result.get("runs", 0),
                "is_out": ball_result.get("is_out", False)
            })

    match_context = {
        "match_format": f"{match.total_overs}over",
        "role": "batting" if role == "bat" else "bowling",
        "current_over": innings.overs_completed,
        "total_overs": innings.total_overs,
        "current_score": innings.total_runs,
        "target": innings.target,
        "wickets_lost": innings.wickets_fallen,
        "balls_left": balls_remaining,
        "batting_first": match.current_innings == 1,
        "last_3_results": last_3_results,
    }

    opponent_history = []
    for ball_result in innings.ball_log[-20:]:
        if opponent_role_history == "bat":
            move = ball_result.get("bat_move")
        else:
            move = ball_result.get("bowl_move")

        if move is not None:
            opponent_history.append(move)

    try:
        cpu_move = manager.cpu_engine.select_move(
            user_id=opponent_user_id,
            match_context=match_context,
            opponent_history=opponent_history,
        )
        return cpu_move
    except Exception as e:
        print(f"⚠ Error in CPU strategy engine: {e}")
        return cpu_pick_move_simple(manager, room, role, cpu_name)


def cpu_pick_move_simple(manager, room, role: str, cpu_name: str) -> int:
    weights = {0: 0.08, 1: 0.16, 2: 0.16, 3: 0.15, 4: 0.16, 5: 0.14, 6: 0.15}
    history_key = "bat" if role == "bowl" else "bowl"
    recent = room.cpu_history.get(cpu_name, {}).get(history_key, [])[-12:]
    if recent:
        counts = {n: 0 for n in range(0, 7)}
        for m in recent:
            counts[m] = counts.get(m, 0) + 1
        top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:2]
        if role == "bowl":
            for num, count in top:
                if count > 0:
                    weights[num] = weights.get(num, 0) + 0.18
        else:
            for num, count in top:
                if count > 0:
                    weights[num] = weights.get(num, 0) * 0.6
    return manager._weighted_choice(weights)


async def maybe_cpu_move(manager, room, innings) -> None:
    """
    Submit CPU moves independently of the human side.
    Skips if captain selection is pending — the captain pick flow handles
    resuming play after the choice is made.
    """
    if not room.cpu_enabled:
        return

    # Do NOT submit CPU ball moves while waiting for a captain to pick
    if innings.needs_batter_choice or innings.needs_bowler_choice:
        # If the relevant captain is a CPU, auto-pick immediately
        await _handle_cpu_captain_picks(manager, room, innings)
        return

    pending = room.pending_moves
    striker_is_cpu = manager._is_cpu(room, innings.striker)
    bowler_is_cpu = manager._is_cpu(room, innings.current_bowler)

    placed = False

    # CPU batter: submit immediately if its slot is empty
    if striker_is_cpu and "bat" not in pending:
        await asyncio.sleep(0.25)
        pending["bat"] = cpu_pick_move(manager, room, "bat", innings.striker)
        placed = True

    # CPU bowler: submit immediately if its slot is empty
    if bowler_is_cpu and "bowl" not in pending:
        if not placed:
            await asyncio.sleep(0.25)
        pending["bowl"] = cpu_pick_move(manager, room, "bowl", innings.current_bowler)
        placed = True

    # Broadcast state so the frontend immediately sees the CPU's ready indicator
    if placed:
        await manager._send_match_state(room)


async def _handle_cpu_captain_picks(manager, room, innings) -> None:
    """Auto-pick captain choices when the relevant captain is a CPU."""
    from .match.match_actions import _team_for_side

    if innings.needs_batter_choice:
        batting_team = _team_for_side(room, innings.batting_side)
        captain = room.captains.get(batting_team) if batting_team else None
        if captain and manager._is_cpu(room, captain):
            options = innings.available_next_batters()
            enabled = [o for o in options if not o["disabled"]]
            choice = (enabled or options)
            if choice:
                await asyncio.sleep(0.3)
                innings.apply_batter_choice(choice[0]["player"])
                await manager._send_match_state(room)
                await manager._maybe_cpu_move(room, innings)
            return

    if innings.needs_bowler_choice:
        bowling_team = _team_for_side(room, innings.bowling_side)
        captain = room.captains.get(bowling_team) if bowling_team else None
        if captain and manager._is_cpu(room, captain):
            options = innings.available_next_bowlers()
            enabled = [o for o in options if not o["disabled"]]
            choice = (enabled or options)
            if choice:
                await asyncio.sleep(0.3)
                innings.apply_bowler_choice(choice[0]["player"])
                await manager._send_match_state(room)
                await manager._maybe_cpu_move(room, innings)


async def cpu_call_toss(manager, room) -> None:
    match = room.match
    if not match:
        return
    call = random.choice(["heads", "tails"])
    result = match.resolve_toss(call)
    room.toss_state["phase"] = "choosing"
    await manager.broadcast(room, {
        "type": "TOSS_RESULT",
        "caller": room.toss_state.get("caller"),
        "call": call,
        "coin": result["coin"],
        "winner": result["winner"],
    })
    if manager._is_cpu(room, result["winner"]):
        await cpu_choose_toss(manager, room)
    else:
        winner_conn = room.players.get(result["winner"])
        if winner_conn:
            await manager.send(winner_conn, {"type": "TOSS_CHOOSE"})


async def cpu_choose_toss(manager, room) -> None:
    match = room.match
    if not match:
        return
    choice = "bat" if random.random() < 0.6 else "bowl"
    match.apply_toss_choice(choice)
    await manager.broadcast(room, {
        "type": "TOSS_DECISION",
        "winner": match.toss_winner,
        "choice": choice,
        "batting_first": match.batting_first,
        "bowling_first": match.bowling_first,
    })
    match.start_innings_1()
    await asyncio.sleep(2)
    await manager._send_match_state(room)
    # Start ball-pick countdowns for the first ball
    from .match.match_actions import start_ball_countdowns
    if match.active_innings:
        start_ball_countdowns(manager, room, match.active_innings)
    await manager._auto_play_cpu_match(room)


async def auto_play_cpu_match(manager, room) -> None:
    if room.cpu_autoplay:
        return
    room.cpu_autoplay = True
    try:
        while True:
            match = room.match
            if not match or match.is_finished:
                return
            innings = match.active_innings
            if not innings:
                return

            # Pause auto-play during captain selection
            if innings.needs_batter_choice or innings.needs_bowler_choice:
                await _handle_cpu_captain_picks(manager, room, innings)
                return

            if not (manager._is_cpu(room, innings.striker) and manager._is_cpu(room, innings.current_bowler)):
                return
            pending = room.pending_moves
            if "bat" not in pending:
                pending["bat"] = cpu_pick_move(manager, room, "bat", innings.striker)
            if "bowl" not in pending:
                pending["bowl"] = cpu_pick_move(manager, room, "bowl", innings.current_bowler)
            await asyncio.sleep(0.25)
            resolved = await manager._resolve_pending_ball(room, innings)
            if not resolved:
                return
            await asyncio.sleep(0)
    finally:
        room.cpu_autoplay = False
