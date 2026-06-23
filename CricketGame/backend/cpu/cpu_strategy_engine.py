"""
CPU Strategy Engine v2 — Frequency-Based Adaptive

Data-driven rewrite based on analysis of 6,700+ balls across 700+ matches.

Design principles:
  1. Three-signal blend: local frequency (this match), global frequency
     (player lifetime profile from DB), and transition prediction (after X,
     what do they play next? from DB).
  2. Weight schedule shifts with match length: early balls lean on global
     profile, later balls lean on local frequency + transitions.
  3. Bowling: use the blended prediction directly (pick numbers the opponent
     is likely to play -> match -> wicket).
  4. Batting: invert the blended prediction (avoid numbers the opponent is
     likely to play -> dodge -> score).
  5. Situational pressure is a lightweight modifier, not a cascading guard.
  6. Hard floor (4%) and peak cap (45%) on all final distributions.

Key insight from data:
  - After playing 6, players play 6 again 46% of the time (3.2x random).
  - MaD Rashi Chakka plays 6 sixty percent of all batting balls.
  - The old 5-voter ensemble with 6 cascading guards added ~2% over random.
  - Simple frequency counting + transitions massively outperform guards.
"""
import random
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session

from ..data.database import SessionLocal
from .cpu_learning_schema import (
    CPUGlobalPattern, CPUUserProfile, CPUSituationalPattern,
    CPUSequencePattern, CPULearningProgress, MatchBallLog,
)
from .cpu_learning_utils import get_game_phase, get_score_situation, get_recent_event


# ── Tuning constants ─────────────────────────────────────────────────────────
FLOOR_PROB      = 0.04              # Hard minimum for every number
PEAK_CAP        = 0.45              # Hard maximum for any single number
_FLOOR_BUDGET   = FLOOR_PROB * 7    # 0.28 — reserved for floor allocation
_DISTR_SHARE    = 1.0 - _FLOOR_BUDGET  # 0.72 — proportionally distributed
MAX_CONF        = 0.65              # Confidence cap for short-match safety

UNIFORM = {n: 1.0 / 7 for n in range(7)}


def get_learning_phase(total_balls: int) -> Dict:
    """
    Calculate learning phase and blending weights based on lifetime balls.
    Returns dict: phase, global_weight, user_weight, confidence.
    """
    if total_balls < 60:
        return {
            'phase': 'global',
            'global_weight': 1.0,
            'user_weight': 0.0,
            'confidence': min(total_balls / 60.0, 0.3),
        }
    elif total_balls < 300:
        progress = (total_balls - 60) / 240.0
        return {
            'phase': 'transition',
            'global_weight': 0.7 - (0.4 * progress),
            'user_weight': 0.3 + (0.4 * progress),
            'confidence': 0.3 + (0.5 * progress),
        }
    else:
        excess = total_balls - 300
        return {
            'phase': 'personalized',
            'global_weight': 0.2,
            'user_weight': 0.8,
            'confidence': min(0.8 + excess / 1000.0, 0.95),
        }


