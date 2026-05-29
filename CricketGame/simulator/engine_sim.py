"""
Self-contained CPU engine for simulation — no database required.

Three engine variants for comparison:
  SimEngine    — full v3 engine (sequence signals, bait/streak guards)
  NaiveEngine  — no in-game adaptation, just picks from db_prior
  UniformEngine — pure uniform random (Nash equilibrium baseline)

Each select_move() returns (chosen_number, distribution_dict) so the
benchmark can track Shannon entropy alongside win/loss metrics.
"""
import random
import math
from typing import Dict, List, Optional, Tuple

# ── Constants (must match cpu_strategy_engine.py exactly) ────────────────────
FLOOR_PROB    = 0.04
PEAK_CAP      = 0.45
_FLOOR_BUDGET = FLOOR_PROB * 7   # 0.28
_DISTR_SHARE  = 1.0 - _FLOOR_BUDGET  # 0.72
BAIT_WINDOW   = 6
BAIT_COUNT    = 3
STREAK_LEN    = 3
SEQ_WINDOW    = 8

HIGH_NUMS = frozenset({4, 5, 6})
LOW_NUMS  = frozenset({1, 2, 3})
LOW_AND_ZERO = (0, 1, 2, 3)   # tuple so it's iterable in for-loops

BASE_WEIGHTS: Dict[int, float] = {
    0: 0.08, 1: 0.16, 2: 0.16, 3: 0.15,
    4: 0.16, 5: 0.14, 6: 0.15,
}


def _cls(n: int) -> str:
    if n == 0: return 'Z'
    if n >= 4: return 'H'
    return 'L'


def score_pressure(batting_first: bool, current_score: int, target: Optional[int],
                   wickets_lost: int, balls_left: int, total_overs: int) -> str:
    """Simplified pressure classifier matching cpu_learning_utils logic."""
    if target is None:
        if wickets_lost >= 7:
            return 'defending_tight'
        return 'normal'
    needed = target - current_score + 1
    if balls_left <= 0:
        return 'chasing_desperate'
    rrr = needed / balls_left          # required runs per ball
    if needed <= 0:
        return 'chasing_comfortable'
    if rrr > 2.0:
        return 'chasing_desperate'
    if rrr > 1.3:
        return 'chasing_very_tight'
    return 'chasing_normal'


def entropy(weights: Dict[int, float]) -> float:
    """Shannon entropy in bits. Max = log2(7) ≈ 2.807 for uniform."""
    h = 0.0
    for p in weights.values():
        if p > 1e-12:
            h -= p * math.log2(p)
    return h


# ── Full v3 engine ────────────────────────────────────────────────────────────

