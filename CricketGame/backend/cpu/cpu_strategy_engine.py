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
import math
import random
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session

from ..data.database import SessionLocal
from .cpu_learning_schema import (
    CPUGlobalPattern, CPUUserProfile, CPUSituationalPattern,
    CPUSequencePattern, CPUStreakPattern, CPULearningProgress, MatchBallLog,
)
from .cpu_learning_utils import get_game_phase, get_score_situation, get_recent_event


# ── Tuning constants ─────────────────────────────────────────────────────────
FLOOR_PROB      = 0.04              # Hard minimum for every number
PEAK_CAP        = 0.45              # Hard maximum for any single number
_FLOOR_BUDGET   = FLOOR_PROB * 7    # 0.28 — reserved for floor allocation
_DISTR_SHARE    = 1.0 - _FLOOR_BUDGET  # 0.72 — proportionally distributed
MAX_CONF        = 0.65              # Confidence cap for short-match safety

UNIFORM = {n: 1.0 / 7 for n in range(7)}

# ── Signal trust scaling (see _blend_signals) ────────────────────────────────
LOCAL_TRUST_BALLS    = 8     # in-match balls for local_freq to reach full trust
GLOBAL_TRUST_SAMPLES = 100   # DB samples for global_freq to reach full trust
TRANS_TRUST_SAMPLES  = 20    # DB samples for transition_pred to reach full trust

LOCAL_MAX_WEIGHT  = 0.50
GLOBAL_MAX_WEIGHT = 0.30
TRANS_MAX_WEIGHT  = 0.45

STREAK_TRUST_SAMPLES = 15    # DB samples for streak_pred to reach full trust
STREAK_MAX_WEIGHT    = 0.40

# Live (in-match) transitions: what followed the opponent's current last
# move earlier in THIS innings. Zero latency and immune to career-data
# dilution — punishes a pattern started this match within a few balls.
LIVE_TRANS_TRUST_OBS  = 4    # in-match observations for full trust
LIVE_TRANS_MAX_WEIGHT = 0.45

# 2-gram live transitions: same idea keyed on the last TWO moves. Catches
# patterns a 1-gram provably can't (when the move after a 4 depends on
# what preceded the 4). Sparse in short innings, so trust ramps fast.
LIVE2_TRUST_OBS  = 4
LIVE2_MIN_OBS    = 2     # a single chance observation is noise, not a pattern
LIVE2_MAX_WEIGHT = 0.50

# Situational patterns (DB): per-player habits in a specific game context
# (phase + chase pressure + recent event, e.g. "just got out"). Human tells
# like tilt or panic live here; a coarse signal, weighted accordingly.
SIT_TRUST_SAMPLES = 12
SIT_MAX_WEIGHT    = 0.25

# ── Endgame win-probability ──────────────────────────────────────────────────
# Near the finish line, runs stop being the objective. Chasing 3: batting
# 3/4/5/6 all win equally, so pick the LEAST-predicted winning number.
# Defending 3: any 3+ the batter sneaks past ends the match, so matching
# those numbers outweighs the runs they deny.
ENDGAME_WIN_EV = 10.0   # batting: EV assigned to any number that wins outright
ENDGAME_DENY   = 10.0   # bowling: deny-value of any number that would lose the match

# ── Being-read defense ───────────────────────────────────────────────────────
# Everything above reads the opponent; this watches whether the opponent is
# reading US. If the CPU's own dismissal rate while batting climbs well above
# chance (1/7 ≈ 0.143), a human has likely decoded its value bias — respond
# by raising entropy (more noise, more bluffs, retract earned sharpness)
# until the bleeding stops. Scripted bots never trigger this.
READ_ALARM_FLOOR = 0.26   # dismissal rate where the alarm starts — well above
                          # what a merely-strong opponent achieves (~0.20), so
                          # it only fires on genuine mind-reading
READ_ALARM_CEIL  = 0.50   # dismissal rate treated as fully read
READ_MIN_BALLS   = 8      # balls faced before the alarm can arm
READ_NOISE_BOOST = 0.5    # max extra noise at full alarm
READ_BLUFF_BOOST = 0.10   # extra bluff probability at full alarm

# ── Bowling payout weighting ─────────────────────────────────────────────────
# Matching the batter's number takes a wicket AND denies those runs, so
# matching their 6 is worth (6 + wicket) while matching their 0 is worth
# only the wicket. Bowl-side EV ∝ p(n) × (n + BOWL_WICKET_VALUE).
BOWL_WICKET_VALUE = 5.0

