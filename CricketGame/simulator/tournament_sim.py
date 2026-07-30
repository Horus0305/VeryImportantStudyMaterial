"""
12-way round-robin tournament: V1/V2/V3 CPU engines vs the 9 scripted bots,
repeated across many tournaments with PERSISTENT memory for the CPU engines
(they keep learning each specific opponent's tendencies from one tournament
to the next -- memory is never reset between tournaments).

Usage (from CricketGame/ directory):
    python -m simulator.tournament_sim
    python -m simulator.tournament_sim --tournaments 200 --overs 2 --seed 42

Persistent memory, full signal set:
    Mirrors every DB-backed signal the real engine has, keyed per
    (engine, opponent, opponent's role) exactly like CPUUserProfile /
    CPUSequencePattern / CPUStreakPattern / CPUSituationalPattern:
      - global frequency            -> db_prior / global_n
      - transition (prev move -> next)  -> transition_pred / trans_n
      - streak (class+len -> next)      -> streak_pred / streak_n
      - situational (phase+pressure+event -> next) -> sit_pred / sit_n
    Local frequency and live 1-/2-gram transitions stay in-match only,
    same as the real engine (they reset every innings by design).

    Simplification kept from the first pass: production's transition table
    is also keyed by the previous ball's result (out/dot/scored); this one
    is keyed by previous move only. Adding result-conditioning would mean
    tracking per-ball outcome history per opponent on top of everything
    else here, for a signal that already competes with 6 others in the
    blend -- marginal value not worth the extra bookkeeping right now.
"""
import argparse
import itertools
import random
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .engine_sim import SimEngine, SimEngineV3, NaiveEngine, BASE_WEIGHTS
from .bots import (
    Bot, FreqBaiter, HEscaper, HShuffler, HLAlternator,
    StreakMaker, PressureReversal, MetaGamer, PureRandom,
)
from backend.cpu.cpu_learning_utils import get_game_phase, get_score_situation, get_recent_event


class Participant:
    """Uniform wrapper around either a scripted Bot or a CPU engine."""

    def __init__(self, name: str, kind: str, obj):
        self.name = name
        self.kind = kind   # 'bot' or 'engine'
        self.obj = obj

    def reset(self):
        if self.kind == 'bot':
            self.obj.reset()


def _streak_class_len(hist: List[int]) -> Optional[Tuple[str, int]]:
    """Same classification as the real engine's _load_streak_patterns."""
    if not hist:
        return None
    def cls(n):
        if n == 0:
            return 'Z'
        return 'H' if n >= 4 else 'L'
    c = cls(hist[-1])
    length = 0
    for m in reversed(hist):
        if cls(m) == c:
            length += 1
        else:
            break
    return c, min(length, 4)


