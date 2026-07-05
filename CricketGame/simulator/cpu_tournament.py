"""
CPU vs CPU round-robin tournament.

Pits the three engine variants directly against each other — every pairing
plays a WARM-UP block first (default 300 matches) so the learning engines
accumulate cross-match memory of their opponent (profile + transitions),
then a MEASURED block whose results are reported.

Each side keeps its own OpponentMemory of the other side, exactly like the
career benchmark does for scripted bots: the batter predicts the bowler
from its memory, the bowler predicts the batter from its own, and both
memories update after every ball.

Usage (from CricketGame/ directory):
    python -m simulator.cpu_tournament
    python -m simulator.cpu_tournament --warmup 300 --matches 1000 --overs 2
"""
import argparse
import random
from typing import Dict, Optional, Tuple

from .engine_sim import SimEngine, NaiveEngine, UniformEngine
from .career_sim import OpponentMemory


def play_innings_vs(
    bat_engine, bat_memory: OpponentMemory,
    bowl_engine, bowl_memory: OpponentMemory,
    total_overs: int,
    target: Optional[int] = None,
    batting_first: bool = True,
) -> Dict:
    """
    One innings, both sides driven by engines.

    bat_memory  — batting side's memory of the OPPONENT (who is bowling)
    bowl_memory — bowling side's memory of the OPPONENT (who is batting)
    """
    total_balls = total_overs * 6
    score = wickets = 0
    bat_history = []    # batter's moves (what the bowler observes)
    bowl_history = []   # bowler's moves (what the batter observes)

    for ball_num in range(total_balls):
        common = {
            'batting_first': batting_first, 'current_score': score,
            'wickets_lost': wickets, 'balls_left': total_balls - ball_num,
            'current_over': ball_num // 6, 'total_overs': total_overs,
            'match_format': f'{total_overs}over', 'target': target,
            'last_3_results': [],
        }

        # Batter predicts the bowler
        prev_bowl = bowl_history[-1] if bowl_history else None
        g, gn = bat_memory.global_signal('bowling')
        tp, tn = bat_memory.transition_signal('bowling', prev_bowl)
        bat_num, _ = bat_engine.select_move(
            g, bowl_history, {**common, 'role': 'batting'},
            bat_memory.confidence(), global_n=gn, trans_n=tn, transition_pred=tp,
        )

        # Bowler predicts the batter
        prev_bat = bat_history[-1] if bat_history else None
        g2, gn2 = bowl_memory.global_signal('batting')
        tp2, tn2 = bowl_memory.transition_signal('batting', prev_bat)
        bowl_num, _ = bowl_engine.select_move(
            g2, bat_history, {**common, 'role': 'bowling'},
            bowl_memory.confidence(), global_n=gn2, trans_n=tn2, transition_pred=tp2,
        )

        was_out = bat_num == bowl_num
        if was_out:
            wickets += 1
        else:
            score += bat_num

        # Both sides remember what the opponent just did
        bat_memory.record('bowling', prev_bowl, bowl_num,
                          was_scored=(not was_out and bowl_num != 0))
        bowl_memory.record('batting', prev_bat, bat_num,
                           was_scored=(not was_out and bat_num != 0))

        bat_history.append(bat_num)
        bowl_history.append(bowl_num)

        if wickets >= 10:
            break
        if target is not None and score > target:
            break

    return {'score': score, 'wickets': wickets}


def play_match_vs(engine_a, mem_a, engine_b, mem_b, total_overs: int) -> bool:
    """Play one full match. Returns True if side A won."""
    a_bats_first = random.random() < 0.5
    if a_bats_first:
        inn1 = play_innings_vs(engine_a, mem_a, engine_b, mem_b, total_overs,
                               target=None, batting_first=True)
        inn2 = play_innings_vs(engine_b, mem_b, engine_a, mem_a, total_overs,
                               target=inn1['score'], batting_first=False)
        return inn2['score'] <= inn1['score']
    else:
        inn1 = play_innings_vs(engine_b, mem_b, engine_a, mem_a, total_overs,
                               target=None, batting_first=True)
        inn2 = play_innings_vs(engine_a, mem_a, engine_b, mem_b, total_overs,
                               target=inn1['score'], batting_first=False)
        return inn2['score'] > inn1['score']


def run_tournament(warmup: int, n_matches: int, total_overs: int, seed: int) -> None:
    engines = [
        ("Uniform", UniformEngine),
        ("Naive",   NaiveEngine),
        ("V2",      SimEngine),
    ]

    print(f"\n{'=' * 78}")
    print(f"  CPU ROUND-ROBIN — {total_overs}-over | warm-up {warmup} matches, "
          f"then {n_matches} measured (seed={seed})")
    print(f"{'=' * 78}")

    results: Dict[Tuple[str, str], float] = {}
    points = {name: 0.0 for name, _ in engines}

    for i in range(len(engines)):
        for j in range(i + 1, len(engines)):
            name_a, cls_a = engines[i]
            name_b, cls_b = engines[j]
            random.seed(seed)
            engine_a, engine_b = cls_a(), cls_b()
            mem_a, mem_b = OpponentMemory(), OpponentMemory()

            # Warm-up: memories accumulate, results discarded
            for _ in range(warmup):
                play_match_vs(engine_a, mem_a, engine_b, mem_b, total_overs)

            # Measured block
            wins_a = 0
            for _ in range(n_matches):
                if play_match_vs(engine_a, mem_a, engine_b, mem_b, total_overs):
                    wins_a += 1

            pct_a = wins_a / n_matches * 100
            results[(name_a, name_b)] = pct_a
            points[name_a] += pct_a
            points[name_b] += 100 - pct_a
            print(f"  {name_a:>8} vs {name_b:<8}  ->  "
                  f"{name_a} {pct_a:5.1f}%  |  {name_b} {100 - pct_a:5.1f}%")

    print(f"\n  Standings (total win% across both pairings):")
    for name, pts in sorted(points.items(), key=lambda kv: -kv[1]):
        print(f"    {name:<8} {pts:6.1f}")
    print(f"{'=' * 78}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CPU vs CPU round-robin tournament")
    parser.add_argument("--warmup",  type=int, default=300, help="Warm-up matches per pairing (default 300)")
    parser.add_argument("--matches", type=int, default=1000, help="Measured matches per pairing (default 1000)")
    parser.add_argument("--overs",   type=int, default=2, choices=[2, 5], help="Overs per innings")
    parser.add_argument("--seed",    type=int, default=42, help="Random seed")
    args = parser.parse_args()
    run_tournament(args.warmup, args.matches, args.overs, args.seed)