# ── Gift-risk discount (0-wildcard exposure) ─────────────────────────────────
# Per innings.py's resolve_ball, bat_move == 0 scores whatever the bowler
# bowled. So bowling a big number while this batter often plays their
# 0-wildcard is a free-runs risk the payout above doesn't see. Discount big
# numbers proportionally to how often they play 0 and how much bowling n
# would gift if they do -- capped well short of zeroing a number out, since
# a straight subtraction can go negative and break normalization downstream.
GIFT_RISK_MAX_DISCOUNT = 0.5

# ── Batting expected value (see _batting_strategy) ───────────────────────────
# EV(n) = n × (1 − p(n)) − W × p(n).  W is the run cost of the CPU's own
# wicket, scaled by scarcity: when remaining wickets outnumber remaining
# balls a wicket costs almost nothing (short formats), but it climbs
# steeply once the tail is exposed.
BAT_WICKET_COST_RATE = 2.0   # cost per unit of scarcity above parity
BAT_WICKET_COST_MAX  = 8.0   # ceiling on the wicket cost
BAT_TEMP_BASE        = 1.5   # softmax temperature at zero confidence
BAT_TEMP_CONF_CUT    = 0.6   # temperature reduction at full confidence

# ── Profile drift guard ──────────────────────────────────────────────────────
# Humans evolve: after getting beaten they change style, which makes their
# stored profile stale — worse than useless, since the CPU would keep
# countering habits the player no longer has. When this match's observed
# behavior (local_freq) diverges sharply from the stored profile
# (global_freq), profile trust is cut for the rest of the match and the
# CPU leans on what it sees NOW.
DRIFT_MIN_BALLS    = 6     # local sample needed before judging drift
DRIFT_TV_NOISE     = 0.40  # total-variation distance expected from sampling noise alone
DRIFT_MAX_DISCOUNT = 0.75  # stored-profile trust can be cut by up to 75%

# ── Earned sharpness ─────────────────────────────────────────────────────────
# When the opponent's recent moves keep landing inside our top-3 prediction,
# they have EARNED a sharper response: peak cap rises and noise drops.
# A baiter defeats predictions by definition, which zeroes this out — so the
# extra commitment only unlocks against genuinely predictable play.
EARNED_CAP_BONUS = 0.15   # peak cap may rise from 0.45 up to 0.60
EARNED_NOISE_CUT = 0.50   # up to 50% noise reduction
_TOP3_CHANCE     = 3.0 / 7.0  # top-3 hit rate of a uniform-random opponent

# ── Required run-rate awareness ──────────────────────────────────────────────
RRR_NEUTRAL = 6.0   # runs/over treated as "par" — no pressure either way
RRR_MAX     = 15.0  # runs/over treated as maximum realistic pressure


