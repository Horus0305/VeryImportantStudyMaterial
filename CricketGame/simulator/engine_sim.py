"""
Self-contained CPU engine for simulation — no database required.

Mirrors backend/cpu/cpu_strategy_engine.py (v2: frequency blend + required
run-rate awareness) exactly, minus all database code. The DB-backed signals
(global per-user profile, sequence-transition pattern) are represented here
by `global_n`/`trans_n` sample counts the caller controls — the benchmark
defaults both to 0 to isolate in-match (local-frequency) adaptation, i.e.
"how good is the engine against an opponent it has zero history on."

Three engine variants for comparison:
  SimEngine     — full v2 engine (local/global/transition blend + RRR)
  NaiveEngine   — no in-game adaptation, just picks from db_prior
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
_FLOOR_BUDGET = FLOOR_PROB * 7        # 0.28
_DISTR_SHARE  = 1.0 - _FLOOR_BUDGET   # 0.72
MAX_CONF      = 0.65

RRR_NEUTRAL = 6.0    # runs/over treated as "par" — no pressure either way
RRR_MAX     = 15.0   # runs/over treated as maximum realistic pressure

LOCAL_TRUST_BALLS    = 8
GLOBAL_TRUST_SAMPLES = 100
TRANS_TRUST_SAMPLES  = 20
LOCAL_MAX_WEIGHT  = 0.50
GLOBAL_MAX_WEIGHT = 0.30
TRANS_MAX_WEIGHT  = 0.45
STREAK_TRUST_SAMPLES = 15
STREAK_MAX_WEIGHT    = 0.40
LIVE_TRANS_TRUST_OBS  = 4
LIVE_TRANS_MAX_WEIGHT = 0.45
LIVE2_TRUST_OBS  = 4
LIVE2_MIN_OBS    = 2
LIVE2_MAX_WEIGHT = 0.50
SIT_TRUST_SAMPLES = 12
SIT_MAX_WEIGHT    = 0.25

ENDGAME_WIN_EV = 10.0
ENDGAME_DENY   = 10.0

READ_ALARM_FLOOR = 0.26
READ_ALARM_CEIL  = 0.50
READ_MIN_BALLS   = 8
READ_NOISE_BOOST = 0.5
READ_BLUFF_BOOST = 0.10

BOWL_WICKET_VALUE = 5.0
EARNED_CAP_BONUS  = 0.15
EARNED_NOISE_CUT  = 0.50
_TOP3_CHANCE      = 3.0 / 7.0

BAT_WICKET_COST_RATE = 2.0
BAT_WICKET_COST_MAX  = 8.0
BAT_TEMP_BASE        = 1.5
BAT_TEMP_CONF_CUT    = 0.6

GIFT_RISK_MAX_DISCOUNT = 0.5   # v3: bowling-side 0-wildcard gift-risk discount

DRIFT_MIN_BALLS    = 6
DRIFT_TV_NOISE     = 0.40
DRIFT_MAX_DISCOUNT = 0.75

UNIFORM: Dict[int, float] = {n: 1.0 / 7 for n in range(7)}

BASE_WEIGHTS: Dict[int, float] = {
    0: 0.08, 1: 0.16, 2: 0.16, 3: 0.15,
    4: 0.16, 5: 0.14, 6: 0.15,
}


def compute_required_run_rate(context: Dict) -> float:
    """Runs-per-over the chasing side needs from this point on. 0.0 if not chasing."""
    target = context.get('target')
    if target is None:
        return 0.0
    runs_needed = target - context['current_score']
    if runs_needed <= 0:
        return 0.0
    balls_left = context['balls_left']
    if balls_left <= 0:
        return RRR_MAX
    return runs_needed / balls_left * 6.0


def rrr_pressure(context: Dict) -> float:
    """Signed pressure derived from required run rate, roughly in [-0.7, 1.6]."""
    rrr = compute_required_run_rate(context)
    if rrr <= 0.0:
        return 0.0
    pressure = (rrr - RRR_NEUTRAL) / (RRR_MAX - RRR_NEUTRAL)
    if pressure > 0:
        wickets_lost = context.get('wickets_lost', 0)
        pressure *= 1.0 + min(wickets_lost, 8) * 0.06
    return max(-0.7, min(1.6, pressure))


def entropy(weights: Dict[int, float]) -> float:
    """Shannon entropy in bits. Max = log2(7) ≈ 2.807 for uniform."""
    h = 0.0
    for p in weights.values():
        if p > 1e-12:
            h -= p * math.log2(p)
    return h


# ── Full v2 engine ────────────────────────────────────────────────────────────

class SimEngine:
    """
    Complete v2 engine: 3-signal blend (local/global/transition) + required
    run-rate awareness. Mirror of CPUStrategyEngine minus all database code.
    """

    def select_move(
        self,
        db_prior: Dict[int, float],
        opponent_history: List[int],
        context: Dict,
        confidence: float = 0.5,
        global_n: int = 0,
        trans_n: int = 0,
        transition_pred: Optional[Dict[int, float]] = None,
        streak_n: int = 0,
        streak_pred: Optional[Dict[int, float]] = None,
    ) -> Tuple[int, Dict[int, float]]:
        """Returns (chosen_number, final_distribution)."""
        local_freq = self._build_local_frequency(opponent_history)
        transition_pred = transition_pred or dict(UNIFORM)
        balls_played = len(opponent_history)
        live_pred, live_n = self._build_live_transitions(opponent_history)
        live2_pred, live2_n = self._build_live_transitions2(opponent_history)

        prediction = self._blend_signals(
            local_freq, db_prior, global_n, transition_pred, trans_n, balls_played,
            streak_pred, streak_n, live_pred, live_n, live2_pred, live2_n,
        )

        alarm  = self._read_alarm(context)
        earned = self._earned_accuracy(opponent_history) * (1.0 - alarm)
        cap    = PEAK_CAP + EARNED_CAP_BONUS * earned

        if context['role'] == 'bowling':
            strategic = self._bowling_strategy(prediction, context, confidence, cap)
        else:
            strategic = self._batting_strategy(prediction, context, confidence, cap)

        noisy = self._add_noise(strategic, confidence, cap, earned, alarm)
        final = self._floor_and_cap(self._normalize(noisy), cap)
        return self._weighted_choice(final), final

    # ── Local frequency builder ───────────────────────────────────────────────

    def _build_local_frequency(self, opponent_history: List[int]) -> Dict[int, float]:
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

    def _build_live_transitions(self, history: List[int]) -> Tuple[Dict[int, float], int]:
        """In-match transitions: what followed the current last move this innings?"""
        if len(history) < 2:
            return dict(UNIFORM), 0
        last = history[-1]
        counts = {n: 0 for n in range(7)}
        total = 0
        for i in range(len(history) - 1):
            if history[i] == last:
                counts[history[i + 1]] += 1
                total += 1
        if total == 0:
            return dict(UNIFORM), 0
        return {n: counts[n] / total for n in range(7)}, total

    def _build_live_transitions2(self, history: List[int]) -> Tuple[Dict[int, float], int]:
        """2-gram in-match transitions: what followed the last TWO moves?"""
        if len(history) < 3:
            return dict(UNIFORM), 0
        pair = (history[-2], history[-1])
        counts = {n: 0 for n in range(7)}
        total = 0
        for i in range(len(history) - 2):
            if (history[i], history[i + 1]) == pair:
                counts[history[i + 2]] += 1
                total += 1
        if total < LIVE2_MIN_OBS:
            return dict(UNIFORM), 0
        return {n: counts[n] / total for n in range(7)}, total

    def _read_alarm(self, context: Dict) -> float:
        """0-1 alarm that the opponent is predicting the CPU (batting only)."""
        if context['role'] != 'batting':
            return 0.0
        balls_faced = context['total_overs'] * 6 - context['balls_left']
        if balls_faced < READ_MIN_BALLS:
            return 0.0
        rate = context['wickets_lost'] / balls_faced
        return max(0.0, min(1.0, (rate - READ_ALARM_FLOOR) / (READ_ALARM_CEIL - READ_ALARM_FLOOR)))

    # ── Earned sharpness ──────────────────────────────────────────────────────

    def _earned_accuracy(self, history: List[int]) -> float:
        """Top-3 prediction hit rate this match, scaled above chance (3/7)."""
        if len(history) < 5:
            return 0.0
        hits = checks = 0
        for i in range(3, len(history)):
            prior = history[:i]
            scores = {n: 0.0 for n in range(7)}
            for m in prior:
                scores[m] += 1.0
            prev = prior[-1]
            for j in range(len(prior) - 1):
                if prior[j] == prev:
                    scores[prior[j + 1]] += 2.0
            top3 = sorted(scores, key=scores.get, reverse=True)[:3]
            if history[i] in top3:
                hits += 1
            checks += 1
        acc = hits / checks
        return max(0.0, min(1.0, (acc - _TOP3_CHANCE) / (1.0 - _TOP3_CHANCE)))

    # ── 3-signal blend ────────────────────────────────────────────────────────

    def _blend_signals(
        self, local_freq, global_freq, global_n, transition_pred, trans_n, balls_played,
        streak_pred=None, streak_n=0, live_pred=None, live_n=0,
        live2_pred=None, live2_n=0, sit_pred=None, sit_n=0,
    ) -> Dict[int, float]:
        w_local  = LOCAL_MAX_WEIGHT  * min(1.0, balls_played / LOCAL_TRUST_BALLS)
        w_global = GLOBAL_MAX_WEIGHT * min(1.0, global_n / GLOBAL_TRUST_SAMPLES)
        w_trans  = TRANS_MAX_WEIGHT  * min(1.0, trans_n / TRANS_TRUST_SAMPLES)
        w_streak = STREAK_MAX_WEIGHT * min(1.0, streak_n / STREAK_TRUST_SAMPLES)
        w_live   = LIVE_TRANS_MAX_WEIGHT * min(1.0, live_n / LIVE_TRANS_TRUST_OBS)
        w_live2  = LIVE2_MAX_WEIGHT  * min(1.0, live2_n / LIVE2_TRUST_OBS)
        w_sit    = SIT_MAX_WEIGHT    * min(1.0, sit_n / SIT_TRUST_SAMPLES)
        if streak_pred is None:
            w_streak = 0.0
            streak_pred = UNIFORM
        if live_pred is None:
            w_live = 0.0
            live_pred = UNIFORM
        if live2_pred is None:
            w_live2 = 0.0
            live2_pred = UNIFORM
        if sit_pred is None:
            w_sit = 0.0
            sit_pred = UNIFORM

        # Streak is a coarser back-off: defer to a sharp transition signal
        # (career or live).
        if w_streak > 0:
            sharpest = max(
                max(transition_pred.values()) if trans_n > 0 else 0.0,
                max(live_pred.values()) if live_n > 0 else 0.0,
                max(live2_pred.values()) if live2_n > 0 else 0.0,
            )
            w_streak *= max(0.0, 1.0 - sharpest)

        # Drift guard: current behavior contradicting the stored profile
        # means the profile is stale — discount it.
        if balls_played >= DRIFT_MIN_BALLS and w_global > 0:
            tv = 0.5 * sum(
                abs(local_freq.get(n, 1 / 7) - global_freq.get(n, 1 / 7))
                for n in range(7)
            )
            drift = max(0.0, min(1.0, (tv - DRIFT_TV_NOISE) / (1.0 - DRIFT_TV_NOISE)))
            w_global *= 1.0 - DRIFT_MAX_DISCOUNT * drift

        total_w = w_local + w_global + w_trans + w_streak + w_live + w_live2 + w_sit
        if total_w < 0.01:
            return dict(UNIFORM)
        w_local  /= total_w
        w_global /= total_w
        w_trans  /= total_w
        w_streak /= total_w
        w_live   /= total_w
        w_live2  /= total_w
        w_sit    /= total_w

        blended = {}
        for n in range(7):
            blended[n] = (
                w_local  * local_freq.get(n, 1 / 7) +
                w_global * global_freq.get(n, 1 / 7) +
                w_trans  * transition_pred.get(n, 1 / 7) +
                w_streak * streak_pred.get(n, 1 / 7) +
                w_live   * live_pred.get(n, 1 / 7) +
                w_live2  * live2_pred.get(n, 1 / 7) +
                w_sit    * sit_pred.get(n, 1 / 7)
            )
        return self._normalize(blended)

    # ── Bowling strategy ──────────────────────────────────────────────────────

    def _bowling_strategy(self, prediction: Dict[int, float], context: Dict, confidence: float, cap: float = PEAK_CAP) -> Dict[int, float]:
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

        # Payout weighting: bowl-side EV ∝ p(n) × (deny value + wicket value).
        # In the endgame any number that would win the match for the batter
        # is a must-stop regardless of run count.
        target = context.get('target')
        runs_to_win = (target - context['current_score']) if target is not None else None
        endgame = runs_to_win is not None and 0 < runs_to_win <= 6

        def _deny(n: int) -> float:
            if endgame and n >= runs_to_win:
                return ENDGAME_DENY
            return float(n)

        s = self._normalize({n: s[n] * (_deny(n) + BOWL_WICKET_VALUE) for n in range(7)})

        pressure = rrr_pressure(context)
        if pressure > 0:
            boost = 1.0 + 0.35 * pressure
            for n in (4, 5, 6):
                s[n] *= boost
            s[0] *= 1.0 + 0.20 * pressure
        elif pressure < 0:
            for n in (4, 5, 6):
                s[n] *= max(0.75, 1.0 + 0.25 * pressure)

        if context['wickets_lost'] >= 7:
            s[0] *= 1.25
            for n in (4, 5, 6):
                s[n] *= 1.10

        return self._floor_and_cap(self._normalize(s), cap)

    # ── Batting strategy ──────────────────────────────────────────────────────

    def _batting_strategy(self, prediction: Dict[int, float], context: Dict, confidence: float, cap: float = PEAK_CAP) -> Dict[int, float]:
        # EV(n) = n × (1 − p(n)) − W × p(n); W scales with wicket scarcity.
        wickets_left = max(1, 10 - context['wickets_lost'])
        balls_left   = max(1, context['balls_left'])
        scarcity     = balls_left / wickets_left
        w_cost = min(BAT_WICKET_COST_MAX,
                     BAT_WICKET_COST_RATE * max(0.0, scarcity - 1.0))

        # Endgame: every number >= runs_to_win wins outright — choose among
        # them purely by "least likely to be matched".
        target = context.get('target')
        runs_to_win = (target - context['current_score']) if target is not None else None
        endgame = runs_to_win is not None and 0 < runs_to_win <= 6

        def _value(n: int) -> float:
            if endgame and n >= runs_to_win:
                return ENDGAME_WIN_EV
            return float(n)

        ev = {
            n: _value(n) * (1.0 - prediction[n]) - w_cost * prediction[n]
            for n in range(7)
        }

        temp   = BAT_TEMP_BASE - BAT_TEMP_CONF_CUT * confidence
        ev_max = max(ev.values())
        s = self._normalize({n: math.exp((ev[n] - ev_max) / temp) for n in range(7)})

        pressure = rrr_pressure(context)
        if pressure > 0:
            boost = 1.0 + 0.45 * pressure
            for n in (4, 5, 6):
                s[n] *= boost
            s[0] *= max(0.55, 1.0 - 0.35 * pressure)
            for n in (1, 2, 3):
                s[n] *= max(0.65, 1.0 - 0.20 * pressure)
        elif pressure < 0:
            for n in (1, 2, 3):
                s[n] *= 1.0 + 0.25 * (-pressure)
            for n in (5, 6):
                s[n] *= max(0.75, 1.0 + 0.25 * pressure)

        return self._floor_and_cap(self._normalize(s), cap)

    # ── Noise ─────────────────────────────────────────────────────────────────

    def _add_noise(self, weights, confidence, cap=PEAK_CAP, earned=0.0, alarm=0.0):
        peak       = max(weights.values()) if weights else 0.0
        base_noise = 0.07 + (0.10 * confidence) + max(0.0, peak - 0.25) * 0.28
        base_noise *= 1.0 - EARNED_NOISE_CUT * earned
        base_noise *= 1.0 + READ_NOISE_BOOST * alarm
        noisy = {}
        for n in range(7):
            noise    = random.uniform(-base_noise, base_noise)
            noisy[n] = max(FLOOR_PROB, weights[n] + noise)
        bluff_prob = 0.08 + max(0.0, peak - 0.28) * 0.14 + READ_BLUFF_BOOST * alarm
        if random.random() < bluff_prob:
            low3      = sorted(noisy.items(), key=lambda x: x[1])[:3]
            bluff_num = low3[random.randint(0, 2)][0]
            noisy[bluff_num] *= 2.5
        return self._floor_and_cap(self._normalize(noisy), cap)

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

    def _cap_peak(self, weights, cap=PEAK_CAP):
        w = dict(weights)
        for _ in range(10):
            if max(w.values()) <= cap + 1e-9:
                break
            excess, capped = 0.0, {}
            for n, v in w.items():
                if v > cap:
                    excess   += v - cap
                    capped[n] = cap
                else:
                    capped[n] = v
            non_capped = [n for n in capped if capped[n] < cap]
            if non_capped:
                share = excess / len(non_capped)
                for n in non_capped:
                    capped[n] += share
            w = capped
        return w

    def _floor_and_cap(self, weights, cap=PEAK_CAP):
        return self._cap_peak(self._apply_floor(weights), cap)

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


# ── v3 engine: RRR hard elimination + 0-wildcard EV + gift-risk discount ──────

class SimEngineV3(SimEngine):
    """
    v2 + three fixes derived from the actual match-resolution rule
    (bat_num == 0 scores whatever the bowler bowled, per innings.py):

      1. Batting: numbers that can no longer keep a chase mathematically
         alive (even with max scoring the rest of the way) are hard-
         eliminated, not just down-weighted. n=0 is exempt since its
         payoff is the bowler's own number, which can still be anything.
      2. Batting: n=0's EV is no longer a flat 0 — it's the expected value
         of the bowler's predicted distribution (the wildcard payoff).
      3. Bowling: bowling a big number while the batter often plays their
         0-wildcard is discounted (that combination gifts them runs for
         free) — a capped multiplicative discount, not a raw subtraction,
         since a raw subtraction can go negative and break normalization.
    """

    def select_move(
        self, db_prior, opponent_history, context, confidence=0.5,
        global_n=0, trans_n=0, transition_pred=None, streak_n=0, streak_pred=None,
    ):
        # Same pipeline as SimEngine.select_move, except the final combine
        # step is banned-aware -- the base version's redundant extra
        # _floor_and_cap call would otherwise hand eliminated numbers their
        # floor probability back right at the last step.
        local_freq = self._build_local_frequency(opponent_history)
        transition_pred = transition_pred or dict(UNIFORM)
        balls_played = len(opponent_history)
        live_pred, live_n = self._build_live_transitions(opponent_history)
        live2_pred, live2_n = self._build_live_transitions2(opponent_history)

        prediction = self._blend_signals(
            local_freq, db_prior, global_n, transition_pred, trans_n, balls_played,
            streak_pred, streak_n, live_pred, live_n, live2_pred, live2_n,
        )

        alarm  = self._read_alarm(context)
        earned = self._earned_accuracy(opponent_history) * (1.0 - alarm)
        cap    = PEAK_CAP + EARNED_CAP_BONUS * earned

        if context['role'] == 'bowling':
            strategic = self._bowling_strategy(prediction, context, confidence, cap)
        else:
            strategic = self._batting_strategy(prediction, context, confidence, cap)

        noisy  = self._add_noise(strategic, confidence, cap, earned, alarm)
        banned = {n for n, w in noisy.items() if w <= 0.0}
        final  = self._floor_and_cap(self._normalize(noisy), cap, banned)
        return self._weighted_choice(final), final

    def _apply_floor(self, weights, banned=frozenset()):
        survivors = [n for n in range(7) if n not in banned] or list(range(7))
        total = sum(weights.get(n, 0.0) for n in survivors)
        if total <= 0:
            even = 1.0 / len(survivors)
            return {n: (even if n in survivors else 0.0) for n in range(7)}
        floor_budget = FLOOR_PROB * len(survivors)
        distr_share  = 1.0 - floor_budget
        return {
            n: (FLOOR_PROB + distr_share * (weights[n] / total)) if n in survivors else 0.0
            for n in range(7)
        }

    def _cap_peak(self, weights, cap=PEAK_CAP, banned=frozenset()):
        w = dict(weights)
        for _ in range(10):
            if max(w.values()) <= cap + 1e-9:
                break
            excess, capped = 0.0, {}
            for n, v in w.items():
                if v > cap:
                    excess   += v - cap
                    capped[n] = cap
                else:
                    capped[n] = v
            non_capped = [n for n in capped if capped[n] < cap and n not in banned]
            if not non_capped:
                break  # cap unsatisfiable with this few survivors -- leave as-is
            share = excess / len(non_capped)
            for n in non_capped:
                capped[n] += share
            w = capped
        for n in banned:
            w[n] = 0.0
        return w

    def _floor_and_cap(self, weights, cap=PEAK_CAP, banned=frozenset()):
        return self._cap_peak(self._apply_floor(weights, banned), cap, banned)

    def _add_noise(self, weights, confidence, cap=PEAK_CAP, earned=0.0, alarm=0.0):
        banned = {n for n, w in weights.items() if w <= 0.0}
        peak       = max(weights.values()) if weights else 0.0
        base_noise = 0.07 + (0.10 * confidence) + max(0.0, peak - 0.25) * 0.28
        base_noise *= 1.0 - EARNED_NOISE_CUT * earned
        base_noise *= 1.0 + READ_NOISE_BOOST * alarm

        noisy = {}
        for n in range(7):
            if n in banned:
                noisy[n] = 0.0
                continue
            noise = random.uniform(-base_noise, base_noise)
            noisy[n] = max(FLOOR_PROB, weights[n] + noise)

        bluff_prob = 0.08 + max(0.0, peak - 0.28) * 0.14 + READ_BLUFF_BOOST * alarm
        if random.random() < bluff_prob:
            candidates = sorted(
                (item for item in noisy.items() if item[0] not in banned),
                key=lambda x: x[1],
            )
            if candidates:
                bluff_num = candidates[random.randint(0, min(2, len(candidates) - 1))][0]
                noisy[bluff_num] *= 2.5

        return self._floor_and_cap(self._normalize(noisy), cap, banned)

    def _bowling_strategy(self, prediction, context, confidence, cap=PEAK_CAP):
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

        target = context.get('target')
        runs_to_win = (target - context['current_score']) if target is not None else None
        endgame = runs_to_win is not None and 0 < runs_to_win <= 6

        def _deny(n: int) -> float:
            if endgame and n >= runs_to_win:
                return ENDGAME_DENY
            return float(n)

        s = self._normalize({n: s[n] * (_deny(n) + BOWL_WICKET_VALUE) for n in range(7)})

        # Gift-risk discount: bowling n while they play 0 hands them n runs
        # for free. Scales with both how often they play 0 and how much n
        # would gift; capped so it can shrink a number but never zero it.
        gift_prob = prediction.get(0, 0.0)
        for n in range(1, 7):
            discount = min(GIFT_RISK_MAX_DISCOUNT, gift_prob * (n / 6.0))
            s[n] *= 1.0 - discount

        pressure = rrr_pressure(context)
        if pressure > 0:
            boost = 1.0 + 0.35 * pressure
            for n in (4, 5, 6):
                s[n] *= boost
            s[0] *= 1.0 + 0.20 * pressure
        elif pressure < 0:
            for n in (4, 5, 6):
                s[n] *= max(0.75, 1.0 + 0.25 * pressure)

        if context['wickets_lost'] >= 7:
            s[0] *= 1.25
            for n in (4, 5, 6):
                s[n] *= 1.10

        return self._floor_and_cap(self._normalize(s), cap)

    def _batting_strategy(self, prediction, context, confidence, cap=PEAK_CAP):
        wickets_left = max(1, 10 - context['wickets_lost'])
        balls_left   = max(1, context['balls_left'])
        scarcity     = balls_left / wickets_left
        w_cost = min(BAT_WICKET_COST_MAX,
                     BAT_WICKET_COST_RATE * max(0.0, scarcity - 1.0))

        target = context.get('target')
        runs_to_win = (target - context['current_score']) if target is not None else None
        endgame = runs_to_win is not None and 0 < runs_to_win <= 6

        # Hard elimination: n in 1..6 that can no longer keep the chase
        # mathematically alive even with max scoring the rest of the way.
        # n=0 is exempt -- its payoff is the bowler's own number.
        chasing = runs_to_win is not None and runs_to_win > 0
        min_viable_n = max(0, runs_to_win - 6 * (balls_left - 1)) if chasing else 0
        banned = {n for n in range(1, 7) if n < min_viable_n}

        def _value(n: int) -> float:
            if endgame and n >= runs_to_win:
                return ENDGAME_WIN_EV
            return float(n)

        ev = {
            n: _value(n) * (1.0 - prediction[n]) - w_cost * prediction[n]
            for n in range(1, 7)
        }
        # Wildcard EV: n=0 inherits the bowler's own number.
        ev[0] = sum(prediction[m] * _value(m) for m in range(1, 7)) - w_cost * prediction[0]

        temp   = BAT_TEMP_BASE - BAT_TEMP_CONF_CUT * confidence
        ev_max = max(ev.values())
        s = self._normalize({n: math.exp((ev[n] - ev_max) / temp) for n in range(7)})

        pressure = rrr_pressure(context)
        if pressure > 0:
            boost = 1.0 + 0.45 * pressure
            for n in (4, 5, 6):
                s[n] *= boost
            s[0] *= max(0.55, 1.0 - 0.35 * pressure)
            for n in (1, 2, 3):
                s[n] *= max(0.65, 1.0 - 0.20 * pressure)
        elif pressure < 0:
            for n in (1, 2, 3):
                s[n] *= 1.0 + 0.25 * (-pressure)
            for n in (5, 6):
                s[n] *= max(0.75, 1.0 + 0.25 * pressure)

        return self._floor_and_cap(self._normalize(s), cap, banned)


# ── Naive engine (no in-game adaptation) ─────────────────────────────────────

class NaiveEngine(SimEngine):
    """
    CPU with no in-game adaptation at all.
    Always picks from the db_prior directly with minimal noise.
    Baseline to show how much the local/global/transition blend adds.
    """

    def select_move(self, db_prior, opponent_history, context, confidence=0.5, **kwargs):
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

    def select_move(self, db_prior, opponent_history, context, confidence=0.5, **kwargs):
        dist = {i: 1.0 / 7 for i in range(7)}
        return random.randint(0, 6), dist