class FullMemory:
    """
    Per-(engine, opponent, opponent_role) accumulated profile covering every
    DB-backed signal the real engine has, persisting across the entire
    tournament series (never reset between tournaments).
    """

    def __init__(self):
        Key = Tuple[str, str, str]
        self._global: Dict[Key, List[int]] = defaultdict(lambda: [0] * 7)
        self._trans:  Dict[Key, Dict[int, List[int]]] = defaultdict(dict)
        self._streak: Dict[Key, Dict[Tuple[str, int], List[int]]] = defaultdict(dict)
        self._sit:    Dict[Key, Dict[Tuple[str, str, str], List[int]]] = defaultdict(dict)

    def profile(self, engine_name: str, opp_name: str, opp_role: str,
                opp_hist: List[int], phase: str, pressure: str, event: str) -> Dict:
        key = (engine_name, opp_name, opp_role)

        gcounts = self._global[key]
        gtotal = sum(gcounts)
        db_prior = {n: gcounts[n] / gtotal for n in range(7)} if gtotal else dict(BASE_WEIGHTS)

        trans_pred, trans_n = None, 0
        if opp_hist:
            tcounts = self._trans[key].get(opp_hist[-1])
            if tcounts:
                ttotal = sum(tcounts)
                if ttotal:
                    trans_pred = {n: tcounts[n] / ttotal for n in range(7)}
                    trans_n = ttotal

        streak_pred, streak_n = None, 0
        cls_len = _streak_class_len(opp_hist)
        if cls_len:
            scounts = self._streak[key].get(cls_len)
            if scounts:
                stotal = sum(scounts)
                if stotal:
                    streak_pred = {n: scounts[n] / stotal for n in range(7)}
                    streak_n = stotal

        sit_pred, sit_n = None, 0
        sit_key = (phase, pressure, event)
        sitcounts = self._sit[key].get(sit_key)
        if sitcounts:
            sittotal = sum(sitcounts)
            if sittotal:
                sit_pred = {n: sitcounts[n] / sittotal for n in range(7)}
                sit_n = sittotal

        return dict(
            db_prior=db_prior, global_n=gtotal,
            transition_pred=trans_pred, trans_n=trans_n,
            streak_pred=streak_pred, streak_n=streak_n,
            sit_pred=sit_pred, sit_n=sit_n,
        )

    def observe_ball(self, engine_name: str, opp_name: str, opp_role: str,
                      opp_hist_before: List[int], opp_move: int,
                      phase: str, pressure: str, event: str) -> None:
        """Record one observed opponent move, using context from BEFORE this ball."""
        key = (engine_name, opp_name, opp_role)

        self._global[key][opp_move] += 1

        if opp_hist_before:
            prev = opp_hist_before[-1]
            row = self._trans[key].setdefault(prev, [0] * 7)
            row[opp_move] += 1

        cls_len = _streak_class_len(opp_hist_before)
        if cls_len:
            row = self._streak[key].setdefault(cls_len, [0] * 7)
            row[opp_move] += 1

        sit_key = (phase, pressure, event)
        row = self._sit[key].setdefault(sit_key, [0] * 7)
        row[opp_move] += 1


class Stats:
    __slots__ = ('matches', 'wins', 'runs_for', 'balls_for', 'wkts_lost',
                 'runs_against', 'balls_against', 'wkts_taken')

    def __init__(self):
        self.matches = 0
        self.wins = 0
        self.runs_for = 0
        self.balls_for = 0
        self.wkts_lost = 0
        self.runs_against = 0
        self.balls_against = 0
        self.wkts_taken = 0

    @property
    def win_pct(self) -> float:
        return self.wins / self.matches * 100 if self.matches else 0.0

    @property
    def nrr(self) -> float:
        rr_for = self.runs_for / self.balls_for * 6 if self.balls_for else 0.0
        rr_against = self.runs_against / self.balls_against * 6 if self.balls_against else 0.0
        return rr_for - rr_against


def _pick(p: Participant, role: str, my_hist: List[int], opp_name: str, opp_role: str,
          opp_hist: List[int], ctx_common: Dict, memory: FullMemory,
          phase: str, pressure: str, event: str) -> int:
    if p.kind == 'bot':
        bot_ctx = {
            'balls_left':  ctx_common['balls_left'],
            'score':       ctx_common['current_score'],
            'wickets':     ctx_common['wickets_lost'],
            'target':      ctx_common['target'],
            'total_balls': ctx_common['total_overs'] * 6,
        }
        return p.obj.pick(my_hist, bot_ctx)

    ctx = dict(ctx_common, role=role)
    prof = memory.profile(p.name, opp_name, opp_role, opp_hist, phase, pressure, event)
    num, _ = p.obj.select_move(prof['db_prior'], opp_hist, ctx, 0.5,
                                global_n=prof['global_n'],
                                trans_n=prof['trans_n'], transition_pred=prof['transition_pred'],
                                streak_n=prof['streak_n'], streak_pred=prof['streak_pred'],
                                sit_n=prof['sit_n'], sit_pred=prof['sit_pred'])
    return num


