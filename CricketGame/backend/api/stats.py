import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..cpu.cpu_strategy_engine import CPUStrategyEngine
from ..data.database import get_db
from ..data.models import MatchHistory, Player, TournamentHistory

router = APIRouter(prefix="/api", tags=["stats"])
_cpu_status_engine = CPUStrategyEngine()


def _json_list(raw) -> list[str]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def _winner_includes_player(winner: str | None, player: str) -> bool:
    if not winner or winner == "TIE":
        return False
    names = [n.strip() for n in winner.split(",") if n.strip()]
    if not names:
        return False
    if len(names) == 1:
        return names[0] == player
    return player in names


@router.get("/match/{match_id}")
def get_match_detail(match_id: str, db: Session = Depends(get_db)):
    match = db.query(MatchHistory).filter(MatchHistory.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match.to_dict()


@router.get("/matches/{username}")
def get_user_matches(username: str, mode: str = Query(None), limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(MatchHistory).filter(
        or_(
            MatchHistory.side_a.contains(username),
            MatchHistory.side_b.contains(username),
        )
    )
    if mode:
        if mode == "team":
            query = query.filter(or_(MatchHistory.mode == "team", MatchHistory.mode == "2v2"))
        else:
            query = query.filter(MatchHistory.mode == mode)

    rows = query.order_by(MatchHistory.timestamp.desc()).all()
    out = []
    safe_limit = min(max(limit, 0), 500)
    if safe_limit == 0:
        return out
    for m in rows:
        side_a = _json_list(m.side_a)
        side_b = _json_list(m.side_b)
        if username in side_a or username in side_b:
            out.append(m.to_dict())
            if len(out) >= safe_limit:
                break
    return out


@router.get("/tournament/{tournament_id}")
def get_tournament_detail(tournament_id: str, db: Session = Depends(get_db)):
    tournament = db.query(TournamentHistory).filter(
        TournamentHistory.tournament_id == tournament_id
    ).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    matches = (
        db.query(MatchHistory)
        .filter(MatchHistory.tournament_id == tournament_id)
        .order_by(MatchHistory.timestamp.asc())
        .all()
    )
    result = tournament.to_dict()
    result["matches"] = [m.to_dict() for m in matches]
    return result


@router.get("/tournaments/{username}")
def get_user_tournaments(username: str, limit: int = 100, db: Session = Depends(get_db)):
    rows = (
        db.query(TournamentHistory)
        .filter(TournamentHistory.players.contains(username))
        .order_by(TournamentHistory.timestamp.desc())
        .all()
    )
    out = []
    safe_limit = min(max(limit, 0), 500)
    if safe_limit == 0:
        return out
    for t in rows:
        players = _json_list(t.players)
        if username in players:
            out.append(t.to_dict())
            if len(out) >= safe_limit:
                break
    return out


@router.get("/head-to-head/{player1}/{player2}")
def get_head_to_head(player1: str, player2: str, db: Session = Depends(get_db)):
    rows = (
        db.query(MatchHistory)
        .filter(
            or_(
                MatchHistory.side_a.contains(player1),
                MatchHistory.side_b.contains(player1),
            )
        )
        .filter(
            or_(
                MatchHistory.side_a.contains(player2),
                MatchHistory.side_b.contains(player2),
            )
        )
        .order_by(MatchHistory.timestamp.desc())
        .all()
    )
    matches: list[tuple[MatchHistory, list[str], list[str]]] = []
    for m in rows:
        side_a = _json_list(m.side_a)
        side_b = _json_list(m.side_b)
        p1_side = "a" if player1 in side_a else "b" if player1 in side_b else None
        p2_side = "a" if player2 in side_a else "b" if player2 in side_b else None
        if p1_side and p2_side and p1_side != p2_side:
            matches.append((m, side_a, side_b))

    if not matches:
        return {"has_history": False}

    def _empty():
        return {
            "wins": 0, "losses": 0, "ties": 0,
            "batting_best": 0, "batting_total_runs": 0, "batting_total_balls": 0,
            "batting_innings": 0,
            "bowling_best_w": 0, "bowling_best_r": 999,
            "bowling_total_wickets": 0, "bowling_total_runs_conceded": 0,
            "bowling_innings": 0,
        }

    stats = {player1: _empty(), player2: _empty()}
    for m, side_a, side_b in matches:
        p1_side = "a" if player1 in side_a else "b"
        p2_side = "a" if player2 in side_a else "b"
        if p1_side == p2_side:
            continue

        winner = m.winner
        if winner == "TIE":
            stats[player1]["ties"] += 1
            stats[player2]["ties"] += 1
        elif _winner_includes_player(winner, player1):
            stats[player1]["wins"] += 1
            stats[player2]["losses"] += 1
        elif _winner_includes_player(winner, player2):
            stats[player2]["wins"] += 1
            stats[player1]["losses"] += 1

        for sc_col in ["scorecard_1", "scorecard_2"]:
            sc_raw = getattr(m, sc_col)
            if not sc_raw:
                continue
            try:
                sc = json.loads(sc_raw) if isinstance(sc_raw, str) else sc_raw
            except Exception:
                continue

            batting_cards = sc.get("batting", [])
            bowling_cards = sc.get("bowling", [])

            for p in [player1, player2]:
                for bc in batting_cards:
                    if bc.get("name") == p:
                        runs = bc.get("runs", 0)
                        balls = bc.get("balls", 0)
                        stats[p]["batting_total_runs"] += runs
                        stats[p]["batting_total_balls"] += balls
                        stats[p]["batting_innings"] += 1
                        if runs > stats[p]["batting_best"]:
                            stats[p]["batting_best"] = runs

                for bw in bowling_cards:
                    if bw.get("name") == p:
                        w = bw.get("wickets", 0)
                        r = bw.get("runs", 0)
                        stats[p]["bowling_total_wickets"] += w
                        stats[p]["bowling_total_runs_conceded"] += r
                        stats[p]["bowling_innings"] += 1
                        if w > stats[p]["bowling_best_w"] or (
                            w == stats[p]["bowling_best_w"] and r < stats[p]["bowling_best_r"]
                        ):
                            stats[p]["bowling_best_w"] = w
                            stats[p]["bowling_best_r"] = r

    def _format(p: str):
        s = stats[p]
        avg = round(s["batting_total_runs"] / s["batting_innings"], 2) if s["batting_innings"] > 0 else 0.0
        sr = round((s["batting_total_runs"] / s["batting_total_balls"]) * 100, 2) if s["batting_total_balls"] > 0 else 0.0
        best_bowl = f"{s['bowling_best_w']}/{s['bowling_best_r']}" if s["bowling_best_w"] > 0 else "0/0"
        return {
            "wins": s["wins"], "losses": s["losses"], "ties": s["ties"],
            "batting_best": s["batting_best"], "batting_avg": avg,
            "avg_strike_rate": sr, "bowling_best": best_bowl,
        }

    return {
        "has_history": True,
        "total_matches": len(matches),
        player1: _format(player1),
        player2: _format(player2),
    }


@router.get("/cpu-status/{username}")
def get_cpu_status(username: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.username == username).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return _cpu_status_engine.get_cpu_status(player.id)
