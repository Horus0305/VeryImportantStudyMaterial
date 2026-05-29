"""
CPU Strategy Engine — Short-Match Adaptive
Optimized for 2-over and 5-over games.

Design principles:
  1. Five-voter ensemble: global stats, user lifetime profile, situational
     buckets, 1-ball sequence, and live case-based retrieval from MatchBallLog.
  2. Each voter is weighted by sample_confidence (thin data → near-zero weight).
  3. Signal agreement: when voters agree on the same top-3 numbers the blend
     is trusted more; when they conflict the result falls toward uniform so
     the CPU doesn't get baited by manufactured patterns.
  4. In-game class-transition engine (bait guard, streak guard, H→Z) runs
     AFTER the DB blend and dominates after 4+ balls — confidence capped at
     0.65 for short-match safety.
  5. Hard floor (9%) and peak cap (38%) on all final distributions.
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


# ── Base prior ───────────────────────────────────────────────────────────────
BASE_WEIGHTS: Dict[int, float] = {
    0: 0.08,
    1: 0.16,
    2: 0.16,
    3: 0.15,
    4: 0.16,
    5: 0.14,
    6: 0.15,
}

# ── Tuning constants ─────────────────────────────────────────────────────────
FLOOR_PROB      = 0.04              # Hard minimum for every number
PEAK_CAP        = 0.45              # Hard maximum for any single number
_FLOOR_BUDGET   = FLOOR_PROB * 7    # 0.28 — reserved for floor allocation
_DISTR_SHARE    = 1.0 - _FLOOR_BUDGET  # 0.72 — proportionally distributed
BAIT_WINDOW   = 6      # Window for frequency-bait scan
BAIT_COUNT    = 3      # Occurrences in BAIT_WINDOW → bait suspected
STREAK_LEN    = 3      # Same class N times → streak → switch expected
SEQ_WINDOW    = 8      # Recent balls used for transition analysis
MAX_CONF      = 0.65   # Confidence cap for short-match safety

HIGH_NUMS    = frozenset({4, 5, 6})
LOW_NUMS     = frozenset({1, 2, 3})
LOW_AND_ZERO = (0, 1, 2, 3)    # tuple for use in for-loops alongside HIGH_NUMS


def _cls(n: int) -> str:
    """Classify a move: H(4-6), L(1-3), Z(0)."""
    if n == 0:
        return 'Z'
    if n >= 4:
        return 'H'
    return 'L'


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
    """Sequence-aware CPU opponent for short cricket matches."""

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
          1. Load five DB voters → weighted ensemble with agreement mixing
          2. Apply in-game sequence strategy (dominant after 4+ balls)
          3. Add noise + apply floor/peak cap
          4. Weighted random choice
        """
        db = self.db_session_factory()
        try:
            global_dist, global_n = self._load_global_patterns(db, match_context)
            user_dist,   user_n   = self._load_user_patterns(db, user_id, match_context)
            sit_dist,    sit_n    = self._load_situational_patterns(db, user_id, match_context)
            seq_dist,    seq_n    = self._load_sequence_patterns(db, user_id, match_context, opponent_history)
            case_dist,   case_n   = self._load_casebased_patterns(db, user_id, match_context, opponent_history)

            total_balls = self._get_total_balls_tracked(db, user_id)
            phase_info  = get_learning_phase(total_balls)

            # Five voters, each weighted by (base_weight × sample_confidence).
            # Voters with too little data are silenced automatically.
            voters = [
                {'dist': global_dist, 'base_weight': 0.15, 'samples': global_n, 'min_samples': 50},
                {'dist': user_dist,   'base_weight': 0.20, 'samples': user_n,   'min_samples': 60},
                {'dist': sit_dist,    'base_weight': 0.20, 'samples': sit_n,    'min_samples': 20},
                {'dist': seq_dist,    'base_weight': 0.20, 'samples': seq_n,    'min_samples': 15},
                {'dist': case_dist,   'base_weight': 0.25, 'samples': case_n,   'min_samples': 15},
            ]

            db_prior   = self._blend_patterns_v2(voters, phase_info)
            confidence = min(phase_info['confidence'], MAX_CONF)

            # Role-specific sequence strategy
            if match_context['role'] == 'bowling':
                strategic = self._bowling_strategy(db_prior, opponent_history, match_context, confidence)
            else:
                strategic = self._batting_strategy(db_prior, opponent_history, match_context, confidence)

            noisy = self._add_noise(strategic, confidence)
            return self._weighted_choice(noisy)

        finally:
            db.close()

    # ── Ensemble voting ───────────────────────────────────────────────────────

    def _compute_agreement(self, distributions: List[Dict[int, float]]) -> float:
        """
        Measure how much a set of distributions agree with each other.

        Uses average pairwise Jaccard similarity on each distribution's
        top-3 numbers. Returns 0.0 (complete disagreement) to 1.0 (identical).
        """
        if len(distributions) < 2:
            return 1.0
        tops = [
            set(sorted(d, key=d.get, reverse=True)[:3])
            for d in distributions
        ]
        pairs, total_sim = 0, 0.0
        for i in range(len(tops)):
            for j in range(i + 1, len(tops)):
                inter = len(tops[i] & tops[j])
                union = len(tops[i] | tops[j])
                total_sim += inter / union if union else 1.0
                pairs += 1
        return total_sim / pairs if pairs else 1.0

    def _blend_patterns_v2(
        self,
        voters: List[Dict],
        phase_info: Dict,
    ) -> Dict[int, float]:
        """
        Weighted ensemble blend with agreement-driven mixing.

        Each voter dict:  {'dist': {0-6: float}, 'base_weight': float,
                           'samples': int, 'min_samples': int}

        Step 1 — effective weight = base_weight × sample_confidence
                  sample_confidence = min(1.0, samples / min_samples)
        Step 2 — weighted average of all active (weight > 0) distributions
        Step 3 — mix blend toward uniform proportional to disagreement:
                  agreement=1.0 → alpha=0.85 (trust the blend)
                  agreement=0.0 → alpha=0.40 (fall back toward uniform)
        """
        effective_weights = []
        for v in voters:
            sc  = min(1.0, v['samples'] / v['min_samples']) if v['min_samples'] > 0 else 0.0
            effective_weights.append(v['base_weight'] * sc)

        total_eff = sum(effective_weights)
        if total_eff < 0.05:
            return dict(BASE_WEIGHTS)

        # Weighted blend
        blended = {n: 0.0 for n in range(7)}
        for v, ew in zip(voters, effective_weights):
            for n in range(7):
                blended[n] += v['dist'][n] * ew
        blended = {n: val / total_eff for n, val in blended.items()}

        # Agreement: only consider voters with meaningful weight
        active_dists = [v['dist'] for v, ew in zip(voters, effective_weights) if ew > 0.01]
        agreement    = self._compute_agreement(active_dists) if len(active_dists) >= 2 else 1.0

        # Mix toward uniform based on agreement level
        alpha   = 0.40 + 0.45 * agreement   # [0.40, 0.85]
        uniform = {n: 1.0 / 7 for n in range(7)}
        result  = {n: alpha * blended[n] + (1 - alpha) * uniform[n] for n in range(7)}
        return self._normalize(result)

    # ── Sequence signal ───────────────────────────────────────────────────────

    def _build_sequence_signal(self, history: List[int]) -> Dict:
        """
        Derive class-transition features from recent in-game history.

        Returns:
          last_class      - H/L/Z of last move
          streak_class    - class if 3+ in a row, else None
          streak_length   - consecutive same-class balls
          bait_number     - number that appears ≥BAIT_COUNT in last BAIT_WINDOW, else None
          transitions     - {from_class: {to_class: count}} built from this match
          patterns        - set of named signals detected
        """
        if not history:
            return {
                'last_class': None, 'streak_class': None,
                'streak_length': 0, 'bait_number': None,
                'transitions': {}, 'patterns': set(),
            }

        recent  = history[-SEQ_WINDOW:]
        classes = [_cls(n) for n in recent]

        # Streak detection
        last_class = classes[-1]
        streak_len = 0
        for c in reversed(classes):
            if c == last_class:
                streak_len += 1
            else:
                break
        streak_class = last_class if streak_len >= STREAK_LEN else None

        # Bait detection: same number too often in a short window
        bait_number = None
        if len(recent) >= BAIT_WINDOW:
            window = recent[-BAIT_WINDOW:]
            for num in range(7):
                if window.count(num) >= BAIT_COUNT:
                    bait_number = num
                    break

        # Class-transition table built from THIS match's history
        transitions: Dict[str, Dict[str, int]] = {}
        for i in range(len(classes) - 1):
            fc, tc = classes[i], classes[i + 1]
            transitions.setdefault(fc, {})
            transitions[fc][tc] = transitions[fc].get(tc, 0) + 1

        # Named pattern signals
        patterns: set = set()
        if len(recent) >= 2:
            prev_cls = _cls(recent[-2])
            curr_cls = _cls(recent[-1])
            if curr_cls == 'H':
                patterns.add('last_was_high')
            if prev_cls != curr_cls:
                patterns.add('just_switched')
        if len(recent) >= 3 and all(_cls(n) == 'H' for n in recent[-3:]):
            patterns.add('H_shuffle')

        return {
            'last_class': last_class,
            'streak_class': streak_class,
            'streak_length': streak_len,
            'bait_number': bait_number,
            'transitions': transitions,
            'patterns': patterns,
        }

    # ── Bowling strategy ──────────────────────────────────────────────────────

    def _bowling_strategy(
        self,
        weights: Dict[int, float],
        opponent_history: List[int],
        context: Dict,
        confidence: float,
    ) -> Dict[int, float]:
        """
        CPU is BOWLING — wants to match batter's number (→ wicket).

        Priority:
          1. Bait guard: detect frequency manipulation → predict switch
          2. Streak guard: 3+ same class → switch incoming
          3. Class transition: what class typically follows the last one?
          4. H→Z special case: after high, 0 is the most common escape
          5. H-shuffle: bouncing 4/5/6 → stay in high class
          6. Situational pressure adjustments
        """
        if len(opponent_history) < 2:
            return self._floor_and_cap(self._normalize(weights))

        s   = dict(weights)
        sig = self._build_sequence_signal(opponent_history)

        # ── 1. Frequency-bait guard ─────────────────────────────────────────
        if sig['bait_number'] is not None:
            bn = sig['bait_number']
            bc = _cls(bn)
            crush = max(0.18, 1.0 - 0.80 * confidence)
            s[bn] *= crush
            if bc == 'H':
                s[0] *= 2.0
                for n in LOW_NUMS: s[n] *= 1.6
            else:
                for n in HIGH_NUMS: s[n] *= 1.9
                s[0] *= 1.3
            return self._floor_and_cap(self._normalize(s))

        # ── 2. Streak guard ─────────────────────────────────────────────────
        # Batter is still IN the streak class right now → bowl that class to
        # match. Switch prediction is handled by the transition signal (step 3)
        # which uses the actual observed transition matrix — not a fixed guess.
        if sig['streak_class'] is not None:
            sc  = sig['streak_class']
            sl  = sig['streak_length']
            boost  = 1.0 + min(0.35 * (sl - STREAK_LEN + 1), 1.0)
            dampen = max(0.50, 1.0 - 0.12 * (sl - STREAK_LEN + 1))
            if sc == 'H':
                for n in HIGH_NUMS: s[n] *= boost
                for n in LOW_AND_ZERO: s[n] *= dampen
            elif sc == 'L':
                for n in LOW_NUMS: s[n] *= boost
                s[0] *= boost * 0.7      # 0 is possible but less likely with L batter
                for n in HIGH_NUMS: s[n] *= dampen
            elif sc == 'Z':
                s[0] *= boost * 1.5      # batter keeps playing 0 → bowl 0
                for n in HIGH_NUMS: s[n] *= dampen
            return self._floor_and_cap(self._normalize(s))

        # ── 3. Class-transition signal ──────────────────────────────────────
        lc = sig['last_class']
        tr = sig['transitions']
        if lc in tr and sum(tr[lc].values()) >= 2:
            total = sum(tr[lc].values())
            for next_c, cnt in tr[lc].items():
                prob  = cnt / total
                blend = 0.40 * confidence * prob
                if next_c == 'H':
                    for n in HIGH_NUMS: s[n] *= 1 + blend * 2.0
                elif next_c == 'L':
                    for n in LOW_NUMS:  s[n] *= 1 + blend * 2.0
                elif next_c == 'Z':
                    s[0] *= 1 + blend * 3.5

        # ── 4. H→Z special case ─────────────────────────────────────────────
        if 'last_was_high' in sig['patterns']:
            s[0] *= 1.50
            for n in LOW_NUMS: s[n] *= 1.15

        # ── 5. H-shuffle ────────────────────────────────────────────────────
        if 'H_shuffle' in sig['patterns']:
            for n in HIGH_NUMS: s[n] *= 1.35

        # ── 6. Situational pressure ──────────────────────────────────────────
        pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs'],
        )
        if 'desperate' in pressure or 'very_tight' in pressure:
            for n in HIGH_NUMS: s[n] *= 1.25
            s[0] *= 1.20
        if context['wickets_lost'] >= 7:
            s[0] *= 1.35
            for n in HIGH_NUMS: s[n] *= 1.15

        return self._floor_and_cap(self._normalize(s))

    # ── Batting strategy ──────────────────────────────────────────────────────

    def _batting_strategy(
        self,
        weights: Dict[int, float],
        opponent_history: List[int],
        context: Dict,
        confidence: float,
    ) -> Dict[int, float]:
        """
        CPU is BATTING — wants to NOT match bowler's number (→ score runs).

        Predicts what the bowler will pick, then moves away from it.
        """
        if len(opponent_history) < 2:
            return self._floor_and_cap(self._normalize(weights))

        s   = dict(weights)
        sig = self._build_sequence_signal(opponent_history)

        # ── 1. Bait guard (bowler side) ──────────────────────────────────────
        if sig['bait_number'] is not None:
            bn = sig['bait_number']
            bc = _cls(bn)
            s[bn] = min(s[bn] * 1.5, BASE_WEIGHTS[bn] * 1.4)
            if bc == 'H':
                for n in LOW_AND_ZERO: s[n] *= 0.60
            else:
                for n in HIGH_NUMS: s[n] *= 0.60
            return self._floor_and_cap(self._normalize(s))

        # ── 2. Streak guard ──────────────────────────────────────────────────
        # Bowler is still bowling the streak class RIGHT NOW — avoid it.
        if sig['streak_class'] is not None:
            sc  = sig['streak_class']
            sl  = sig['streak_length']
            avoid = max(0.40, 1.0 - min(0.22 * (sl - STREAK_LEN + 1), 0.55))
            if sc == 'H':
                for n in HIGH_NUMS: s[n] *= avoid
                s[0] *= 1.05
                for n in LOW_NUMS: s[n] *= 1.05
            elif sc == 'L':
                for n in LOW_AND_ZERO: s[n] *= avoid
                for n in HIGH_NUMS: s[n] *= 1.05
            elif sc == 'Z':
                s[0] *= avoid
                for n in HIGH_NUMS: s[n] *= 1.20
            return self._floor_and_cap(self._normalize(s))

        # ── 3. Class-transition: avoid predicted class ───────────────────────
        lc = sig['last_class']
        tr = sig['transitions']
        if lc in tr and sum(tr[lc].values()) >= 2:
            total = sum(tr[lc].values())
            for next_c, cnt in tr[lc].items():
                prob  = cnt / total
                avoid = 0.42 * confidence * prob
                if next_c == 'H':
                    for n in HIGH_NUMS: s[n] *= max(0.45, 1 - avoid * 2.0)
                elif next_c == 'L':
                    for n in LOW_NUMS:  s[n] *= max(0.45, 1 - avoid * 2.0)
                elif next_c == 'Z':
                    s[0] *= max(0.45, 1 - avoid * 3.5)

        if 'last_was_high' in sig['patterns']:
            s[0] *= 0.75

        # ── 4. Situational adjustments ───────────────────────────────────────
        pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs'],
        )
        if 'desperate' in pressure or 'very_tight' in pressure:
            for n in HIGH_NUMS: s[n] *= 1.40
            s[0] *= 0.70
            for n in LOW_NUMS:  s[n] *= 0.80
        elif 'comfortable' in pressure:
            for n in LOW_NUMS:  s[n] *= 1.20
            for n in (5, 6):    s[n] *= 0.80
        if context['wickets_lost'] >= 7:
            for n in LOW_NUMS:  s[n] *= 1.25
            for n in (5, 6):    s[n] *= 0.65

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

    def _load_global_patterns(
        self, db: Session, context: Dict
    ) -> Tuple[Dict[int, float], int]:
        game_phase     = get_game_phase(context['current_over'], context['total_overs'])
        score_pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs'],
        )
        pattern = db.query(CPUGlobalPattern).filter(
            CPUGlobalPattern.match_format    == context['match_format'],
            CPUGlobalPattern.game_phase      == game_phase,
            CPUGlobalPattern.role            == context['role'],
            CPUGlobalPattern.score_situation == score_pressure,
            CPUGlobalPattern.wickets_lost    == context['wickets_lost'],
        ).first()
        if pattern and pattern.total_samples > 10:
            return (
                {
                    0: pattern.num_0_freq, 1: pattern.num_1_freq,
                    2: pattern.num_2_freq, 3: pattern.num_3_freq,
                    4: pattern.num_4_freq, 5: pattern.num_5_freq,
                    6: pattern.num_6_freq,
                },
                pattern.total_samples,
            )
        return dict(BASE_WEIGHTS), 0

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

    def _load_situational_patterns(
        self, db: Session, user_id: int, context: Dict
    ) -> Tuple[Dict[int, float], int]:
        if user_id == -1:
            return {i: 1.0 / 7 for i in range(7)}, 0
        game_phase     = get_game_phase(context['current_over'], context['total_overs'])
        score_pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs'],
        )
        recent_event  = get_recent_event(context.get('last_3_results', []))
        opponent_role = 'batting' if context['role'] == 'bowling' else 'bowling'
        pattern = db.query(CPUSituationalPattern).filter(
            CPUSituationalPattern.user_id       == user_id,
            CPUSituationalPattern.match_format  == context['match_format'],
            CPUSituationalPattern.game_phase    == game_phase,
            CPUSituationalPattern.role          == opponent_role,
            CPUSituationalPattern.score_pressure == score_pressure,
            CPUSituationalPattern.recent_event  == recent_event,
        ).first()
        if pattern and pattern.sample_count > 5:
            return (
                {
                    0: pattern.num_0_freq, 1: pattern.num_1_freq,
                    2: pattern.num_2_freq, 3: pattern.num_3_freq,
                    4: pattern.num_4_freq, 5: pattern.num_5_freq,
                    6: pattern.num_6_freq,
                },
                pattern.sample_count,
            )
        return {i: 1.0 / 7 for i in range(7)}, 0

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

    def _load_casebased_patterns(
        self, db: Session, user_id: int, context: Dict, opponent_history: List[int]
    ) -> Tuple[Dict[int, float], int]:
        """
        Live case-based retrieval from MatchBallLog.

        Finds all past balls where the opponent was in a similar game situation
        (format + phase + pressure) and returns their move distribution.

        Falls back to a relaxed query (format + phase only) when the strict
        filter returns fewer than 8 balls. Returns uniform + 0 if still sparse.
        """
        if user_id == -1:
            return {i: 1.0 / 7 for i in range(7)}, 0

        game_phase     = get_game_phase(context['current_over'], context['total_overs'])
        score_pressure = get_score_situation(
            batting_first=context['batting_first'],
            current_score=context['current_score'],
            target=context.get('target'),
            wickets_lost=context['wickets_lost'],
            balls_left=context['balls_left'],
            total_overs=context['total_overs'],
        )

        # When CPU is bowling we predict the batter; when batting, the bowler.
        if context['role'] == 'bowling':
            id_filter  = MatchBallLog.batter_user_id == user_id
            move_col   = MatchBallLog.bat_move
        else:
            id_filter  = MatchBallLog.bowler_user_id == user_id
            move_col   = MatchBallLog.bowl_move

        # Strict query: format + phase + pressure
        rows = db.query(move_col).filter(
            id_filter,
            MatchBallLog.match_format  == context['match_format'],
            MatchBallLog.game_phase    == game_phase,
            MatchBallLog.score_pressure == score_pressure,
        ).all()

        # Relaxed fallback: drop pressure filter
        if len(rows) < 8:
            rows = db.query(move_col).filter(
                id_filter,
                MatchBallLog.match_format == context['match_format'],
                MatchBallLog.game_phase   == game_phase,
            ).all()

        if len(rows) < 5:
            return {i: 1.0 / 7 for i in range(7)}, 0

        counts: Dict[int, int] = {n: 0 for n in range(7)}
        for (move,) in rows:
            if 0 <= move <= 6:
                counts[move] += 1

        total = sum(counts.values())
        if total == 0:
            return {i: 1.0 / 7 for i in range(7)}, 0

        return {n: counts[n] / total for n in range(7)}, total

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
