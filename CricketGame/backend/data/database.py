"""
Database — SQLAlchemy engine, session, and base model.
"""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from ..core.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Global learning processor instance
_learning_processor = None


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "match_history" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("match_history")}
        if "end_timestamp" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE match_history ADD COLUMN end_timestamp DATETIME"))
        if "super_over_timeline" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE match_history ADD COLUMN super_over_timeline TEXT"))


def get_learning_processor():
    """Get or create the global learning processor instance."""
    global _learning_processor
    if _learning_processor is None:
        from ..cpu.cpu_learning_processor import CPULearningProcessor
        _learning_processor = CPULearningProcessor(SessionLocal)
    return _learning_processor


def start_learning_processor():
    """Start the background learning processor."""
    processor = get_learning_processor()
    processor.start()
    print("✅ CPU Learning Processor started")


def stop_learning_processor():
    """Stop the background learning processor."""
    global _learning_processor
    if _learning_processor:
        _learning_processor.stop()
        print("🛑 CPU Learning Processor stopped")
