from typing import Dict, List
from collections import defaultdict
from .match import Match


def compute_potm(match: Match) -> dict:
    all_players = match.side_a + match.side_b
    scores: Dict[str, dict] = {}

    for player_name in all_players:
        runs = 0
        balls_faced = 0
        wickets = 0
        runs_conceded = 0
        overs_bowled = 0.0

        for inn in [match.innings_1, match.innings_2]:
            if not inn:
                continue
            if player_name in inn.batting_cards:
                card = inn.batting_cards[player_name]
                runs += card.runs
                balls_faced += card.balls
            if player_name in inn.bowling_cards:
                card = inn.bowling_cards[player_name]
                wickets += card.wickets
                runs_conceded += card.runs_conceded
                overs_bowled += card.overs_completed + card.balls_bowled_in_over / 6

        sr = (runs / balls_faced * 100) if balls_faced > 0 else 0.0
        sr_bonus = max(0, (sr - 100) * 0.1) if balls_faced >= 3 else 0
        econ = (runs_conceded / overs_bowled) if overs_bowled > 0 else 99
        econ_bonus = max(0, (8.0 - econ) * 3) if overs_bowled >= 1 else 0
        is_winner = match.winner and player_name in match.winner
        win_bonus = 10 if is_winner else 0

        total_score = (
            runs * 1.0
            + wickets * 25
            + sr_bonus
            + econ_bonus
            + win_bonus
        )

        scores[player_name] = {
            "player": player_name,
            "score": round(total_score, 1),
            "runs": runs,
            "balls": balls_faced,
            "wickets": wickets,
            "sr": round(sr, 1),
            "economy": round(econ, 1) if overs_bowled > 0 else None,
        }

    best = max(scores.values(), key=lambda x: x["score"])
    parts = []
    if best["runs"] > 0:
        parts.append(f"{best['runs']}({best['balls']})")
    if best["wickets"] > 0:
        parts.append(f"{best['wickets']} wkt(s)")
    summary = " & ".join(parts) if parts else "All-round contribution"

    return {
        "player": best["player"],
        "score": best["score"],
        "summary": summary,
        "runs": best["runs"],
        "balls": best["balls"],
        "wickets": best["wickets"],
        "sr": best["sr"],
        "economy": best["economy"],
    }


def compute_tournament_awards(match_scorecards: List[dict]) -> dict:
    stats: Dict[str, dict] = defaultdict(lambda: {
        "runs": 0, "balls": 0, "wickets": 0,
        "runs_conceded": 0, "overs": 0.0,
        "innings_bat": 0, "dismissals": 0,
    })

    for match_data in match_scorecards:
        for sc_key in ["scorecard_1", "scorecard_2"]:
            sc = match_data.get(sc_key)
            if not sc:
                continue
            for bat in sc.get("batting", []):
                name = bat["name"]
                s = stats[name]
                s["runs"] += bat.get("runs", 0)
                s["balls"] += bat.get("balls", 0)
                s["innings_bat"] += 1
                if bat.get("is_out", False):
                    s["dismissals"] += 1
            for bowl in sc.get("bowling", []):
                name = bowl["name"]
                s = stats[name]
                s["wickets"] += bowl.get("wickets", 0)
                s["runs_conceded"] += bowl.get("runs", 0)
                overs_str = str(bowl.get("overs", "0"))
                if "." in overs_str:
                    whole, frac = overs_str.split(".")
                    s["overs"] += int(whole) + int(frac) / 6
                else:
                    s["overs"] += float(overs_str)

    orange_cap = None
    if stats:
        best_bat = max(stats.items(), key=lambda x: x[1]["runs"])
        if best_bat[1]["runs"] > 0:
            s = best_bat[1]
            orange_cap = {
                "player": best_bat[0],
                "runs": s["runs"],
                "balls": s["balls"],
                "sr": round(s["runs"] / s["balls"] * 100, 1) if s["balls"] > 0 else 0,
            }

    purple_cap = None
    if stats:
        best_bowl = max(stats.items(), key=lambda x: x[1]["wickets"])
        if best_bowl[1]["wickets"] > 0:
            s = best_bowl[1]
            purple_cap = {
                "player": best_bowl[0],
                "wickets": s["wickets"],
                "overs": round(s["overs"], 1),
                "economy": round(s["runs_conceded"] / s["overs"], 1) if s["overs"] > 0 else 0,
            }

    best_sr = None
    sr_candidates = [(n, s) for n, s in stats.items() if s["balls"] >= 10]
    if sr_candidates:
        top = max(sr_candidates, key=lambda x: x[1]["runs"] / x[1]["balls"] if x[1]["balls"] > 0 else 0)
        s = top[1]
        sr_val = round(s["runs"] / s["balls"] * 100, 1) if s["balls"] > 0 else 0
        best_sr = {"player": top[0], "sr": sr_val, "runs": s["runs"], "balls": s["balls"]}

    best_avg = None
    avg_candidates = [(n, s) for n, s in stats.items() if s["innings_bat"] >= 2]
    if avg_candidates:
        def calc_avg(s: dict) -> float:
            if s["dismissals"] > 0:
                return s["runs"] / s["dismissals"]
            return float(s["runs"])
        top = max(avg_candidates, key=lambda x: calc_avg(x[1]))
        s = top[1]
        avg_val = round(calc_avg(s), 1)
        best_avg = {
            "player": top[0], "average": avg_val,
            "runs": s["runs"], "innings": s["innings_bat"], "dismissals": s["dismissals"],
        }

    best_econ = None
    econ_candidates = [(n, s) for n, s in stats.items() if s["overs"] >= 2]
    if econ_candidates:
        top = min(econ_candidates, key=lambda x: x[1]["runs_conceded"] / x[1]["overs"] if x[1]["overs"] > 0 else 999)
        s = top[1]
        econ_val = round(s["runs_conceded"] / s["overs"], 1) if s["overs"] > 0 else 0
        best_econ = {
            "player": top[0], "economy": econ_val,
            "overs": round(s["overs"], 1), "runs_conceded": s["runs_conceded"],
        }

    pot = None
    if stats:
        composite_scores = {}
        for name, s in stats.items():
            score = (
                s["runs"] * 1.0
                + s["wickets"] * 25
                + (max(0, s["runs"] / s["balls"] * 100 - 100) * 0.1 if s["balls"] >= 10 else 0)
                + (max(0, 8.0 - s["runs_conceded"] / s["overs"]) * 3 if s["overs"] >= 2 else 0)
            )
            composite_scores[name] = score

        best_name = max(composite_scores, key=composite_scores.get)
        s = stats[best_name]
        pot = {
            "player": best_name,
            "score": round(composite_scores[best_name], 1),
            "runs": s["runs"],
            "wickets": s["wickets"],
        }

    return {
        "orange_cap": orange_cap,
        "purple_cap": purple_cap,
        "best_strike_rate": best_sr,
        "best_average": best_avg,
        "best_economy": best_econ,
        "player_of_tournament": pot,
    }
