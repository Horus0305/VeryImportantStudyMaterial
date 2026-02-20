from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from ..data.database import get_db
from ..core.auth import register_player, login_player, get_player_stats, decode_token, create_token
from ..data.models import Player, MatchHistory, TournamentHistory, FormatStats

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRequest(BaseModel):
    username: str
    password: str

class RenameRequest(BaseModel):
    token: str
    new_username: str

@router.post("/register")
def register(req: AuthRequest, db: Session = Depends(get_db)):
    ok, msg = register_player(db, req.username, req.password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"msg": msg}

@router.post("/login")
def login(req: AuthRequest, db: Session = Depends(get_db)):
    ok, msg, token = login_player(db, req.username, req.password)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    return {"msg": msg, "token": token, "username": req.username}

@router.get("/stats/{username}")
def stats(username: str, db: Session = Depends(get_db)):
    data = get_player_stats(db, username)
    if not data:
        raise HTTPException(status_code=404, detail="Player not found")
    return data

def _merge_format_stats(keeper: FormatStats, src: FormatStats) -> None:
    keeper.matches_played        += src.matches_played
    keeper.matches_won           += src.matches_won
    keeper.total_runs            += src.total_runs
    keeper.total_balls_faced     += src.total_balls_faced
    keeper.fours                 += src.fours
    keeper.sixes                 += src.sixes
    keeper.fifties               += src.fifties
    keeper.hundreds              += src.hundreds
    keeper.innings_batted        += src.innings_batted
    keeper.wickets_taken         += src.wickets_taken
    keeper.runs_conceded         += src.runs_conceded
    keeper.overs_bowled          += src.overs_bowled
    keeper.innings_bowled        += src.innings_bowled
    keeper.potm_count            += src.potm_count
    if src.highest_score > keeper.highest_score:
        keeper.highest_score = src.highest_score
    if (src.best_bowling_wickets > keeper.best_bowling_wickets or
            (src.best_bowling_wickets == keeper.best_bowling_wickets
             and src.best_bowling_runs < keeper.best_bowling_runs)):
        keeper.best_bowling_wickets = src.best_bowling_wickets
        keeper.best_bowling_runs    = src.best_bowling_runs

@router.get("/migrate-formats")
def migrate_formats(db: Session = Depends(get_db)):
    stats_merged_2v2 = 0
    stats_deduped = 0
    legacy_rows = db.query(FormatStats).filter(FormatStats.format == "2v2").all()
    for legacy in legacy_rows:
        team_row = db.query(FormatStats).filter(FormatStats.player_id == legacy.player_id, FormatStats.format == "team").first()
        if team_row:
            _merge_format_stats(team_row, legacy)
            db.delete(legacy)
        else:
            legacy.format = "team"
        stats_merged_2v2 += 1
    db.flush()

    players = db.query(Player).all()
    for player in players:
        rows_by_fmt: dict[str, list] = {}
        for row in db.query(FormatStats).filter(FormatStats.player_id == player.id).all():
            rows_by_fmt.setdefault(row.format, []).append(row)
        for fmt, rows in rows_by_fmt.items():
            if len(rows) <= 1:
                continue
            rows.sort(key=lambda r: r.matches_played, reverse=True)
            keeper = rows[0]
            for dup in rows[1:]:
                _merge_format_stats(keeper, dup)
                db.delete(dup)
                stats_deduped += 1
    db.flush()

    history_fixed = 0
    for m in db.query(MatchHistory).filter(MatchHistory.mode == "2v2").all():
        m.mode = "team"
        history_fixed += 1

    db.commit()
    return {
        "format_stats_2v2_merged": stats_merged_2v2,
        "duplicate_rows_removed": stats_deduped,
        "match_history_fixed": history_fixed,
    }

@router.post("/rename")
def rename(req: RenameRequest, db: Session = Depends(get_db)):
    current = decode_token(req.token)
    if not current:
        raise HTTPException(status_code=401, detail="Invalid token")
    new_username = req.new_username.strip()
    if not new_username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if db.query(Player).filter(Player.username == new_username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    player = db.query(Player).filter(Player.username == current).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    player.username = new_username

    matches = db.query(MatchHistory).all()
    for m in matches:
        side_a = json.loads(m.side_a) if m.side_a else []
        side_b = json.loads(m.side_b) if m.side_b else []
        if current in side_a:
            side_a = [new_username if n == current else n for n in side_a]
            m.side_a = json.dumps(side_a)
        if current in side_b:
            side_b = [new_username if n == current else n for n in side_b]
            m.side_b = json.dumps(side_b)

        if m.winner and current in m.winner:
            m.winner = m.winner.replace(current, new_username)
        if m.result_text and current in m.result_text:
            m.result_text = m.result_text.replace(current, new_username)
        if m.potm == current:
            m.potm = new_username
        if m.potm_stats:
            try:
                potm = json.loads(m.potm_stats)
                if potm.get("player") == current:
                    potm["player"] = new_username
                    m.potm_stats = json.dumps(potm)
            except Exception:
                pass

        for sc_col in ["scorecard_1", "scorecard_2"]:
            sc_raw = getattr(m, sc_col)
            if sc_raw:
                try:
                    sc = json.loads(sc_raw)
                    for row in sc.get("batting", []):
                        if row.get("name") == current: row["name"] = new_username
                    for row in sc.get("bowling", []):
                        if row.get("name") == current: row["name"] = new_username
                    setattr(m, sc_col, json.dumps(sc))
                except Exception:
                    pass

    tournaments = db.query(TournamentHistory).all()
    for t in tournaments:
        if t.players:
            try:
                players = json.loads(t.players)
                if current in players:
                    t.players = json.dumps([new_username if n == current else n for n in players])
            except Exception:
                pass
        if t.standings:
            try:
                standings = json.loads(t.standings)
                for row in standings:
                    if row.get("player") == current:
                        row["player"] = new_username
                t.standings = json.dumps(standings)
            except Exception:
                pass
        if t.playoff_bracket:
            try:
                bracket = json.loads(t.playoff_bracket)
                for key, pair in bracket.items():
                    if pair:
                        bracket[key] = [new_username if n == current else n for n in pair]
                t.playoff_bracket = json.dumps(bracket)
            except Exception:
                pass
        if t.playoff_results:
            try:
                results = json.loads(t.playoff_results)
                for key, value in results.items():
                    if value == current:
                        results[key] = new_username
                t.playoff_results = json.dumps(results)
            except Exception:
                pass
        if t.champion == current:
            t.champion = new_username

        for field in ["orange_cap", "purple_cap", "best_strike_rate", "best_average", "best_economy", "player_of_tournament"]:
            raw = getattr(t, field)
            if not raw: continue
            try:
                data = json.loads(raw)
                if data.get("player") == current:
                    data["player"] = new_username
                    setattr(t, field, json.dumps(data))
            except Exception:
                pass

    db.commit()
    return {"token": create_token(new_username), "username": new_username}
