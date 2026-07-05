"""
Career benchmark — simulates a SERIES of matches against the same opponent,
persisting the DB-backed signals (per-user profile, sequence transitions)
across matches exactly as production does.

The one-shot benchmark.py deliberately starts every match cold (global_n=0,
trans_n=0) to isolate in-match adaptation. That understates real performance
against a *repeat* opponent, since CPUUserProfile and CPUSequencePattern
persist per-user across a player's whole history with the CPU. This script
answers "how good does the CPU get once it has actually played this person
before" by carrying that memory forward match-to-match.

Usage (from CricketGame/ directory):
    python -m simulator.career_sim
    python -m simulator.career_sim --matches 3000 --overs 2 --batch 300
"""
import argparse
import random
from typing import Dict, List, Tuple

from .engine_sim import SimEngine, NaiveEngine, UniformEngine, BASE_WEIGHTS
from .bots import ALL_BOTS, Bot

MAX_SAMPLES_USER = 250          # matches MAX_SAMPLES_USER in cpu_learning_utils.py
MAX_SAMPLES_SEQ  = 120          # matches MAX_SAMPLES_SITUATIONAL in cpu_learning_utils.py
UNIFORM = {n: 1.0 / 7 for n in range(7)}


def get_learning_phase(total_balls: int) -> float:
    """Confidence value only — mirrors cpu_strategy_engine.get_learning_phase."""
    if total_balls < 60:
        return min(total_balls / 60.0, 0.3)
    elif total_balls < 300:
        progress = (total_balls - 60) / 240.0
        return 0.3 + (0.5 * progress)
    else:
        excess = total_balls - 300
        return min(0.8 + excess / 1000.0, 0.95)


def _ema(freqs: List[float], observed: int, n: int, max_samples: int) -> Tuple[List[float], int]:
    alpha = 1.0 / min(n + 1, max_samples)
    new = list(freqs)
    for i in range(7):
        new[i] = freqs[i] * (1 - alpha) + (alpha if i == observed else 0.0)
    tot = sum(new)
    return [x / tot for x in new], n + 1


def _cls(n: int) -> str:
    """Classify a move: H (4-6), L (1-3), Z (0)."""
    if n == 0:
        return 'Z'
    return 'H' if n >= 4 else 'L'


def current_streak(history: List[int]) -> Tuple[str, int]:
    """(streak_class, capped_length) of the streak ending at the last move."""
    if not history:
        return '', 0
    sc = _cls(history[-1])
    sl = 0
    for m in reversed(history):
        if _cls(m) == sc:
            sl += 1
        else:
            break
    return sc, min(sl, 4)


class OpponentMemory:
    """
    Stand-in for a real player's persisted CPUUserProfile + CPUSequencePattern
    rows. One instance = one bot's entire career against the CPU.
    """

    def __init__(self):
        self.total_balls = 0
        self.bat_freq: List[float] = [1 / 7] * 7
        self.bat_n = 0
        self.bowl_freq: List[float] = [1 / 7] * 7
        self.bowl_n = 0
        # role -> {previous_move: (freqs, count)}
        self.trans: Dict[str, Dict[int, Tuple[List[float], int]]] = {'batting': {}, 'bowling': {}}
        # role -> {(streak_class, streak_len): (freqs, count)}
        self.streaks: Dict[str, Dict[Tuple[str, int], Tuple[List[float], int]]] = {'batting': {}, 'bowling': {}}

    def confidence(self) -> float:
        return get_learning_phase(self.total_balls)

    def global_signal(self, opponent_role: str) -> Tuple[Dict[int, float], int]:
        """opponent_role = the human's role this innings ('batting' or 'bowling')."""
        freqs, n = (self.bat_freq, self.bat_n) if opponent_role == 'batting' else (self.bowl_freq, self.bowl_n)
        if n < 10:
            return dict(UNIFORM), 0
        return {i: freqs[i] for i in range(7)}, n

    def transition_signal(self, opponent_role: str, prev_move) -> Tuple[Dict[int, float], int]:
        if prev_move is None:
            return dict(UNIFORM), 0
        entry = self.trans[opponent_role].get(prev_move)
        if not entry or entry[1] <= 3:
            return dict(UNIFORM), 0
        freqs, n = entry
        return {i: freqs[i] for i in range(7)}, n

    def streak_signal(self, opponent_role: str, streak_class: str, streak_len: int) -> Tuple[Dict[int, float], int]:
        entry = self.streaks[opponent_role].get((streak_class, streak_len))
        if not entry or entry[1] <= 3:
            return dict(UNIFORM), 0
        freqs, n = entry
        return {i: freqs[i] for i in range(7)}, n

    def record(self, opponent_role: str, prev_move, move: int, was_scored: bool,
               streak: Tuple[str, int] = ('', 0)) -> None:
        self.total_balls += 1
        if opponent_role == 'batting':
            self.bat_freq, self.bat_n = _ema(self.bat_freq, move, self.bat_n, MAX_SAMPLES_USER)
        else:
            self.bowl_freq, self.bowl_n = _ema(self.bowl_freq, move, self.bowl_n, MAX_SAMPLES_USER)
        if prev_move is not None and was_scored:
            freqs, n = self.trans[opponent_role].get(prev_move, ([1 / 7] * 7, 0))
            self.trans[opponent_role][prev_move] = _ema(freqs, move, n, MAX_SAMPLES_SEQ)
        if streak[1] > 0:
            freqs, n = self.streaks[opponent_role].get(streak, ([1 / 7] * 7, 0))
            self.streaks[opponent_role][streak] = _ema(freqs, move, n, MAX_SAMPLES_SEQ)


