"""
CPU Learning Background Processor - Async queue processing for omniscient learning
"""
import asyncio
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from .cpu_learning_schema import (
    MatchBallLog, CPUGlobalPattern, CPUUserProfile, CPUSituationalPattern,
    CPUSequencePattern, CPULearningProgress, CPULearningQueue
)
from .cpu_learning_utils import (
    exponential_moving_average_update, normalize_frequencies,
    calculate_learning_phase, MAX_SAMPLES_GLOBAL, MAX_SAMPLES_USER, MAX_SAMPLES_SITUATIONAL
)


class CPULearningProcessor:
    """Background processor for CPU learning queue."""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.is_running = False
        self.processing_task: Optional[asyncio.Task] = None
    
    def start(self):
        """Start the background processing task."""
        if not self.is_running:
            self.is_running = True
            self.processing_task = asyncio.create_task(self._process_queue_loop())
    
    def stop(self):
        """Stop the background processing task."""
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
    
    async def _process_queue_loop(self):
        """Main processing loop - runs continuously."""
        while self.is_running:
            try:
                await self._process_batch()
                await asyncio.sleep(0.1)  # Brief sleep between batches
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠ Error in learning queue processor: {e}")
                await asyncio.sleep(1)  # Longer sleep on error
    
    async def _process_batch(self):
        """Process a batch of unprocessed balls."""
        db = self.db_session_factory()
        try:
            # Get unprocessed queue items (batch of 10)
            queue_items = db.query(CPULearningQueue).filter(
                CPULearningQueue.processed == False
            ).order_by(CPULearningQueue.id).limit(10).all()
            
            if not queue_items:
                return  # Nothing to process
            
            for item in queue_items:
                try:
                    item.processing_started_at = datetime.utcnow()
                    db.flush()
                    
                    # Process this ball
                    await self._update_cpu_knowledge(db, item.ball_log_id)
                    
                    # Mark as processed
                    item.processed = True
                    item.processing_completed_at = datetime.utcnow()
                    db.commit()
                    
                except Exception as e:
                    print(f"⚠ Error processing ball_log_id {item.ball_log_id}: {e}")
                    db.rollback()
                    # Mark as processed anyway to avoid infinite retry
                    item.processed = True
                    item.processing_completed_at = datetime.utcnow()
                    db.commit()
        
        finally:
            db.close()
    
    async def _update_cpu_knowledge(self, db: Session, ball_log_id: int):
        """Update all CPU knowledge tables based on a single ball."""
        # Fetch ball data
        ball = db.query(MatchBallLog).filter(MatchBallLog.id == ball_log_id).first()
        if not ball:
            return
        
        # Update global patterns (both batting and bowling perspectives)
        self._update_global_pattern(db, ball, 'batting', ball.bat_move)
        self._update_global_pattern(db, ball, 'bowling', ball.bowl_move)
        
        # Update user profiles (skip CPU user_id = -1)
        if ball.batter_user_id != -1:
            self._update_user_profile(db, ball.batter_user_id, ball.match_format, 'batting', ball.bat_move)
            self._update_user_learning_progress(db, ball.batter_user_id)
            self._update_situational_pattern(db, ball, ball.batter_user_id, 'batting', ball.bat_move)
        
        if ball.bowler_user_id != -1:
            self._update_user_profile(db, ball.bowler_user_id, ball.match_format, 'bowling', ball.bowl_move)
            self._update_user_learning_progress(db, ball.bowler_user_id)
            self._update_situational_pattern(db, ball, ball.bowler_user_id, 'bowling', ball.bowl_move)
        
        # Update sequence patterns
        self._update_sequence_patterns(db, ball)
    
    def _update_global_pattern(self, db: Session, ball: MatchBallLog, role: str, move: int):
        """Update global pattern aggregates."""
        # Find or create pattern record
        pattern = db.query(CPUGlobalPattern).filter(
            CPUGlobalPattern.match_format == ball.match_format,
            CPUGlobalPattern.game_phase == ball.game_phase,
            CPUGlobalPattern.role == role,
            CPUGlobalPattern.score_situation == ball.score_pressure,
            CPUGlobalPattern.wickets_lost == ball.batting_wickets
        ).first()
        
        if pattern:
            # Update existing pattern
            old_freqs = [
                pattern.num_0_freq, pattern.num_1_freq, pattern.num_2_freq,
                pattern.num_3_freq, pattern.num_4_freq, pattern.num_5_freq, pattern.num_6_freq
            ]
            new_freqs, new_total = exponential_moving_average_update(
                old_freqs, move, pattern.total_samples, MAX_SAMPLES_GLOBAL
            )
            
            pattern.num_0_freq = new_freqs[0]
            pattern.num_1_freq = new_freqs[1]
            pattern.num_2_freq = new_freqs[2]
            pattern.num_3_freq = new_freqs[3]
            pattern.num_4_freq = new_freqs[4]
            pattern.num_5_freq = new_freqs[5]
            pattern.num_6_freq = new_freqs[6]
            pattern.total_samples = new_total
        else:
            # Create new pattern
            freqs = [0.0] * 7
            freqs[move] = 1.0
            
            pattern = CPUGlobalPattern(
                match_format=ball.match_format,
                game_phase=ball.game_phase,
                role=role,
                score_situation=ball.score_pressure,
                wickets_lost=ball.batting_wickets,
                num_0_freq=freqs[0],
                num_1_freq=freqs[1],
                num_2_freq=freqs[2],
                num_3_freq=freqs[3],
                num_4_freq=freqs[4],
                num_5_freq=freqs[5],
                num_6_freq=freqs[6],
                total_samples=1
            )
            db.add(pattern)
        
        db.flush()
    
    def _update_user_profile(self, db: Session, user_id: int, match_format: str, role: str, move: int):
        """Update user profile statistics."""
        profile = db.query(CPUUserProfile).filter(
            CPUUserProfile.user_id == user_id,
            CPUUserProfile.match_format == match_format
        ).first()
        
        if profile:
            # Update existing profile
            if role == 'batting':
                old_freqs = [
                    profile.bat_num_0_freq, profile.bat_num_1_freq, profile.bat_num_2_freq,
                    profile.bat_num_3_freq, profile.bat_num_4_freq, profile.bat_num_5_freq, profile.bat_num_6_freq
                ]
                new_freqs, new_total = exponential_moving_average_update(
                    old_freqs, move, profile.total_balls_faced, MAX_SAMPLES_USER
                )
                
                profile.bat_num_0_freq = new_freqs[0]
                profile.bat_num_1_freq = new_freqs[1]
                profile.bat_num_2_freq = new_freqs[2]
                profile.bat_num_3_freq = new_freqs[3]
                profile.bat_num_4_freq = new_freqs[4]
                profile.bat_num_5_freq = new_freqs[5]
                profile.bat_num_6_freq = new_freqs[6]
                profile.total_balls_faced = new_total
                
                # Update aggression metric (higher numbers = more aggressive)
                profile.batting_aggression = (new_freqs[4] + new_freqs[5] + new_freqs[6]) / sum(new_freqs)
            else:
                old_freqs = [
                    profile.bowl_num_0_freq, profile.bowl_num_1_freq, profile.bowl_num_2_freq,
                    profile.bowl_num_3_freq, profile.bowl_num_4_freq, profile.bowl_num_5_freq, profile.bowl_num_6_freq
                ]
                new_freqs, new_total = exponential_moving_average_update(
                    old_freqs, move, profile.total_balls_bowled, MAX_SAMPLES_USER
                )
                
                profile.bowl_num_0_freq = new_freqs[0]
                profile.bowl_num_1_freq = new_freqs[1]
                profile.bowl_num_2_freq = new_freqs[2]
                profile.bowl_num_3_freq = new_freqs[3]
                profile.bowl_num_4_freq = new_freqs[4]
                profile.bowl_num_5_freq = new_freqs[5]
                profile.bowl_num_6_freq = new_freqs[6]
                profile.total_balls_bowled = new_total
                
                # Update variation metric (entropy-based)
                import math
                entropy = -sum(f * math.log(f + 1e-10) for f in new_freqs if f > 0)
                max_entropy = math.log(7)
                profile.bowling_variation = entropy / max_entropy
        else:
            # Create new profile
            freqs = [0.0] * 7
            freqs[move] = 1.0
            
            profile = CPUUserProfile(
                user_id=user_id,
                match_format=match_format,
                matches_played=0,
                total_balls_faced=1 if role == 'batting' else 0,
                total_balls_bowled=1 if role == 'bowling' else 0
            )
            
            if role == 'batting':
                profile.bat_num_0_freq = freqs[0]
                profile.bat_num_1_freq = freqs[1]
                profile.bat_num_2_freq = freqs[2]
                profile.bat_num_3_freq = freqs[3]
                profile.bat_num_4_freq = freqs[4]
                profile.bat_num_5_freq = freqs[5]
                profile.bat_num_6_freq = freqs[6]
                profile.batting_aggression = 1.0 if move >= 4 else 0.0
            else:
                profile.bowl_num_0_freq = freqs[0]
                profile.bowl_num_1_freq = freqs[1]
                profile.bowl_num_2_freq = freqs[2]
                profile.bowl_num_3_freq = freqs[3]
                profile.bowl_num_4_freq = freqs[4]
                profile.bowl_num_5_freq = freqs[5]
                profile.bowl_num_6_freq = freqs[6]
                profile.bowling_variation = 0.5
            
            db.add(profile)
        
        db.flush()
    
    def _update_user_learning_progress(self, db: Session, user_id: int):
        """Update learning progress tracking."""
        progress = db.query(CPULearningProgress).filter(
            CPULearningProgress.user_id == user_id
        ).first()
        
        if progress:
            progress.total_balls_tracked += 1
            phase, confidence = calculate_learning_phase(progress.total_balls_tracked)
            progress.learning_phase = phase
            progress.confidence_score = confidence
        else:
            phase, confidence = calculate_learning_phase(1)
            progress = CPULearningProgress(
                user_id=user_id,
                total_balls_tracked=1,
                learning_phase=phase,
                confidence_score=confidence
            )
            db.add(progress)
        
        db.flush()
    
    def _update_situational_pattern(self, db: Session, ball: MatchBallLog, user_id: int, role: str, move: int):
        """Update situational patterns."""
        # Get recent event from previous balls in same match
        recent_event = self._get_recent_event_for_ball(db, ball)
        
        # Find or create situational pattern
        pattern = db.query(CPUSituationalPattern).filter(
            CPUSituationalPattern.user_id == user_id,
            CPUSituationalPattern.match_format == ball.match_format,
            CPUSituationalPattern.game_phase == ball.game_phase,
            CPUSituationalPattern.role == role,
            CPUSituationalPattern.score_pressure == ball.score_pressure,
            CPUSituationalPattern.recent_event == recent_event
        ).first()
        
        if pattern:
            old_freqs = [
                pattern.num_0_freq, pattern.num_1_freq, pattern.num_2_freq,
                pattern.num_3_freq, pattern.num_4_freq, pattern.num_5_freq, pattern.num_6_freq
            ]
            new_freqs, new_count = exponential_moving_average_update(
                old_freqs, move, pattern.sample_count, MAX_SAMPLES_SITUATIONAL
            )
            
            pattern.num_0_freq = new_freqs[0]
            pattern.num_1_freq = new_freqs[1]
            pattern.num_2_freq = new_freqs[2]
            pattern.num_3_freq = new_freqs[3]
            pattern.num_4_freq = new_freqs[4]
            pattern.num_5_freq = new_freqs[5]
            pattern.num_6_freq = new_freqs[6]
            pattern.sample_count = new_count
        else:
            freqs = [0.0] * 7
            freqs[move] = 1.0
            
            pattern = CPUSituationalPattern(
                user_id=user_id,
                match_format=ball.match_format,
                game_phase=ball.game_phase,
                role=role,
                score_pressure=ball.score_pressure,
                recent_event=recent_event,
                num_0_freq=freqs[0],
                num_1_freq=freqs[1],
                num_2_freq=freqs[2],
                num_3_freq=freqs[3],
                num_4_freq=freqs[4],
                num_5_freq=freqs[5],
                num_6_freq=freqs[6],
                sample_count=1
            )
            db.add(pattern)
        
        db.flush()
    
    def _update_sequence_patterns(self, db: Session, ball: MatchBallLog):
        """Update sequence patterns based on previous ball."""
        # Get previous ball for batter
        if ball.batter_user_id != -1:
            prev_ball = db.query(MatchBallLog).filter(
                MatchBallLog.match_id == ball.match_id,
                MatchBallLog.batter_user_id == ball.batter_user_id,
                MatchBallLog.ball_number < ball.ball_number
            ).order_by(MatchBallLog.ball_number.desc()).first()
            
            if prev_ball:
                prev_result = 'out' if prev_ball.is_out else ('dot' if prev_ball.runs_scored == 0 else 'scored')
                self._update_sequence_pattern_record(
                    db, ball.batter_user_id, ball.match_format, 'batting',
                    prev_ball.bat_move, prev_result, ball.bat_move
                )
        
        # Get previous ball for bowler
        if ball.bowler_user_id != -1:
            prev_ball = db.query(MatchBallLog).filter(
                MatchBallLog.match_id == ball.match_id,
                MatchBallLog.bowler_user_id == ball.bowler_user_id,
                MatchBallLog.ball_number < ball.ball_number
            ).order_by(MatchBallLog.ball_number.desc()).first()
            
            if prev_ball:
                prev_result = 'out' if prev_ball.is_out else ('dot' if prev_ball.runs_scored == 0 else 'scored')
                self._update_sequence_pattern_record(
                    db, ball.bowler_user_id, ball.match_format, 'bowling',
                    prev_ball.bowl_move, prev_result, ball.bowl_move
                )
    
    def _update_sequence_pattern_record(
        self, db: Session, user_id: int, match_format: str, role: str,
        prev_move: int, prev_result: str, next_move: int
    ):
        """Update a single sequence pattern record."""
        pattern = db.query(CPUSequencePattern).filter(
            CPUSequencePattern.user_id == user_id,
            CPUSequencePattern.match_format == match_format,
            CPUSequencePattern.role == role,
            CPUSequencePattern.previous_move == prev_move,
            CPUSequencePattern.previous_result == prev_result
        ).first()
        
        if pattern:
            old_freqs = [
                pattern.next_0_freq, pattern.next_1_freq, pattern.next_2_freq,
                pattern.next_3_freq, pattern.next_4_freq, pattern.next_5_freq, pattern.next_6_freq
            ]
            new_freqs, new_count = exponential_moving_average_update(
                old_freqs, next_move, pattern.sample_count, MAX_SAMPLES_SITUATIONAL
            )
            
            pattern.next_0_freq = new_freqs[0]
            pattern.next_1_freq = new_freqs[1]
            pattern.next_2_freq = new_freqs[2]
            pattern.next_3_freq = new_freqs[3]
            pattern.next_4_freq = new_freqs[4]
            pattern.next_5_freq = new_freqs[5]
            pattern.next_6_freq = new_freqs[6]
            pattern.sample_count = new_count
        else:
            freqs = [0.0] * 7
            freqs[next_move] = 1.0
            
            pattern = CPUSequencePattern(
                user_id=user_id,
                match_format=match_format,
                role=role,
                previous_move=prev_move,
                previous_result=prev_result,
                next_0_freq=freqs[0],
                next_1_freq=freqs[1],
                next_2_freq=freqs[2],
                next_3_freq=freqs[3],
                next_4_freq=freqs[4],
                next_5_freq=freqs[5],
                next_6_freq=freqs[6],
                sample_count=1
            )
            db.add(pattern)
        
        db.flush()
    
    def _get_recent_event_for_ball(self, db: Session, ball: MatchBallLog) -> str:
        """Determine recent event based on previous balls."""
        # Get last 3 balls for this batter in this match
        prev_balls = db.query(MatchBallLog).filter(
            MatchBallLog.match_id == ball.match_id,
            MatchBallLog.batter_user_id == ball.batter_user_id,
            MatchBallLog.ball_number < ball.ball_number
        ).order_by(MatchBallLog.ball_number.desc()).limit(3).all()
        
        if not prev_balls:
            return 'normal'
        
        last = prev_balls[0]
        if last.is_out:
            return 'just_out'
        if last.runs_scored == 6:
            return 'hit_six'
        if last.runs_scored == 0:
            return 'dot_ball'
        
        # Check for hot streak
        if len(prev_balls) >= 3:
            if all(b.runs_scored >= 4 for b in prev_balls[:3]):
                return 'hot_streak'
        
        return 'normal'
