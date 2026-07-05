"""
Old CPU (commit b0c00da, before today) vs New CPU (current) — two-part showdown.

Part A — Bot gauntlet: both engines run a career (persistent memory) against
         every scripted bot; average win% compared side by side.
Part B — Direct duel: old and new engines play each other head-to-head,
         300 warm-up matches (mutual learning) then a measured block.

Usage (from CricketGame/ directory):
    python -m simulator.old_vs_new --overs 2
    python -m simulator.old_vs_new --overs 5 --gauntlet-matches 2000 --duel-matches 1000
"""
import argparse
import random

from .engine_sim import SimEngine
from .old_engine import OldEngine
from .bots import ALL_BOTS
from .career_sim import OpponentMemory, play_match
from .cpu_tournament import play_match_vs


def run_gauntlet(total_overs: int, n_matches: int, seed: int) -> None:
    print(f"\n  PART A — BOT GAUNTLET ({n_matches} career matches per bot, {total_overs}-over)")
    print(f"  {'Bot':<38}{'OLD win%':>10}{'NEW win%':>10}{'Delta':>8}")
    print("  " + "-" * 66)

    old_total = new_total = 0.0
    for bot in ALL_BOTS:
        rates = {}
        for label, engine_cls in (("old", OldEngine), ("new", SimEngine)):
            random.seed(seed)
            engine, memory = engine_cls(), OpponentMemory()
            wins = 0
            for _ in range(n_matches):
                bot.reset()
                if play_match(engine, bot, memory, total_overs)['cpu_won']:
                    wins += 1
            rates[label] = wins / n_matches * 100

        delta = rates['new'] - rates['old']
        old_total += rates['old']
        new_total += rates['new']
        marker = "+" if delta > 1 else ("-" if delta < -1 else "~")
        print(f"  {bot.name:<38}{rates['old']:>9.1f}%{rates['new']:>9.1f}%{delta:>+7.1f}{marker}")

    n_bots = len(ALL_BOTS)
    print("  " + "-" * 66)
    print(f"  {'MEAN':<38}{old_total / n_bots:>9.1f}%{new_total / n_bots:>9.1f}%"
          f"{(new_total - old_total) / n_bots:>+7.1f}")


def run_duel(total_overs: int, warmup: int, n_matches: int, seed: int) -> None:
    print(f"\n  PART B — HEAD-TO-HEAD DUEL ({total_overs}-over, "
          f"{warmup} warm-up + {n_matches} measured)")
    random.seed(seed)
    old_engine, new_engine = OldEngine(), SimEngine()
    mem_old, mem_new = OpponentMemory(), OpponentMemory()

    for _ in range(warmup):
        play_match_vs(old_engine, mem_old, new_engine, mem_new, total_overs)

    old_wins = 0
    for _ in range(n_matches):
        if play_match_vs(old_engine, mem_old, new_engine, mem_new, total_overs):
            old_wins += 1

    old_pct = old_wins / n_matches * 100
    print(f"    OLD CPU (b0c00da): {old_pct:5.1f}%")
    print(f"    NEW CPU (current): {100 - old_pct:5.1f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Old vs New CPU comparison")
    parser.add_argument("--overs", type=int, default=2, choices=[2, 5])
    parser.add_argument("--gauntlet-matches", type=int, default=2000)
    parser.add_argument("--duel-warmup", type=int, default=300)
    parser.add_argument("--duel-matches", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("=" * 70)
    print(f"  OLD CPU (pre-today, b0c00da)  vs  NEW CPU (current)  —  {args.overs}-over")
    print("=" * 70)
    run_gauntlet(args.overs, args.gauntlet_matches, args.seed)
    run_duel(args.overs, args.duel_warmup, args.duel_matches, args.seed)
    print()
