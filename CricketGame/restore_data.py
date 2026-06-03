"""
Data Restore Script
===================
Imports players, match history, and tournament history from cricket_data_export.json
into the backend SQLite database.

HOW TO RUN (on AlwaysData server console):
  1. Pull the latest code
  2. Navigate to the CricketGame directory:
       cd ~/www/CricketGame        (or wherever your app lives)
  3. Run:
       python restore_data.py

NOTES:
  - All restored player accounts get the default password: Cricket2026!
    Players should change their password after logging in.
  - CPU / CPU Bot accounts are skipped (not real users).
  - Already-existing records are skipped (script is safe to re-run).
  - MatchBallLog (CPU learning data) is NOT restored — it will rebuild
    automatically as new matches are played.
"""

import json
import os
import sys
import bcrypt
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, Text, inspect, text
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase, relationship


# ── Locate files ──────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH   = os.path.join(SCRIPT_DIR, "cricket_data_export.json")

# DB path: respect DATABASE_URL env var (same as backend config.py does)
# If not set, look for cricket.db next to the backend directory
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Try common locations
    candidates = [
        os.path.join(SCRIPT_DIR, "backend", "cricket.db"),
        os.path.join(SCRIPT_DIR, "cricket.db"),
        os.path.join(os.path.dirname(SCRIPT_DIR), "cricket.db"),
    ]
    db_file = next((p for p in candidates if os.path.exists(p)), None)
    if db_file:
        DATABASE_URL = f"sqlite:///{db_file}"
    else:
        # Default: create next to this script (same as running uvicorn from here)
        DATABASE_URL = f"sqlite:///{os.path.join(SCRIPT_DIR, 'cricket.db')}"

print(f"Using database : {DATABASE_URL}")
print(f"Using JSON file: {JSON_PATH}")
print()

if not os.path.exists(JSON_PATH):
    print("ERROR: cricket_data_export.json not found.")
    sys.exit(1)


# ── Minimal ORM (mirrors backend models exactly) ──────────────────────────────

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"
    id            = Column(Integer, primary_key=True)
    username      = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    created_at    = Column(DateTime)
    format_stats  = relationship("FormatStats", back_populates="player",
                                 cascade="all, delete-orphan")


class FormatStats(Base):
    __tablename__ = "format_stats"
    id                       = Column(Integer, primary_key=True)
    player_id                = Column(Integer, ForeignKey("players.id"), nullable=False)
    format                   = Column(String(20), nullable=False)
    matches_played           = Column(Integer, default=0)
    matches_won              = Column(Integer, default=0)
    total_runs               = Column(Integer, default=0)
    total_balls_faced        = Column(Integer, default=0)
    highest_score            = Column(Integer, default=0)
    fours                    = Column(Integer, default=0)
    sixes                    = Column(Integer, default=0)
    fifties                  = Column(Integer, default=0)
    hundreds                 = Column(Integer, default=0)
    innings_batted           = Column(Integer, default=0)
    wickets_taken            = Column(Integer, default=0)
    best_bowling_wickets     = Column(Integer, default=0)
    best_bowling_runs        = Column(Integer, default=999)
    runs_conceded            = Column(Integer, default=0)
    overs_bowled             = Column(Float, default=0.0)
    innings_bowled           = Column(Integer, default=0)
    tournaments_played       = Column(Integer, default=0)
    tournaments_won          = Column(Integer, default=0)
    potm_count               = Column(Integer, default=0)
    player_of_tournament_count = Column(Integer, default=0)
    player                   = relationship("Player", back_populates="format_stats")


class MatchHistory(Base):
    __tablename__       = "match_history"
    id                  = Column(Integer, primary_key=True)
    match_id            = Column(String(20), unique=True, nullable=False, index=True)
    room_code           = Column(String(20), nullable=False)
    mode                = Column(String(20), nullable=False)
    timestamp           = Column(DateTime)
    end_timestamp       = Column(DateTime)
    side_a              = Column(Text, nullable=False)
    side_b              = Column(Text, nullable=False)
    scorecard_1         = Column(Text, nullable=False)
    scorecard_2         = Column(Text, nullable=False)
    result_text         = Column(String(200), nullable=False)
    winner              = Column(String(200), nullable=True)
    potm                = Column(String(50), nullable=True)
    potm_stats          = Column(Text, nullable=True)
    super_over_timeline = Column(Text, nullable=True)
    tournament_id       = Column(String(20), nullable=True, index=True)


