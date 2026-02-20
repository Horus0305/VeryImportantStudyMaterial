from ...game.game_engine import Match
from ...cpu.cpu_ball_logger import log_ball_async


def record_cpu_history(manager, room, innings, bat_move: int, bowl_move: int) -> None:
    if not room.cpu_enabled:
        return
    if innings.striker in room.cpu_names:
        room.cpu_history.setdefault(innings.striker, {"bat": [], "bowl": []})
        room.cpu_history[innings.striker]["bowl"].append(bowl_move)
    if innings.current_bowler in room.cpu_names:
        room.cpu_history.setdefault(innings.current_bowler, {"bat": [], "bowl": []})
        room.cpu_history[innings.current_bowler]["bat"].append(bat_move)


def log_ball_for_learning(manager, room, match: Match, innings, bat_move: int, bowl_move: int, result: dict) -> None:
    if innings.striker in room.cpu_names and innings.current_bowler in room.cpu_names:
        return
    try:
        balls_bowled = innings.overs_completed * 6 + innings.balls_in_over
        total_balls = innings.total_overs * 6
        balls_remaining = total_balls - balls_bowled
        batting_first = match.current_innings == 1
        log_ball_async(
            match_id=match.id,
            ball_number=result.get("ball_num", balls_bowled),
            batter_username=innings.striker,
            bowler_username=innings.current_bowler,
            bat_move=bat_move,
            bowl_move=bowl_move,
            runs_scored=result.get("runs", 0),
            is_out=result.get("is_out", False),
            match_format_overs=match.total_overs,
            current_over=innings.overs_completed,
            total_overs=innings.total_overs,
            innings=match.current_innings,
            batting_score=innings.total_runs,
            batting_wickets=innings.wickets_fallen,
            target=innings.target,
            balls_remaining=balls_remaining,
            batting_first=batting_first,
        )
    except Exception as e:
        print(f"⚠ Error logging ball for learning: {e}")
