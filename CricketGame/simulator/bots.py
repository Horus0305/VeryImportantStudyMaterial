"""
Scripted attacker bots representing known human exploitation strategies.

Each bot is a self-contained player with a pick() method:
    pick(my_history, context) → int (0-6)

where:
    my_history  — list of numbers this bot has played so far this innings
    context     — dict with balls_left, score, wickets, target, total_balls
"""
import random
from typing import List, Dict


class Bot:
    @property
    def name(self) -> str:
        return self.__class__.__name__

    def pick(self, my_history: List[int], context: Dict) -> int:
        raise NotImplementedError

    def reset(self):
        """Called between matches. Override if the bot is stateful."""
        pass


# ── Exploitation bots ─────────────────────────────────────────────────────────

class FreqBaiter(Bot):
    """
    Spam one number for N balls to inflate its CPU probability,
    then switch hard to opposite class.
    Exploits frequency-tracking CPUs.
    """
    def __init__(self, spam_num: int = 1, switch_to: List[int] = None, cycle: int = 8):
        self.spam_num  = spam_num
        self.switch_to = switch_to or [4, 5, 6]
        self.cycle     = cycle

    @property
    def name(self) -> str:
        switch_label = 'high' if self.switch_to[0] >= 4 else 'low'
        return f"FreqBaiter  (spam {self.spam_num} -> {switch_label})"

    def pick(self, my_history, context):
        phase = len(my_history) % self.cycle
        if phase < self.cycle // 2:
            return self.spam_num
        return random.choice(self.switch_to)


class HEscaper(Bot):
    """
    Play high (4/5/6) for 3 balls then escape with 0.
    Exploits CPUs that raise high probability after an H-streak.
    """
    @property
    def name(self) -> str:
        return "H->0 Escaper  (x3 high, then 0)"

    def pick(self, my_history, context):
        if len(my_history) % 4 < 3:
            return random.choice([4, 5, 6])
        return 0


class HShuffler(Bot):
    """
    Rotate 4 → 5 → 6 → 4 → 5 → 6 indefinitely.
    Never leaves the H class. Tests whether the CPU can stay with high
    numbers without being tricked into predicting a class switch.
    """
    @property
    def name(self) -> str:
        return "H Shuffler   (4->5->6 loop)"

    def pick(self, my_history, context):
        return [4, 5, 6][len(my_history) % 3]


class HLAlternator(Bot):
    """
    Strict ball-by-ball alternation: H, L, H, L, …
    Generates a perfectly predictable class-transition pattern.
    """
    @property
    def name(self) -> str:
        return "H<>L Alt.    (strict alternation)"

    def pick(self, my_history, context):
        if len(my_history) % 2 == 0:
            return random.choice([4, 5, 6])
        return random.choice([1, 2, 3])


class StreakMaker(Bot):
    """
    Build a long H-streak (N balls), then abruptly switch to L for N balls.
    Tests streak guard effectiveness — CPU should predict the switch.
    """
    def __init__(self, streak_len: int = 5):
        self.streak_len = streak_len

    @property
    def name(self) -> str:
        return f"StreakMaker   (Hx{self.streak_len} -> Lx{self.streak_len})"

    def pick(self, my_history, context):
        phase = len(my_history) % (self.streak_len * 2)
        if phase < self.streak_len:
            return random.choice([4, 5, 6])
        return random.choice([1, 2, 3])


class PressureReversal(Bot):
    """
    Conservative (1/2/3) when time is plentiful; all-in (5/6) in the
    final 4 balls. Tests situational pressure awareness.
    """
    @property
    def name(self) -> str:
        return "PressureRev. (safe early, big late)"

    def pick(self, my_history, context):
        if context.get('balls_left', 12) > 4:
            return random.choice([1, 2, 3])
        return random.choice([5, 6])


class MetaGamer(Bot):
    """
    Always plays the OPPOSITE class of their own last move.
    'I know you'll predict my last class, so I'll switch every ball.'
    Tests how the CPU handles perfect single-step meta-reasoning.
    """
    @property
    def name(self) -> str:
        return "MetaGamer    (always switch own class)"

    def pick(self, my_history, context):
        if not my_history:
            return random.choice([4, 5, 6])
        last = my_history[-1]
        if last >= 4:
            return random.choice([0, 1, 2, 3])
        return random.choice([4, 5, 6])


# ── Baseline bot ──────────────────────────────────────────────────────────────

class PureRandom(Bot):
    """
    Uniform random every ball — the Nash equilibrium strategy.
    Theoretically unexploitable. Any CPU doing worse than Uniform vs this
    has a bug; any CPU doing better has found a real human bias.
    Expected wicket rate against any CPU: 1/7 ≈ 14.3%.
    """
    @property
    def name(self) -> str:
        return "PureRandom   (Nash baseline)"

    def pick(self, my_history, context):
        return random.randint(0, 6)


# ── Full suite ────────────────────────────────────────────────────────────────

ALL_BOTS: List[Bot] = [
    FreqBaiter(spam_num=1, switch_to=[4, 5, 6]),   # spam low → switch high
    FreqBaiter(spam_num=6, switch_to=[0, 1, 2]),   # spam high → switch low/zero
    HEscaper(),
    HShuffler(),
    HLAlternator(),
    StreakMaker(streak_len=5),
    PressureReversal(),
    MetaGamer(),
    PureRandom(),
]
