async def configure(manager, room, player, msg: dict) -> None:
    if player.username != room.host:
        return
    if room.cpu_only:
        room.mode = "1v1"
    else:
        room.mode = msg.get("mode", room.mode)
    room.overs = msg.get("overs", room.overs)
    room.wickets = msg.get("wickets", room.wickets)
    room.host_plays = bool(msg.get("host_plays", room.host_plays))
    if not room.host_plays:
        print(f"🛑 Host opt-out: host={room.host} room={room.code} mode={room.mode}")
        for t in room.teams.values():
            if room.host in t:
                t.remove(room.host)
        for team_key, captain in list(room.captains.items()):
            if captain == room.host:
                room.captains[team_key] = None
        if room.host in room.players:
            room.players[room.host].team = None
            room.players[room.host].is_captain = False
    await manager.broadcast_lobby(room)


async def assign_team(manager, room, player, msg: dict) -> None:
    if player.username != room.host:
        return
    target = msg.get("player")
    team = msg.get("team")
    if team not in ("A", "B") or not target:
        return
    if target == room.host and not room.host_plays:
        return
    for t in room.teams.values():
        if target in t:
            t.remove(target)
    room.teams[team].append(target)
    if target in room.players:
        room.players[target].team = team
    await manager.broadcast_lobby(room)


async def set_team_name(manager, room, player, msg: dict) -> None:
    team = msg.get("team")
    name = msg.get("name", "")
    if player.username == room.captains.get(team) or player.username == room.host:
        room.team_names[team] = name
        await manager.broadcast_lobby(room)


async def set_captain(manager, room, player, msg: dict) -> None:
    if player.username != room.host:
        return
    team = msg.get("team")
    captain = msg.get("captain")
    if team not in ("A", "B") or not captain:
        return
    if captain == room.host and not room.host_plays:
        return
    if captain not in room.teams.get(team, []):
        for t in room.teams.values():
            if captain in t:
                t.remove(captain)
        room.teams[team].append(captain)
        if captain in room.players:
            room.players[captain].team = team
    old_captain = room.captains.get(team)
    if old_captain and old_captain in room.players:
        room.players[old_captain].is_captain = False
    room.captains[team] = captain
    if captain in room.players:
        room.players[captain].is_captain = True
    await manager.broadcast_lobby(room)


async def reset_teams(manager, room, player) -> None:
    if player.username != room.host:
        return
    room.teams = {"A": [], "B": []}
    room.captains = {"A": None, "B": None}
    for p in room.players.values():
        p.team = None
        p.is_captain = False
    await manager.broadcast_lobby(room)


async def add_cpu(manager, room, player) -> None:
    if player.username != room.host:
        return
    if room.cpu_only:
        return
    if room.match or room.tournament:
        return
    room.cpu_enabled = True
    room.cpu_only = False
    cpu_name = manager._next_cpu_name(room)
    room.cpu_names.append(cpu_name)
    room.cpu_history[cpu_name] = {"bat": [], "bowl": []}
    await manager.broadcast_lobby(room)


async def remove_cpu(manager, room, player) -> None:
    if player.username != room.host:
        return
    if room.cpu_only or not room.cpu_enabled:
        return
    if room.match or room.tournament:
        return
    if not room.cpu_names:
        return
    cpu_name = room.cpu_names.pop()
    for t in room.teams.values():
        if cpu_name in t:
            t.remove(cpu_name)
    for team_key, captain in list(room.captains.items()):
        if captain == cpu_name:
            room.captains[team_key] = None
    room.cpu_history.pop(cpu_name, None)
    if not room.cpu_names:
        room.cpu_enabled = False
    await manager.broadcast_lobby(room)