def simulate_innings_any(
    p_bat: Participant, p_bowl: Participant, memory: FullMemory,
    total_overs: int, target, batting_first: bool,
) -> Dict:
    score = wickets = 0
    bat_hist: List[int] = []
    bowl_hist: List[int] = []
    ball_log: List[Dict] = []
    total_balls = total_overs * 6

    for ball_num in range(total_balls):
        current_over = ball_num // 6
        last_3 = ball_log[-3:]
        phase = get_game_phase(current_over, total_overs)
        pressure = get_score_situation(
            batting_first=batting_first, current_score=score, target=target,
            wickets_lost=wickets, balls_left=total_balls - ball_num, total_overs=total_overs,
        )
        event = get_recent_event(last_3)

        ctx_common = {
            'batting_first': batting_first, 'current_score': score,
            'wickets_lost': wickets, 'balls_left': total_balls - ball_num,
            'current_over': current_over, 'total_overs': total_overs,
            'match_format': f'{total_overs}over', 'target': target,
            'last_3_results': last_3,
        }

        # Snapshot histories BEFORE this ball for transition/streak keys --
        # the bowler is p_bat's opponent (role 'bowling'), and vice versa.
        bat_num = _pick(p_bat, 'batting', bat_hist, p_bowl.name, 'bowling',
                        bowl_hist, ctx_common, memory, phase, pressure, event)
        bowl_num = _pick(p_bowl, 'bowling', bowl_hist, p_bat.name, 'batting',
                         bat_hist, ctx_common, memory, phase, pressure, event)

        if p_bat.kind == 'engine':
            memory.observe_ball(p_bat.name, p_bowl.name, 'bowling', bowl_hist, bowl_num,
                                phase, pressure, event)
        if p_bowl.kind == 'engine':
            memory.observe_ball(p_bowl.name, p_bat.name, 'batting', bat_hist, bat_num,
                                phase, pressure, event)

        bat_hist.append(bat_num)
        bowl_hist.append(bowl_num)

        if bat_num == bowl_num:
            wickets += 1
            ball_log.append({'runs': 0, 'is_out': True})
            if wickets >= 10:
                break
        else:
            runs = bowl_num if bat_num == 0 else bat_num
            score += runs
            ball_log.append({'runs': runs, 'is_out': False})
            if target is not None and score > target:
                break

    return {'score': score, 'wickets': wickets, 'balls': len(bat_hist)}


def simulate_match_any(p1: Participant, p2: Participant, memory: FullMemory,
                        total_overs: int) -> Dict:
    p1_bats_first = random.random() < 0.5
    if p1_bats_first:
        inn1 = simulate_innings_any(p1, p2, memory, total_overs, None, True)
        target = inn1['score']
        inn2 = simulate_innings_any(p2, p1, memory, total_overs, target, False)
        p1_inn, p2_inn = inn1, inn2
        p1_won = inn2['score'] <= target
    else:
        inn1 = simulate_innings_any(p2, p1, memory, total_overs, None, True)
        target = inn1['score']
        inn2 = simulate_innings_any(p1, p2, memory, total_overs, target, False)
        p1_inn, p2_inn = inn2, inn1
        p1_won = inn2['score'] > target

    return {'p1_inn': p1_inn, 'p2_inn': p2_inn, 'p1_won': p1_won}


def build_participants() -> List[Participant]:
    return [
        Participant('V1/Naive', 'engine', NaiveEngine()),
        Participant('V2', 'engine', SimEngine()),
        Participant('V3', 'engine', SimEngineV3()),
        Participant('FreqBaiter(1->high)', 'bot', FreqBaiter(spam_num=1, switch_to=[4, 5, 6])),
        Participant('FreqBaiter(6->low)', 'bot', FreqBaiter(spam_num=6, switch_to=[0, 1, 2])),
        Participant('H->0 Escaper', 'bot', HEscaper()),
        Participant('H Shuffler', 'bot', HShuffler()),
        Participant('H<>L Alternator', 'bot', HLAlternator()),
        Participant('StreakMaker', 'bot', StreakMaker(streak_len=5)),
        Participant('PressureReversal', 'bot', PressureReversal()),
        Participant('MetaGamer', 'bot', MetaGamer()),
        Participant('PureRandom', 'bot', PureRandom()),
    ]


def _apply_result(standings: Dict[str, Stats], p1: Participant, p2: Participant, result: Dict) -> None:
    s1, s2 = standings[p1.name], standings[p2.name]
    inn1, inn2 = result['p1_inn'], result['p2_inn']

    for s, own_inn, opp_inn, won in (
        (s1, inn1, inn2, result['p1_won']),
        (s2, inn2, inn1, not result['p1_won']),
    ):
        s.matches += 1
        s.wins += 1 if won else 0
        s.runs_for += own_inn['score']
        s.balls_for += own_inn['balls']
        s.wkts_lost += own_inn['wickets']
        s.runs_against += opp_inn['score']
        s.balls_against += opp_inn['balls']
        s.wkts_taken += opp_inn['wickets']