class TournamentHistory(Base):
    __tablename__        = "tournament_history"
    id                   = Column(Integer, primary_key=True)
    tournament_id        = Column(String(20), unique=True, nullable=False, index=True)
    room_code            = Column(String(20), nullable=False)
    timestamp            = Column(DateTime)
    players              = Column(Text, nullable=False)
    standings            = Column(Text, nullable=False)
    playoff_bracket      = Column(Text, nullable=True)
    playoff_results      = Column(Text, nullable=True)
    match_ids            = Column(Text, nullable=False)
    champion             = Column(String(50), nullable=True)
    orange_cap           = Column(Text, nullable=True)
    purple_cap           = Column(Text, nullable=True)
    best_strike_rate     = Column(Text, nullable=True)
    best_average         = Column(Text, nullable=True)
    best_economy         = Column(Text, nullable=True)
    player_of_tournament = Column(Text, nullable=True)


# ── Create tables if they don't exist yet ────────────────────────────────────

Base.metadata.create_all(bind=engine)

# Add columns that older DBs might be missing (same logic as backend init_db)
inspector = inspect(engine)
if "match_history" in inspector.get_table_names():
    cols = {c["name"] for c in inspector.get_columns("match_history")}
    with engine.begin() as conn:
        if "end_timestamp" not in cols:
            conn.execute(text("ALTER TABLE match_history ADD COLUMN end_timestamp DATETIME"))
        if "super_over_timeline" not in cols:
            conn.execute(text("ALTER TABLE match_history ADD COLUMN super_over_timeline TEXT"))


# ── Helpers ───────────────────────────────────────────────────────────────────

DEFAULT_PASSWORD = "Cricket2026!"
CPU_NAMES = {"CPU", "CPU Bot", "CPU Bot 2", "CPU Bot 3", "CPU Bot 4", "CPU Bot 5"}

