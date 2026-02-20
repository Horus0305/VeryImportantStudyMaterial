import asyncio

CPU_PICK_TIMEOUT = 30


def _human_captain_for_cpu(manager, room, cpu_player: str):
    team_key = manager._team_for_player(room, cpu_player)
    if not team_key:
        return None
    captain = room.captains.get(team_key)
    if captain and not manager._is_cpu(room, captain):
        return captain
    return None


async def _cpu_call_timeout(manager, room, caller: str) -> None:
    await asyncio.sleep(CPU_PICK_TIMEOUT)
    match = room.match
    if not match:
        return
    if room.toss_state.get("phase") != "calling":
        return
    if not manager._is_cpu(room, caller):
        return
    print(f"⏱ CPU toss call timeout: room={room.code} caller={caller}")
    await manager._cpu_call_toss(room)


async def _cpu_choice_timeout(manager, room, winner: str) -> None:
    await asyncio.sleep(CPU_PICK_TIMEOUT)
    match = room.match
    if not match or match.toss_choice is not None:
        return
    if room.toss_state.get("phase") != "choosing":
        return
    if not manager._is_cpu(room, winner):
        return
    print(f"⏱ CPU toss choice timeout: room={room.code} winner={winner}")
    await manager._cpu_choose_toss(room)


async def initiate_toss(manager, room) -> None:
    match = room.match
    toss_info = match.do_toss()
    caller = toss_info["caller"]
    toss_caller = caller
    human_captain = None
    if room.mode == "team" and room.cpu_enabled and manager._is_cpu(room, caller):
        human_captain = _human_captain_for_cpu(manager, room, caller)
        if human_captain:
            toss_caller = human_captain
    room.toss_state = {"caller": toss_caller, "phase": "calling"}

    if room.cpu_enabled and manager._is_cpu(room, caller) and not human_captain:
        for username, p in room.players.items():
            await manager.send(p, {"type": "TOSS_WAITING", "caller": toss_caller})
        await asyncio.sleep(0.3)
        await manager._cpu_call_toss(room)
        asyncio.create_task(_cpu_call_timeout(manager, room, caller))
        return

    for username, p in room.players.items():
        if username == toss_caller:
            await manager.send(p, {"type": "TOSS_CALLER", "caller": toss_caller})
        else:
            await manager.send(p, {"type": "TOSS_WAITING", "caller": toss_caller})


async def toss_call(manager, room, player, msg: dict) -> None:
    match = room.match
    toss = room.toss_state
    if not match or player.username != toss.get("caller"):
        return
    if room.cpu_enabled and manager._is_cpu(room, toss.get("caller", "")):
        return

    call = msg.get("call", "heads")
    result = match.resolve_toss(call)
    toss["phase"] = "choosing"

    await manager.broadcast(room, {
        "type": "TOSS_RESULT",
        "caller": toss["caller"], "call": call,
        "coin": result["coin"], "winner": result["winner"],
    })

    winner = result["winner"]
    chooser = winner
    human_captain = None
    if room.mode == "team" and room.cpu_enabled and manager._is_cpu(room, winner):
        human_captain = _human_captain_for_cpu(manager, room, winner)
        if human_captain:
            chooser = human_captain
    if room.cpu_enabled and manager._is_cpu(room, winner) and not human_captain:
        await manager._cpu_choose_toss(room)
        asyncio.create_task(_cpu_choice_timeout(manager, room, winner))
        return
    winner_conn = room.players.get(chooser)
    if winner_conn:
        await manager.send(winner_conn, {"type": "TOSS_CHOOSE"})


async def toss_choice(manager, room, player, msg: dict) -> None:
    match = room.match
    if not match:
        return
    toss_winner = match.toss_winner
    human_captain = None
    if room.mode == "team" and room.cpu_enabled and manager._is_cpu(room, toss_winner):
        human_captain = _human_captain_for_cpu(manager, room, toss_winner)
    allowed = {toss_winner}
    if human_captain:
        allowed.add(human_captain)
    if player.username not in allowed:
        return
    if room.cpu_enabled and manager._is_cpu(room, toss_winner) and not human_captain:
        await manager._cpu_choose_toss(room)
        asyncio.create_task(_cpu_choice_timeout(manager, room, toss_winner))
        return

    choice = msg.get("choice", "bat")
    match.apply_toss_choice(choice)

    await manager.broadcast(room, {
        "type": "TOSS_DECISION",
        "winner": match.toss_winner, "choice": choice,
        "batting_first": match.batting_first,
        "bowling_first": match.bowling_first,
    })

    match.start_innings_1()
    await asyncio.sleep(2)
    await manager._send_match_state(room)
    # Start 10-second ball-pick countdowns for the opening ball
    from .match_actions import start_ball_countdowns
    if match.active_innings:
        start_ball_countdowns(manager, room, match.active_innings)
    await manager._auto_play_cpu_match(room)
