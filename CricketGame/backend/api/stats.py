import json
import re
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..cpu.cpu_strategy_engine import CPUStrategyEngine
from ..data.database import get_db
from ..data.models import MatchHistory, Player, TournamentHistory

router = APIRouter(prefix="/api", tags=["stats"])
_cpu_status_engine = CPUStrategyEngine()


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


@router.get("/match/{match_id}")
def get_match_detail(match_id: str, db: Session = Depends(get_db)):
    match = db.query(MatchHistory).filter(MatchHistory.match_id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match.to_dict()


@router.get("/matches/{username}")
def get_user_matches(username: str, mode: str = Query(None), limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(MatchHistory).filter(
        or_(
            MatchHistory.side_a.contains(username),
            MatchHistory.side_b.contains(username),
        )
    )
    if mode:
        if mode == "team":
            query = query.filter(or_(MatchHistory.mode == "team", MatchHistory.mode == "2v2"))
        else:
            query = query.filter(MatchHistory.mode == mode)

    rows = query.order_by(MatchHistory.timestamp.desc()).all()
    out = []
    safe_limit = min(max(limit, 0), 500)
    if safe_limit == 0:
        return out
    for m in rows:
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
def get_user_tournaments(username: str, limit: int = 100, db: Session = Depends(get_db)):
    rows = (
        db.query(TournamentHistory)
        .order_by(TournamentHistory.timestamp.desc())
        .all()
    )
    out = []
    safe_limit = min(max(limit, 0), 500)
    if safe_limit == 0:
        return out
    for t in rows:
        players = _json_list(t.players)
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
                MatchHistory.side_a.contains(player1),
                MatchHistory.side_b.contains(player1),
            )
        )
        .filter(
            or_(
                MatchHistory.side_a.contains(player2),
                MatchHistory.side_b.contains(player2),
            )
        )
        .order_by(MatchHistory.timestamp.desc())
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

    return {
        "has_history": True,
        "total_matches": len(matches),
        player1: _format(player1),
        player2: _format(player2),
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
def get_leaderboard(limit: int = 50, db: Session = Depends(get_db)):
    from ..data.models import FormatStats
    from datetime import datetime as _dt

    players = db.query(Player).all()
    entries: dict[str, dict] = {}

    # ── 1. Aggregate FormatStats ──────────────────────────────────
    for player in players:
        rows = db.query(FormatStats).filter(
            FormatStats.player_id == player.id,
            FormatStats.format == 'tournament',
        ).all()
        if not rows:
            continue
        mp = sum(r.matches_played for r in rows)
        if mp < 1:
            continue

        mw         = sum(r.matches_won for r in rows)
        runs       = sum(r.total_runs for r in rows)
        balls      = sum(r.total_balls_faced for r in rows)
        hs         = max((r.highest_score for r in rows), default=0)
        fours      = sum(r.fours for r in rows)
        sixes      = sum(r.sixes for r in rows)
        fifties    = sum(r.fifties for r in rows)
        hundreds   = sum(r.hundreds for r in rows)
        innings_b  = sum(r.innings_batted for r in rows)
        wickets    = sum(r.wickets_taken for r in rows)
        r_conceded = sum(r.runs_conceded for r in rows)
        overs      = sum(r.overs_bowled for r in rows)
        potm       = sum(r.potm_count for r in rows)
        t_won      = sum(r.tournaments_won for r in rows)
        t_played   = sum(r.tournaments_played for r in rows)

        best_w, best_r = 0, 999
        for r in rows:
            if r.best_bowling_wickets > best_w or (
                r.best_bowling_wickets == best_w and r.best_bowling_runs < best_r
            ):
                best_w, best_r = r.best_bowling_wickets, r.best_bowling_runs

        entries[player.username] = {
            "username":           player.username,
            "matches_played":     mp,
            "matches_won":        mw,
            "matches_lost":       mp - mw,
            "win_pct":            round(mw / mp * 100, 1),
            "total_runs":         runs,
            "highest_score":      hs,
            "batting_avg":        round(runs / innings_b, 2) if innings_b else 0.0,
            "strike_rate":        round(runs / balls * 100, 1) if balls else 0.0,
            "fours":              fours,
            "sixes":              sixes,
            "boundaries":         fours + sixes,
            "fifties":            fifties,
            "hundreds":           hundreds,
            "wickets_taken":      wickets,
            "best_bowling":       f"{best_w}/{best_r}" if best_w else "—",
            "bowling_avg":        round(r_conceded / wickets, 2) if wickets else None,
            "economy":            round(r_conceded / overs, 2) if overs else None,
            "potm_count":         potm,
            "tournaments_won":    t_won,
            "tournaments_played": t_played,
            # computed from MatchHistory / TournamentHistory below
            "playoffs_reached":    0,
            "finals_reached":      0,
            "total_balls":         balls,
            "ducks":               0,
            "ducks_taken":         0,
            "close_losses":        0,   # lost by < 10 runs
            "heavy_losses":        0,   # lost by > 30 runs
            "six_shower":          0,   # innings where bowling side conceded 3+ sixes
            "max_duck_streak":     0,   # longest consecutive duck streak
            "not_out_pct":         0.0,
            "miser_innings":       0,
            "chasing_avg":         0.0,
            "wickets_per_ball":    0.0,
            "balls_per_dismissal": 0.0,
            "finals_lost":         0,
        }

    # Per-player chronological innings for duck streak calculation
    player_innings: dict[str, list[bool]] = defaultdict(list)

    # Tracking dicts for new stats
    player_not_out:      dict[str, int] = defaultdict(int)
    player_dismissals:   dict[str, int] = defaultdict(int)
    player_bat_balls:    dict[str, int] = defaultdict(int)
    player_chasing_runs: dict[str, int] = defaultdict(int)
    player_chasing_inn:  dict[str, int] = defaultdict(int)
    player_bowl_wkts:    dict[str, int] = defaultdict(int)
    player_bowl_balls:   dict[str, int] = defaultdict(int)

    # ── 2. Scan MatchHistory ──────────────────────────────────────
    all_matches = (
        db.query(MatchHistory)
        .filter(MatchHistory.mode == 'tournament')
        .order_by(MatchHistory.timestamp.asc())
        .all()
    )

    for match in all_matches:
        side_a = _json_list(match.side_a)
        side_b = _json_list(match.side_b)
        margin = _parse_run_margin(match.result_text)

        # Determine losing side for close/heavy loss stats
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

            for bc in batting_cards:
                name = bc.get("name")
                if not name or name not in entries:
                    continue

                is_out = bc.get("is_out", False)
                is_duck = bc.get("runs", -1) == 0 and is_out
                player_innings[name].append(is_duck)

                if is_duck:
                    entries[name]["ducks"] += 1
                    bowler = _extract_bowler(bc.get("dismissal"))
                    if bowler and bowler in entries:
                        entries[bowler]["ducks_taken"] += 1

                # New stat tracking
                if is_out:
                    player_dismissals[name] += 1
                else:
                    player_not_out[name] += 1
                player_bat_balls[name] += bc.get("balls", 0)
                if is_chasing:
                    player_chasing_runs[name] += bc.get("runs", 0)
                    player_chasing_inn[name] += 1

            # Bowling card — The Miser + The Oracle
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
                player_bowl_balls[name] += balls_b
                if overs_f >= 1.0 and runs_b / overs_f <= 8.0:
                    entries[name]["miser_innings"] += 1

    # ── 3. Compute max consecutive duck streak ────────────────────
    for player, innings_list in player_innings.items():
        if player not in entries:
            continue
        max_streak = cur = 0
        for is_duck in innings_list:
            cur = cur + 1 if is_duck else 0
            if cur > max_streak:
                max_streak = cur
        entries[player]["max_duck_streak"] = max_streak

    # ── 4. Finalize new computed stats ────────────────────────────
    for player in list(entries.keys()):
        e = entries[player]
        total_inn = player_not_out[player] + player_dismissals[player]
        if total_inn >= 50:
            e["not_out_pct"] = round(player_not_out[player] / total_inn * 100, 1)
        if player_chasing_inn[player] >= 30:
            e["chasing_avg"] = round(player_chasing_runs[player] / player_chasing_inn[player], 2)
        if player_bowl_wkts[player] >= 20 and player_bowl_balls[player] > 0:
            e["wickets_per_ball"] = round(player_bowl_wkts[player] / player_bowl_balls[player], 4)
        if player_dismissals[player] >= 30:
            e["balls_per_dismissal"] = round(player_bat_balls[player] / player_dismissals[player], 1)

    # ── 5. Playoff / Final achievements — scan TournamentHistory ──
    for t in db.query(TournamentHistory).all():
        try:
            bracket = json.loads(t.playoff_bracket) if t.playoff_bracket else {}
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
