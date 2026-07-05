"""
Faithful replica of the CPU engine as of commit b0c00da — the state BEFORE
today's improvements. Used only for old-vs-new comparison runs.

What this engine has (original v2):
  - 3-signal blend with a balls-played weight schedule
    (ball 0-1: 0/.80/.20, 2-3: .25/.50/.25, 4-6: .40/.30/.30, 7+: .50/.15/.35)
  - Bowling: confidence-sharpened prediction, string-bucket pressure mods
  - Batting: inversion of the prediction blended with uniform
  - Fixed peak cap 0.45, same noise/bluff layer

What it does NOT have (today's additions):
  RRR awareness, trust-based blending, drift guard, bowling payout
  weighting, EV batting, earned sharpness, streak patterns, live
  in-match transitions, result-aware transition lookup.
"""
from typing import Dict, List, Optional, Tuple

from .engine_sim import SimEngine, UNIFORM, PEAK_CAP


def old_score_pressure(batting_first, current_score, target, wickets_lost,
                       balls_left, total_overs) -> str:
    """Copy of cpu_learning_utils.get_score_situation as of b0c00da."""
    if batting_first:
        overs_bowled = total_overs - (balls_left / 6.0)
        run_rate = current_score / overs_bowled if overs_bowled > 0 else 0
        if wickets_lost >= 7:
            return 'defending_collapse'
        elif run_rate >= 10:
            return 'defending_safe'
        elif run_rate >= 7:
            return 'defending_comfortable'
        elif run_rate >= 5:
            return 'defending_moderate'
        else:
            return 'defending_tight'
    else:
        runs_needed = (target or 0) - current_score
        if runs_needed <= 0:
            return 'chasing_won'
        required_rate = (runs_needed / balls_left * 6.0) if balls_left > 0 else 999
        if wickets_lost >= 8 or required_rate > 15:
            return 'chasing_desperate'
        elif required_rate > 12:
            return 'chasing_very_tight'
        elif required_rate > 9:
            return 'chasing_tight'
        elif required_rate > 6:
            return 'chasing_moderate'
        else:
            return 'chasing_comfortable'


class OldEngine(SimEngine):
    """The pre-today engine. Reuses SimEngine's math/noise helpers only."""

    def select_move(
        self,
        db_prior: Dict[int, float],
        opponent_history: List[int],
        context: Dict,
        confidence: float = 0.5,
        global_n: int = 0,
        trans_n: int = 0,
        transition_pred: Optional[Dict[int, float]] = None,
        **_ignored,   # streak/live signals didn't exist before today
    ) -> Tuple[int, Dict[int, float]]:
        local_freq = self._build_local_frequency(opponent_history)
        transition_pred = transition_pred or dict(UNIFORM)
        balls_played = len(opponent_history)

        prediction = self._old_blend(
            local_freq, db_prior, global_n, transition_pred, trans_n, balls_played,
        )

        if context['role'] == 'bowling':
            strategic = self._old_bowling(prediction, context, confidence)
        else:
            strategic = self._old_batting(prediction, context, confidence)

        noisy = self._add_noise(strategic, confidence)          # defaults: cap .45, earned 0
        final = self._floor_and_cap(self._normalize(noisy))
        return self._weighted_choice(final), final

    # ── b0c00da _blend_signals ────────────────────────────────────────────────

    def _old_blend(self, local_freq, global_freq, global_n,
                   transition_pred, trans_n, balls_played) -> Dict[int, float]:
        if balls_played <= 1:
            w_local, w_global, w_trans = 0.0, 0.80, 0.20
        elif balls_played <= 3:
            w_local, w_global, w_trans = 0.25, 0.50, 0.25
        elif balls_played <= 6:
            w_local, w_global, w_trans = 0.40, 0.30, 0.30
        else:
            w_local, w_global, w_trans = 0.50, 0.15, 0.35

        if global_n == 0:
            w_local += w_global * 0.6
            w_trans += w_global * 0.4
            w_global = 0.0
        if trans_n == 0:
            w_local += w_trans * 0.5
            w_global += w_trans * 0.5
            w_trans = 0.0
        if balls_played == 0:
            w_local = 0.0

        total_w = w_local + w_global + w_trans
        if total_w < 0.01:
            return dict(UNIFORM)
        w_local /= total_w
        w_global /= total_w
        w_trans /= total_w

        blended = {}
        for n in range(7):
            blended[n] = (
                w_local * local_freq.get(n, 1 / 7) +
                w_global * global_freq.get(n, 1 / 7) +
                w_trans * transition_pred.get(n, 1 / 7)
            )
        return self._normalize(blended)

    # ── b0c00da _bowling_strategy ─────────────────────────────────────────────

    def _old_bowling(self, prediction, context, confidence) -> Dict[int, float]:
        s = dict(prediction)

        if confidence > 0.15:
            avg = sum(s.values()) / 7
            sharpness = 1.0 + confidence * 1.5
            for n in range(7):
                if s[n] > avg:
                    s[n] = avg + (s[n] - avg) * sharpness
                else:
                    s[n] = avg - (avg - s[n]) * min(sharpness * 0.7, 1.4)
                s[n] = max(s[n], 0.01)

        pressure = old_score_pressure(
            context['batting_first'], context['current_score'], context.get('target'),
            context['wickets_lost'], context['balls_left'], context['total_overs'],
        )
        if 'desperate' in pressure or 'very_tight' in pressure:
            for n in (4, 5, 6):
                s[n] *= 1.20
            s[0] *= 1.15
        if context['wickets_lost'] >= 7:
            s[0] *= 1.25
            for n in (4, 5, 6):
                s[n] *= 1.10

        return self._floor_and_cap(self._normalize(s))

    # ── b0c00da _batting_strategy ─────────────────────────────────────────────

    def _old_batting(self, prediction, context, confidence) -> Dict[int, float]:
        max_pred = max(prediction.values())
        min_pred = min(prediction.values())

        if max_pred - min_pred < 0.01:
            s = dict(UNIFORM)
        else:
            strength = 0.5 + confidence * 1.0
            s = {}
            for n in range(7):
                inverted = max_pred - prediction[n] + min_pred
                s[n] = (1.0 - strength * 0.6) * UNIFORM[n] + strength * 0.6 * inverted
                s[n] = max(s[n], 0.01)

        pressure = old_score_pressure(
            context['batting_first'], context['current_score'], context.get('target'),
            context['wickets_lost'], context['balls_left'], context['total_overs'],
        )
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
        if context['wickets_lost'] >= 7:
            for n in (1, 2, 3):
                s[n] *= 1.25
            for n in (5, 6):
                s[n] *= 0.65

        return self._floor_and_cap(self._normalize(s))
