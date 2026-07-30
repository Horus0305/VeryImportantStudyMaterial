"""
Hand cricket match simulator.

Ball resolution (mirrors backend/game/innings.py resolve_ball exactly):
    bat_num == bowl_num  →  wicket  (batting team scores 0 that ball)
    bat_num == 0, bowl_num != 0  →  WILDCARD: batting team scores bowl_num
    bat_num != 0, != bowl_num    →  batting team scores bat_num runs

Innings ends when: 10 wickets fall, all overs are used, or (innings 2 only)
the chasing team overtakes the target.
"""
import random
from typing import Dict, List, Optional, Tuple

from .engine_sim import BASE_WEIGHTS


def _build_cpu_context(
    cpu_role: str,
    batting_first: bool,
    score: int,
    wickets: int,
    ball_num: int,
    total_overs: int,
    target: Optional[int],
) -> Dict:
    total_balls = total_overs * 6
    return {
        'role':          cpu_role,
        'batting_first': batting_first,
        'current_score': score,
        'wickets_lost':  wickets,
        'balls_left':    total_balls - ball_num,
        'current_over':  ball_num // 6,
        'total_overs':   total_overs,
        'match_format':  f'{total_overs}over',
        'target':        target,
        'last_3_results': [],
    }


def simulate_innings(
    cpu_engine,
    cpu_role: str,           # 'batting' or 'bowling'
    bot,
    db_prior: Dict[int, float],
    confidence: float = 0.5,
    total_overs: int = 2,
    target: Optional[int] = None,
    batting_first: bool = True,
) -> Dict:
    """
    Simulate one innings.

    cpu_role='bowling': CPU bowls, bot bats. Score/wickets track the bot.
    cpu_role='batting': CPU bats, bot bowls. Score/wickets track the CPU.

    Returns:
        score           — runs scored by the batting side
        wickets         — wickets lost by the batting side
        balls           — total balls bowled
        cpu_dists       — list of CPU distributions, one per ball (for entropy)
    """
    score: int   = 0
    wickets: int = 0
    cpu_history:  List[int] = []
    bot_history:  List[int] = []
    cpu_dists:    List[Dict] = []
    total_balls = total_overs * 6

    for ball_num in range(total_balls):
        ctx     = _build_cpu_context(cpu_role, batting_first, score, wickets,
                                     ball_num, total_overs, target)
        bot_ctx = {
            'balls_left':  total_balls - ball_num,
            'score':       score,
            'wickets':     wickets,
            'target':      target,
            'total_balls': total_balls,
        }

        # CPU and bot pick simultaneously
        cpu_num, cpu_dist = cpu_engine.select_move(db_prior, bot_history, ctx, confidence)
        bot_num = bot.pick(bot_history, bot_ctx)

        cpu_dists.append(cpu_dist)

        if cpu_role == 'batting':
            bat_num, bowl_num = cpu_num, bot_num
        else:
            bat_num, bowl_num = bot_num, cpu_num

        cpu_history.append(cpu_num)
        bot_history.append(bot_num)

        if bat_num == bowl_num:
            wickets += 1
            if wickets >= 10:
                break
        else:
            runs = bowl_num if bat_num == 0 else bat_num
            score += runs
            if target is not None and score > target:
                break

    return {
        'score':    score,
        'wickets':  wickets,
        'balls':    len(cpu_history),
        'cpu_dists': cpu_dists,
    }


def simulate_innings_h2h(
    engine_a, prior_a: Dict[int, float], conf_a: float,
    engine_b, prior_b: Dict[int, float], conf_b: float,
    role_a: str,              # 'batting' or 'bowling' -- A's role this innings
    total_overs: int = 2,
    target: Optional[int] = None,
    batting_first: bool = True,
) -> Dict:
    """One innings, both sides are CPU engines instead of a scripted bot."""
    role_b = 'bowling' if role_a == 'batting' else 'batting'
    score: int   = 0
    wickets: int = 0
    a_history: List[int] = []
    b_history: List[int] = []
    total_balls = total_overs * 6

    for ball_num in range(total_balls):
        ctx_a = _build_cpu_context(role_a, batting_first, score, wickets,
                                   ball_num, total_overs, target)
        ctx_b = _build_cpu_context(role_b, batting_first, score, wickets,
                                   ball_num, total_overs, target)

        # Each engine's "opponent" is the other engine, so it sees the
        # other's own history, not its own.
        a_num, _ = engine_a.select_move(prior_a, b_history, ctx_a, conf_a)
        b_num, _ = engine_b.select_move(prior_b, a_history, ctx_b, conf_b)

        a_history.append(a_num)
        b_history.append(b_num)

        if role_a == 'batting':
            bat_num, bowl_num = a_num, b_num
        else:
            bat_num, bowl_num = b_num, a_num

        if bat_num == bowl_num:
            wickets += 1
            if wickets >= 10:
                break
        else:
            runs = bowl_num if bat_num == 0 else bat_num
            score += runs
            if target is not None and score > target:
                break

    return {'score': score, 'wickets': wickets, 'balls': len(a_history)}


