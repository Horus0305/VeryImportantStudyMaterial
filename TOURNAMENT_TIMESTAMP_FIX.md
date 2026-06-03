# Tournament Timestamp Fix - Implementation Summary

## Problem
The following tournaments had invalid timestamps (01/01/1970 - Unix epoch):
- c6e5
- 64c5
- 8247
- 369c
- 1738
- 088b

This was caused by:
1. `restore_data.py` returning `None` when timestamp parsing failed, which SQLAlchemy stored as epoch (01/01/1970)
2. `realtime/tournament.py` not explicitly setting the timestamp when saving tournament history
3. Relying on `server_default=func.now()` which doesn't always work reliably across all database configurations

## Changes Made

### 1. **backend/realtime/tournament.py**
   - **Line 191**: Added explicit `timestamp=datetime.utcnow()` when creating `TournamentHistory` objects
   - This ensures all new tournaments always have a valid timestamp, never relying on database defaults

### 2. **restore_data.py**
   - **Lines 191-200**: Added new function `_dt_with_fallback()` that returns current UTC time as fallback instead of None
   - **Line 305**: Match history timestamps now use `_dt_with_fallback()` instead of `_dt()`
   - **Line 338**: Tournament history timestamps now use `_dt_with_fallback()` instead of `_dt()`
   - This prevents NULL timestamps from being stored, which could default to epoch

### 3. **fix_tournament_timestamps.py** (NEW)
   - Migration script to fix existing tournaments with problematic timestamps
   - Targets specific tournament IDs (c6e5, 64c5, 8247, 369c, 1738, 088b)
   - Also fixes any other tournaments with NULL or epoch (01/01/1970) timestamps

## How to Apply Fixes

### For Future Tournaments
The code changes in `backend/realtime/tournament.py` and `restore_data.py` will automatically prevent this issue for:
- Any tournaments created going forward (due to explicit timestamp in `save_tournament_history`)
- Any tournaments imported via `restore_data.py` (due to `_dt_with_fallback` function)

### For Existing Problematic Tournaments
Run the migration script to fix the specific tournament IDs:

```bash
cd ~/www/CricketGame  # or wherever your app is installed
python fix_tournament_timestamps.py
```

This script will:
1. Find and update the specific problematic tournament IDs with current datetime
2. Find and fix any other tournaments with NULL timestamps
3. Find and fix any other tournaments with epoch (01/01/1970) timestamps
4. Report the number of tournaments fixed

## Database Verification

After running the migration script, verify the fixes by checking the database:

```bash
cd ~/www/CricketGame
python3 << 'EOF'
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///cricket.db"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check the specific tournament IDs
    for tid in ['c6e5', '64c5', '8247', '369c', '1738', '088b']:
        result = conn.execute(text(
            f"SELECT tournament_id, timestamp FROM tournament_history WHERE tournament_id = '{tid}'"
        )).fetchone()
        if result:
            print(f"{tid}: {result[1]}")
        else:
            print(f"{tid}: Not found")
EOF
```

## Notes
- All timestamps in the database are in UTC (using `datetime.utcnow()`)
- The migration script uses `datetime.utcnow()` to ensure consistency
- Running the migration script multiple times is safe - it will update timestamps again if needed
- No other tournament data is modified, only the timestamp field
