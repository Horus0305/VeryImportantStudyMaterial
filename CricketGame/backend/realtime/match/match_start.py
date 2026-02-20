import uuid
from ...game.game_engine import Match


async def start_match(manager, room, player) -> None:
    if player.username != room.host:
        return
    if not room.host_plays:
        for t in room.teams.values():
            if room.host in t:
                t.remove(room.host)
        for team_key, captain in list(room.captains.items()):
            if captain == room.host:
                room.captains[team_key] = None
        if room.host in room.players:
            room.players[room.host].team = None
            room.players[room.host].is_captain = False
    if room.mode == "team":
        active_humans = manager._active_humans(room)
        active_set = set(active_humans)
        team_a = [p for p in room.teams.get("A", []) if p in active_set or p in room.cpu_names]
        team_b = [p for p in room.teams.get("B", []) if p in active_set or p in room.cpu_names]
        total_players = len(active_humans) + (len(room.cpu_names) if room.cpu_enabled and not room.cpu_only else 0)
        assigned_total = len(team_a) + len(team_b)
        if assigned_total != total_players:
            await manager.send(player, {"type": "ERROR", "msg": "Assign all players to teams."})
            return
        if len(team_a) < 2 or len(team_b) < 2 or len(team_a) != len(team_b):
            await manager.send(player, {"type": "ERROR", "msg": "Teams must be equal size with at least 2 players."})
            return
        if not room.captains.get("A") or not room.captains.get("B"):
            await manager.send(player, {"type": "ERROR", "msg": "Both teams need a captain."})
            return
        side_a = list(team_a)
        side_b = list(team_b)
        match_mode = room.mode
    else:
        usernames = manager._active_humans(room)
        if room.cpu_only or (room.cpu_enabled and len(usernames) == 1):
            if len(usernames) != 1:
                await manager.send(player, {"type": "ERROR", "msg": "CPU mode supports 1 player."})
                return
            if len(room.cpu_names) > 1:
                await manager.send(player, {"type": "ERROR", "msg": "1v1 supports only 1 CPU."})
                return
            side_a = [usernames[0]]
            side_b = [room.cpu_names[0]]
            match_mode = "cpu"
        else:
            if len(usernames) < 2:
                await manager.send(player, {"type": "ERROR", "msg": "Need at least 2 players."})
                return
            side_a = [usernames[0]]
            side_b = [usernames[1]]
            match_mode = room.mode

    match_id = str(uuid.uuid4())[:8]
    room.match = Match(
        match_id=match_id, mode=match_mode,
        side_a=side_a, side_b=side_b,
        total_overs=room.overs, total_wickets=room.wickets,
    )
    room.pending_moves = {}
    # Reset countdown state for a fresh match
    room.auto_move_strikes = {}
    for task in room.pending_timeouts.values():
        if task and not task.done():
            task.cancel()
    room.pending_timeouts = {}
    await manager._initiate_toss(room)
