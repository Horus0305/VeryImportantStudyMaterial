import json
from datetime import datetime

from ...data.database import SessionLocal
from ...core.auth import update_player_stats
from ...data.models import MatchHistory
from ...game.game_engine import Match


def save_match_stats(manager, room, match: Match) -> None:
    db = SessionLocal()
    try:
        # Normalize legacy "2v2" → "team" so stats always land on the team tab
        game_format = match.mode
        if game_format in ("2v2", "team"):
            game_format = "team"

        all_players = match.side_a + match.side_b
        for player_name in all_players:
            is_winner = match.winner and player_name in match.winner

            bat_data = None
            bowl_data = None

            for inn in [match.innings_1, match.innings_2]:
                if inn and player_name in inn.batting_cards:
                    card = inn.batting_cards[player_name]
                    bat_data = {
                        "runs": card.runs, "balls": card.balls,
                        "fours": card.fours, "sixes": card.sixes,
                    }
                if inn and player_name in inn.bowling_cards:
                    card = inn.bowling_cards[player_name]
                    bowl_data = {
                        "wickets": card.wickets,
                        "runs_conceded": card.runs_conceded,
                        "overs": card.overs_completed + card.balls_bowled_in_over / 6,
                    }

            update_player_stats(db, player_name, game_format,
                                batting_data=bat_data,
                                bowling_data=bowl_data,
                                won=is_winner)
    finally:
        db.close()


def save_match_history(manager, room, match: Match, potm_data: dict, tournament_id=None) -> None:
    db = SessionLocal()
    try:
        sc1 = match.innings_1.get_scorecard() if match.innings_1 else {}
        sc2 = match.innings_2.get_scorecard() if match.innings_2 else {}
        super_over_timeline = match.get_super_over_timeline() if hasattr(match, "get_super_over_timeline") else []
        potm_payload = dict(potm_data) if isinstance(potm_data, dict) else None

        if match.is_super_over and potm_payload is not None:
            latest_round = super_over_timeline[-1] if super_over_timeline else None
            if latest_round:
                potm_payload["super_over_data"] = {
                    "scorecard_3": latest_round.get("scorecard_3") or {},
                    "scorecard_4": latest_round.get("scorecard_4") or {},
                    "bat_team_3": latest_round.get("bat_team_3") or match.bowling_first,
                    "bat_team_4": latest_round.get("bat_team_4") or match.batting_first,
                }
            else:
                potm_payload["super_over_data"] = {
                    "scorecard_3": match.innings_3.get_scorecard() if getattr(match, "innings_3", None) else {},
                    "scorecard_4": match.innings_4.get_scorecard() if getattr(match, "innings_4", None) else {},
                    "bat_team_3": match.bowling_first,
                    "bat_team_4": match.batting_first,
                }

        history = MatchHistory(
            match_id=match.id,
            room_code=room.code,
            mode=match.mode,
            side_a=json.dumps(match.side_a),
            side_b=json.dumps(match.side_b),
            scorecard_1=json.dumps(sc1),
            scorecard_2=json.dumps(sc2),
            result_text=match.result_text,
            winner=match.winner,
            potm=potm_payload.get("player") if potm_payload else None,
            potm_stats=json.dumps(potm_payload) if potm_payload else None,
            super_over_timeline=json.dumps(super_over_timeline) if super_over_timeline else None,
            tournament_id=tournament_id,
            end_timestamp=datetime.utcnow(),
        )

        db.add(history)
        db.commit()

        if tournament_id:
            room.tournament_match_ids.append(match.id)
            room.tournament_scorecards.append({
                "scorecard_1": sc1,
                "scorecard_2": sc2,
            })
    except Exception as e:
        print(f"⚠ Error saving match history: {e}")
        db.rollback()
    finally:
        db.close()
