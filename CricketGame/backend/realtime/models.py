import random
import string
from typing import Dict, Optional, List, Any

from fastapi import WebSocket
from ..game.game_engine import Match
from ..game.tournament import Tournament


def gen_room_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


class PlayerConn:
    """A single authenticated WebSocket connection."""
    def __init__(self, ws: WebSocket, username: str):
        self.ws = ws
        self.username = username
        self.team: Optional[str] = None
        self.is_captain = False


class Room:
    """A game room with lobby, settings, and active match state."""
    def __init__(self, code: str, host: str):
        self.code = code
        self.host = host
        self.players: Dict[str, PlayerConn] = {}

        self.mode = "1v1"
        self.overs = 2
        self.wickets = 1
        self.host_plays = True

        self.teams: Dict[str, List[str]] = {"A": [], "B": []}
        self.team_names: Dict[str, str] = {"A": "Team A", "B": "Team B"}
        self.captains: Dict[str, Optional[str]] = {"A": None, "B": None}

        self.match: Optional[Match] = None
        self.pending_moves: Dict[str, int] = {}
        self.toss_state: Dict[str, Any] = {}
        self.cpu_enabled = False
        self.cpu_only = False
        self.cpu_names: List[str] = []
        self.cpu_history: Dict[str, Dict[str, List[int]]] = {}
        self.cpu_autoplay = False

        self.tournament: Optional[Tournament] = None
        self.tournament_id: Optional[str] = None
        self.tournament_match_ids: List[str] = []
        self.tournament_scorecards: List[dict] = []

        # Captain selection & countdown state
        # Tracks how many times CPU auto-played for a human player this innings
        self.auto_move_strikes: Dict[str, int] = {}
        # Holds running asyncio timeout Tasks keyed by "bat", "bowl", or "captain"
        self.pending_timeouts: Dict[str, Any] = {}

    @property
    def player_list(self) -> List[dict]:
        players = [
            {
                "username": p.username,
                "team": p.team,
                "is_captain": p.is_captain,
                "in_match": self.match is not None and not self.match.is_finished,
            }
            for p in self.players.values()
            if self.host_plays or p.username != self.host
        ]
        if self.cpu_enabled:
            for cpu_name in self.cpu_names:
                cpu_team = None
                if cpu_name in self.teams.get("A", []):
                    cpu_team = "A"
                elif cpu_name in self.teams.get("B", []):
                    cpu_team = "B"
                cpu_is_captain = self.captains.get("A") == cpu_name or self.captains.get("B") == cpu_name
                players.append({
                    "username": cpu_name,
                    "team": cpu_team,
                    "is_captain": cpu_is_captain,
                    "in_match": self.match is not None and not self.match.is_finished,
                })
        return players
