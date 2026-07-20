"""
Auth — Password hashing and JWT token utilities.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import or_, text

from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import json
from ..data.models import Player, FormatStats, MatchHistory, TournamentHistory

FORMATS = ["1v1", "tournament", "team", "cpu"]
SEASON_1_CUTOFF = datetime(2026, 7, 20, 0, 0, 0)


def hash_password(password: str) -> str:
    """Hash password using bcrypt directly (passlib has bcrypt 5.x compat issues)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    """Returns username or None if invalid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def register_player(db: Session, username: str, password: str) -> tuple[bool, str]:
    if db.query(Player).filter(Player.username == username).first():
        return False, "Username already exists."
    player = Player(username=username, password_hash=hash_password(password))
    db.add(player)
    db.flush()
    # Create format stats rows
    for fmt in FORMATS:
        db.add(FormatStats(player_id=player.id, format=fmt))
    db.commit()
    return True, "Registration successful."


def login_player(db: Session, username: str, password: str) -> tuple[bool, str, Optional[str]]:
    """Returns (ok, message, token_or_none)."""
    player = db.query(Player).filter(Player.username == username).first()
    if not player:
        return False, "User not found.", None
    if not verify_password(password, player.password_hash):
        return False, "Incorrect password.", None
    token = create_token(username)
    return True, "Login successful.", token


def get_player_stats(db: Session, username: str, season: str = "2") -> dict:
    """Return all per-format stats for a player for the specified season."""
    player = db.query(Player).filter(Player.username == username).first()
    if not player:
        return {}

    MAIN_HUMANS = {"AniketKS", "Atharva", "Sahil", "Yash", "Meet", "Atharva Kolekar", "hetvig04"}

    # Find valid tournament IDs for this season
    all_tournaments = db.query(TournamentHistory).all()
    valid_tids = set()
    t_played_count = 0
    t_won_count = 0

    for t in all_tournaments:
        if season == "1" and t.timestamp and t.timestamp >= SEASON_1_CUTOFF:
            continue
        if season == "2" and t.timestamp and t.timestamp < SEASON_1_CUTOFF:
            continue

        players = []
        if t.players:
            try:
                players = json.loads(t.players) if isinstance(t.players, str) else t.players
            except Exception:
                players = []

        intersect = set(players) & MAIN_HUMANS
        if len(intersect) >= 2:
            valid_tids.add(t.tournament_id)
            if username in players:
                t_played_count += 1
            if t.champion == username:
                t_won_count += 1

    fmt_keys = ["1v1", "tournament", "team", "cpu", "overall"]
    fmt_stats = {
        fmt: {
            "format": fmt, "matches_played": 0, "matches_won": 0,
            "total_runs": 0, "total_balls_faced": 0, "highest_score": 0,
            "fours": 0, "sixes": 0, "fifties": 0, "hundreds": 0,
            "innings_batted": 0, "wickets_taken": 0, "best_bowling_wickets": 0,
            "best_bowling_runs": 999, "runs_conceded": 0, "overs_bowled": 0.0,
            "innings_bowled": 0, "tournaments_played": 0, "tournaments_won": 0,
            "potm_count": 0, "player_of_tournament_count": 0, "total_titles": 0,
            "avg_runs": 0.0, "avg_strike_rate": 0.0, "bowling_average": 0.0, "win_rate": 0.0,
            "best_bowling": "0/0"
        }
        for fmt in fmt_keys
    }

    fmt_stats["tournament"]["tournaments_played"] = t_played_count
    fmt_stats["tournament"]["tournaments_won"] = t_won_count
    fmt_stats["overall"]["tournaments_played"] = t_played_count
    fmt_stats["overall"]["tournaments_won"] = t_won_count

    # Fetch matches for this season
    m_query = db.query(MatchHistory).filter(
        or_(
            text("exists (select 1 from json_each(side_a) where value = :username)"),
            text("exists (select 1 from json_each(side_b) where value = :username)")
        )
    )
    if season == "1":
        m_query = m_query.filter(MatchHistory.timestamp < SEASON_1_CUTOFF)
    elif season == "2":
        m_query = m_query.filter(MatchHistory.timestamp >= SEASON_1_CUTOFF)

    matches = m_query.params(username=username).all()

    for m in matches:
        if m.mode == "tournament" and m.tournament_id not in valid_tids:
            continue

        canonical_fmt = "team" if m.mode in ("team", "2v2") else m.mode
        if canonical_fmt not in fmt_stats:
            continue

        targets = [fmt_stats[canonical_fmt], fmt_stats["overall"]]

        is_winner = False
        if m.winner and m.winner != "TIE":
            winners = [x.strip() for x in m.winner.split(",") if x.strip()]
            if username in winners:
                is_winner = True

        for st in targets:
            st["matches_played"] += 1
            if is_winner:
                st["matches_won"] += 1

            if m.potm == username and st["format"] != "overall":
                st["potm_count"] += 1

            # Parse scorecards
            for sc_raw in [m.scorecard_1, m.scorecard_2]:
                if not sc_raw:
                    continue
                try:
                    sc = json.loads(sc_raw) if isinstance(sc_raw, str) else sc_raw
                except Exception:
                    continue

                for bat in sc.get("batting", []):
                    if bat.get("name") == username:
                        r = bat.get("runs", 0)
                        b = bat.get("balls", 0)
                        f = bat.get("fours", 0)
                        sx = bat.get("sixes", 0)
                        st["total_runs"] += r
                        st["total_balls_faced"] += b
                        st["fours"] += f
                        st["sixes"] += sx
                        st["innings_batted"] += 1
                        if r > st["highest_score"]:
                            st["highest_score"] = r
                        if r >= 100:
                            st["hundreds"] += 1
                        elif r >= 50:
                            st["fifties"] += 1

                for bowl in sc.get("bowling", []):
                    if bowl.get("name") == username:
                        w = bowl.get("wickets", 0)
                        rc = bowl.get("runs", 0)
                        ov = float(bowl.get("overs", 0))
                        st["wickets_taken"] += w
                        st["runs_conceded"] += rc
                        st["overs_bowled"] += ov
                        st["innings_bowled"] += 1
                        bbw = st["best_bowling_wickets"]
                        bbr = st["best_bowling_runs"]
                        if w > bbw or (w == bbw and rc < bbr):
                            st["best_bowling_wickets"] = w
                            st["best_bowling_runs"] = rc

    for st in fmt_stats.values():
        if st["matches_played"] > 0:
            st["win_rate"] = round(st["matches_won"] / st["matches_played"] * 100, 1)
        if st["innings_batted"] > 0:
            st["avg_runs"] = round(st["total_runs"] / st["innings_batted"], 2)
        if st["total_balls_faced"] > 0:
            st["avg_strike_rate"] = round(st["total_runs"] / st["total_balls_faced"] * 100, 2)
        if st["wickets_taken"] > 0:
            st["bowling_average"] = round(st["runs_conceded"] / st["wickets_taken"], 2)
        if st["best_bowling_wickets"] > 0:
            st["best_bowling"] = f"{st['best_bowling_wickets']}/{st['best_bowling_runs']}"
        else:
            st["best_bowling"] = "0/0"
        if st["best_bowling_runs"] == 999:
            st["best_bowling_runs"] = 0

    fmt_stats["overall"]["potm_count"] = sum(fmt_stats[k]["potm_count"] for k in ["1v1", "tournament", "team", "cpu"])
    fmt_stats["username"] = username
    return fmt_stats


def _aggregate_rows(rows: list) -> dict:
    """Merge a list of FormatStats ORM objects into a single stats dict."""
    agg = {
        "matches_played": 0, "matches_won": 0,
        "total_runs": 0, "total_balls_faced": 0,
        "highest_score": 0, "fours": 0, "sixes": 0,
        "fifties": 0, "hundreds": 0, "innings_batted": 0,
        "wickets_taken": 0, "best_bowling_wickets": 0, "best_bowling_runs": 999,
        "runs_conceded": 0, "overs_bowled": 0.0, "innings_bowled": 0,
        "tournaments_played": 0, "tournaments_won": 0,
        "potm_count": 0, "player_of_tournament_count": 0,
    }
    for fs in rows:
        agg["matches_played"]    += fs.matches_played
        agg["matches_won"]       += fs.matches_won
        agg["total_runs"]        += fs.total_runs
        agg["total_balls_faced"] += fs.total_balls_faced
        agg["fours"]             += fs.fours
        agg["sixes"]             += fs.sixes
        agg["fifties"]           += fs.fifties
        agg["hundreds"]          += fs.hundreds
        agg["innings_batted"]    += fs.innings_batted
        agg["wickets_taken"]     += fs.wickets_taken
        agg["runs_conceded"]     += fs.runs_conceded
        agg["overs_bowled"]      += fs.overs_bowled
        agg["innings_bowled"]    += fs.innings_bowled
        agg["potm_count"]        += fs.potm_count
        agg["tournaments_played"] += fs.tournaments_played
        if fs.highest_score > agg["highest_score"]:
            agg["highest_score"] = fs.highest_score
        if (fs.best_bowling_wickets > agg["best_bowling_wickets"] or
                (fs.best_bowling_wickets == agg["best_bowling_wickets"]
                 and fs.best_bowling_runs < agg["best_bowling_runs"])):
            agg["best_bowling_wickets"] = fs.best_bowling_wickets
            agg["best_bowling_runs"]    = fs.best_bowling_runs

    # Computed stats
    agg["avg_runs"] = round(agg["total_runs"] / agg["innings_batted"], 2) \
        if agg["innings_batted"] > 0 else 0.0
    agg["avg_strike_rate"] = round((agg["total_runs"] / agg["total_balls_faced"]) * 100, 2) \
        if agg["total_balls_faced"] > 0 else 0.0
    agg["bowling_average"] = round(agg["runs_conceded"] / agg["wickets_taken"], 2) \
        if agg["wickets_taken"] > 0 else 0.0
    agg["best_bowling"] = f"{agg['best_bowling_wickets']}/{agg['best_bowling_runs']}" \
        if agg["best_bowling_wickets"] > 0 else "0/0"
    return agg


def update_player_stats(db: Session, username: str, game_format: str,
                        batting_data: Optional[dict] = None,
                        bowling_data: Optional[dict] = None,
                        won: bool = False) -> None:
    """Update a player's stats after a match. 
       Note: PoTM and PoT are now calculated dynamically from history tables,
       so we don't need to increment counters here.
    """
    player = db.query(Player).filter(Player.username == username).first()
    if not player:
        return

    fs = db.query(FormatStats).filter(
        FormatStats.player_id == player.id,
        FormatStats.format == game_format
    ).first()
    # Legacy: some users only have a "2v2" row — find and migrate it on first write
    if not fs and game_format == "team":
        fs = db.query(FormatStats).filter(
            FormatStats.player_id == player.id,
            FormatStats.format == "2v2"
        ).first()
        if fs:
            fs.format = "team"  # Rename in-place for consistency
    if not fs:
        fs = FormatStats(player_id=player.id, format=game_format)
        db.add(fs)
        db.flush()

    fs.matches_played += 1
    if won:
        fs.matches_won += 1
    
    # Remove manual increment of potm/pot columns as they are now dynamic

    if batting_data:
        runs = batting_data.get("runs", 0)
        balls = batting_data.get("balls", 0)
        fs.total_runs += runs
        fs.total_balls_faced += balls
        fs.fours += batting_data.get("fours", 0)
        fs.sixes += batting_data.get("sixes", 0)
        fs.innings_batted += 1
        if runs > fs.highest_score:
            fs.highest_score = runs
        if runs >= 100:
            fs.hundreds += 1
        elif runs >= 50:
            fs.fifties += 1

    if bowling_data:
        wkts = bowling_data.get("wickets", 0)
        runs_c = bowling_data.get("runs_conceded", 0)
        fs.wickets_taken += wkts
        fs.runs_conceded += runs_c
        fs.overs_bowled += bowling_data.get("overs", 0)
        fs.innings_bowled += 1
        # Best bowling: more wickets better, then fewer runs better
        if wkts > fs.best_bowling_wickets or (wkts == fs.best_bowling_wickets and runs_c < fs.best_bowling_runs):
            fs.best_bowling_wickets = wkts
            fs.best_bowling_runs = runs_c

    db.commit()
