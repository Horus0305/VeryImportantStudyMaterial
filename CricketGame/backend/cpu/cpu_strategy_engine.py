"""
CPU Strategy Engine - Intelligent move selection using learned patterns
"""
import random
from typing import Dict, List, Optional, Tuple
from collections import Counter
from sqlalchemy.orm import Session

from ..data.database import SessionLocal
from .cpu_learning_schema import (
    CPUGlobalPattern, CPUUserProfile, CPUSituationalPattern,
    CPUSequencePattern, CPULearningProgress
)
from .cpu_learning_utils import get_game_phase, get_score_situation, get_recent_event


# Base weights when no data available (realistic human tendencies)
BASE_WEIGHTS = {
    0: 0.08,  # Defensive, risk of 0-0 out
    1: 0.16,  # Safe, common choice
    2: 0.16,  # Safe, common choice
    3: 0.15,  # Moderate
    4: 0.16,  # Safe, common choice
    5: 0.14,  # Slightly risky
    6: 0.15   # High risk, high reward
}


def get_learning_phase(total_balls: int) -> Dict:
    """
    Calculate learning phase and blending weights.
    
    Returns:
        Dict with phase, global_weight, user_weight, confidence
    """
    if total_balls < 60:
        # Phase 1 - Global
        return {
            'phase': 'global',
            'global_weight': 1.0,
            'user_weight': 0.0,
            'confidence': min(total_balls / 60.0, 0.3)
        }
    elif total_balls < 300:
        # Phase 2 - Transition
        progress = (total_balls - 60) / 240.0
        return {
            'phase': 'transition',
            'global_weight': 0.7 - (0.4 * progress),  # 0.7 → 0.3
            'user_weight': 0.3 + (0.4 * progress),     # 0.3 → 0.7
            'confidence': 0.3 + (0.5 * progress)       # 0.3 → 0.8
        }
    else:
        # Phase 3 - Personalized
        excess = total_balls - 300
        return {
            'phase': 'personalized',
            'global_weight': 0.2,
            'user_weight': 0.8,
            'confidence': min(0.8 + excess / 1000.0, 0.95)
        }


