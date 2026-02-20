"""
ORM Models — Player, per-format statistics, match history, tournament history.
"""
import json
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from .database import Base

# Import CPU learning schema to ensure tables are registered
from ..cpu import cpu_learning_schema


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    format_stats = relationship("FormatStats", back_populates="player", cascade="all, delete-orphan")


class FormatStats(Base):
    """
    Per-format statistics.  One row per (player_id, format) combination.
    Formats: '1v1', 'tournament', 'team', 'cpu'
    """
    __tablename__ = "format_stats"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    format = Column(String(20), nullable=False)  # '1v1' | 'tournament' | 'team' | 'cpu'

    # Match record
    matches_played = Column(Integer, default=0)
    matches_won = Column(Integer, default=0)

    # Batting
    total_runs = Column(Integer, default=0)
    total_balls_faced = Column(Integer, default=0)
    highest_score = Column(Integer, default=0)
    fours = Column(Integer, default=0)
    sixes = Column(Integer, default=0)
    fifties = Column(Integer, default=0)
    hundreds = Column(Integer, default=0)
    innings_batted = Column(Integer, default=0)

    # Bowling
    wickets_taken = Column(Integer, default=0)
    best_bowling_wickets = Column(Integer, default=0)
    best_bowling_runs = Column(Integer, default=999)
    runs_conceded = Column(Integer, default=0)
    overs_bowled = Column(Float, default=0.0)
    innings_bowled = Column(Integer, default=0)

    # Tournament specific
    tournaments_played = Column(Integer, default=0)
    tournaments_won = Column(Integer, default=0)

    # Awards
    potm_count = Column(Integer, default=0)
    player_of_tournament_count = Column(Integer, default=0)

    player = relationship("Player", back_populates="format_stats")

    @property
    def avg_runs(self) -> float:
        """Batting average = total runs / innings batted."""
        return round(self.total_runs / self.innings_batted, 2) if self.innings_batted > 0 else 0.0

    @property
    def avg_strike_rate(self) -> float:
        """Average SR = (total runs / total balls) * 100."""
        return round((self.total_runs / self.total_balls_faced) * 100, 2) if self.total_balls_faced > 0 else 0.0

    @property
    def bowling_average(self) -> float:
        return round(self.runs_conceded / self.wickets_taken, 2) if self.wickets_taken > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "format": self.format,
            "matches_played": self.matches_played,
            "matches_won": self.matches_won,
            "total_runs": self.total_runs,
            "total_balls_faced": self.total_balls_faced,
            "avg_runs": self.avg_runs,
            "avg_strike_rate": self.avg_strike_rate,
            "highest_score": self.highest_score,
            "fours": self.fours,
            "sixes": self.sixes,
            "fifties": self.fifties,
            "hundreds": self.hundreds,
            "wickets_taken": self.wickets_taken,
            "best_bowling": f"{self.best_bowling_wickets}/{self.best_bowling_runs}"
                            if self.best_bowling_wickets > 0 else "0/0",
            "bowling_average": self.bowling_average,
            "tournaments_played": self.tournaments_played,
            "tournaments_won": self.tournaments_won,
            "potm_count": self.potm_count,
            "player_of_tournament_count": self.player_of_tournament_count,
        }


class MatchHistory(Base):
    """Persisted match scorecard with Player of the Match."""
    __tablename__ = "match_history"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(String(20), unique=True, nullable=False, index=True)
    room_code = Column(String(20), nullable=False)
    mode = Column(String(20), nullable=False)  # '1v1' | 'team' | 'tournament' | 'cpu'
    timestamp = Column(DateTime, server_default=func.now())
    end_timestamp = Column(DateTime, server_default=func.now())

    # Participants (JSON arrays of usernames)
    side_a = Column(Text, nullable=False)   # json.dumps(list)
    side_b = Column(Text, nullable=False)

    # Full innings scorecards (JSON)
    scorecard_1 = Column(Text, nullable=False)
    scorecard_2 = Column(Text, nullable=False)

    # Result
    result_text = Column(String(200), nullable=False)
    winner = Column(String(200), nullable=True)  # Winning side label or "TIE"

    # Player of the Match
    potm = Column(String(50), nullable=True)
    potm_stats = Column(Text, nullable=True)  # JSON summary

    # Tournament link (nullable for non-tournament matches)
    tournament_id = Column(String(20), nullable=True, index=True)

    def _json(self, col: str) -> any:
        """Helper: parse a JSON text column."""
        val = getattr(self, col)
        return json.loads(val) if val else None

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "room_code": self.room_code,
            "mode": self.mode,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "end_timestamp": self.end_timestamp.isoformat() if self.end_timestamp else None,
            "side_a": self._json("side_a"),
            "side_b": self._json("side_b"),
            "scorecard_1": self._json("scorecard_1"),
            "scorecard_2": self._json("scorecard_2"),
            "result_text": self.result_text,
            "winner": self.winner,
            "potm": self.potm,
            "potm_stats": self._json("potm_stats"),
            "tournament_id": self.tournament_id,
        }


class TournamentHistory(Base):
    """Persisted tournament with awards and playoff bracket."""
    __tablename__ = "tournament_history"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(String(20), unique=True, nullable=False, index=True)
    room_code = Column(String(20), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

    # Participants
    players = Column(Text, nullable=False)  # JSON list

    # Final standings table (JSON)
    standings = Column(Text, nullable=False)

    # Playoff bracket & results (JSON)
    playoff_bracket = Column(Text, nullable=True)
    playoff_results = Column(Text, nullable=True)

    # Match IDs in this tournament (JSON list)
    match_ids = Column(Text, nullable=False)

    # Champion
    champion = Column(String(50), nullable=True)

    # Awards (each is JSON: {player, value, ...})
    orange_cap = Column(Text, nullable=True)
    purple_cap = Column(Text, nullable=True)
    best_strike_rate = Column(Text, nullable=True)
    best_average = Column(Text, nullable=True)
    best_economy = Column(Text, nullable=True)
    player_of_tournament = Column(Text, nullable=True)

    def _json(self, col: str) -> any:
        val = getattr(self, col)
        return json.loads(val) if val else None

    def to_dict(self) -> dict:
        return {
            "tournament_id": self.tournament_id,
            "room_code": self.room_code,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "players": self._json("players"),
            "standings": self._json("standings"),
            "playoff_bracket": self._json("playoff_bracket"),
            "playoff_results": self._json("playoff_results"),
            "match_ids": self._json("match_ids"),
            "champion": self.champion,
            "orange_cap": self._json("orange_cap"),
            "purple_cap": self._json("purple_cap"),
            "best_strike_rate": self._json("best_strike_rate"),
            "best_average": self._json("best_average"),
            "best_economy": self._json("best_economy"),
            "player_of_tournament": self._json("player_of_tournament"),
        }