class CPUStrategyEngine:
    """Frequency-based CPU opponent for short cricket matches."""

    def __init__(self, db_session_factory=None):
        self.db_session_factory = db_session_factory or SessionLocal

    # ── Public entry point ────────────────────────────────────────────────────

    def select_move(
        self,
        user_id: int,
        match_context: Dict,
        opponent_history: List[int],
    ) -> int:
        """
        Select CPU's next move (0-6).

        Pipeline:
          1. Build 3 signals: local_freq, global_freq, transition_pred
          2. Blend with weights that shift based on match length
          3. Apply role-specific strategy (bowl=match, bat=dodge)
          4. Lightweight situational pressure modifier
          5. Add noise + floor/cap
          6. Weighted random choice
        """
        db = self.db_session_factory()
        try:
            # ── Signal 1: Local frequency (this match) ────────────────────
            local_freq = self._build_local_frequency(opponent_history)

            # ── Signal 2: Global frequency (player lifetime from DB) ──────
            global_freq, global_n = self._load_user_patterns(db, user_id, match_context)

            # ── Signal 3: Transition prediction (after X -> ?) from DB ────
            transition_pred, trans_n = self._load_sequence_patterns(
                db, user_id, match_context, opponent_history
            )

            # ── Confidence from learning phase ────────────────────────────
            total_balls = self._get_total_balls_tracked(db, user_id)
            phase_info  = get_learning_phase(total_balls)
            confidence  = min(phase_info['confidence'], MAX_CONF)

            # ── Blend the 3 signals ───────────────────────────────────────
            balls_played = len(opponent_history)
            prediction = self._blend_signals(
                local_freq, global_freq, global_n,
                transition_pred, trans_n, balls_played,
            )

            # ── Role-specific strategy ────────────────────────────────────
            if match_context['role'] == 'bowling':
                strategic = self._bowling_strategy(prediction, match_context, confidence)
            else:
                strategic = self._batting_strategy(prediction, match_context, confidence)

            # ── Noise + choose ────────────────────────────────────────────
            noisy = self._add_noise(strategic, confidence)
            return self._weighted_choice(noisy)

        finally:
            db.close()

    # ── Local frequency builder ───────────────────────────────────────────────

    def _build_local_frequency(self, opponent_history: List[int]) -> Dict[int, float]:
        """
        Count each number in the current match history -> normalized distribution.

        Returns uniform if history is empty.
        """
        if not opponent_history:
            return dict(UNIFORM)

        counts = {n: 0 for n in range(7)}
        for move in opponent_history:
            if 0 <= move <= 6:
                counts[move] += 1

        total = sum(counts.values())
        if total == 0:
            return dict(UNIFORM)

        return {n: counts[n] / total for n in range(7)}

    # ── 3-signal blend ────────────────────────────────────────────────────────

    def _blend_signals(
        self,
        local_freq: Dict[int, float],
        global_freq: Dict[int, float],
        global_n: int,
        transition_pred: Dict[int, float],
        trans_n: int,
        balls_played: int,
    ) -> Dict[int, float]:
        """
        Blend local frequency, global profile, and transition prediction.

        Weight schedule based on balls played this match:
          Ball 0-1:  local=0.0, global=0.80, transition=0.20
          Ball 2-3:  local=0.25, global=0.50, transition=0.25
          Ball 4-6:  local=0.40, global=0.30, transition=0.30
          Ball 7+:   local=0.50, global=0.15, transition=0.35

        If global or transition data is unavailable (n=0), their weight
        is redistributed to the remaining signals.
        """
        # Base weight schedule
        if balls_played <= 1:
            w_local, w_global, w_trans = 0.0, 0.80, 0.20
        elif balls_played <= 3:
            w_local, w_global, w_trans = 0.25, 0.50, 0.25
        elif balls_played <= 6:
            w_local, w_global, w_trans = 0.40, 0.30, 0.30
        else:
            w_local, w_global, w_trans = 0.50, 0.15, 0.35

        # Zero out unavailable signals and redistribute
        if global_n == 0:
            w_local += w_global * 0.6
            w_trans += w_global * 0.4
            w_global = 0.0
        if trans_n == 0:
            w_local += w_trans * 0.5
            w_global += w_trans * 0.5
            w_trans = 0.0
        if balls_played == 0:
            w_local = 0.0  # No local data at all

        # Normalize weights
        total_w = w_local + w_global + w_trans
        if total_w < 0.01:
            return dict(UNIFORM)
        w_local  /= total_w
        w_global /= total_w
        w_trans  /= total_w

        # Weighted blend
        blended = {}
        for n in range(7):
            blended[n] = (
                w_local  * local_freq.get(n, 1/7) +
                w_global * global_freq.get(n, 1/7) +
                w_trans  * transition_pred.get(n, 1/7)
            )

        return self._normalize(blended)

    # ── Bowling strategy ──────────────────────────────────────────────────────

    def _bowling_strategy(
        self,
        prediction: Dict[int, float],
        context: Dict,
        confidence: float,
    ) -> Dict[int, float]:
        """
        CPU is BOWLING — wants to match batter's number (-> wicket).

        Uses the blended prediction directly: numbers the batter is
        likely to play get higher weight. Situational pressure is a
        lightweight modifier on top.
        """
        # Start from prediction — the CPU bowls what the batter is likely to play
        s = dict(prediction)

        # Amplify the prediction signal based on confidence
        # Higher confidence = sharpen the distribution toward predicted numbers
        if confidence > 0.15:
            # Sharpen: raise peaks, suppress lows
            avg = sum(s.values()) / 7
            sharpness = 1.0 + confidence * 1.5  # 1.0 to 1.975
            for n in range(7):
                if s[n] > avg:
                    s[n] = avg + (s[n] - avg) * sharpness
                else:
                    s[n] = avg - (avg - s[n]) * min(sharpness * 0.7, 1.4)
                s[n] = max(s[n], 0.01)

        # Situational pressure modifier (lightweight)
        pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs'],
        )

        # Under pressure, batters tend toward high numbers -> boost 4,5,6
        if 'desperate' in pressure or 'very_tight' in pressure:
            for n in (4, 5, 6):
                s[n] *= 1.20
            s[0] *= 1.15  # Some batters play 0 as a desperation move

        # Near all-out, batters play conservatively
        if context['wickets_lost'] >= 7:
            s[0] *= 1.25
            for n in (4, 5, 6):
                s[n] *= 1.10

        return self._floor_and_cap(self._normalize(s))

    # ── Batting strategy ──────────────────────────────────────────────────────

    def _batting_strategy(
        self,
        prediction: Dict[int, float],
        context: Dict,
        confidence: float,
    ) -> Dict[int, float]:
        """
        CPU is BATTING — wants to NOT match bowler's number (-> score runs).

        Inverts the blended prediction: numbers the bowler is likely to
        play get LOWER weight (avoid them). Numbers they're unlikely to
        play get HIGHER weight (safe to bat there).
        """
        # Invert: high prediction -> low weight, low prediction -> high weight
        max_pred = max(prediction.values())
        min_pred = min(prediction.values())

        if max_pred - min_pred < 0.01:
            # Prediction is flat / no signal -> use uniform
            s = dict(UNIFORM)
        else:
            # Inversion strength scales with confidence
            strength = 0.5 + confidence * 1.0  # 0.5 to 1.15

            s = {}
            for n in range(7):
                # Mirror the prediction: highest predicted -> lowest weight
                inverted = max_pred - prediction[n] + min_pred
                # Blend inversion with uniform (don't over-dodge)
                s[n] = (1.0 - strength * 0.6) * UNIFORM[n] + strength * 0.6 * inverted
                s[n] = max(s[n], 0.01)

        # Situational pressure modifier
        pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs'],
        )

        # Under pressure, CPU batter should go for high runs
        if 'desperate' in pressure or 'very_tight' in pressure:
            for n in (4, 5, 6):
                s[n] *= 1.40
            s[0] *= 0.70
            for n in (1, 2, 3):
                s[n] *= 0.80
        elif 'comfortable' in pressure:
            for n in (1, 2, 3):
                s[n] *= 1.20
            for n in (5, 6):
                s[n] *= 0.80

        # Near all-out, play conservatively
        if context['wickets_lost'] >= 7:
            for n in (1, 2, 3):
                s[n] *= 1.25
            for n in (5, 6):
                s[n] *= 0.65

        return self._floor_and_cap(self._normalize(s))

    # ── Noise ─────────────────────────────────────────────────────────────────

    def _add_noise(self, weights: Dict[int, float], confidence: float) -> Dict[int, float]:
        """
        Add controlled randomness to prevent full predictability.

        Base noise scales with confidence (higher confidence = more noise to compensate).
        Bluff: ~8% chance to boost a low-probability number.
        """
        peak = max(weights.values()) if weights else 0.0
        base_noise = 0.07 + (0.10 * confidence) + max(0.0, peak - 0.25) * 0.28

        noisy = {}
        for n in range(7):
            noise = random.uniform(-base_noise, base_noise)
            noisy[n] = max(FLOOR_PROB, weights[n] + noise)

        bluff_prob = 0.08 + max(0.0, peak - 0.28) * 0.14
        if random.random() < bluff_prob:
            sorted_by_prob = sorted(noisy.items(), key=lambda x: x[1])
            bluff_num = sorted_by_prob[random.randint(0, 2)][0]
            noisy[bluff_num] *= 2.5

        return self._floor_and_cap(self._normalize(noisy))

    # ── Math helpers ──────────────────────────────────────────────────────────

    def _normalize(self, weights: Dict[int, float]) -> Dict[int, float]:
        total = sum(weights.values())
        if total > 0:
            return {k: v / total for k, v in weights.items()}
        return {i: 1.0 / 7 for i in range(7)}

    def _apply_floor(self, weights: Dict[int, float]) -> Dict[int, float]:
        total = sum(weights.values())
        if total <= 0:
            return {i: 1.0 / 7 for i in range(7)}
        return {
            n: FLOOR_PROB + _DISTR_SHARE * (weights[n] / total)
            for n in range(7)
        }

    def _cap_peak(self, weights: Dict[int, float]) -> Dict[int, float]:
        """
        Iteratively cap any value exceeding PEAK_CAP, distributing excess
        uniformly across non-capped numbers.
        """
        w = dict(weights)
        for _ in range(10):
            if max(w.values()) <= PEAK_CAP + 1e-9:
                break
            excess  = 0.0
            capped  = {}
            for n, v in w.items():
                if v > PEAK_CAP:
                    excess   += v - PEAK_CAP
                    capped[n] = PEAK_CAP
                else:
                    capped[n] = v
            non_capped = [n for n in capped if capped[n] < PEAK_CAP]
            if non_capped:
                share = excess / len(non_capped)
                for n in non_capped:
                    capped[n] += share
            w = capped
        return w

    def _floor_and_cap(self, weights: Dict[int, float]) -> Dict[int, float]:
        return self._cap_peak(self._apply_floor(weights))

    def _weighted_choice(self, weights: Dict[int, float]) -> int:
        total = sum(weights.values())
        if total <= 0:
            return random.randint(0, 6)
        r      = random.uniform(0, total)
        cumsum = 0.0
        for num in range(7):
            cumsum += weights[num]
            if r <= cumsum:
                return num
        return 6

    # ── DB pattern loaders ────────────────────────────────────────────────────

    def _load_user_patterns(
        self, db: Session, user_id: int, context: Dict
    ) -> Tuple[Dict[int, float], int]:
        if user_id == -1:
            return {i: 1.0 / 7 for i in range(7)}, 0
        profile = db.query(CPUUserProfile).filter(
            CPUUserProfile.user_id      == user_id,
            CPUUserProfile.match_format == context['match_format'],
        ).first()
        if not profile:
            return {i: 1.0 / 7 for i in range(7)}, 0
        if context['role'] == 'bowling':
            if profile.total_balls_faced < 10:
                return {i: 1.0 / 7 for i in range(7)}, 0
            return (
                {
                    0: profile.bat_num_0_freq, 1: profile.bat_num_1_freq,
                    2: profile.bat_num_2_freq, 3: profile.bat_num_3_freq,
                    4: profile.bat_num_4_freq, 5: profile.bat_num_5_freq,
                    6: profile.bat_num_6_freq,
                },
                profile.total_balls_faced,
            )
        else:
            if profile.total_balls_bowled < 10:
                return {i: 1.0 / 7 for i in range(7)}, 0
            return (
                {
                    0: profile.bowl_num_0_freq, 1: profile.bowl_num_1_freq,
                    2: profile.bowl_num_2_freq, 3: profile.bowl_num_3_freq,
                    4: profile.bowl_num_4_freq, 5: profile.bowl_num_5_freq,
                    6: profile.bowl_num_6_freq,
                },
                profile.total_balls_bowled,
            )

    def _load_sequence_patterns(
        self, db: Session, user_id: int, context: Dict, opponent_history: List[int]
    ) -> Tuple[Dict[int, float], int]:
        if user_id == -1 or not opponent_history:
            return {i: 1.0 / 7 for i in range(7)}, 0
        last_move     = opponent_history[-1]
        opponent_role = 'batting' if context['role'] == 'bowling' else 'bowling'
        pattern = db.query(CPUSequencePattern).filter(
            CPUSequencePattern.user_id         == user_id,
            CPUSequencePattern.match_format    == context['match_format'],
            CPUSequencePattern.role            == opponent_role,
            CPUSequencePattern.previous_move   == last_move,
            CPUSequencePattern.previous_result == 'scored',
        ).first()
        if pattern and pattern.sample_count > 3:
            return (
                {
                    0: pattern.next_0_freq, 1: pattern.next_1_freq,
                    2: pattern.next_2_freq, 3: pattern.next_3_freq,
                    4: pattern.next_4_freq, 5: pattern.next_5_freq,
                    6: pattern.next_6_freq,
                },
                pattern.sample_count,
            )
        return {i: 1.0 / 7 for i in range(7)}, 0

    def _get_total_balls_tracked(self, db: Session, user_id: int) -> int:
        if user_id == -1:
            return 0
        progress = db.query(CPULearningProgress).filter(
            CPULearningProgress.user_id == user_id,
        ).first()
        return progress.total_balls_tracked if progress else 0

    # ── Status endpoint ───────────────────────────────────────────────────────

    def get_cpu_status(self, user_id: int) -> Dict:
        db = self.db_session_factory()
        try:
            total_balls  = self._get_total_balls_tracked(db, user_id)
            phase_info   = get_learning_phase(total_balls)
            conf_pct     = round(phase_info['confidence'] * 100, 1)
            messages = {
                'global':       f"CPU is learning from all players ({conf_pct}% confident)",
                'transition':   f"CPU is adapting to your style ({conf_pct}% confident)",
                'personalized': f"CPU has mastered your patterns ({conf_pct}% confident)",
            }
            return {
                'balls_tracked': total_balls,
                'phase':         phase_info['phase'],
                'confidence':    conf_pct,
                'message':       messages.get(phase_info['phase'], "CPU is learning..."),
            }
        finally:
            db.close()