class CPUStrategyEngine:
    """Intelligent CPU opponent using learned patterns."""
    
    def __init__(self, db_session_factory=None):
        """
        Initialize the strategy engine.
        
        Args:
            db_session_factory: Factory function to create DB sessions (defaults to SessionLocal)
        """
        self.db_session_factory = db_session_factory or SessionLocal
    
    def select_move(
        self,
        user_id: int,
        match_context: Dict,
        opponent_history: List[int]
    ) -> int:
        """
        Main entry point: Select CPU's next move.
        
        Args:
            user_id: The human opponent's user ID
            match_context: Dict with match state (format, role, score, etc.)
            opponent_history: List of opponent's recent moves (last 12-20)
            
        Returns:
            Selected move (0-6)
        """
        db = self.db_session_factory()
        try:
            # Step 1: Load all pattern sources
            global_patterns = self._load_global_patterns(db, match_context)
            user_patterns = self._load_user_patterns(db, user_id, match_context)
            situational_patterns = self._load_situational_patterns(db, user_id, match_context)
            sequence_patterns = self._load_sequence_patterns(db, user_id, match_context, opponent_history)
            
            # Get learning phase info
            total_balls = self._get_total_balls_tracked(db, user_id)
            phase_info = get_learning_phase(total_balls)
            
            # Step 2: Intelligent blending
            blended = self._blend_patterns(
                global_patterns, user_patterns, situational_patterns,
                sequence_patterns, phase_info
            )
            
            # Step 3: Apply role-specific strategy
            strategic = self._apply_role_strategy(
                blended, match_context, opponent_history, phase_info['confidence']
            )
            
            # Step 4: Add strategic noise (anti-exploitation)
            noisy = self._add_strategic_noise(strategic, phase_info['confidence'])
            
            # Step 5: Weighted random selection
            return self._weighted_choice(noisy)
            
        finally:
            db.close()
    
    def _load_global_patterns(self, db: Session, context: Dict) -> Dict[int, float]:
        """Load global patterns from database."""
        game_phase = get_game_phase(context['current_over'], context['total_overs'])
        score_pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs']
        )
        
        pattern = db.query(CPUGlobalPattern).filter(
            CPUGlobalPattern.match_format == context['match_format'],
            CPUGlobalPattern.game_phase == game_phase,
            CPUGlobalPattern.role == context['role'],
            CPUGlobalPattern.score_situation == score_pressure,
            CPUGlobalPattern.wickets_lost == context['wickets_lost']
        ).first()
        
        if pattern and pattern.total_samples > 10:
            return {
                0: pattern.num_0_freq,
                1: pattern.num_1_freq,
                2: pattern.num_2_freq,
                3: pattern.num_3_freq,
                4: pattern.num_4_freq,
                5: pattern.num_5_freq,
                6: pattern.num_6_freq
            }
        
        # Fallback to base weights
        return dict(BASE_WEIGHTS)
    
    def _load_user_patterns(self, db: Session, user_id: int, context: Dict) -> Dict[int, float]:
        """Load user-specific patterns (opponent's tendencies)."""
        if user_id == -1:  # CPU vs CPU (shouldn't happen, but handle gracefully)
            return {i: 1.0/7 for i in range(7)}
        
        profile = db.query(CPUUserProfile).filter(
            CPUUserProfile.user_id == user_id,
            CPUUserProfile.match_format == context['match_format']
        ).first()
        
        if not profile:
            return {i: 1.0/7 for i in range(7)}
        
        # Get opponent's patterns (opposite role)
        # If CPU is bowling, we want user's batting patterns
        if context['role'] == 'bowling':
            if profile.total_balls_faced < 10:
                return {i: 1.0/7 for i in range(7)}
            return {
                0: profile.bat_num_0_freq,
                1: profile.bat_num_1_freq,
                2: profile.bat_num_2_freq,
                3: profile.bat_num_3_freq,
                4: profile.bat_num_4_freq,
                5: profile.bat_num_5_freq,
                6: profile.bat_num_6_freq
            }
        else:  # CPU is batting, get user's bowling patterns
            if profile.total_balls_bowled < 10:
                return {i: 1.0/7 for i in range(7)}
            return {
                0: profile.bowl_num_0_freq,
                1: profile.bowl_num_1_freq,
                2: profile.bowl_num_2_freq,
                3: profile.bowl_num_3_freq,
                4: profile.bowl_num_4_freq,
                5: profile.bowl_num_5_freq,
                6: profile.bowl_num_6_freq
            }
    
    def _load_situational_patterns(self, db: Session, user_id: int, context: Dict) -> Dict[int, float]:
        """Load context-specific patterns."""
        if user_id == -1:
            return {i: 1.0/7 for i in range(7)}
        
        game_phase = get_game_phase(context['current_over'], context['total_overs'])
        score_pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs']
        )
        recent_event = get_recent_event(context.get('last_3_results', []))
        
        # Get opponent's role (opposite of CPU)
        opponent_role = 'batting' if context['role'] == 'bowling' else 'bowling'
        
        pattern = db.query(CPUSituationalPattern).filter(
            CPUSituationalPattern.user_id == user_id,
            CPUSituationalPattern.match_format == context['match_format'],
            CPUSituationalPattern.game_phase == game_phase,
            CPUSituationalPattern.role == opponent_role,
            CPUSituationalPattern.score_pressure == score_pressure,
            CPUSituationalPattern.recent_event == recent_event
        ).first()
        
        if pattern and pattern.sample_count > 5:
            return {
                0: pattern.num_0_freq,
                1: pattern.num_1_freq,
                2: pattern.num_2_freq,
                3: pattern.num_3_freq,
                4: pattern.num_4_freq,
                5: pattern.num_5_freq,
                6: pattern.num_6_freq
            }
        
        return {i: 1.0/7 for i in range(7)}
    
    def _load_sequence_patterns(
        self, db: Session, user_id: int, context: Dict, opponent_history: List[int]
    ) -> Dict[int, float]:
        """Load sequential patterns (what opponent does after their last move)."""
        if user_id == -1 or not opponent_history:
            return {i: 1.0/7 for i in range(7)}
        
        last_move = opponent_history[-1]
        
        # Determine result of last move (simplified - we don't have full context here)
        # In real implementation, this would come from match_context
        last_result = 'scored'  # Default assumption
        
        opponent_role = 'batting' if context['role'] == 'bowling' else 'bowling'
        
        pattern = db.query(CPUSequencePattern).filter(
            CPUSequencePattern.user_id == user_id,
            CPUSequencePattern.match_format == context['match_format'],
            CPUSequencePattern.role == opponent_role,
            CPUSequencePattern.previous_move == last_move,
            CPUSequencePattern.previous_result == last_result
        ).first()
        
        if pattern and pattern.sample_count > 3:
            return {
                0: pattern.next_0_freq,
                1: pattern.next_1_freq,
                2: pattern.next_2_freq,
                3: pattern.next_3_freq,
                4: pattern.next_4_freq,
                5: pattern.next_5_freq,
                6: pattern.next_6_freq
            }
        
        return {i: 1.0/7 for i in range(7)}
    
    def _get_total_balls_tracked(self, db: Session, user_id: int) -> int:
        """Get total balls tracked for learning phase calculation."""
        if user_id == -1:
            return 0
        
        progress = db.query(CPULearningProgress).filter(
            CPULearningProgress.user_id == user_id
        ).first()
        
        return progress.total_balls_tracked if progress else 0
    
    def _blend_patterns(
        self,
        global_patterns: Dict[int, float],
        user_patterns: Dict[int, float],
        situational_patterns: Dict[int, float],
        sequence_patterns: Dict[int, float],
        phase_info: Dict
    ) -> Dict[int, float]:
        """Intelligently blend all pattern sources."""
        blended = {}
        
        for num in range(7):
            # Base blend (global + user weighted by phase)
            base = (
                global_patterns[num] * phase_info['global_weight'] +
                user_patterns[num] * phase_info['user_weight']
            )
            
            # Layer situational (30% influence scaled by confidence)
            situational_factor = 0.3 * phase_info['confidence']
            base = base * (1 - situational_factor) + situational_patterns[num] * situational_factor
            
            # Layer sequence (40% influence scaled by confidence)
            sequence_factor = 0.4 * phase_info['confidence']
            blended[num] = base * (1 - sequence_factor) + sequence_patterns[num] * sequence_factor
        
        # Normalize
        total = sum(blended.values())
        if total > 0:
            blended = {k: v / total for k, v in blended.items()}
        else:
            blended = {i: 1.0/7 for i in range(7)}
        
        return blended
    
    def _apply_role_strategy(
        self,
        weights: Dict[int, float],
        context: Dict,
        opponent_history: List[int],
        confidence: float
    ) -> Dict[int, float]:
        """Apply role-specific strategic adjustments."""
        strategic = dict(weights)
        
        if context['role'] == 'bowling':
            # CPU is BOWLING - trying to get user out
            strategic = self._bowling_strategy(strategic, opponent_history, context, confidence)
        else:
            # CPU is BATTING - trying to score without getting out
            strategic = self._batting_strategy(strategic, opponent_history, context, confidence)
        
        # Normalize
        total = sum(strategic.values())
        if total > 0:
            strategic = {k: v / total for k, v in strategic.items()}
        
        return strategic
    
    def _bowling_strategy(
        self,
        weights: Dict[int, float],
        opponent_history: List[int],
        context: Dict,
        confidence: float
    ) -> Dict[int, float]:
        """Bowling strategy: Target opponent's favorite batting numbers."""
        strategic = dict(weights)
        
        if opponent_history:
            # Analyze opponent's recent batting
            recent = opponent_history[-12:]
            freq = Counter(recent)
            
            # Get top 2 most frequent numbers
            top_2 = [num for num, count in freq.most_common(2)]
            
            # BOOST probability of matching their favorites
            boost_factor = 1.5 * confidence
            for num in top_2:
                strategic[num] *= (1 + boost_factor * 0.5)
        
        # Situational adjustments
        score_pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs']
        )
        
        if context['wickets_lost'] >= 7:
            # Opponent is desperate
            strategic[0] *= 1.3  # They'll play more 0s
            strategic[6] *= 1.2  # Expect big hits
        
        if 'desperate' in score_pressure or 'very_tight' in score_pressure:
            # Opponent needs quick runs
            strategic[4] *= 1.2
            strategic[5] *= 1.3
            strategic[6] *= 1.4
        
        return strategic
    
    def _batting_strategy(
        self,
        weights: Dict[int, float],
        opponent_history: List[int],
        context: Dict,
        confidence: float
    ) -> Dict[int, float]:
        """Batting strategy: Avoid opponent's favorite bowling numbers."""
        strategic = dict(weights)
        
        if opponent_history:
            # Analyze opponent's recent bowling
            recent = opponent_history[-12:]
            freq = Counter(recent)
            
            # Get top 2 most frequent numbers
            top_2 = [num for num, count in freq.most_common(2)]
            
            # REDUCE probability of their favorite numbers (avoid getting out)
            avoid_factor = 0.4 * confidence
            for num in top_2:
                strategic[num] *= avoid_factor
        
        # Situational adjustments based on score pressure
        score_pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs']
        )
        
        if 'desperate' in score_pressure or 'very_tight' in score_pressure:
            # Need quick runs
            strategic[5] *= 1.4
            strategic[6] *= 1.6
            strategic[0] *= 0.7
            strategic[1] *= 0.8
        elif 'comfortable' in score_pressure:
            # Play safe
            strategic[1] *= 1.3
            strategic[2] *= 1.3
            strategic[3] *= 1.2
            strategic[6] *= 0.7
            strategic[5] *= 0.8
        
        # If many wickets lost, play more conservatively
        if context['wickets_lost'] >= 7:
            strategic[0] *= 1.2
            strategic[1] *= 1.3
            strategic[6] *= 0.6
            strategic[5] *= 0.7
        
        return strategic
    
    def _add_strategic_noise(
        self,
        weights: Dict[int, float],
        confidence: float
    ) -> Dict[int, float]:
        """Add strategic noise for unpredictability and anti-exploitation."""
        noisy = {}
        noise_factor = 0.15 * confidence
        
        # Random perturbation
        for num in range(7):
            noise = random.uniform(-noise_factor, noise_factor)
            noisy[num] = max(0.01, weights[num] + noise)
        
        # Occasional bluff (5% chance at high confidence)
        if random.random() < 0.05 * confidence:
            # Pick a low-probability number and boost it
            sorted_by_prob = sorted(noisy.items(), key=lambda x: x[1])
            bluff_num = sorted_by_prob[random.randint(0, 2)][0]
            noisy[bluff_num] *= 3
        
        # Normalize
        total = sum(noisy.values())
        if total > 0:
            noisy = {k: v / total for k, v in noisy.items()}
        
        return noisy
    
    def _weighted_choice(self, weights: Dict[int, float]) -> int:
        """Select a number using weighted random selection."""
        total = sum(weights.values())
        if total <= 0:
            return random.randint(0, 6)
        
        r = random.uniform(0, total)
        cumsum = 0
        
        for num in range(7):
            cumsum += weights[num]
            if r <= cumsum:
                return num
        
        return 6  # Fallback
    
    def get_cpu_status(self, user_id: int) -> Dict:
        """
        Get CPU learning status for a specific user (for frontend display).
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict with balls_tracked, phase, confidence, message
        """
        db = self.db_session_factory()
        try:
            total_balls = self._get_total_balls_tracked(db, user_id)
            phase_info = get_learning_phase(total_balls)
            
            confidence_pct = round(phase_info['confidence'] * 100, 1)
            
            messages = {
                'global': f"CPU is learning from all players ({confidence_pct}% confident)",
                'transition': f"CPU is adapting to your style ({confidence_pct}% confident)",
                'personalized': f"CPU has mastered your patterns ({confidence_pct}% confident)"
            }
            
            return {
                'balls_tracked': total_balls,
                'phase': phase_info['phase'],
                'confidence': confidence_pct,
                'message': messages.get(phase_info['phase'], "CPU is learning...")
            }
        finally:
            db.close()
