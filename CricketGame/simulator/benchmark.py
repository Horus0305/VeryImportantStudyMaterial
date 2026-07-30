"""
CPU Benchmark — compare engine variants against scripted attacker bots.

Usage (from CricketGame/ directory):
    python -m simulator.benchmark
    python -m simulator.benchmark --matches 2000 --overs 5
    python -m simulator.benchmark --matches 500 --overs 2 --seed 0

Metrics explained:
    Bowl WR%  — when CPU bowls: wickets per ball × 100  (higher = better)
                Nash baseline ≈ 14.3%  (1 in 7 chance)
    Econ/over — when CPU bowls: runs conceded per over   (lower = better)
                Nash baseline ≈ 15.4 runs/over
    Bat SR    — when CPU bats:  runs per 100 balls       (higher = better)
                Nash baseline ≈ 257
    Entropy   — avg Shannon entropy of CPU distribution  (max = 2.807 bits)
                Near max = near-uniform (safe, hard to exploit)
                Near 0   = fully committed (easy to exploit)
    Win%      — fraction of full matches CPU won         (higher = better)
                Nash baseline ≈ 50%
"""
import argparse
import random
import sys
from collections import defaultdict
from typing import List, Dict

from .engine_sim import SimEngine, SimEngineV3, NaiveEngine, UniformEngine, BASE_WEIGHTS, entropy
from .bots import ALL_BOTS
from .match_sim import simulate_match

# Nash equilibrium theoretical values (both sides uniform)
NASH_WR   = 100 / 7          # ≈ 14.29 %
NASH_ECON = (6 / 7) * 3 * 6  # ≈ 15.43 runs/over  (E[bat|no match] × 6)
NASH_SR   = (6 / 7) * 3 * 100  # ≈ 257.1


def _avg(lst: List[float]) -> float:
    return sum(lst) / len(lst) if lst else 0.0


def run_benchmark(n_matches: int = 1000, total_overs: int = 2, seed: int = 42) -> None:
    random.seed(seed)

    engines = [
        ("CPU Uniform  (Nash baseline)",   UniformEngine()),
        ("CPU Naive    (no adaptation)",   NaiveEngine()),
        ("CPU V2       (freq blend+RRR)",  SimEngine()),
        ("CPU V3       (+elim+wildcard)",  SimEngineV3()),
    ]

    db_prior    = dict(BASE_WEIGHTS)   # no DB data — tests in-game signal only
    confidence  = 0.5
    col_bot     = 36
    col_metric  = 9

    header = (
        f"  {'Bot':<{col_bot}}"
        f"{'BowlWR%':>{col_metric}}"
        f"{'Econ/ov':>{col_metric}}"
        f"{'BatSR':>{col_metric}}"
        f"{'Entropy':>{col_metric}}"
        f"{'Win%':>{col_metric}}"
    )
    divider = "  " + "-" * col_bot + (" " + "-" * (col_metric - 1)) * 5

    sep = "=" * (col_bot + col_metric * 5 + 4)

    print(f"\n{sep}")
    print(f"  CPU BENCHMARK  —  {n_matches} matches × {total_overs}-over  "
          f"(seed={seed})")
    print(f"  Nash WR~{NASH_WR:.1f}%  Econ~{NASH_ECON:.1f}  SR~{NASH_SR:.0f}")
    print(sep)

    for engine_name, engine in engines:
        print(f"\n  -- {engine_name} --")
        print(header)
        print(divider)

        for bot in ALL_BOTS:
            bot.reset()

            bowl_wk:  List[int]   = []
            bowl_run: List[int]   = []
            bowl_bl:  List[int]   = []
            bat_run:  List[int]   = []
            bat_bl:   List[int]   = []
            ents:     List[float] = []
            wins:     int         = 0

            for _ in range(n_matches):
                result = simulate_match(engine, bot, db_prior, confidence, total_overs)

                cpu_inn = result['cpu_bat_inn']
                bot_inn = result['bot_bat_inn']

                # Bowling stats: bot was batting in bot_bat_inn
                bowl_wk.append(bot_inn['wickets'])
                bowl_run.append(bot_inn['score'])
                bowl_bl.append(bot_inn['balls'])

                # Batting stats: CPU was batting in cpu_bat_inn
                bat_run.append(cpu_inn['score'])
                bat_bl.append(cpu_inn['balls'])

                # Entropy from both innings' CPU distributions
                for dist in bot_inn['cpu_dists'] + cpu_inn['cpu_dists']:
                    if dist:
                        ents.append(entropy(dist))

                if result['cpu_won']:
                    wins += 1

            total_bowl = sum(bowl_bl) or 1
            total_bat  = sum(bat_bl) or 1

            wr_pct  = sum(bowl_wk) / total_bowl * 100
            econ    = sum(bowl_run) / total_bowl * 6
            bat_sr  = sum(bat_run)  / total_bat  * 100
            avg_ent = _avg(ents)
            win_pct = wins / n_matches * 100

            # Direction markers vs Nash baseline
            wr_mark  = "+" if wr_pct  > NASH_WR   + 0.5 else ("-" if wr_pct  < NASH_WR   - 0.5 else "~")
            eco_mark = "-" if econ    < NASH_ECON - 0.5 else ("+" if econ    > NASH_ECON + 0.5 else "~")
            sr_mark  = "+" if bat_sr  > NASH_SR   + 5   else ("-" if bat_sr  < NASH_SR   - 5   else "~")

            print(
                f"  {bot.name:<{col_bot}}"
                f"{wr_pct:>{col_metric - 1}.1f}%{wr_mark}"
                f"{econ:>{col_metric}.2f}{eco_mark}"
                f"{bat_sr:>{col_metric - 1}.1f}%{sr_mark}"
                f"{avg_ent:>{col_metric}.3f}"
                f"{win_pct:>{col_metric - 1}.1f}%"
            )

    print(f"\n{sep}")
    print("  +/- = better/worse than Nash baseline  ~ = within noise")
    print(f"{sep}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CPU strategy benchmark")
    parser.add_argument("--matches", type=int,   default=1000,
                        help="Simulated matches per bot (default 1000)")
    parser.add_argument("--overs",   type=int,   default=2, choices=[2, 5],
                        help="Overs per innings (default 2)")
    parser.add_argument("--seed",    type=int,   default=42,
                        help="Random seed for reproducibility (default 42)")
    args = parser.parse_args()
    run_benchmark(n_matches=args.matches, total_overs=args.overs, seed=args.seed)
