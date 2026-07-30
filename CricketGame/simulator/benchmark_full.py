"""
Bot-battery benchmark for V1/V2/V3, but each CPU builds PERSISTENT
full-signal memory (global frequency + transitions + streaks + situational
patterns) against each bot across many repeated matches -- unlike
benchmark.py/match_sim.py, which run every match memory-less (global_n=0,
no transition/streak/situational at all). This is the "full-fledged CPU"
version of the same bot battery.

One FullMemory instance per engine, shared across all 9 bots (matches
production semantics: a real CPU holds a separate profile per opponent
identity simultaneously, not reset between opponents).

Usage (from CricketGame/ directory):
    python -m simulator.benchmark_full
    python -m simulator.benchmark_full --matches 2000 --overs 2 --seed 42
"""
import argparse
import random

from .engine_sim import SimEngine, SimEngineV3, NaiveEngine
from .bots import ALL_BOTS
from .tournament_sim import Participant, FullMemory, simulate_match_any

NASH_WR   = 100 / 7            # ~14.3%
NASH_ECON = (6 / 7) * 3 * 6    # ~15.4 runs/over
NASH_SR   = (6 / 7) * 3 * 100  # ~257


def run_full_benchmark(n_matches: int = 1000, total_overs: int = 2, seed: int = 42) -> None:
    random.seed(seed)

    engines = [
        ("V1/Naive", NaiveEngine()),
        ("V2",       SimEngine()),
        ("V3",       SimEngineV3()),
    ]

    col_bot, col_metric = 24, 9
    header = (f"  {'Bot':<{col_bot}}{'BowlWR%':>{col_metric}}{'Econ/ov':>{col_metric}}"
              f"{'BatSR':>{col_metric}}{'Win%':>{col_metric}}")
    divider = "  " + "-" * col_bot + (" " + "-" * (col_metric - 1)) * 4
    sep = "=" * (col_bot + col_metric * 4 + 4)

    print(f"\n{sep}")
    print(f"  FULL-SIGNAL BOT BENCHMARK  —  {n_matches} matches x {total_overs}-over  (seed={seed})")
    print(f"  Persistent memory per (engine, bot) pair, accumulated across all {n_matches} matches")
    print(f"  Nash WR~{NASH_WR:.1f}%  Econ~{NASH_ECON:.1f}  SR~{NASH_SR:.0f}")
    print(sep)

    for name, engine in engines:
        print(f"\n  -- {name} --")
        print(header)
        print(divider)

        p_cpu = Participant(name, 'engine', engine)
        memory = FullMemory()   # shared across all bots this engine faces

        for bot in ALL_BOTS:
            p_bot = Participant(bot.name, 'bot', bot)

            bowl_wk = bowl_run = bowl_bl = 0
            bat_run = bat_bl = 0
            wins = 0

            for _ in range(n_matches):
                bot.reset()
                result = simulate_match_any(p_cpu, p_bot, memory, total_overs)
                cpu_inn = result['p1_inn']   # p_cpu is always p1
                bot_inn = result['p2_inn']

                bowl_wk  += bot_inn['wickets']
                bowl_run += bot_inn['score']
                bowl_bl  += bot_inn['balls']
                bat_run  += cpu_inn['score']
                bat_bl   += cpu_inn['balls']
                if result['p1_won']:
                    wins += 1

            total_bowl = bowl_bl or 1
            total_bat  = bat_bl or 1
            wr_pct  = bowl_wk / total_bowl * 100
            econ    = bowl_run / total_bowl * 6
            bat_sr  = bat_run / total_bat * 100
            win_pct = wins / n_matches * 100

            wr_mark  = "+" if wr_pct > NASH_WR + 0.5 else ("-" if wr_pct < NASH_WR - 0.5 else "~")
            eco_mark = "-" if econ < NASH_ECON - 0.5 else ("+" if econ > NASH_ECON + 0.5 else "~")
            sr_mark  = "+" if bat_sr > NASH_SR + 5 else ("-" if bat_sr < NASH_SR - 5 else "~")

            print(
                f"  {bot.name:<{col_bot}}"
                f"{wr_pct:>{col_metric - 1}.1f}%{wr_mark}"
                f"{econ:>{col_metric}.2f}{eco_mark}"
                f"{bat_sr:>{col_metric - 1}.1f}%{sr_mark}"
                f"{win_pct:>{col_metric - 1}.1f}%"
            )

    print(f"\n{sep}")
    print("  +/- = better/worse than Nash baseline  ~ = within noise")
    print(f"{sep}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full-signal persistent-memory bot benchmark")
    parser.add_argument("--matches", type=int, default=1000)
    parser.add_argument("--overs",   type=int, default=2, choices=[2, 5])
    parser.add_argument("--seed",    type=int, default=42)
    args = parser.parse_args()
    run_full_benchmark(n_matches=args.matches, total_overs=args.overs, seed=args.seed)
