import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..data.database import get_db
from ..data.models import MatchHistory, TournamentHistory, Player
from ..cpu.cpu_strategy_engine import CPUStrategyEngine

router = APIRouter(prefix="/api", tags=["stats"])

@router.get("/match/{match_id}")
def get_match_detail(match_id: str, db: Session = Depends(get_db)):
    match = db.query(MatchHistory).filter(MatchHistory.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match.to_dict()

@router.get("/matches/{username}")
def get_user_matches(username: str, mode: str = Query(None), limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(MatchHistory).filter(
        (MatchHistory.side_a.contains(username)) | (MatchHistory.side_b.contains(username))
    )
    if mode:
        if mode == "team":
            query = query.filter(or_(MatchHistory.mode == "team", MatchHistory.mode == "2v2"))
        else:
            query = query.filter(MatchHistory.mode == mode)
    matches = query.order_by(MatchHistory.timestamp.desc()).limit(limit).all()
    return [m.to_dict() for m in matches]

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
def get_user_tournaments(username: str, limit: int = 3, db: Session = Depends(get_db)):
    tournaments = (
        db.query(TournamentHistory)
        .filter(TournamentHistory.players.contains(username))
        .order_by(TournamentHistory.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [t.to_dict() for t in tournaments]

@router.get("/head-to-head/{player1}/{player2}")
def get_head_to_head(player1: str, player2: str, db: Session = Depends(get_db)):
    matches = (
        db.query(MatchHistory)
        .filter(
            (MatchHistory.side_a.contains(player1) & MatchHistory.side_b.contains(player2))
            | (MatchHistory.side_a.contains(player2) & MatchHistory.side_b.contains(player1)),
        )
        .order_by(MatchHistory.timestamp.desc())
        .all()
    )
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
    for m in matches:
        side_a = json.loads(m.side_a) if isinstance(m.side_a, str) else m.side_a
        side_b = json.loads(m.side_b) if isinstance(m.side_b, str) else m.side_b

        p1_side = "a" if player1 in side_a else "b" if player1 in side_b else None
        p2_side = "a" if player2 in side_a else "b" if player2 in side_b else None
        if not p1_side or not p2_side or p1_side == p2_side:
            continue

        winner = m.winner
        for p in [player1, player2]:
            if winner and p in winner:
                stats[p]["wins"] += 1
                other = player2 if p == player1 else player1
                stats[other]["losses"] += 1
                break
            elif winner == "TIE":
                stats[player1]["ties"] += 1
                stats[player2]["ties"] += 1
                break

        for sc_col in ["scorecard_1", "scorecard_2"]:
            sc_raw = getattr(m, sc_col)
            if not sc_raw: continue
            try: sc = json.loads(sc_raw) if isinstance(sc_raw, str) else sc_raw
            except Exception: continue

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
                        if runs > stats[p]["batting_best"]: stats[p]["batting_best"] = runs

                for bw in bowling_cards:
                    if bw.get("name") == p:
                        w = bw.get("wickets", 0)
                        r = bw.get("runs", 0)
                        stats[p]["bowling_total_wickets"] += w
                        stats[p]["bowling_total_runs_conceded"] += r
                        stats[p]["bowling_innings"] += 1
                        if w > stats[p]["bowling_best_w"] or (w == stats[p]["bowling_best_w"] and r < stats[p]["bowling_best_r"]):
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
        "has_history": True, "total_matches": len(matches),
        player1: _format(player1), player2: _format(player2),
    }

@router.get("/cpu-status/{username}")
def get_cpu_status(username: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.username == username).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    engine = CPUStrategyEngine()
    return engine.get_cpu_status(player.id)