def compute_required_run_rate(context: Dict) -> float:
    """
    Runs-per-over the chasing side needs from this point on.
    Returns 0.0 when batting first (no target) or when the chase is already won.
    """
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
    """
    Signed pressure derived from the required run rate, roughly in [-0.7, 1.6].
      > 0  chasing side needs to accelerate relative to a par rate
      < 0  chasing side is comfortably ahead of the required rate
      = 0  batting first (no target exists yet)
    Wickets lost sharpen positive pressure: the same required rate is harder
    to chase safely with fewer wickets in hand.
    """
    rrr = compute_required_run_rate(context)
    if rrr <= 0.0:
        return 0.0
    pressure = (rrr - RRR_NEUTRAL) / (RRR_MAX - RRR_NEUTRAL)
    if pressure > 0:
        wickets_lost = context.get('wickets_lost', 0)
        pressure *= 1.0 + min(wickets_lost, 8) * 0.06  # up to +48% at 8 down
    return max(-0.7, min(1.6, pressure))


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

            # ── Signal 4: Streak prediction (N same-class balls -> ?) ─────
            streak_pred, streak_n = self._load_streak_patterns(
                db, user_id, match_context, opponent_history
            )

            # ── Signal 5: Live in-match transitions (zero latency) ────────
            live_pred, live_n = self._build_live_transitions(opponent_history)

            # ── Signal 6: 2-gram live transitions (last TWO moves -> ?) ───
            live2_pred, live2_n = self._build_live_transitions2(opponent_history)

            # ── Signal 7: Situational habits (phase/pressure/event) ───────
            sit_pred, sit_n = self._load_situational_patterns(db, user_id, match_context)

            # ── Confidence from learning phase ────────────────────────────
            total_balls = self._get_total_balls_tracked(db, user_id)
            phase_info  = get_learning_phase(total_balls)
            confidence  = min(phase_info['confidence'], MAX_CONF)

            # ── Blend the signals ─────────────────────────────────────────
            balls_played = len(opponent_history)
            prediction = self._blend_signals(
                local_freq, global_freq, global_n,
                transition_pred, trans_n, balls_played,
                streak_pred, streak_n,
                live_pred, live_n,
                live2_pred, live2_n,
                sit_pred, sit_n,
            )

            # ── Earned sharpness, tempered by the being-read alarm ────────
            alarm  = self._read_alarm(match_context)
            earned = self._earned_accuracy(opponent_history) * (1.0 - alarm)
            cap    = PEAK_CAP + EARNED_CAP_BONUS * earned

            # ── Role-specific strategy ────────────────────────────────────
            if match_context['role'] == 'bowling':
                strategic = self._bowling_strategy(prediction, match_context, confidence, cap)
            else:
                strategic = self._batting_strategy(prediction, match_context, confidence, cap)

            # ── Noise + choose ────────────────────────────────────────────
            noisy = self._add_noise(strategic, confidence, cap, earned, alarm)
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

    def _build_live_transitions(self, history: List[int]) -> Tuple[Dict[int, float], int]:
        """
        In-match transition signal: what has followed the opponent's CURRENT
        last move earlier in this innings? Complements the DB transition
        table — a habit started this match dominates here immediately
        instead of being EMA-diluted into career data.
        """
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
        """
        2-gram in-match transitions: what has followed the opponent's
        current last TWO moves earlier this innings? Finer-grained than the
        1-gram — catches conditional patterns like '4 then 5 -> always 6'.
        """
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

    # ── Being-read defense ────────────────────────────────────────────────────

    def _read_alarm(self, context: Dict) -> float:
        """
        0.0-1.0 alarm that the OPPONENT is successfully predicting the CPU.

        Only meaningful when the CPU is batting: its own dismissal rate this
        innings sitting well above chance (1/7) means the bowler keeps
        matching its numbers. Bots and non-reading humans leave this at ~0.
        """
        if context['role'] != 'batting':
            return 0.0
        balls_faced = context['total_overs'] * 6 - context['balls_left']
        if balls_faced < READ_MIN_BALLS:
            return 0.0
        rate = context['wickets_lost'] / balls_faced
        return max(0.0, min(1.0, (rate - READ_ALARM_FLOOR) / (READ_ALARM_CEIL - READ_ALARM_FLOOR)))

    # ── Earned sharpness ──────────────────────────────────────────────────────

    def _earned_accuracy(self, history: List[int]) -> float:
        """
        Measure how predictable the opponent has been THIS match.

        Replays the match: for each ball i, build a simple prediction from
        the balls before it (local frequency + in-match 1-gram transitions)
        and score a hit when the actual move landed in the top-3. Returns
        0.0-1.0 scaled above chance level (a uniform-random opponent scores
        ~3/7 on top-3, which maps to 0.0).

        A frequency-baiter defeats this automatically: their switch balls
        miss the prediction, dragging accuracy back toward chance.
        """
        if len(history) < 5:
            return 0.0

        hits = checks = 0
        for i in range(3, len(history)):
            prior = history[:i]
            scores = {n: 0.0 for n in range(7)}
            for m in prior:
                scores[m] += 1.0
            # In-match transitions from the current previous move,
            # weighted heavier than raw frequency.
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
        self,
        local_freq: Dict[int, float],
        global_freq: Dict[int, float],
        global_n: int,
        transition_pred: Dict[int, float],
        trans_n: int,
        balls_played: int,
        streak_pred: Dict[int, float] = None,
        streak_n: int = 0,
        live_pred: Dict[int, float] = None,
        live_n: int = 0,
        live2_pred: Dict[int, float] = None,
        live2_n: int = 0,
        sit_pred: Dict[int, float] = None,
        sit_n: int = 0,
    ) -> Dict[int, float]:
        """
        Blend local frequency, global profile, transition prediction, and
        streak prediction.

        Each signal's weight scales with its OWN evidence rather than a
        shared match-length clock. local_freq resets every innings, so it
        genuinely has nothing useful to say on ball 0 -- its weight ramps
        with balls_played. The DB signals (global/transition/streak)
        represent this player's whole history against the CPU; a pattern
        confirmed thousands of times is just as trustworthy on ball 1 of a
        new match as ball 10, so their weight ramps with their own sample
        counts instead.
        """
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

        # The streak signal is a coarser back-off model: when an
        # exact-number transition signal (career or live) is sharp,
        # class-level streak data adds dilution, not information —
        # let the finer model win.
        if w_streak > 0:
            sharpest = max(
                max(transition_pred.values()) if trans_n > 0 else 0.0,
                max(live_pred.values()) if live_n > 0 else 0.0,
                max(live2_pred.values()) if live2_n > 0 else 0.0,
            )
            w_streak *= max(0.0, 1.0 - sharpest)

        # Drift guard: if this match's behavior contradicts the stored
        # profile, the profile is stale (the player evolved) — discount it.
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

        # Weighted blend
        blended = {}
        for n in range(7):
            blended[n] = (
                w_local  * local_freq.get(n, 1/7) +
                w_global * global_freq.get(n, 1/7) +
                w_trans  * transition_pred.get(n, 1/7) +
                w_streak * streak_pred.get(n, 1/7) +
                w_live   * live_pred.get(n, 1/7) +
                w_live2  * live2_pred.get(n, 1/7) +
                w_sit    * sit_pred.get(n, 1/7)
            )

        return self._normalize(blended)

    # ── Bowling strategy ──────────────────────────────────────────────────────

    def _bowling_strategy(
        self,
        prediction: Dict[int, float],
        context: Dict,
        confidence: float,
        cap: float = PEAK_CAP,
    ) -> Dict[int, float]:
        """
        CPU is BOWLING — wants to match batter's number (-> wicket).

        Uses the blended prediction directly: numbers the batter is
        likely to play get higher weight, then payout-weighted — matching
        their 6 takes the wicket AND denies six runs, matching their 0
        only takes the wicket. Situational pressure is a lightweight
        modifier on top.
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

        # Payout weighting: bowl-side EV ∝ p(n) × (deny value + wicket value).
        # Deny value is normally the runs (denying their 6 matters more than
        # their 1) — but in the endgame, any number that would win the match
        # for the batter is a must-stop regardless of its run count.
        target = context.get('target')
        runs_to_win = (target - context['current_score']) if target is not None else None
        endgame = runs_to_win is not None and 0 < runs_to_win <= 6

        def _deny(n: int) -> float:
            if endgame and n >= runs_to_win:
                return ENDGAME_DENY
            return float(n)

        s = self._normalize({n: s[n] * (_deny(n) + BOWL_WICKET_VALUE) for n in range(7)})

        # ── Gift-risk discount ──────────────────────────────────────────────
        # Bowling n while the batter plays 0 hands them n runs for free.
        # Discount scales with both how often they play 0 and how much n
        # would gift, so a 6 is discounted harder than a 1 for the same
        # 0-habit, and a batter who never plays 0 sees no change at all.
        gift_prob = prediction.get(0, 0.0)
        for n in range(1, 7):
            discount = min(GIFT_RISK_MAX_DISCOUNT, gift_prob * (n / 6.0))
            s[n] *= 1.0 - discount

        # ── Required run-rate awareness ────────────────────────────────────
        # CPU bowling while defending a target: the higher the batter's
        # required rate, the more likely they gamble on boundaries.
        pressure = rrr_pressure(context)
        if pressure > 0:
            boost = 1.0 + 0.35 * pressure
            for n in (4, 5, 6):
                s[n] *= boost
            s[0] *= 1.0 + 0.20 * pressure  # mistimed big shots -> more dots/wickets too
        elif pressure < 0:
            # Batter is comfortably ahead of the rate -> plays safe
            for n in (4, 5, 6):
                s[n] *= max(0.75, 1.0 + 0.25 * pressure)

        # Near all-out, batters play conservatively regardless of chase state
        if context['wickets_lost'] >= 7:
            s[0] *= 1.25
            for n in (4, 5, 6):
                s[n] *= 1.10

        return self._floor_and_cap(self._normalize(s), cap)

    # ── Batting strategy ──────────────────────────────────────────────────────

    def _batting_strategy(
        self,
        prediction: Dict[int, float],
        context: Dict,
        confidence: float,
        cap: float = PEAK_CAP,
    ) -> Dict[int, float]:
        """
        CPU is BATTING — maximize expected runs, not just survival.

        EV(n) = n × (1 − p(n)) − W × p(n)  for n = 1..6
          p(n): blended probability the bowler bowls n
          W:    scarcity-scaled cost of the CPU's own wicket — near zero
                while wickets outnumber the balls left (dodging into cheap
                singles wastes runs there), climbing steeply once losing
                a wicket could actually end the innings early.

        n = 0 is a WILDCARD, not "score zero": per the match rules
        (innings.py resolve_ball), bat_move == 0 scores whatever the
        bowler bowled (unless the bowler also bowled 0, which is a
        wicket like any other match). Its EV is therefore the expected
        value of the bowler's own distribution, not a flat 0.

        Weights are a softmax over EV (sharper with confidence), so a
        heavily-predicted 6 still loses to a safe 5, but a merely-average
        risk on a boundary beats a guaranteed single.
        """
        # Scarcity-scaled wicket cost
        wickets_left = max(1, 10 - context['wickets_lost'])
        balls_left   = max(1, context['balls_left'])
        scarcity     = balls_left / wickets_left
        w_cost = min(BAT_WICKET_COST_MAX,
                     BAT_WICKET_COST_RATE * max(0.0, scarcity - 1.0))

        # Endgame: chasing few runs, every number >= runs_to_win wins the
        # match outright — their run counts stop mattering, so the choice
        # among them should be purely "which is least likely to be matched".
        target = context.get('target')
        runs_to_win = (target - context['current_score']) if target is not None else None
        endgame = runs_to_win is not None and 0 < runs_to_win <= 6

        # Hard elimination: numbers that can no longer keep the chase alive
        # even with max (6) scoring on every remaining ball. Only applies to
        # n = 1..6 — 0's payoff is the bowler's own number, which can land
        # anywhere, so it can never be ruled out the same way.
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
        # Wildcard EV: sum over what the bowler actually bowls (m=1..6),
        # weighted by that same _value so endgame win-EV still applies.
        ev[0] = sum(prediction[m] * _value(m) for m in range(1, 7)) - w_cost * prediction[0]

        # Softmax over EV; higher confidence -> sharper commitment
        temp  = BAT_TEMP_BASE - BAT_TEMP_CONF_CUT * confidence
        ev_max = max(ev.values())
        s = self._normalize({n: math.exp((ev[n] - ev_max) / temp) for n in range(7)})

        # ── Required run-rate awareness ────────────────────────────────────
        # CPU batting while chasing: the higher the ask, the more it must
        # gamble on boundaries; comfortably ahead -> bat to keep wickets in hand.
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

        # (No separate near-all-out guard: the scarcity-scaled wicket cost
        # in the EV term already makes the CPU protective when the tail
        # is exposed.)

        return self._floor_and_cap(self._normalize(s), cap, banned)

    # ── Noise ─────────────────────────────────────────────────────────────────

    def _add_noise(
        self,
        weights: Dict[int, float],
        confidence: float,
        cap: float = PEAK_CAP,
        earned: float = 0.0,
        alarm: float = 0.0,
    ) -> Dict[int, float]:
        """
        Add controlled randomness to prevent full predictability.

        Base noise scales with confidence (higher confidence = more noise to
        compensate), shrinks by up to EARNED_NOISE_CUT when the opponent has
        proven predictable (see _earned_accuracy), and GROWS by up to
        READ_NOISE_BOOST when the being-read alarm fires — an opponent who
        keeps matching the CPU's numbers gets served extra entropy.
        Bluff: ~8% chance to boost a low-probability number, raised further
        under alarm.

        A weight of exactly 0 only ever comes from _batting_strategy's hard
        elimination (mathematically-dead chase numbers) — noise, floor, and
        bluff all leave those at 0 rather than reviving them.
        """
        banned = {n for n, w in weights.items() if w <= 0.0}
        peak = max(weights.values()) if weights else 0.0
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

    # ── Math helpers ──────────────────────────────────────────────────────────

    def _normalize(self, weights: Dict[int, float]) -> Dict[int, float]:
        total = sum(weights.values())
        if total > 0:
            return {k: v / total for k, v in weights.items()}
        return {i: 1.0 / 7 for i in range(7)}

    def _apply_floor(
        self, weights: Dict[int, float], banned: set = frozenset()
    ) -> Dict[int, float]:
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

    def _cap_peak(
        self, weights: Dict[int, float], cap: float = PEAK_CAP, banned: set = frozenset()
    ) -> Dict[int, float]:
        """
        Iteratively cap any value exceeding `cap`, distributing excess
        uniformly across non-capped, non-banned numbers.
        """
        w = dict(weights)
        for _ in range(10):
            if max(w.values()) <= cap + 1e-9:
                break
            excess  = 0.0
            capped  = {}
            for n, v in w.items():
                if v > cap:
                    excess   += v - cap
                    capped[n] = cap
                else:
                    capped[n] = v
            non_capped = [n for n in capped if capped[n] < cap and n not in banned]
            if not non_capped:
                # No eligible receiver for the excess (heavy banning can leave
                # only 1-2 survivors, where cap * survivors < 1 makes the cap
                # unsatisfiable). Keeping banned entries at 0 wins over
                # enforcing the cap here, so stop and leave values as-is.
                break
            share = excess / len(non_capped)
            for n in non_capped:
                capped[n] += share
            w = capped
        for n in banned:
            w[n] = 0.0
        return w

    def _floor_and_cap(
        self, weights: Dict[int, float], cap: float = PEAK_CAP, banned: set = frozenset()
    ) -> Dict[int, float]:
        return self._cap_peak(self._apply_floor(weights, banned), cap, banned)

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

        # Use the ACTUAL result of the last ball when available — players
        # behave differently after a wicket or a dot than after scoring.
        # Fall back to the (most common) 'scored' row when the specific
        # result row is too thin.
        last_result = 'scored'
        last_3 = context.get('last_3_results') or []
        if last_3:
            lr = last_3[-1]
            if lr.get('is_out'):
                last_result = 'out'
            elif lr.get('runs', 0) == 0:
                last_result = 'dot'

        for result_key in ([last_result, 'scored'] if last_result != 'scored'
                           else ['scored']):
            pattern = db.query(CPUSequencePattern).filter(
                CPUSequencePattern.user_id         == user_id,
                CPUSequencePattern.match_format    == context['match_format'],
                CPUSequencePattern.role            == opponent_role,
                CPUSequencePattern.previous_move   == last_move,
                CPUSequencePattern.previous_result == result_key,
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

    def _load_situational_patterns(
        self, db: Session, user_id: int, context: Dict
    ) -> Tuple[Dict[int, float], int]:
        """
        Situational habits: what this player does in the CURRENT game
        situation (phase + chase pressure + recent event). Coarse but
        captures human tells — tilt after a wicket, panic at a high ask.
        """
        if user_id == -1:
            return {i: 1.0 / 7 for i in range(7)}, 0
        game_phase = get_game_phase(context['current_over'], context['total_overs'])
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
            CPUSituationalPattern.user_id        == user_id,
            CPUSituationalPattern.match_format   == context['match_format'],
            CPUSituationalPattern.game_phase     == game_phase,
            CPUSituationalPattern.role           == opponent_role,
            CPUSituationalPattern.score_pressure == score_pressure,
            CPUSituationalPattern.recent_event   == recent_event,
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

    def _load_streak_patterns(
        self, db: Session, user_id: int, context: Dict, opponent_history: List[int]
    ) -> Tuple[Dict[int, float], int]:
        """
        Streak signal: after N consecutive same-class balls (H/L/Z), what
        does this player do next? Disambiguates multi-ball habits like
        'three highs then escape with 0' that the 1-ball transition table
        averages into noise.
        """
        if user_id == -1 or not opponent_history:
            return {i: 1.0 / 7 for i in range(7)}, 0

        def _cls(n: int) -> str:
            if n == 0:
                return 'Z'
            return 'H' if n >= 4 else 'L'

        streak_class = _cls(opponent_history[-1])
        streak_len = 0
        for m in reversed(opponent_history):
            if _cls(m) == streak_class:
                streak_len += 1
            else:
                break
        streak_len = min(streak_len, 4)

        opponent_role = 'batting' if context['role'] == 'bowling' else 'bowling'
        pattern = db.query(CPUStreakPattern).filter(
            CPUStreakPattern.user_id      == user_id,
            CPUStreakPattern.match_format == context['match_format'],
            CPUStreakPattern.role         == opponent_role,
            CPUStreakPattern.streak_class == streak_class,
            CPUStreakPattern.streak_len   == streak_len,
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
