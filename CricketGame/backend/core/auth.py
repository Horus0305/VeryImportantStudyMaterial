"""
Auth — Password hashing and JWT token utilities.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import json
from ..data.models import Player, FormatStats, MatchHistory, TournamentHistory

FORMATS = ["1v1", "tournament", "team", "cpu"]


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


def get_player_stats(db: Session, username: str) -> dict:
    """Return all per-format stats for a player, plus an 'overall' aggregation."""
    player = db.query(Player).filter(Player.username == username).first()
    if not player:
        return {}

    result = {"username": username}

    # Calculate PoTM counts dynamically from MatchHistory
    potm_matches = db.query(MatchHistory.mode).filter(MatchHistory.potm == username).all()
    potm_counts = {"1v1": 0, "team": 0, "tournament": 0, "cpu": 0}
    for m in potm_matches:
        key = "team" if m.mode in ("team", "2v2") else m.mode
        if key in potm_counts:
            potm_counts[key] += 1

    # Calculate ALL tournament awards dynamically from TournamentHistory
    tournament_records = db.query(TournamentHistory).filter(
        or_(
            TournamentHistory.champion == username,
            TournamentHistory.orange_cap.contains(username),
            TournamentHistory.purple_cap.contains(username),
            TournamentHistory.best_strike_rate.contains(username),
            TournamentHistory.best_average.contains(username),
            TournamentHistory.best_economy.contains(username),
            TournamentHistory.player_of_tournament.contains(username),
        )
    ).all()
    pot_count = 0
    titles_won = 0
    tournament_award_count = 0
    award_json_fields = [
        'orange_cap', 'purple_cap', 'best_strike_rate',
        'best_average', 'best_economy', 'player_of_tournament',
    ]

    for t in tournament_records:
        if t.champion == username:
            titles_won += 1
            tournament_award_count += 1
        for field in award_json_fields:
            val = getattr(t, field, None)
            if val:
                try:
                    data = json.loads(val)
                    if data.get("player") == username:
                        tournament_award_count += 1
                        if field == "player_of_tournament":
                            pot_count += 1
                except Exception:
                    pass

    total_titles = tournament_award_count + sum(potm_counts.values())

    overall = {
        "format": "overall",
        "matches_played": 0, "matches_won": 0,
        "total_runs": 0, "total_balls_faced": 0,
        "highest_score": 0, "fours": 0, "sixes": 0,
        "fifties": 0, "hundreds": 0, "innings_batted": 0,
        "wickets_taken": 0, "best_bowling_wickets": 0, "best_bowling_runs": 999,
        "runs_conceded": 0, "overs_bowled": 0.0, "innings_bowled": 0,
        "tournaments_played": 0,
        "tournaments_won": titles_won,
        "potm_count": 0, "player_of_tournament_count": pot_count,
        "total_titles": total_titles,
    }

    # ── Group all rows by their canonical format name ──────────────────────────
    # A player can have duplicate 'team' rows (legacy bug). We merge them here
    # so the profile always shows correct totals regardless of DB state.
    rows_by_fmt: dict[str, list] = {}
    for fs in player.format_stats:
        canonical = "team" if fs.format == "2v2" else fs.format
        rows_by_fmt.setdefault(canonical, []).append(fs)

    for canonical_fmt, rows in rows_by_fmt.items():
        # Merge all duplicate rows into a single virtual dict
        merged = _aggregate_rows(rows)
        format_key = canonical_fmt

        # Override counts with dynamic values
        if format_key in potm_counts:
            merged["potm_count"] = potm_counts[format_key]
        if format_key == "tournament":
            merged["player_of_tournament_count"] = pot_count
            merged["tournaments_won"] = titles_won

        merged["format"] = format_key
        result[format_key] = merged

        # Aggregate overall
        overall["matches_played"]    += merged["matches_played"]
        overall["matches_won"]       += merged["matches_won"]
        overall["total_runs"]        += merged["total_runs"]
        overall["total_balls_faced"] += merged["total_balls_faced"]
        overall["fours"]             += merged["fours"]
        overall["sixes"]             += merged["sixes"]
        overall["fifties"]           += merged["fifties"]
        overall["hundreds"]          += merged["hundreds"]
        overall["innings_batted"]    += merged["innings_batted"]
        overall["wickets_taken"]     += merged["wickets_taken"]
        overall["runs_conceded"]     += merged["runs_conceded"]
        overall["overs_bowled"]      += merged["overs_bowled"]
        overall["innings_bowled"]    += merged["innings_bowled"]
        overall["tournaments_played"] += merged.get("tournaments_played", 0)

        if merged["highest_score"] > overall["highest_score"]:
            overall["highest_score"] = merged["highest_score"]

        bbw = merged.get("best_bowling_wickets", 0)
        bbr = merged.get("best_bowling_runs", 999)
        if bbw > overall["best_bowling_wickets"] or \
           (bbw == overall["best_bowling_wickets"] and bbr < overall["best_bowling_runs"]):
            overall["best_bowling_wickets"] = bbw
            overall["best_bowling_runs"] = bbr

    overall["potm_count"] = sum(potm_counts.values())

    # Computed averages for overall
    overall["avg_runs"] = round(overall["total_runs"] / overall["innings_batted"], 2) \
        if overall["innings_batted"] > 0 else 0.0
    overall["avg_strike_rate"] = round((overall["total_runs"] / overall["total_balls_faced"]) * 100, 2) \
        if overall["total_balls_faced"] > 0 else 0.0
    overall["bowling_average"] = round(overall["runs_conceded"] / overall["wickets_taken"], 2) \
        if overall["wickets_taken"] > 0 else 0.0
    overall["best_bowling"] = f"{overall['best_bowling_wickets']}/{overall['best_bowling_runs']}" \
        if overall["best_bowling_wickets"] > 0 else "0/0"

    result["overall"] = overall
    return result


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
