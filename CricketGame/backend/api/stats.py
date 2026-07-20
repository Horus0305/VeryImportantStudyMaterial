import json
import re
from datetime import datetime
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from ..cpu.cpu_strategy_engine import CPUStrategyEngine
from ..data.database import get_db
from ..data.models import MatchHistory, Player, TournamentHistory

router = APIRouter(prefix="/api", tags=["stats"])
_cpu_status_engine = CPUStrategyEngine()

SEASON_1_CUTOFF = datetime(2026, 7, 20, 0, 0, 0)


def _json_list(raw) -> list[str]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def _winner_includes_player(winner: str | None, player: str) -> bool:
    if not winner or winner == "TIE":
        return False
    names = [n.strip() for n in winner.split(",") if n.strip()]
    if not names:
        return False
    if len(names) == 1:
        return names[0] == player
    return player in names


def _player_recent_form(player: str, db: Session, limit: int = 6) -> list[str]:
    rows = (
        db.query(MatchHistory)
        .filter(
            or_(
                text("exists (select 1 from json_each(side_a) where value = :player)"),
                text("exists (select 1 from json_each(side_b) where value = :player)")
            )
        )
        .order_by(MatchHistory.timestamp.desc())
        .limit(limit)
        .params(player=player)
        .all()
    )
    results = []
    for m in rows:
        if m.winner == "TIE":
            results.append("T")
        elif _winner_includes_player(m.winner, player):
            results.append("W")
        else:
            results.append("L")
    return results


