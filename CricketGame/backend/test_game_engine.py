import asyncio

from .game.game_engine import Innings, Match, compute_potm, compute_tournament_awards
from .realtime.models import Room, PlayerConn
from .realtime.match.match_start import start_match
from .realtime.match.match_actions import resolve_pending_ball
from .realtime.match import toss as toss_module


def test_innings_resolution():
    innings = Innings(["A", "B"], ["C", "D"], total_overs=1, total_wickets=1)
    result = innings.resolve_ball(1, 2)
    assert result["runs"] == 1
    assert innings.total_runs == 1
    result = innings.resolve_ball(3, 3)
    assert result["is_out"] is True
    assert result["innings_complete"] is True


def test_match_flow_and_potm():
    match = Match("M1", "quick", ["A", "B"], ["C", "D"], total_overs=1, total_wickets=1)
    match.toss_winner = "A"
    match.apply_toss_choice("bat")
    match.start_innings_1()
    match.innings_1.resolve_ball(0, 0)
    match.start_innings_2()
    match.innings_2.resolve_ball(1, 2)
    result = match.determine_result()
    assert result["winner"] is not None
    potm = compute_potm(match)
    assert potm["player"] in ["A", "B", "C", "D"]


def test_tournament_awards():
    match = Match("M2", "quick", ["A", "B"], ["C", "D"], total_overs=1, total_wickets=1)
    match.toss_winner = "A"
    match.apply_toss_choice("bat")
    match.start_innings_1()
    match.innings_1.resolve_ball(2, 3)
    match.start_innings_2()
    match.innings_2.resolve_ball(1, 2)
    result = match.determine_result()
    awards = compute_tournament_awards([result])
    assert "orange_cap" in awards
    assert "purple_cap" in awards


def test_host_opt_out_excludes_from_lobby_and_match_start():
    room = Room("ROOM1", "Host")
    room.players["Host"] = PlayerConn(None, "Host")
    room.players["Alice"] = PlayerConn(None, "Alice")
    room.players["Host"].team = "A"
    room.players["Host"].is_captain = True
    room.teams["A"] = ["Host"]
    room.teams["B"] = ["Alice"]
    room.captains["A"] = "Host"
    room.captains["B"] = "Alice"
    room.host_plays = False

    assert all(p["username"] != "Host" for p in room.player_list)

    class DummyManager:
        def __init__(self):
            self.sent = []

        async def send(self, player, msg):
            self.sent.append(msg)

        def _active_humans(self, current_room):
            return [p.username for p in current_room.players.values() if current_room.host_plays or p.username != current_room.host]

        async def _initiate_toss(self, current_room):
            return None

    manager = DummyManager()

    async def run():
        await start_match(manager, room, room.players["Host"])

    asyncio.run(run())
    assert "Host" not in room.teams.get("A", [])
    assert room.captains.get("A") != "Host"
    assert room.players["Host"].team is None
    assert room.players["Host"].is_captain is False


def test_cpu_toss_timeout_fallback_triggers():
    room = Room("ROOM2", "Host")
    room.mode = "team"
    room.cpu_enabled = True
    room.cpu_names = ["CPU Bot"]
    room.cpu_history = {"CPU Bot": {"bat": [], "bowl": []}}
    room.teams["A"] = ["CPU Bot"]
    room.captains["A"] = "CPU Bot"
    match = Match("M3", "team", ["CPU Bot"], ["Host"], total_overs=1, total_wickets=1)

    def fixed_do_toss(caller=None):
        match.toss_caller = "CPU Bot"
        return {"caller": "CPU Bot"}

    match.do_toss = fixed_do_toss
    room.match = match

    class DummyManager:
        def __init__(self):
            self.cpu_calls = 0

        async def send(self, player, msg):
            return None

        def _is_cpu(self, current_room, username: str) -> bool:
            return username in current_room.cpu_names

        def _team_for_player(self, current_room, username: str):
            for team_key, members in current_room.teams.items():
                if username in members:
                    return team_key
            return None

        async def _cpu_call_toss(self, current_room):
            self.cpu_calls += 1

    manager = DummyManager()
    old_timeout = toss_module.CPU_PICK_TIMEOUT
    toss_module.CPU_PICK_TIMEOUT = 0.01

    async def run():
        await toss_module.initiate_toss(manager, room)
        await asyncio.sleep(0.05)

    asyncio.run(run())
    toss_module.CPU_PICK_TIMEOUT = old_timeout
    assert manager.cpu_calls >= 2


def test_cpu_toss_choice_timeout_fallback_triggers():
    room = Room("ROOM3", "Host")
    room.cpu_enabled = True
    room.cpu_names = ["CPU Bot"]
    room.toss_state = {"phase": "choosing"}
    match = Match("M4", "team", ["CPU Bot"], ["Host"], total_overs=1, total_wickets=1)
    match.toss_winner = "CPU Bot"
    room.match = match

    class DummyManager:
        def __init__(self):
            self.cpu_choices = 0

        def _is_cpu(self, current_room, username: str) -> bool:
            return username in current_room.cpu_names

        async def _cpu_choose_toss(self, current_room):
            self.cpu_choices += 1

    manager = DummyManager()
    old_timeout = toss_module.CPU_PICK_TIMEOUT
    toss_module.CPU_PICK_TIMEOUT = 0.01

    async def run():
        await toss_module._cpu_choice_timeout(manager, room, "CPU Bot")

    asyncio.run(run())
    toss_module.CPU_PICK_TIMEOUT = old_timeout
    assert manager.cpu_choices == 1


def test_cpu_autoplay_triggers_after_over_resolution():
    room = Room("ROOM4", "Host")
    room.cpu_enabled = True
    room.cpu_names = ["CPU Bot", "CPU Bot 2"]
    room.cpu_history = {
        "CPU Bot": {"bat": [], "bowl": []},
        "CPU Bot 2": {"bat": [], "bowl": []},
    }
    match = Match("M5", "team", ["CPU Bot", "CPU Bot 2"], ["CPU Bot", "CPU Bot 2"], total_overs=1, total_wickets=2)
    match.toss_winner = "CPU Bot"
    match.apply_toss_choice("bat")
    match.start_innings_1()
    room.match = match

    innings = match.active_innings
    room.pending_moves = {"bat": 1, "bowl": 2}

    class DummyManager:
        def __init__(self):
            self.auto_play_calls = 0
            self.cpu_move_calls = 0

        async def broadcast(self, current_room, msg, exclude=None):
            return None

        async def broadcast_lobby(self, current_room):
            return None

        async def _send_match_state(self, current_room):
            return None

        async def _maybe_cpu_move(self, current_room, current_innings):
            self.cpu_move_calls += 1

        async def _auto_play_cpu_match(self, current_room):
            self.auto_play_calls += 1

        def _apply_tournament_result(self, current_room, current_match):
            return {}

        def _start_next_tournament_match(self, current_room):
            return None

    manager = DummyManager()

    async def run():
        await resolve_pending_ball(manager, room, innings)

    asyncio.run(run())
    assert manager.auto_play_calls == 1
    assert manager.cpu_move_calls == 1


def run_all_tests():
    test_innings_resolution()
    test_match_flow_and_potm()
    test_tournament_awards()
    test_host_opt_out_excludes_from_lobby_and_match_start()
    test_cpu_toss_timeout_fallback_triggers()
    test_cpu_toss_choice_timeout_fallback_triggers()
    test_cpu_autoplay_triggers_after_over_resolution()


if __name__ == "__main__":
    run_all_tests()