FORMATS_ALL = ["1v1", "tournament", "team", "cpu"]


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _dt(s):
    """Parse ISO timestamp string → datetime, or None."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00").split("+")[0])
    except Exception:
        return None


def _dt_with_fallback(s):
    """Parse ISO timestamp string → datetime, or current UTC time as fallback.
    This prevents timestamps from defaulting to epoch (01/01/1970)."""
    if not s:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00").split("+")[0])
    except Exception:
        return datetime.utcnow()


def _j(obj):
    return json.dumps(obj) if obj is not None else None


# ── Load data ─────────────────────────────────────────────────────────────────

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

players_data     = data.get("players", {})
matches_data     = data.get("matches", {})
tournaments_data = data.get("tournaments", {})

print(f"Loaded: {len(players_data)} players  "
      f"{len(matches_data)} matches  "
      f"{len(tournaments_data)} tournaments")
print()

db = Session()

# ── 1. Players & FormatStats ──────────────────────────────────────────────────

print("--- Importing players ---")
default_hash = hash_pw(DEFAULT_PASSWORD)

players_created = 0
players_skipped = 0

for username, pdata in players_data.items():
    if username in CPU_NAMES:
        continue

    existing = db.query(Player).filter(Player.username == username).first()
    if existing:
        players_skipped += 1
        continue

    player = Player(
        username=username,
        password_hash=default_hash,
        created_at=datetime.utcnow(),
    )
    db.add(player)
    db.flush()  # get player.id

    stats = pdata.get("stats", {})

    # Create all four format rows; fill known formats from export
    for fmt in FORMATS_ALL:
        fs = FormatStats(player_id=player.id, format=fmt)
        s  = stats.get(fmt, {})
        if s:
            fs.matches_played       = s.get("matches_played", 0)
            fs.matches_won          = s.get("matches_won", 0)
            fs.total_runs           = s.get("total_runs", 0)
            fs.total_balls_faced    = s.get("total_balls_faced", 0)
            fs.highest_score        = s.get("highest_score", 0)
            fs.fours                = s.get("fours", 0)
            fs.sixes                = s.get("sixes", 0)
            fs.fifties              = s.get("fifties", 0)
            fs.hundreds             = s.get("hundreds", 0)
            fs.innings_batted       = s.get("innings_batted", 0)
            fs.wickets_taken        = s.get("wickets_taken", 0)
            fs.runs_conceded        = s.get("runs_conceded", 0)
            fs.overs_bowled         = s.get("overs_bowled", 0.0)
            fs.innings_bowled       = s.get("innings_bowled", 0)
            fs.tournaments_played   = s.get("tournaments_played", 0)
            fs.tournaments_won      = s.get("tournaments_won", 0)
            fs.potm_count           = s.get("potm_count", 0)
            fs.player_of_tournament_count = s.get("player_of_tournament_count", 0)
            # best bowling
            bb = s.get("best_bowling", "0/0")
            try:
                bbw, bbr = bb.split("/")
                fs.best_bowling_wickets = int(bbw)
                fs.best_bowling_runs    = int(bbr)
            except Exception:
                pass
        db.add(fs)

    db.commit()
    players_created += 1
    print(f"  + {username}")

print(f"Players: {players_created} created, {players_skipped} already existed")
print()

# ── 2. Match History ──────────────────────────────────────────────────────────

print("--- Importing matches ---")
matches_created = 0
matches_skipped = 0

for mid, m in matches_data.items():
    if db.query(MatchHistory).filter(MatchHistory.match_id == mid).first():
        matches_skipped += 1
        continue

    row = MatchHistory(
        match_id            = mid,
        room_code           = m.get("room_code", ""),
        mode                = m.get("mode", "1v1"),
        timestamp           = _dt_with_fallback(m.get("timestamp")),
        end_timestamp       = _dt_with_fallback(m.get("end_timestamp")),
        side_a              = _j(m.get("side_a", [])),
        side_b              = _j(m.get("side_b", [])),
        scorecard_1         = _j(m.get("scorecard_1", {})),
        scorecard_2         = _j(m.get("scorecard_2", {})),
        result_text         = m.get("result_text", ""),
        winner              = m.get("winner"),
        potm                = m.get("potm"),
        potm_stats          = _j(m.get("potm_stats")),
        super_over_timeline = _j(m.get("super_over_timeline")),
        tournament_id       = m.get("tournament_id"),
    )
    db.add(row)
    matches_created += 1

db.commit()
print(f"Matches: {matches_created} created, {matches_skipped} already existed")
print()

# ── 3. Tournament History ─────────────────────────────────────────────────────

print("--- Importing tournaments ---")
tours_created = 0
tours_skipped = 0

for tid, t in tournaments_data.items():
    if db.query(TournamentHistory).filter(TournamentHistory.tournament_id == tid).first():
        tours_skipped += 1
        continue

    row = TournamentHistory(
        tournament_id        = tid,
        room_code            = t.get("room_code", ""),
        timestamp            = _dt_with_fallback(t.get("timestamp")),
        players              = _j(t.get("players", [])),
        standings            = _j(t.get("standings", [])),
        playoff_bracket      = _j(t.get("playoff_bracket")),
        playoff_results      = _j(t.get("playoff_results")),
        match_ids            = _j(t.get("match_ids", [])),
        champion             = t.get("champion"),
        orange_cap           = _j(t.get("orange_cap")),
        purple_cap           = _j(t.get("purple_cap")),
        best_strike_rate     = _j(t.get("best_strike_rate")),
        best_average         = _j(t.get("best_average")),
        best_economy         = _j(t.get("best_economy")),
        player_of_tournament = _j(t.get("player_of_tournament")),
    )
    db.add(row)
    tours_created += 1

db.commit()
print(f"Tournaments: {tours_created} created, {tours_skipped} already existed")
print()

db.close()

print("=" * 50)
print("Restore complete!")
print()
print(f"Default password for all accounts: {DEFAULT_PASSWORD}")
print("Tell players to change their password after logging in.")
print("=" * 50)