class SimEngine:
    """
    Complete v3 engine: DB prior (injected) + in-game sequence signals.
    Mirror of CPUStrategyEngine minus all database code.
    """

    def select_move(
        self,
        db_prior: Dict[int, float],
        opponent_history: List[int],
        context: Dict,
        confidence: float = 0.5,
    ) -> Tuple[int, Dict[int, float]]:
        """Returns (chosen_number, final_distribution)."""
        if context['role'] == 'bowling':
            strategic = self._bowling_strategy(db_prior, opponent_history, context, confidence)
        else:
            strategic = self._batting_strategy(db_prior, opponent_history, context, confidence)
        noisy = self._add_noise(strategic, confidence)
        final = self._floor_and_cap(self._normalize(noisy))
        return self._weighted_choice(final), final

    # ── Sequence signal ───────────────────────────────────────────────────────

    def _build_sequence_signal(self, history: List[int]) -> Dict:
        if not history:
            return {
                'last_class': None, 'streak_class': None, 'streak_length': 0,
                'bait_number': None, 'transitions': {}, 'patterns': set(),
            }
        recent  = history[-SEQ_WINDOW:]
        classes = [_cls(n) for n in recent]
        last_class = classes[-1]

        streak_len = 0
        for c in reversed(classes):
            if c == last_class: streak_len += 1
            else: break
        streak_class = last_class if streak_len >= STREAK_LEN else None

        bait_number = None
        if len(recent) >= BAIT_WINDOW:
            window = recent[-BAIT_WINDOW:]
            for num in range(7):
                if window.count(num) >= BAIT_COUNT:
                    bait_number = num
                    break

        transitions: Dict[str, Dict[str, int]] = {}
        for i in range(len(classes) - 1):
            fc, tc = classes[i], classes[i + 1]
            transitions.setdefault(fc, {})
            transitions[fc][tc] = transitions[fc].get(tc, 0) + 1

        patterns: set = set()
        if len(recent) >= 2:
            if _cls(recent[-1]) == 'H':
                patterns.add('last_was_high')
            if _cls(recent[-2]) != _cls(recent[-1]):
                patterns.add('just_switched')
        if len(recent) >= 3 and all(_cls(n) == 'H' for n in recent[-3:]):
            patterns.add('H_shuffle')

        return {
            'last_class': last_class, 'streak_class': streak_class,
            'streak_length': streak_len, 'bait_number': bait_number,
            'transitions': transitions, 'patterns': patterns,
        }

    # ── Bowling strategy ──────────────────────────────────────────────────────

    def _bowling_strategy(self, weights, opponent_history, context, confidence):
        if len(opponent_history) < 2:
            return self._floor_and_cap(self._normalize(weights))
        s   = dict(weights)
        sig = self._build_sequence_signal(opponent_history)

        # 1. Bait guard
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

        # 2. Streak guard — batter is still IN the streak class → bowl it to match
        if sig['streak_class'] is not None:
            sc, sl = sig['streak_class'], sig['streak_length']
            boost  = 1.0 + min(0.35 * (sl - STREAK_LEN + 1), 1.0)
            dampen = max(0.50, 1.0 - 0.12 * (sl - STREAK_LEN + 1))
            if sc == 'H':
                for n in HIGH_NUMS: s[n] *= boost
                for n in LOW_AND_ZERO: s[n] *= dampen
            elif sc == 'L':
                for n in LOW_NUMS: s[n] *= boost
                s[0] *= boost * 0.7
                for n in HIGH_NUMS: s[n] *= dampen
            elif sc == 'Z':
                s[0] *= boost * 1.5
                for n in HIGH_NUMS: s[n] *= dampen
            return self._floor_and_cap(self._normalize(s))

        # 3. Class-transition signal
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

        # 4. H→Z special case
        if 'last_was_high' in sig['patterns']:
            s[0] *= 1.50
            for n in LOW_NUMS: s[n] *= 1.15

        # 5. H-shuffle
        if 'H_shuffle' in sig['patterns']:
            for n in HIGH_NUMS: s[n] *= 1.35

        # 6. Situational pressure
        pressure = score_pressure(
            context['batting_first'], context['current_score'], context.get('target'),
            context['wickets_lost'], context['balls_left'], context['total_overs'],
        )
        if 'desperate' in pressure or 'very_tight' in pressure:
            for n in HIGH_NUMS: s[n] *= 1.25
            s[0] *= 1.20
        if context['wickets_lost'] >= 7:
            s[0] *= 1.35
            for n in HIGH_NUMS: s[n] *= 1.15

        return self._floor_and_cap(self._normalize(s))

    # ── Batting strategy ──────────────────────────────────────────────────────

    def _batting_strategy(self, weights, opponent_history, context, confidence):
        if len(opponent_history) < 2:
            return self._floor_and_cap(self._normalize(weights))
        s   = dict(weights)
        sig = self._build_sequence_signal(opponent_history)

        # 1. Bait guard (bowler side)
        if sig['bait_number'] is not None:
            bn = sig['bait_number']
            bc = _cls(bn)
            s[bn] = min(s[bn] * 1.5, BASE_WEIGHTS[bn] * 1.4)
            if bc == 'H':
                for n in LOW_AND_ZERO: s[n] *= 0.60
            else:
                for n in HIGH_NUMS: s[n] *= 0.60
            return self._floor_and_cap(self._normalize(s))

        # 2. Streak guard — avoid the CURRENT streak class (bowler is still in it)
        if sig['streak_class'] is not None:
            sc, sl = sig['streak_class'], sig['streak_length']
            avoid  = max(0.40, 1.0 - min(0.22 * (sl - STREAK_LEN + 1), 0.55))
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

        # 3. Class-transition: avoid predicted class
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

        # 4. Situational adjustments
        pressure = score_pressure(
            context['batting_first'], context['current_score'], context.get('target'),
            context['wickets_lost'], context['balls_left'], context['total_overs'],
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

    def _add_noise(self, weights, confidence):
        peak       = max(weights.values()) if weights else 0.0
        base_noise = 0.07 + (0.10 * confidence) + max(0.0, peak - 0.25) * 0.28
        noisy = {}
        for n in range(7):
            noise    = random.uniform(-base_noise, base_noise)
            noisy[n] = max(FLOOR_PROB, weights[n] + noise)
        bluff_prob = 0.08 + max(0.0, peak - 0.28) * 0.14
        if random.random() < bluff_prob:
            low3      = sorted(noisy.items(), key=lambda x: x[1])[:3]
            bluff_num = low3[random.randint(0, 2)][0]
            noisy[bluff_num] *= 2.5
        return self._floor_and_cap(self._normalize(noisy))

    # ── Math helpers ──────────────────────────────────────────────────────────

    def _normalize(self, weights):
        total = sum(weights.values())
        if total > 0:
            return {k: v / total for k, v in weights.items()}
        return {i: 1.0 / 7 for i in range(7)}

    def _apply_floor(self, weights):
        total = sum(weights.values())
        if total <= 0:
            return {i: 1.0 / 7 for i in range(7)}
        return {n: FLOOR_PROB + _DISTR_SHARE * (weights[n] / total) for n in range(7)}

    def _cap_peak(self, weights):
        w = dict(weights)
        for _ in range(10):
            if max(w.values()) <= PEAK_CAP + 1e-9:
                break
            excess, capped = 0.0, {}
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

    def _floor_and_cap(self, weights):
        return self._cap_peak(self._apply_floor(weights))

    def _weighted_choice(self, weights):
        total = sum(weights.values())
        if total <= 0:
            return random.randint(0, 6)
        r, cumsum = random.uniform(0, total), 0.0
        for num in range(7):
            cumsum += weights[num]
            if r <= cumsum:
                return num
        return 6


# ── Naive engine (no in-game adaptation) ─────────────────────────────────────

class NaiveEngine(SimEngine):
    """
    CPU with no in-game sequence adaptation.
    Always picks from the db_prior directly with minimal noise.
    Baseline to show how much the sequence strategy adds.
    """

    def select_move(self, db_prior, opponent_history, context, confidence=0.5):
        final = self._floor_and_cap(self._normalize(db_prior))
        # Low noise — CPU is static and predictable
        noisy = {}
        for n in range(7):
            noisy[n] = max(FLOOR_PROB, final[n] + random.uniform(-0.04, 0.04))
        result = self._floor_and_cap(self._normalize(noisy))
        return self._weighted_choice(result), result


# ── Uniform engine (Nash equilibrium baseline) ────────────────────────────────

class UniformEngine:
    """
    Always picks uniformly at random.
    Theoretically unexploitable — sets the floor for all comparisons.
    Any CPU that scores better than this is genuinely exploiting bot patterns.
    """

    def select_move(self, db_prior, opponent_history, context, confidence=0.5):
        dist = {i: 1.0 / 7 for i in range(7)}
        return random.randint(0, 6), dist