def play_innings(engine, cpu_role: str, bot: Bot, memory: OpponentMemory, total_overs: int) -> Dict:
    total_balls = total_overs * 6
    score = wickets = 0
    bot_history: List[int] = []
    cpu_dists: List[Dict] = []
    opponent_role = 'batting' if cpu_role == 'bowling' else 'bowling'
    confidence = memory.confidence()

    for ball_num in range(total_balls):
        ctx = {
            'role': cpu_role, 'batting_first': True, 'current_score': score,
            'wickets_lost': wickets, 'balls_left': total_balls - ball_num,
            'current_over': ball_num // 6, 'total_overs': total_overs,
            'match_format': f'{total_overs}over', 'target': None, 'last_3_results': [],
        }
        prev_move = bot_history[-1] if bot_history else None
        streak = current_streak(bot_history)
        global_freq, global_n = memory.global_signal(opponent_role)
        trans_pred, trans_n   = memory.transition_signal(opponent_role, prev_move)
        streak_pred, streak_n = memory.streak_signal(opponent_role, *streak) if streak[1] else (None, 0)

        cpu_num, dist = engine.select_move(
            global_freq, bot_history, ctx, confidence,
            global_n=global_n, trans_n=trans_n, transition_pred=trans_pred,
            streak_n=streak_n, streak_pred=streak_pred,
        )
        bot_ctx = {'balls_left': total_balls - ball_num, 'score': score,
                   'wickets': wickets, 'target': None, 'total_balls': total_balls}
        bot_num = bot.pick(bot_history, bot_ctx)
        cpu_dists.append(dist)

        bat_num, bowl_num = (bot_num, cpu_num) if cpu_role == 'bowling' else (cpu_num, bot_num)
        was_out = bat_num == bowl_num
        if was_out:
            wickets += 1
        else:
            score += bat_num

        memory.record(opponent_role, prev_move, bot_num,
                      was_scored=(not was_out and bot_num != 0), streak=streak)
        bot_history.append(bot_num)
        if wickets >= 10:
            break

    return {'score': score, 'wickets': wickets, 'balls': len(bot_history), 'cpu_dists': cpu_dists}


def play_match(engine, bot: Bot, memory: OpponentMemory, total_overs: int) -> Dict:
    cpu_bats_first = random.random() < 0.5
    if cpu_bats_first:
        inn1 = play_innings(engine, 'batting', bot, memory, total_overs)
        inn2 = play_innings(engine, 'bowling', bot, memory, total_overs)
        cpu_won = inn2['score'] <= inn1['score']
        return {'cpu_bat_inn': inn1, 'bot_bat_inn': inn2, 'cpu_won': cpu_won}
    else:
        inn1 = play_innings(engine, 'bowling', bot, memory, total_overs)
        inn2 = play_innings(engine, 'batting', bot, memory, total_overs)
        cpu_won = inn2['score'] > inn1['score']
        return {'cpu_bat_inn': inn2, 'bot_bat_inn': inn1, 'cpu_won': cpu_won}


def run_career_benchmark(n_matches: int, total_overs: int, batch: int, seed: int) -> None:
    random.seed(seed)
    engines = [
        ("CPU Uniform  (Nash baseline)",  UniformEngine()),
        ("CPU Naive    (no adaptation)",  NaiveEngine()),
        ("CPU V2       (freq blend+RRR)", SimEngine()),
    ]

    n_buckets = max(1, n_matches // batch)
    col_bot, col_metric = 36, 9
    sep = "=" * (col_bot + col_metric * n_buckets + 4)

    print(f"\n{sep}")
    print(f"  CPU CAREER BENCHMARK — {n_matches} sequential matches × {total_overs}-over "
          f"(seed={seed}, memory persists across matches)")
    print(f"  Columns show Win% in successive batches of {batch} matches — rising = CPU is learning the opponent")
    print(sep)

    for engine_name, engine in engines:
        print(f"\n  -- {engine_name} --")
        header = f"  {'Bot':<{col_bot}}" + "".join(f"{'M'+str((i+1)*batch):>{col_metric}}" for i in range(n_buckets))
        print(header)
        print("  " + "-" * (col_bot + col_metric * n_buckets - 2))

        for bot in ALL_BOTS:
            memory = OpponentMemory()
            win_buckets = [0] * n_buckets
            for i in range(n_matches):
                bot.reset()
                result = play_match(engine, bot, memory, total_overs)
                if result['cpu_won']:
                    win_buckets[min(i // batch, n_buckets - 1)] += 1

            row = f"  {bot.name:<{col_bot}}"
            for wins in win_buckets:
                row += f"{wins / batch * 100:>{col_metric-1}.1f}%"
            print(row)

    print(f"\n{sep}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CPU career (repeat-opponent) benchmark")
    parser.add_argument("--matches", type=int, default=3000, help="Sequential matches per bot (default 3000)")
    parser.add_argument("--overs",   type=int, default=2, choices=[2, 5], help="Overs per innings (default 2)")
    parser.add_argument("--batch",   type=int, default=300, help="Matches per reported bucket (default 300)")
    parser.add_argument("--seed",    type=int, default=42, help="Random seed (default 42)")
    args = parser.parse_args()
    run_career_benchmark(n_matches=args.matches, total_overs=args.overs, batch=args.batch, seed=args.seed)