@router.get("/match/{match_id}")
def get_match_detail(match_id: str, db: Session = Depends(get_db)):
    match = db.query(MatchHistory).filter(MatchHistory.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match.to_dict()


@router.get("/matches/{username}")
def get_user_matches(username: str, mode: str = Query(None), season: str = Query("2"), limit: int = 100, db: Session = Depends(get_db)):
    MAIN_HUMANS = {"AniketKS", "Atharva", "Sahil", "Yash", "Meet", "Atharva Kolekar", "hetvig04"}
    
    t_query = db.query(TournamentHistory)
    if season == "1":
        t_query = t_query.filter(TournamentHistory.timestamp < SEASON_1_CUTOFF)
    elif season == "2":
        t_query = t_query.filter(TournamentHistory.timestamp >= SEASON_1_CUTOFF)

    all_tournaments = t_query.all()
    valid_tournament_ids = set()
    for t in all_tournaments:
        players = _json_list(t.players)
        intersect = set(players) & MAIN_HUMANS
        if len(intersect) >= 2:
            valid_tournament_ids.add(t.tournament_id)

    query = db.query(MatchHistory).filter(
        or_(
            text("exists (select 1 from json_each(side_a) where value = :username)"),
            text("exists (select 1 from json_each(side_b) where value = :username)")
        )
    )
    if season == "1":
        query = query.filter(MatchHistory.timestamp < SEASON_1_CUTOFF)
    elif season == "2":
        query = query.filter(MatchHistory.timestamp >= SEASON_1_CUTOFF)

    if mode:
        if mode == "team":
            query = query.filter(or_(MatchHistory.mode == "team", MatchHistory.mode == "2v2"))
        else:
            query = query.filter(MatchHistory.mode == mode)

    rows = query.order_by(MatchHistory.timestamp.desc()).params(username=username).all()
    out = []
    safe_limit = min(max(limit, 0), 500)
    if safe_limit == 0:
        return out
    for m in rows:
        if m.mode == "tournament" and m.tournament_id not in valid_tournament_ids:
            continue
        side_a = _json_list(m.side_a)
        side_b = _json_list(m.side_b)
        if username in side_a or username in side_b:
            out.append(m.to_dict())
            if len(out) >= safe_limit:
                break
    return out


@router.get("/tournament/{tournament_id}")
def get_tournament_detail(tournament_id: str, db: Session = Depends(get_db)):
    tournament = db.query(TournamentHistory).filter(
        TournamentHistory.tournament_id == tournament_id
    ).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    matches = (
        db.query(MatchHistory)
        .filter(MatchHistory.tournament_id == tournament_id)
        .order_by(MatchHistory.timestamp.asc())
        .all()
    )
    result = tournament.to_dict()
    result["matches"] = [m.to_dict() for m in matches]
    return result


@router.get("/tournaments/{username}")
def get_user_tournaments(username: str, season: str = Query("2"), limit: int = 100, db: Session = Depends(get_db)):
    MAIN_HUMANS = {"AniketKS", "Atharva", "Sahil", "Yash", "Meet", "Atharva Kolekar", "hetvig04"}
    query = db.query(TournamentHistory)
    if season == "1":
        query = query.filter(TournamentHistory.timestamp < SEASON_1_CUTOFF)
    elif season == "2":
        query = query.filter(TournamentHistory.timestamp >= SEASON_1_CUTOFF)

    rows = query.order_by(TournamentHistory.timestamp.desc()).all()
    out = []
    safe_limit = min(max(limit, 0), 500)
    if safe_limit == 0:
        return out
    for t in rows:
        players = _json_list(t.players)
        # Check if tournament is valid (>= 2 main humans)
        intersect = set(players) & MAIN_HUMANS
        if len(intersect) < 2:
            continue
        if username in players:
            out.append(t.to_dict())
            if len(out) >= safe_limit:
                break
    return out


@router.get("/head-to-head/{player1}/{player2}")
def get_head_to_head(player1: str, player2: str, db: Session = Depends(get_db)):
    rows = (
        db.query(MatchHistory)
        .filter(
            or_(
                text("exists (select 1 from json_each(side_a) where value = :player1)"),
                text("exists (select 1 from json_each(side_b) where value = :player1)")
            )
        )
        .filter(
            or_(
                text("exists (select 1 from json_each(side_a) where value = :player2)"),
                text("exists (select 1 from json_each(side_b) where value = :player2)")
            )
        )
        .order_by(MatchHistory.timestamp.desc())
        .params(player1=player1, player2=player2)
        .all()
    )
    matches: list[tuple[MatchHistory, list[str], list[str]]] = []
    for m in rows:
        side_a = _json_list(m.side_a)
        side_b = _json_list(m.side_b)
        p1_side = "a" if player1 in side_a else "b" if player1 in side_b else None
        p2_side = "a" if player2 in side_a else "b" if player2 in side_b else None
        if p1_side and p2_side and p1_side != p2_side:
            matches.append((m, side_a, side_b))

    if not matches:
        return {"has_history": False}

    def _empty():
        return {
            "wins": 0, "losses": 0, "ties": 0,
            "batting_best": 0, "batting_total_runs": 0, "batting_total_balls": 0,
            "batting_innings": 0,
            "bowling_best_w": 0, "bowling_best_r": 999,
            "bowling_total_wickets": 0, "bowling_total_runs_conceded": 0,
            "bowling_innings": 0,
        }

    stats = {player1: _empty(), player2: _empty()}
    for m, side_a, side_b in matches:
        p1_side = "a" if player1 in side_a else "b"
        p2_side = "a" if player2 in side_a else "b"
        if p1_side == p2_side:
            continue

        winner = m.winner
        if winner == "TIE":
            stats[player1]["ties"] += 1
            stats[player2]["ties"] += 1
        elif _winner_includes_player(winner, player1):
            stats[player1]["wins"] += 1
            stats[player2]["losses"] += 1
        elif _winner_includes_player(winner, player2):
            stats[player2]["wins"] += 1
            stats[player1]["losses"] += 1

        for sc_col in ["scorecard_1", "scorecard_2"]:
            sc_raw = getattr(m, sc_col)
            if not sc_raw:
                continue
            try:
                sc = json.loads(sc_raw) if isinstance(sc_raw, str) else sc_raw
            except Exception:
                continue

            batting_cards = sc.get("batting", [])
            bowling_cards = sc.get("bowling", [])

            for p in [player1, player2]:
                for bc in batting_cards:
                    if bc.get("name") == p:
                        runs = bc.get("runs", 0)
                        balls = bc.get("balls", 0)
                        stats[p]["batting_total_runs"] += runs
                        stats[p]["batting_total_balls"] += balls
                        stats[p]["batting_innings"] += 1
                        if runs > stats[p]["batting_best"]:
                            stats[p]["batting_best"] = runs

                for bw in bowling_cards:
                    if bw.get("name") == p:
                        w = bw.get("wickets", 0)
                        r = bw.get("runs", 0)
                        stats[p]["bowling_total_wickets"] += w
                        stats[p]["bowling_total_runs_conceded"] += r
                        stats[p]["bowling_innings"] += 1
                        if w > stats[p]["bowling_best_w"] or (
                            w == stats[p]["bowling_best_w"] and r < stats[p]["bowling_best_r"]
                        ):
                            stats[p]["bowling_best_w"] = w
                            stats[p]["bowling_best_r"] = r

    def _format(p: str):
        s = stats[p]
        avg = round(s["batting_total_runs"] / s["batting_innings"], 2) if s["batting_innings"] > 0 else 0.0
        sr = round((s["batting_total_runs"] / s["batting_total_balls"]) * 100, 2) if s["batting_total_balls"] > 0 else 0.0
        best_bowl = f"{s['bowling_best_w']}/{s['bowling_best_r']}" if s["bowling_best_w"] > 0 else "0/0"
        return {
            "wins": s["wins"], "losses": s["losses"], "ties": s["ties"],
            "batting_best": s["batting_best"], "batting_avg": avg,
            "avg_strike_rate": sr, "bowling_best": best_bowl,
        }

    h2h_form: list[str] = []
    for m, _sa, _sb in matches[:6]:
        if m.winner == "TIE":
            h2h_form.append("T")
        elif _winner_includes_player(m.winner, player1):
            h2h_form.append("W")
        else:
            h2h_form.append("L")

    form = {
        player1: _player_recent_form(player1, db),
        player2: _player_recent_form(player2, db),
    }

    return {
        "has_history": True,
        "total_matches": len(matches),
        player1: _format(player1),
        player2: _format(player2),
        "h2h_form": h2h_form,
        "form": form,
    }


def _extract_bowler(dismissal: str | None) -> str | None:
    """Parse bowler name from dismissal text like 'b Alice', 'c Bob b Alice', 'lbw b Alice'."""
    if not dismissal:
        return None
    idx = dismissal.rfind(" b ")
    if idx >= 0:
        return dismissal[idx + 3:].strip() or None
    if dismissal.startswith("b "):
        return dismissal[2:].strip() or None
    return None


def _parse_run_margin(result_text: str | None) -> int | None:
    """Extract run margin from 'X won by N runs'. Returns None for wicket wins or ties."""
    if not result_text:
        return None
    m = re.search(r"won by (\d+) run", result_text, re.IGNORECASE)
    return int(m.group(1)) if m else None


@router.get("/leaderboard")
def get_leaderboard(limit: int = 50, season: str = Query("2"), db: Session = Depends(get_db)):
    entries: dict[str, dict] = {}

    # Per-player tracking structures
    player_innings = defaultdict(list)
    player_not_out = defaultdict(int)
    player_dismissals = defaultdict(int)
    player_bat_balls = defaultdict(int)
    player_chasing_runs = defaultdict(int)
    player_chasing_inn = defaultdict(int)
    player_bowl_wkts = defaultdict(int)
    player_bowl_runs = defaultdict(int)
    player_bowl_balls = defaultdict(int)
    player_bowl_best_w = defaultdict(int)
    player_bowl_best_r = defaultdict(lambda: 999)

    ALLOWED_LEADERBOARD_PLAYERS = ["AniketKS", "Atharva", "CPU", "Sahil", "Yash", "Meet", "Atharva Kolekar", "hetvig04"]
    MAIN_HUMANS = {"AniketKS", "Atharva", "Sahil", "Yash", "Meet", "Atharva Kolekar", "hetvig04"}

    # Always initialize entries for all 8 main players so Season 2 has clean rows ready
    for p in ALLOWED_LEADERBOARD_PLAYERS:
        entries[p] = {
            "username":           p,
            "matches_played":     0,
            "matches_won":        0,
            "matches_lost":       0,
            "win_pct":            0.0,
            "total_runs":         0,
            "highest_score":      0,
            "batting_avg":        0.0,
            "strike_rate":        0.0,
            "fours":              0,
            "sixes":              0,
            "boundaries":         0,
            "fifties":            0,
            "hundreds":           0,
            "wickets_taken":      0,
            "best_bowling":       "—",
            "bowling_avg":        None,
            "economy":            None,
            "potm_count":         0,
            "tournaments_won":    0,
            "tournaments_played": 0,
            "playoffs_reached":    0,
            "finals_reached":      0,
            "total_balls":         0,
            "ducks":               0,
            "ducks_taken":         0,
            "close_losses":        0,
            "heavy_losses":        0,
            "six_shower":          0,
            "max_duck_streak":     0,
            "not_out_pct":         0.0,
            "miser_innings":       0,
            "chasing_avg":         0.0,
            "wickets_per_ball":    0.0,
            "balls_per_dismissal": 0.0,
            "finals_lost":         0,
        }

    # Dynamically find valid tournament IDs (having >= 2 main human players) filtered by season
    t_query = db.query(TournamentHistory)
    if season == "1":
        t_query = t_query.filter(TournamentHistory.timestamp < SEASON_1_CUTOFF)
    elif season == "2":
        t_query = t_query.filter(TournamentHistory.timestamp >= SEASON_1_CUTOFF)

    all_tournaments = t_query.all()
    valid_tournament_ids = set()
    for t in all_tournaments:
        players = _json_list(t.players)
        intersect = set(players) & MAIN_HUMANS
        if len(intersect) >= 2:
            valid_tournament_ids.add(t.tournament_id)

    # ── 1. Scan MatchHistory for Tournament matches ──────────────────────
    m_query = db.query(MatchHistory).filter(MatchHistory.mode == 'tournament')
    if season == "1":
        m_query = m_query.filter(MatchHistory.timestamp < SEASON_1_CUTOFF)
    elif season == "2":
        m_query = m_query.filter(MatchHistory.timestamp >= SEASON_1_CUTOFF)

    all_matches = m_query.order_by(MatchHistory.timestamp.asc()).all()

    for match in all_matches:
        if match.tournament_id not in valid_tournament_ids:
            continue

        side_a = _json_list(match.side_a)
        side_b = _json_list(match.side_b)
        margin = _parse_run_margin(match.result_text)

        all_players_in_match = set(side_a + side_b)

        # Initialize player entries on-the-fly
        for p in all_players_in_match:
            if p not in ALLOWED_LEADERBOARD_PLAYERS:
                continue
            if p not in entries:
                entries[p] = {
                    "username":           p,
                    "matches_played":     0,
                    "matches_won":        0,
                    "matches_lost":       0,
                    "win_pct":            0.0,
                    "total_runs":         0,
                    "highest_score":      0,
                    "batting_avg":        0.0,
                    "strike_rate":        0.0,
                    "fours":              0,
                    "sixes":              0,
                    "boundaries":         0,
                    "fifties":            0,
                    "hundreds":           0,
                    "wickets_taken":      0,
                    "best_bowling":       "—",
                    "bowling_avg":        None,
                    "economy":            None,
                    "potm_count":         0,
                    "tournaments_won":    0,
                    "tournaments_played": 0,
                    "playoffs_reached":    0,
                    "finals_reached":      0,
                    "total_balls":         0,
                    "ducks":               0,
                    "ducks_taken":         0,
                    "close_losses":        0,
                    "heavy_losses":        0,
                    "six_shower":          0,
                    "max_duck_streak":     0,
                    "not_out_pct":         0.0,
                    "miser_innings":       0,
                    "chasing_avg":         0.0,
                    "wickets_per_ball":    0.0,
                    "balls_per_dismissal": 0.0,
                    "finals_lost":         0,
                }

        # Track win / loss
        for p in all_players_in_match:
            if p not in entries:
                continue
            entries[p]["matches_played"] += 1
            if match.winner == "TIE":
                pass
            elif _winner_includes_player(match.winner, p):
                entries[p]["matches_won"] += 1
            else:
                entries[p]["matches_lost"] += 1

        if match.potm and match.potm in entries:
            entries[match.potm]["potm_count"] += 1

        # Track close/heavy losses
        losing_side: list[str] = []
        if match.winner and match.winner != "TIE" and margin is not None:
            winner_names = {n.strip() for n in match.winner.split(",") if n.strip()}
            if winner_names & set(side_a):
                losing_side = side_b
            elif winner_names & set(side_b):
                losing_side = side_a

        if losing_side and margin is not None:
            for p in losing_side:
                if p in entries:
                    if margin < 10:
                        entries[p]["close_losses"] += 1
                    if margin > 30:
                        entries[p]["heavy_losses"] += 1

        # Scan scorecards
        for sc_idx, sc_col in enumerate(("scorecard_1", "scorecard_2")):
            sc_raw = getattr(match, sc_col)
            if not sc_raw:
                continue
            try:
                sc = json.loads(sc_raw) if isinstance(sc_raw, str) else sc_raw
            except Exception:
                continue

            is_chasing = (sc_col == "scorecard_2")
            batting_cards = sc.get("batting", [])
            batter_names = {bc.get("name") for bc in batting_cards if bc.get("name")}

            # Determine bowling side for this innings
            batting_side = side_a if (batter_names & set(side_a)) else side_b
            bowling_side = side_b if batting_side is side_a else side_a

            # Count sixes in this innings
            innings_sixes = sum(bc.get("sixes", 0) for bc in batting_cards)
            if innings_sixes >= 3:
                for p in bowling_side:
                    if p in entries:
                        entries[p]["six_shower"] += 1

            # Batting card stats
            for bc in batting_cards:
                name = bc.get("name")
                if not name or name not in entries:
                    continue

                is_out = bc.get("is_out", False)
                is_duck = bc.get("runs", -1) == 0 and is_out
                player_innings[name].append(is_duck)

                runs = bc.get("runs", 0)
                balls = bc.get("balls", 0)

                entries[name]["total_runs"] += runs
                entries[name]["total_balls"] += balls
                entries[name]["fours"] += bc.get("fours", 0)
                entries[name]["sixes"] += bc.get("sixes", 0)
                entries[name]["boundaries"] += bc.get("fours", 0) + bc.get("sixes", 0)

                if runs > entries[name]["highest_score"]:
                    entries[name]["highest_score"] = runs
                if runs >= 100:
                    entries[name]["hundreds"] += 1
                elif runs >= 50:
                    entries[name]["fifties"] += 1

                if is_duck:
                    entries[name]["ducks"] += 1
                    bowler = _extract_bowler(bc.get("dismissal"))
                    if bowler and bowler in entries:
                        entries[bowler]["ducks_taken"] += 1

                if is_out:
                    player_dismissals[name] += 1
                else:
                    player_not_out[name] += 1

                player_bat_balls[name] += balls
                if is_chasing:
                    player_chasing_runs[name] += runs
                    player_chasing_inn[name] += 1

            # Bowling card stats
            for bw in sc.get("bowling", []):
                name = bw.get("name")
                if not name or name not in entries:
                    continue
                wkts = bw.get("wickets", 0)
                runs_b = bw.get("runs", 0)
                overs_str = str(bw.get("overs", "0"))
                parts = overs_str.split(".")
                balls_b = int(parts[0]) * 6 + (int(parts[1]) if len(parts) > 1 and parts[1] else 0)
                overs_f = balls_b / 6

                player_bowl_wkts[name] += wkts
                player_bowl_runs[name] += runs_b
                player_bowl_balls[name] += balls_b

                if wkts > player_bowl_best_w[name] or (
                    wkts == player_bowl_best_w[name] and runs_b < player_bowl_best_r[name]
                ):
                    player_bowl_best_w[name] = wkts
                    player_bowl_best_r[name] = runs_b

                if overs_f >= 1.0 and runs_b / overs_f <= 8.0:
                    entries[name]["miser_innings"] += 1

    # ── 2. Finalize basic stats & averages ───────────────────────────────────
    for p in list(entries.keys()):
        e = entries[p]
        e["win_pct"] = round(e["matches_won"] / e["matches_played"] * 100, 1) if e["matches_played"] else 0.0

        # Batting avg and strike rate
        total_inn = player_not_out[p] + player_dismissals[p]
        e["batting_avg"] = round(e["total_runs"] / player_dismissals[p], 2) if player_dismissals[p] else (float(e["total_runs"]) if total_inn else 0.0)
        e["strike_rate"] = round(e["total_runs"] / e["total_balls"] * 100, 1) if e["total_balls"] else 0.0

        # Bowling stats
        wkts = player_bowl_wkts[p]
        runs_c = player_bowl_runs[p]
        balls_c = player_bowl_balls[p]
        e["wickets_taken"] = wkts
        best_w = player_bowl_best_w[p]
        best_r = player_bowl_best_r[p]
        e["best_bowling"] = f"{best_w}/{best_r}" if best_w > 0 else "—"
        e["bowling_avg"] = round(runs_c / wkts, 2) if wkts else None
        e["economy"] = round((runs_c / balls_c) * 6, 2) if balls_c else None

        # Duck streaks
        max_streak = cur = 0
        for is_duck in player_innings[p]:
            cur = cur + 1 if is_duck else 0
            if cur > max_streak:
                max_streak = cur
        e["max_duck_streak"] = max_streak

        # Advanced stats threshold checks
        if total_inn >= 50:
            e["not_out_pct"] = round(player_not_out[p] / total_inn * 100, 1)
        if player_chasing_inn[p] >= 30:
            e["chasing_avg"] = round(player_chasing_runs[p] / player_chasing_inn[p], 2)
        if wkts >= 20 and balls_c > 0:
            e["wickets_per_ball"] = round(wkts / balls_c, 4)
        if player_dismissals[p] >= 30:
            e["balls_per_dismissal"] = round(player_bat_balls[p] / player_dismissals[p], 1)

    for t in db.query(TournamentHistory).all():
        if t.tournament_id not in valid_tournament_ids:
            continue
        try:
            players_list = _json_list(t.players)
            bracket = json.loads(t.playoff_bracket) if t.playoff_bracket else {}

            for player in players_list:
                if player in entries:
                    entries[player]["tournaments_played"] += 1

            if t.champion and t.champion in entries:
                entries[t.champion]["tournaments_won"] += 1

            # Finalists
            final_pair = bracket.get("final") or []
            for player in final_pair:
                if player in entries:
                    entries[player]["finals_reached"] += 1

            if len(final_pair) == 2 and t.champion and t.champion in final_pair:
                runner_up = final_pair[0] if final_pair[1] == t.champion else final_pair[1]
                if runner_up in entries:
                    entries[runner_up]["finals_lost"] += 1

            # Playoff reaches (Q1, Elim, Q2, or Final participants)
            playoff_players = set()
            for key in ["qualifier_1", "eliminator", "qualifier_2", "final"]:
                match_pair = bracket.get(key)
                if match_pair:
                    for player in match_pair:
                        if player:
                            playoff_players.add(player)

            for player in playoff_players:
                if player in entries:
                    entries[player]["playoffs_reached"] += 1
        except Exception:
            pass

    result = sorted(entries.values(), key=lambda x: (-x["total_runs"], -x["highest_score"]))
    return {"leaderboard": result[:min(max(limit, 1), 200)]}


@router.get("/cpu-status/{username}")
def get_cpu_status(username: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.username == username).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return _cpu_status_engine.get_cpu_status(player.id)
