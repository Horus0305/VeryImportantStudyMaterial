import random
from typing import Dict, Optional, List
from ..cpu.cpu_strategy_engine import CPUStrategyEngine
from .models import Room, PlayerConn, gen_room_code
from . import cpu as cpu_logic
from . import lobby as lobby_actions
from . import match as match_flow
from . import tournament as tournament_flow


class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.cpu_engine = CPUStrategyEngine()
    def create_room(self, host: str) -> str:
        code = gen_room_code()
        while code in self.rooms:
            code = gen_room_code()
        self.rooms[code] = Room(code, host)
        return code
    def create_cpu_room(self, host: str) -> str:
        code = gen_room_code()
        while code in self.rooms:
            code = gen_room_code()
        room = Room(code, host)
        room.cpu_enabled = True
        room.cpu_only = True
        cpu_name = self._next_cpu_name(room)
        room.cpu_names.append(cpu_name)
        room.cpu_history[cpu_name] = {"bat": [], "bowl": []}
        self.rooms[code] = room
        return code
    def _next_cpu_name(self, room: Room) -> str:
        taken = set(room.players.keys()) | set(room.cpu_names)
        if room.host != "CPU" and "CPU" not in taken:
            return "CPU"
        base = "CPU Bot"
        index = 1
        candidate = base
        while candidate in taken:
            index += 1
            candidate = f"{base} {index}"
        return candidate
    def get_room(self, code: str) -> Optional[Room]:
        return self.rooms.get(code)
    def delete_room(self, code: str) -> None:
        self.rooms.pop(code, None)
    async def send(self, player: PlayerConn, msg: dict) -> None:
        try:
            await player.ws.send_json(msg)
        except Exception:
            pass
    async def broadcast(self, room: Room, msg: dict, exclude: Optional[str] = None) -> None:
        for username, p in room.players.items():
            if username != exclude:
                await self.send(p, msg)
    async def broadcast_lobby(self, room: Room) -> None:
        await self.broadcast(room, {
            "type": "LOBBY_UPDATE",
            "players": room.player_list,
            "host": room.host,
            "mode": room.mode,
            "overs": room.overs,
            "wickets": room.wickets,
            "teams": room.teams,
            "team_names": room.team_names,
            "captains": room.captains,
            "room_code": room.code,
            "cpu_enabled": room.cpu_enabled,
            "cpu_only": room.cpu_only,
            "cpu_count": len(room.cpu_names),
            "host_plays": room.host_plays,
        })
    def _is_cpu(self, room: Room, username: str) -> bool:
        return room.cpu_enabled and username in room.cpu_names
    def _team_for_player(self, room: Room, username: str) -> Optional[str]:
        for team_key, members in room.teams.items():
            if username in members:
                return team_key
        return None
    def _active_humans(self, room: Room) -> List[str]:
        return [p.username for p in room.players.values() if room.host_plays or p.username != room.host]
    def _weighted_choice(self, weights: Dict[int, float]) -> int:
        total = sum(weights.values())
        if total <= 0:
            return 0
        roll = random.random() * total
        upto = 0.0
        for move, weight in weights.items():
            upto += weight
            if roll <= upto:
                return move
        return 0
    async def handle_message(self, room: Room, player: PlayerConn, msg: dict) -> None:
        action = msg.get("action", "")
        if action == "CONFIGURE":
            await self._configure(room, player, msg)
        elif action == "START_MATCH":
            await self._start_match(room, player)
        elif action == "START_TOURNAMENT":
            await self._start_tournament(room, player)
        elif action == "TOSS_CALL":
            await self._toss_call(room, player, msg)
        elif action == "TOSS_CHOICE":
            await self._toss_choice(room, player, msg)
        elif action == "GAME_MOVE":
            await self._game_move(room, player, msg)
        elif action == "ASSIGN_TEAM":
            await self._assign_team(room, player, msg)
        elif action == "SET_TEAM_NAME":
            await self._set_team_name(room, player, msg)
        elif action == "SET_CAPTAIN":
            await self._set_captain(room, player, msg)
        elif action == "RESET_TEAMS":
            await self._reset_teams(room, player)
        elif action == "ADD_CPU":
            await self._add_cpu(room, player)
        elif action == "REMOVE_CPU":
            await self._remove_cpu(room, player)
        elif action == "CANCEL_MATCH":
            await self._cancel_match(room, player)
        elif action == "PICK_BATTER":
            await self._pick_batter(room, player, msg)
        elif action == "PICK_BOWLER":
            await self._pick_bowler(room, player, msg)
    async def _configure(self, room: Room, player: PlayerConn, msg: dict) -> None:
        await lobby_actions.configure(self, room, player, msg)
    async def _assign_team(self, room: Room, player: PlayerConn, msg: dict) -> None:
        await lobby_actions.assign_team(self, room, player, msg)
    async def _set_team_name(self, room: Room, player: PlayerConn, msg: dict) -> None:
        await lobby_actions.set_team_name(self, room, player, msg)
    async def _set_captain(self, room: Room, player: PlayerConn, msg: dict) -> None:
        await lobby_actions.set_captain(self, room, player, msg)
    async def _reset_teams(self, room: Room, player: PlayerConn) -> None:
        await lobby_actions.reset_teams(self, room, player)
    async def _add_cpu(self, room: Room, player: PlayerConn) -> None:
        await lobby_actions.add_cpu(self, room, player)
    async def _remove_cpu(self, room: Room, player: PlayerConn) -> None:
        await lobby_actions.remove_cpu(self, room, player)
    async def _start_match(self, room: Room, player: PlayerConn) -> None:
        await match_flow.start_match(self, room, player)
    async def _initiate_toss(self, room: Room) -> None:
        await match_flow.initiate_toss(self, room)
    async def _toss_call(self, room: Room, player: PlayerConn, msg: dict) -> None:
        await match_flow.toss_call(self, room, player, msg)
    async def _toss_choice(self, room: Room, player: PlayerConn, msg: dict) -> None:
        await match_flow.toss_choice(self, room, player, msg)
    async def _game_move(self, room: Room, player: PlayerConn, msg: dict) -> None:
        await match_flow.game_move(self, room, player, msg)
    async def _send_match_state(self, room: Room) -> None:
        await match_flow.send_match_state(self, room)
    async def _resolve_pending_ball(self, room: Room, innings) -> bool:
        return await match_flow.resolve_pending_ball(self, room, innings)
    def _save_match_stats(self, room: Room, match) -> None:
        return match_flow.save_match_stats(self, room, match)
    def _save_match_history(self, room: Room, match, potm_data: dict, tournament_id: Optional[str] = None) -> None:
        return match_flow.save_match_history(self, room, match, potm_data, tournament_id)
    async def _cancel_match(self, room: Room, player: PlayerConn) -> None:
        await match_flow.cancel_match(self, room, player)
    async def _pick_batter(self, room: Room, player: PlayerConn, msg: dict) -> None:
        await match_flow.handle_pick_batter(self, room, player, msg)
    async def _pick_bowler(self, room: Room, player: PlayerConn, msg: dict) -> None:
        await match_flow.handle_pick_bowler(self, room, player, msg)
    async def _cpu_call_toss(self, room: Room) -> None:
        await cpu_logic.cpu_call_toss(self, room)
    async def _cpu_choose_toss(self, room: Room) -> None:
        await cpu_logic.cpu_choose_toss(self, room)
    async def _maybe_cpu_move(self, room: Room, innings) -> None:
        await cpu_logic.maybe_cpu_move(self, room, innings)
    async def _auto_play_cpu_match(self, room: Room) -> None:
        await cpu_logic.auto_play_cpu_match(self, room)
    async def _start_tournament(self, room: Room, player: PlayerConn) -> None:
        await tournament_flow.start_tournament(self, room, player)
    async def _start_next_tournament_match(self, room: Room) -> None:
        await tournament_flow.start_next_tournament_match(self, room)
    async def _create_tournament_match(self, room: Room, p1: str, p2: str) -> None:
        await tournament_flow.create_tournament_match(self, room, p1, p2)
    def _apply_tournament_result(self, room: Room, match) -> dict:
        return tournament_flow.apply_tournament_result(self, room, match)
    def _apply_tournament_cancellation(self, room: Room, match) -> dict:
        return tournament_flow.apply_tournament_cancellation(self, room, match)
    def _build_tournament_payload(self, tournament, skip_current: bool) -> dict:
        return tournament_flow.build_tournament_payload(tournament, skip_current)
