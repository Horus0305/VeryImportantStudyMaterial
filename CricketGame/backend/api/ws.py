from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ..realtime.ws_manager import room_manager, PlayerConn
from ..core.auth import decode_token

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

    player = PlayerConn(ws, username)
    room.players[username] = player
    print(f"✅ {username} joined room {room_code}")

    await room_manager.broadcast_lobby(room)

    try:
        while True:
            msg = await ws.receive_json()
            await room_manager.handle_message(room, player, msg)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"⚠ WebSocket error for {username}: {e}")
    finally:
        room.players.pop(username, None)
        for team_list in room.teams.values():
            if username in team_list:
                team_list.remove(username)
        print(f"❌ {username} left room {room_code}")

        if not room.players:
            room_manager.delete_room(room_code)
            print(f"🗑 Room {room_code} deleted (empty)")
        else:
            await room_manager.broadcast_lobby(room)
