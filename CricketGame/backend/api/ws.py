from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ..core.auth import decode_token
from ..realtime.ws_manager import PlayerConn, room_manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/{room_code}")
async def websocket_endpoint(ws: WebSocket, room_code: str, token: str = Query(...)):
    await ws.accept()

    username = decode_token(token)
    if not username:
        await ws.send_json({"type": "ERROR", "msg": "Invalid or expired token"})
        await ws.close(code=4001, reason="Invalid token")
        return

    room = room_manager.get_room(room_code)
    if not room:
        await ws.send_json({"type": "ERROR", "msg": "Room not found (server may have restarted)"})
        await ws.close(code=4004, reason="Room not found")
        return

    # Replace any stale connection for the same username.
    old_player = room.players.get(username)
    player = PlayerConn(ws, username)
    player.team = room_manager._team_for_player(room, username)
    player.is_captain = room.captains.get("A") == username or room.captains.get("B") == username
    room.players[username] = player
    if old_player and old_player.ws is not ws:
        try:
            await old_player.ws.close(code=4000, reason="Reconnected from another session")
        except Exception:
            pass
    print(f"[WS] {username} joined room {room_code}")

    await room_manager.broadcast_lobby(room)

    if room.match and room.match.active_innings:
        await room_manager._send_match_state(room)
    elif room.tournament:
        payload = room_manager._build_tournament_payload(room.tournament, skip_current=False)
        await room_manager.send(player, {"type": "TOURNAMENT_STANDINGS", **payload})

    try:
        while True:
            msg = await ws.receive_json()
            await room_manager.handle_message(room, player, msg)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS] Error for {username}: {e}")
    finally:
        # Only cleanup if this connection is still the active mapping.
        active = room.players.get(username)
        if active is player:
            room.players.pop(username, None)
            for team_list in room.teams.values():
                if username in team_list:
                    team_list.remove(username)
            print(f"[WS] {username} left room {room_code}")

            if not room.players:
                room_manager.delete_room(room_code)
                print(f"[WS] Room {room_code} deleted (empty)")
            else:
                await room_manager.broadcast_lobby(room)
