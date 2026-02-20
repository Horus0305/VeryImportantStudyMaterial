"""
CPU Learning Database Schema - Omniscient Learning Infrastructure
Creates tables for capturing and analyzing data from ALL matches on the platform.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index, func, UniqueConstraint, text
from ..data.database import Base


class MatchBallLog(Base):
    """Records every ball from every match with complete context."""
    __tablename__ = "match_ball_log"

    id = Column(Integer, primary_key=True, index=True)
    
    # Ball identification
    match_id = Column(String(20), nullable=False, index=True)
    ball_number = Column(Integer, nullable=False)
    
    # Players (use -1 for CPU)
    batter_user_id = Column(Integer, nullable=False, index=True)
    bowler_user_id = Column(Integer, nullable=False, index=True)
    
    # Moves and result
    bat_move = Column(Integer, nullable=False)  # 0-6
    bowl_move = Column(Integer, nullable=False)  # 0-6
    runs_scored = Column(Integer, nullable=False)
    is_out = Column(Boolean, nullable=False, default=False)
    
    # Match context
    match_format = Column(String(20), nullable=False, index=True)  # '2over', '5over', '10over'
    current_over = Column(Integer, nullable=False)
    total_overs = Column(Integer, nullable=False)
    innings = Column(Integer, nullable=False)  # 1 or 2
    
    # Score context
    batting_score = Column(Integer, nullable=False)
    batting_wickets = Column(Integer, nullable=False)
    target = Column(Integer, nullable=True)  # null if innings 1
    balls_remaining = Column(Integer, nullable=False)
    
    # Computed context
    game_phase = Column(String(20), nullable=False, index=True)  # 'powerplay', 'middle', 'death'
    score_pressure = Column(String(30), nullable=False)  # 'chasing_desperate', 'defending_tight', etc.
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_match_format_phase', 'match_format', 'game_phase'),
    )


class CPUGlobalPattern(Base):
    """Aggregate patterns from all players across dimensions."""
    __tablename__ = "cpu_global_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Keys
    match_format = Column(String(20), nullable=False)
    game_phase = Column(String(20), nullable=False)
    role = Column(String(10), nullable=False)  # 'batting' or 'bowling'
    score_situation = Column(String(30), nullable=False)
    wickets_lost = Column(Integer, nullable=False)  # 0-9
    
    # Frequency data (normalized probabilities)
    num_0_freq = Column(Float, nullable=False, default=0.0)
    num_1_freq = Column(Float, nullable=False, default=0.0)
    num_2_freq = Column(Float, nullable=False, default=0.0)
    num_3_freq = Column(Float, nullable=False, default=0.0)
    num_4_freq = Column(Float, nullable=False, default=0.0)
    num_5_freq = Column(Float, nullable=False, default=0.0)
    num_6_freq = Column(Float, nullable=False, default=0.0)
    
    total_samples = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('match_format', 'game_phase', 'role', 'score_situation', 'wickets_lost', 
                        name='uq_global_pattern'),
    )


class CPUUserProfile(Base):
    """Per-user, per-format overall statistics."""
    __tablename__ = "cpu_user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Keys
    user_id = Column(Integer, nullable=False, index=True)
    match_format = Column(String(20), nullable=False)
    
    # Match statistics
    matches_played = Column(Integer, nullable=False, default=0)
    total_balls_faced = Column(Integer, nullable=False, default=0)
    total_balls_bowled = Column(Integer, nullable=False, default=0)
    
    # Batting tendencies
    bat_num_0_freq = Column(Float, nullable=False, default=0.0)
    bat_num_1_freq = Column(Float, nullable=False, default=0.0)
    bat_num_2_freq = Column(Float, nullable=False, default=0.0)
    bat_num_3_freq = Column(Float, nullable=False, default=0.0)
    bat_num_4_freq = Column(Float, nullable=False, default=0.0)
    bat_num_5_freq = Column(Float, nullable=False, default=0.0)
    bat_num_6_freq = Column(Float, nullable=False, default=0.0)
    
    # Bowling tendencies
    bowl_num_0_freq = Column(Float, nullable=False, default=0.0)
    bowl_num_1_freq = Column(Float, nullable=False, default=0.0)
    bowl_num_2_freq = Column(Float, nullable=False, default=0.0)
    bowl_num_3_freq = Column(Float, nullable=False, default=0.0)
    bowl_num_4_freq = Column(Float, nullable=False, default=0.0)
    bowl_num_5_freq = Column(Float, nullable=False, default=0.0)
    bowl_num_6_freq = Column(Float, nullable=False, default=0.0)
    
    # Derived metrics
    batting_aggression = Column(Float, nullable=False, default=0.5)  # 0.0-1.0
    bowling_variation = Column(Float, nullable=False, default=0.5)  # 0.0-1.0
    
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'match_format', name='uq_user_profile'),
    )


class CPUSituationalPattern(Base):
    """Context-specific behavior patterns."""
    __tablename__ = "cpu_situational_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Keys
    user_id = Column(Integer, nullable=False, index=True)
    match_format = Column(String(20), nullable=False)
    game_phase = Column(String(20), nullable=False)
    role = Column(String(10), nullable=False)  # 'batting' or 'bowling'
    score_pressure = Column(String(30), nullable=False)
    recent_event = Column(String(20), nullable=False)  # 'just_out', 'hit_six', 'dot_ball', 'hot_streak', 'normal'
    
    # Frequency data
    num_0_freq = Column(Float, nullable=False, default=0.0)
    num_1_freq = Column(Float, nullable=False, default=0.0)
    num_2_freq = Column(Float, nullable=False, default=0.0)
    num_3_freq = Column(Float, nullable=False, default=0.0)
    num_4_freq = Column(Float, nullable=False, default=0.0)
    num_5_freq = Column(Float, nullable=False, default=0.0)
    num_6_freq = Column(Float, nullable=False, default=0.0)
    
    sample_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CPUSequencePattern(Base):
    """Sequential dependencies - what users do AFTER specific moves."""
    __tablename__ = "cpu_sequence_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Keys
    user_id = Column(Integer, nullable=False, index=True)
    match_format = Column(String(20), nullable=False)
    role = Column(String(10), nullable=False)  # 'batting' or 'bowling'
    previous_move = Column(Integer, nullable=False)  # 0-6
    previous_result = Column(String(10), nullable=False)  # 'scored', 'out', 'dot'
    
    # Next move frequencies
    next_0_freq = Column(Float, nullable=False, default=0.0)
    next_1_freq = Column(Float, nullable=False, default=0.0)
    next_2_freq = Column(Float, nullable=False, default=0.0)
    next_3_freq = Column(Float, nullable=False, default=0.0)
    next_4_freq = Column(Float, nullable=False, default=0.0)
    next_5_freq = Column(Float, nullable=False, default=0.0)
    next_6_freq = Column(Float, nullable=False, default=0.0)
    
    sample_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CPULearningProgress(Base):
    """Tracks learning phase per user."""
    __tablename__ = "cpu_learning_progress"
    
    user_id = Column(Integer, primary_key=True, index=True)
    
    total_balls_tracked = Column(Integer, nullable=False, default=0)
    learning_phase = Column(String(20), nullable=False, default='global')  # 'global', 'transition', 'personalized'
    confidence_score = Column(Float, nullable=False, default=0.0)  # 0.0-0.95
    
    # Future anti-cheat metrics
    exploitation_attempts = Column(Integer, nullable=False, default=0)
    last_pattern_break = Column(DateTime, nullable=True)
    
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CPULearningQueue(Base):
    """Async processing queue to ensure match flow is never blocked."""
    __tablename__ = "cpu_learning_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    
    ball_log_id = Column(Integer, ForeignKey('match_ball_log.id'), nullable=False)
    processed = Column(Boolean, nullable=False, default=False, index=True)
    
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_queue_processing', 'processed', 'id'),
    )
