import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.stats import get_user_tournaments
from backend.data.database import Base
from backend.data.models import TournamentHistory
from backend.realtime.tournament import save_tournament_history


def _session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def test_get_user_tournaments_includes_cpu_involved_tournaments():
    SessionLocal = _session_factory()
    db = SessionLocal()
    try:
        db.add_all([
            TournamentHistory(
                tournament_id="T-1",
                room_code="R-1",
                players=json.dumps(["Alice", "CPU Pro", "Bob"]),
                standings=json.dumps([]),
                playoff_bracket=json.dumps({}),
                playoff_results=json.dumps({}),
                match_ids=json.dumps([]),
                champion="CPU Pro",
            ),
            TournamentHistory(
                tournament_id="T-2",
                room_code="R-2",
                players=json.dumps(["Alice", "CPU Max"]),
                standings=json.dumps([]),
                playoff_bracket=json.dumps({}),
                playoff_results=json.dumps({}),
                match_ids=json.dumps([]),
                champion="Alice",
            ),
            TournamentHistory(
                tournament_id="T-3",
                room_code="R-3",
                players=json.dumps(["Bob", "CPU Max"]),
                standings=json.dumps([]),
                playoff_bracket=json.dumps({}),
                playoff_results=json.dumps({}),
                match_ids=json.dumps([]),
                champion="CPU Max",
            ),
        ])
        db.commit()

        tournaments = get_user_tournaments("Alice", limit=100, db=db)
        ids = {t["tournament_id"] for t in tournaments}
        assert ids == {"T-1", "T-2"}
    finally:
        db.close()


def test_save_tournament_history_persists_human_and_cpu_players(monkeypatch):
    SessionLocal = _session_factory()

    class DummyRoom:
        tournament_id = "T-4"
        code = "R-4"
        tournament_match_ids = ["M-1"]

    class DummyTournament:
        players = ["Alice", "CPU Pro", "Bob"]
        champion = "CPU Pro"
        playoff_matches = {
            "qualifier_1": None,
            "eliminator": None,
            "qualifier_2": None,
            "final": ("Alice", "CPU Pro"),
        }
        playoff_results = {"final": "CPU Pro"}

        @staticmethod
        def get_sorted_standings():
            return [
                {"player": "CPU Pro", "points": 10},
                {"player": "Alice", "points": 8},
                {"player": "Bob", "points": 4},
            ]

    monkeypatch.setattr("backend.realtime.tournament.SessionLocal", SessionLocal)
    save_tournament_history(None, DummyRoom(), DummyTournament(), awards={})

    db = SessionLocal()
    try:
        saved = db.query(TournamentHistory).filter(TournamentHistory.tournament_id == "T-4").one()
        assert json.loads(saved.players) == ["Alice", "CPU Pro", "Bob"]
    finally:
        db.close()