def simulate_match_h2h(
    engine_a, prior_a: Dict[int, float], conf_a: float,
    engine_b, prior_b: Dict[int, float], conf_b: float,
    total_overs: int = 2,
) -> Dict:
    """Full 2-innings match between two CPU engines. Who bats first is random."""
    a_bats_first = random.random() < 0.5

    if a_bats_first:
        inn1 = simulate_innings_h2h(engine_a, prior_a, conf_a, engine_b, prior_b, conf_b,
                                    role_a='batting', total_overs=total_overs,
                                    target=None, batting_first=True)
        target = inn1['score']
        inn2 = simulate_innings_h2h(engine_a, prior_a, conf_a, engine_b, prior_b, conf_b,
                                    role_a='bowling', total_overs=total_overs,
                                    target=target, batting_first=False)
        a_score, b_score = inn1['score'], inn2['score']
        a_won = inn2['score'] <= target
    else:
        inn1 = simulate_innings_h2h(engine_a, prior_a, conf_a, engine_b, prior_b, conf_b,
                                    role_a='bowling', total_overs=total_overs,
                                    target=None, batting_first=True)
        target = inn1['score']
        inn2 = simulate_innings_h2h(engine_a, prior_a, conf_a, engine_b, prior_b, conf_b,
                                    role_a='batting', total_overs=total_overs,
                                    target=target, batting_first=False)
        a_score, b_score = inn2['score'], inn1['score']
        a_won = inn2['score'] > target

    return {'a_score': a_score, 'b_score': b_score, 'target': target, 'a_won': a_won}


def simulate_match(
    cpu_engine,
    bot,
    db_prior: Dict[int, float],
    confidence: float = 0.5,
    total_overs: int = 2,
) -> Dict:
    """
    Simulate a full 2-innings match. Who bats first is decided randomly.

    Returns a dict with:
        cpu_bat_inn   — stats from the innings where CPU was batting
        bot_bat_inn   — stats from the innings where the bot was batting
        cpu_score     — CPU's batting total
        bot_score     — bot's batting total
        target        — score set by innings-1 side
        cpu_won       — bool
        cpu_bats_first — bool
    """
    cpu_bats_first = random.random() < 0.5

    if cpu_bats_first:
        # Innings 1: CPU bats, bot bowls
        inn1 = simulate_innings(cpu_engine, 'batting', bot, db_prior,
                                confidence, total_overs, target=None, batting_first=True)
        target = inn1['score']
        # Innings 2: bot bats (chases), CPU bowls
        inn2 = simulate_innings(cpu_engine, 'bowling', bot, db_prior,
                                confidence, total_overs, target=target, batting_first=False)
        cpu_won = inn2['score'] <= target   # bot failed to beat CPU's total
        return {
            'cpu_bat_inn':    inn1,
            'bot_bat_inn':    inn2,
            'cpu_score':      inn1['score'],
            'bot_score':      inn2['score'],
            'target':         target,
            'cpu_won':        cpu_won,
            'cpu_bats_first': True,
        }
    else:
        # Innings 1: bot bats, CPU bowls
        inn1 = simulate_innings(cpu_engine, 'bowling', bot, db_prior,
                                confidence, total_overs, target=None, batting_first=True)
        target = inn1['score']
        # Innings 2: CPU bats (chases), bot bowls
        inn2 = simulate_innings(cpu_engine, 'batting', bot, db_prior,
                                confidence, total_overs, target=target, batting_first=False)
        cpu_won = inn2['score'] > target    # CPU beat bot's total
        return {
            'cpu_bat_inn':    inn2,
            'bot_bat_inn':    inn1,
            'cpu_score':      inn2['score'],
            'bot_score':      inn1['score'],
            'target':         target,
            'cpu_won':        cpu_won,
            'cpu_bats_first': False,
        }