def run_tournament_series(n_tournaments: int = 200, total_overs: int = 2, seed: int = 42):
    random.seed(seed)
    participants = build_participants()
    memory = FullMemory()
    standings: Dict[str, Stats] = {p.name: Stats() for p in participants}
    # Snapshot standings at the halfway point -- comparing the first half of
    # the series against the second half (not tournament-1-alone, which is
    # only 11 matches per engine and far too noisy to read anything into)
    # is the honest way to check whether persistent memory pays off over time.
    halfway = max(1, n_tournaments // 2)
    snapshot_at_half: Dict[str, Stats] = None

    for t in range(n_tournaments):
        for p in participants:
            p.reset()
        for p_a, p_b in itertools.combinations(participants, 2):
            result = simulate_match_any(p_a, p_b, memory, total_overs)
            _apply_result(standings, p_a, p_b, result)
        if t == halfway - 1:
            snapshot_at_half = {name: _copy_stats(s) for name, s in standings.items()}

    return standings, snapshot_at_half, participants


def _copy_stats(s: Stats) -> Stats:
    c = Stats()
    for attr in Stats.__slots__:
        setattr(c, attr, getattr(s, attr))
    return c


def _diff_stats(final: Stats, snap: Stats) -> Stats:
    """Stats for the second half only (final minus the halfway snapshot)."""
    d = Stats()
    for attr in Stats.__slots__:
        setattr(d, attr, getattr(final, attr) - getattr(snap, attr))
    return d


def print_report(standings, snapshot_at_half, n_tournaments, total_overs, seed):
    col_name = 22
    header = (f"  {'Rank':<5}{'Name':<{col_name}}{'MP':>6}{'W':>6}{'Win%':>8}"
              f"{'NRR':>8}{'RunsFor':>9}{'RunsAg':>9}{'WktsTk':>8}{'WktsLost':>9}")
    sep = "=" * len(header)

    print(f"\n{sep}")
    print(f"  TOURNAMENT SERIES (FULL SIGNAL SET)  —  {n_tournaments} tournaments x {total_overs}-over  "
          f"(seed={seed})")
    print(sep)

    ranked = sorted(standings.items(), key=lambda kv: (-kv[1].wins, -kv[1].nrr))
    for i, (name, s) in enumerate(ranked, 1):
        print(f"  {i:<5}{name:<{col_name}}{s.matches:>6}{s.wins:>6}{s.win_pct:>7.1f}%"
              f"{s.nrr:>8.2f}{s.runs_for:>9}{s.runs_against:>9}{s.wkts_taken:>8}{s.wkts_lost:>9}")

    print(sep)
    print("  Rank by wins, then net run rate (NRR = for-rate minus against-rate, runs/over)")

    half = n_tournaments // 2
    print(f"\n  -- Persistent-memory effect (win%% tournaments 1-{half} vs {half + 1}-{n_tournaments}) --")
    print(f"  {'Name':<{col_name}}{'1st half':>10}{'2nd half':>12}{'Delta':>9}")
    for name in ('V1/Naive', 'V2', 'V3'):
        first = snapshot_at_half[name]
        second = _diff_stats(standings[name], first)
        first_pct = first.win_pct
        second_pct = second.win_pct
        print(f"  {name:<{col_name}}{first_pct:>9.1f}%{second_pct:>11.1f}%{second_pct - first_pct:>+8.1f}pp")
    print(f"{sep}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CPU tournament series with persistent memory")
    parser.add_argument("--tournaments", type=int, default=200)
    parser.add_argument("--overs", type=int, default=2, choices=[2, 5])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    standings, snap1, participants = run_tournament_series(
        n_tournaments=args.tournaments, total_overs=args.overs, seed=args.seed,
    )
    print_report(standings, snap1, args.tournaments, args.overs, args.seed)
