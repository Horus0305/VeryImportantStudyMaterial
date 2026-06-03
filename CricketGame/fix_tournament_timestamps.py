"""
Tournament Timestamp Fix Script
================================
Fixes tournaments with 01/01/1970 timestamps or NULL timestamps.
Also updates specific problematic tournament IDs.

HOW TO RUN (on AlwaysData server console):
  1. Navigate to the CricketGame directory:
       cd ~/www/CricketGame
  2. Run:
       python fix_tournament_timestamps.py

NOTES:
  - Tournaments with epoch (01/01/1970) or NULL timestamps are updated with current datetime
  - Specific tournament IDs (c6e5, 64c5, 8247, 369c, 1738, 088b) are targeted for fixing
"""

import os
import sys
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, ForeignKey, inspect, text
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── Locate database ──────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# DB path: respect DATABASE_URL env var (same as backend config.py does)
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
        # Default: use next to this script (same as running uvicorn from here)
        DATABASE_URL = f"sqlite:///{os.path.join(SCRIPT_DIR, 'cricket.db')}"

print(f"Using database: {DATABASE_URL}")
print()

# ── Minimal ORM (mirrors backend models) ─────────────────────────────────────────

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class TournamentHistory(Base):
    __tablename__ = "tournament_history"
    id = Column(Integer, primary_key=True)
    tournament_id = Column(String(20), unique=True, nullable=False, index=True)
    room_code = Column(String(20), nullable=False)
    timestamp = Column(DateTime)
    players = Column(Text, nullable=False)
    standings = Column(Text, nullable=False)
    playoff_bracket = Column(Text, nullable=True)
    playoff_results = Column(Text, nullable=True)
    match_ids = Column(Text, nullable=False)
    champion = Column(String(50), nullable=True)
    orange_cap = Column(Text, nullable=True)
    purple_cap = Column(Text, nullable=True)
    best_strike_rate = Column(Text, nullable=True)
    best_average = Column(Text, nullable=True)
    best_economy = Column(Text, nullable=True)
    player_of_tournament = Column(Text, nullable=True)

# ── Check if tournament_history table exists ──────────────────────────────────────

inspector = inspect(engine)
if "tournament_history" not in inspector.get_table_names():
    print("ERROR: tournament_history table not found in database.")
    sys.exit(1)

db = Session()

# ── Find and fix problematic tournaments ──────────────────────────────────────────

PROBLEMATIC_IDS = {'c6e5', '64c5', '8247', '369c', '1738', '088b'}

print("--- Fixing tournament timestamps ---")
print()

# 1. Fix specific tournament IDs
print("Step 1: Fixing specific problematic tournament IDs...")
fixed_count = 0
for tid in PROBLEMATIC_IDS:
    tournament = db.query(TournamentHistory).filter(
        TournamentHistory.tournament_id == tid
    ).first()
    if tournament:
        old_ts = tournament.timestamp
        tournament.timestamp = datetime.utcnow()
        db.commit()
        print(f"  ✓ {tid}: Updated from {old_ts} to {tournament.timestamp}")
        fixed_count += 1
    else:
        print(f"  - {tid}: Not found in database")

print(f"  Fixed {fixed_count} specific tournament IDs")
print()

# 2. Fix tournaments with NULL or epoch (01/01/1970) timestamps
print("Step 2: Fixing tournaments with NULL or epoch timestamps...")

# Find NULL timestamps
null_count = 0
null_tournaments = db.query(TournamentHistory).filter(
    TournamentHistory.timestamp == None
).all()

for tournament in null_tournaments:
    tournament.timestamp = datetime.utcnow()
    db.commit()
    print(f"  ✓ {tournament.tournament_id}: Updated from NULL to {tournament.timestamp}")
    null_count += 1

print(f"  Fixed {null_count} tournaments with NULL timestamps")
print()

# Find epoch (01/01/1970) timestamps
epoch_count = 0
all_tournaments = db.query(TournamentHistory).all()

for tournament in all_tournaments:
    if tournament.timestamp and tournament.timestamp.year == 1970 and \
       tournament.timestamp.month == 1 and tournament.timestamp.day == 1:
        old_ts = tournament.timestamp
        tournament.timestamp = datetime.utcnow()
        db.commit()
        print(f"  ✓ {tournament.tournament_id}: Updated from {old_ts} to {tournament.timestamp}")
        epoch_count += 1

print(f"  Fixed {epoch_count} tournaments with epoch (01/01/1970) timestamps")
print()

# ── Summary ────────────────────────────────────────────────────────────────────────

total_fixed = fixed_count + null_count + epoch_count
print("=" * 50)
print(f"Total tournaments fixed: {total_fixed}")
print("=" * 50)

db.close()

if total_fixed > 0:
    print("✅ Timestamp fixes applied successfully!")
else:
    print("ℹ No problematic timestamps found.")
