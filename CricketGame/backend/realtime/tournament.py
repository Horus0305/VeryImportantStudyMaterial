import json
import random
import uuid

from ..data.database import SessionLocal
from ..data.models import TournamentHistory
from ..game.game_engine import Match, compute_tournament_awards
from ..game.tournament import Tournament


def build_tournament_payload(tournament: Tournament, skip_current: bool) -> dict:
    upcoming = []
    if tournament.phase == Tournament.PHASE_GROUP:
        start = tournament.current_group_match_idx + (1 if skip_current else 0)
        remaining = tournament.group_matches[start:]
        upcoming = [{"label": "group", "teams": [a, b]} for a, b in remaining]
    else:
        phases = [Tournament.PHASE_Q1, Tournament.PHASE_ELIM, Tournament.PHASE_Q2, Tournament.PHASE_FINAL]
        for key in phases:
            pair = tournament.playoff_matches.get(key)
            teams = list(pair) if pair else []
            upcoming.append({"label": key, "teams": teams})
    return {
        "standings": tournament.get_sorted_standings(),
        "phase": tournament.phase,
        "info": tournament.to_dict(),
        "upcoming_matches": upcoming,
    }


async def start_tournament(manager, room, player) -> None:
    if player.username != room.host:
        return
    if room.cpu_only:
        await manager.send(player, {"type": "ERROR", "msg": "CPU-only rooms cannot start tournaments."})
        return
    usernames = manager._active_humans(room)
    if room.cpu_enabled:
        usernames.extend(room.cpu_names)
    if len(usernames) < 4:
        await manager.send(player, {"type": "ERROR", "msg": "Need at least 4 players."})
        return

    room.tournament = Tournament(usernames, room.overs, room.wickets)
    room.tournament_id = str(uuid.uuid4())[:8]
    room.tournament_match_ids = []
    room.tournament_scorecards = []

    db = SessionLocal()
    try:
        from ..data.models import FormatStats, Player
        for u in usernames:
            player = db.query(Player).filter(Player.username == u).first()
            if player:
                fs = db.query(FormatStats).filter(
                    FormatStats.player_id == player.id,
                    FormatStats.format == "tournament"
                ).first()
                if fs:
                    fs.tournaments_played += 1
        db.commit()
    finally:
        db.close()

    await manager.broadcast(room, {
        "type": "TOURNAMENT_STANDINGS",
        **build_tournament_payload(room.tournament, skip_current=False),
    })
    await manager._start_next_tournament_match(room)


async def start_next_tournament_match(manager, room) -> None:
    t = room.tournament
    if not t:
        return

    if t.phase == Tournament.PHASE_GROUP:
        pair = t.get_next_group_match()
        if pair:
            await manager._create_tournament_match(room, pair[0], pair[1])
    elif t.phase in (Tournament.PHASE_Q1, Tournament.PHASE_ELIM,
                     Tournament.PHASE_Q2, Tournament.PHASE_FINAL):
        pair = t.get_current_playoff_match()
        if pair:
            await manager.broadcast(room, {
                "type": "TOURNAMENT_PHASE",
                "phase": t.phase, "match": list(pair),
            })
            await manager._create_tournament_match(room, pair[0], pair[1])
    elif t.phase == Tournament.PHASE_COMPLETE:
        awards = compute_tournament_awards(room.tournament_scorecards)

        db = SessionLocal()
        try:
            from ..data.models import FormatStats, Player
            if t.champion:
                player = db.query(Player).filter(Player.username == t.champion).first()
                if player:
                    fs = db.query(FormatStats).filter(
                        FormatStats.player_id == player.id,
                        FormatStats.format == "tournament"
                    ).first()
                    if fs:
                        fs.tournaments_won += 1

            db.commit()
        except Exception as e:
            print(f"Error updating tournament stats: {e}")
            db.rollback()
        finally:
            db.close()

        await manager.broadcast(room, {
            "type": "TOURNAMENT_OVER",
            "champion": t.champion,
            "standings": t.get_sorted_standings(),
            "awards": awards,
            "tournament_id": room.tournament_id,
            "info": t.to_dict(),
        })

        save_tournament_history(manager, room, t, awards)

        room.tournament = None
        room.tournament_id = None
        room.tournament_match_ids = []
        room.tournament_scorecards = []


async def create_tournament_match(manager, room, p1: str, p2: str) -> None:
    match_id = str(uuid.uuid4())[:8]
    room.match = Match(
        match_id=match_id, mode="tournament",
        side_a=[p1], side_b=[p2],
        total_overs=room.overs, total_wickets=room.wickets,
    )
    room.pending_moves = {}
    await manager._initiate_toss(room)


def apply_tournament_result(manager, room, match: Match) -> dict:
    t = room.tournament
    if not t:
        return {}
    winner = match.winner if match.winner != "TIE" else match.side_a[0]
    nrr = match.get_nrr_data()
    p1, p2 = match.side_a[0], match.side_b[0]

    if t.phase == Tournament.PHASE_GROUP:
        t.record_group_result(p1, p2, winner, nrr)
    else:
        loser = p2 if winner == p1 else p1
        t.record_playoff_result(winner, loser)

    return build_tournament_payload(t, skip_current=False)


def apply_tournament_cancellation(manager, room, match: Match) -> dict:
    t = room.tournament
    if not t:
        return {}

    p1 = match.side_a[0]
    p2 = match.side_b[0]

    if t.phase == Tournament.PHASE_GROUP:
        t.record_group_result(p1, p2, winner=None, nrr_data={
            "runs_scored_1": 0, "overs_faced_1": 0,
            "runs_scored_2": 0, "overs_faced_2": 0
        })
    else:
        winner = random.choice([p1, p2])
        loser = p2 if winner == p1 else p1
        t.record_playoff_result(winner, loser)

    return build_tournament_payload(t, skip_current=True)


def save_tournament_history(manager, room, t: Tournament, awards: dict) -> None:
    db = SessionLocal()
    try:
        history = TournamentHistory(
            tournament_id=room.tournament_id,
            room_code=room.code,
            players=json.dumps(t.players),
            standings=json.dumps(t.get_sorted_standings()),
            playoff_bracket=json.dumps({
                k: list(v) if v else None
                for k, v in t.playoff_matches.items()
            }),
            playoff_results=json.dumps(t.playoff_results),
            match_ids=json.dumps(room.tournament_match_ids),
            champion=t.champion,
            orange_cap=json.dumps(awards.get("orange_cap")),
            purple_cap=json.dumps(awards.get("purple_cap")),
            best_strike_rate=json.dumps(awards.get("best_strike_rate")),
            best_average=json.dumps(awards.get("best_average")),
            best_economy=json.dumps(awards.get("best_economy")),
            player_of_tournament=json.dumps(awards.get("player_of_tournament")),
        )
        db.add(history)
        db.commit()
    except Exception as e:
        print(f"⚠ Error saving tournament history: {e}")
        db.rollback()
    finally:
        db.close()
