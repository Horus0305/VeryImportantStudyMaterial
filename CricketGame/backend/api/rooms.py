from fastapi import APIRouter, HTTPException, Query
from ..core.auth import decode_token
from ..realtime.ws_manager import room_manager
import socket

router = APIRouter(tags=["rooms"])

@router.post("/rooms")
def create_room(token: str = Query(...)):
    username = decode_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    code = room_manager.create_room(username)
    return {"room_code": code}

@router.post("/rooms/cpu")
def create_cpu_room(token: str = Query(...)):
    username = decode_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    code = room_manager.create_cpu_room(username)
    return {"room_code": code}

@router.get("/rooms/{code}")
def get_room_info(code: str):
    room = room_manager.get_room(code)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return {
        "code": room.code,
        "host": room.host,
        "players": room.player_list,
        "mode": room.mode,
        "overs": room.overs,
        "wickets": room.wickets,
        "cpu_enabled": room.cpu_enabled,
        "cpu_only": room.cpu_only,
        "cpu_count": len(room.cpu_names),
    }

@router.get("/network/local-ip")
def get_local_ip():
    def _try_udp_trick() -> str | None:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    def _try_hostname() -> str | None:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except Exception:
            return None

    def _is_lan_ip(ip: str | None) -> bool:
        if not ip:
            return False
        if ip.startswith("127.") or ip.startswith("169.254.") or ip == "::1":
            return False
        return True

    ip = _try_udp_trick()
    if not _is_lan_ip(ip):
        ip = _try_hostname()
    if not _is_lan_ip(ip):
        ip = None

    return {"local_ip": ip}
