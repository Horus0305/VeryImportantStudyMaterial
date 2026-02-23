"""
Tournament Manager — Round-robin scheduling + IPL-style playoffs.

Playoff format:
  Qualifier 1: #1 vs #2  → Winner → FINAL, Loser → Q2
  Eliminator:  #3 vs #4  → Loser OUT
  Qualifier 2: Loser of Q1 vs Winner of Elim → Winner → FINAL
  FINAL:       Winner Q1 vs Winner Q2
"""

from typing import List, Dict, Optional, Any


class StandingsEntry:
    def __init__(self, player: str):
        self.player = player
        self.played = 0
        self.won = 0
        self.lost = 0
        self.tied = 0
        self.points = 0
        self.runs_scored = 0
        self.overs_faced = 0.0
        self.runs_conceded = 0
        self.overs_bowled = 0.0

    @property
    def nrr(self) -> float:
        """Net Run Rate = (Runs scored / Overs faced) - (Runs conceded / Overs bowled)."""
        scoring_rate = (self.runs_scored / self.overs_faced) if self.overs_faced > 0 else 0
        conceding_rate = (self.runs_conceded / self.overs_bowled) if self.overs_bowled > 0 else 0
        return scoring_rate - conceding_rate

    def to_dict(self) -> dict:
        return {
            "player": self.player, "played": self.played,
            "won": self.won, "lost": self.lost, "tied": self.tied,
            "points": self.points, "nrr": round(self.nrr, 3),
        }


class Tournament:
    """Manages a full tournament lifecycle."""

    # Playoff phase labels
    PHASE_GROUP = "group"
    PHASE_Q1 = "qualifier_1"
    PHASE_ELIM = "eliminator"
    PHASE_Q2 = "qualifier_2"
    PHASE_FINAL = "final"
    PHASE_COMPLETE = "complete"

    def __init__(self, players: List[str], overs: int, wickets: int):
        self.players = players
        self.overs = overs
        self.wickets = wickets

        rounds = self._build_round_robin_rounds(players)
        self.group_matches = self._flatten_rounds(rounds)
        self.current_group_match_idx = 0

        # Standings
        self.standings: Dict[str, StandingsEntry] = {
            p: StandingsEntry(p) for p in players
        }

        # Playoff state
        self.phase = self.PHASE_GROUP
        self.playoff_matches: Dict[str, Optional[tuple]] = {
            self.PHASE_Q1: None,
            self.PHASE_ELIM: None,
            self.PHASE_Q2: None,
            self.PHASE_FINAL: None,
        }
        self.playoff_results: Dict[str, Optional[str]] = {}
        self.champion: Optional[str] = None

    def get_next_group_match(self) -> Optional[tuple]:
        """Return next unplayed group match or None if group stage done."""
        if self.current_group_match_idx < len(self.group_matches):
            return self.group_matches[self.current_group_match_idx]
        return None

    def record_group_result(self, player_a: str, player_b: str,
                            winner: Optional[str], nrr_data: dict) -> None:
        """Record result of a group stage match."""
        sa = self.standings[player_a]
        sb = self.standings[player_b]
        sa.played += 1
        sb.played += 1

        if winner == player_a:
            sa.won += 1
            sa.points += 2
            sb.lost += 1
        elif winner == player_b:
            sb.won += 1
            sb.points += 2
            sa.lost += 1
        else:
            # Tie
            sa.tied += 1
            sb.tied += 1
            sa.points += 1
            sb.points += 1

        # Update NRR data — correctly attribute based on who actually batted first
        # innings_1 = batting_first team, innings_2 = bowling_first team
        batting_first_player = nrr_data.get("batting_first_player")

        if batting_first_player == player_a:
            # player_a batted first (innings 1), player_b batted second (innings 2)
            sa.runs_scored += nrr_data.get("runs_scored_1", 0)
            sa.overs_faced += nrr_data.get("overs_faced_1", 0)
            sa.runs_conceded += nrr_data.get("runs_scored_2", 0)
            sa.overs_bowled += nrr_data.get("overs_faced_2", 0)

            sb.runs_scored += nrr_data.get("runs_scored_2", 0)
            sb.overs_faced += nrr_data.get("overs_faced_2", 0)
            sb.runs_conceded += nrr_data.get("runs_scored_1", 0)
            sb.overs_bowled += nrr_data.get("overs_faced_1", 0)
        else:
            # player_b batted first (innings 1), player_a batted second (innings 2)
            sb.runs_scored += nrr_data.get("runs_scored_1", 0)
            sb.overs_faced += nrr_data.get("overs_faced_1", 0)
            sb.runs_conceded += nrr_data.get("runs_scored_2", 0)
            sb.overs_bowled += nrr_data.get("overs_faced_2", 0)

            sa.runs_scored += nrr_data.get("runs_scored_2", 0)
            sa.overs_faced += nrr_data.get("overs_faced_2", 0)
            sa.runs_conceded += nrr_data.get("runs_scored_1", 0)
            sa.overs_bowled += nrr_data.get("overs_faced_1", 0)

        self.current_group_match_idx += 1

        # Check if group stage is complete
        if self.current_group_match_idx >= len(self.group_matches):
            self._setup_playoffs()

    def get_sorted_standings(self) -> List[dict]:
        """Return standings sorted by points (desc), then NRR (desc)."""
        entries = sorted(
            self.standings.values(),
            key=lambda e: (e.points, e.nrr),
            reverse=True,
        )
        return [e.to_dict() for e in entries]

    def _setup_playoffs(self) -> None:
        """Transition to playoff stage after group matches are done."""
        self.phase = self.PHASE_Q1
        ranked = self.get_sorted_standings()
        if len(ranked) >= 4:
            self.playoff_matches[self.PHASE_Q1] = (ranked[0]["player"], ranked[1]["player"])
            self.playoff_matches[self.PHASE_ELIM] = (ranked[2]["player"], ranked[3]["player"])

    def get_current_playoff_match(self) -> Optional[tuple]:
        """Return the next playoff match to play."""
        if self.phase in self.playoff_matches:
            return self.playoff_matches.get(self.phase)
        return None

    def _build_round_robin_rounds(self, players: List[str]) -> List[List[tuple]]:
        pool = list(players)
        if len(pool) % 2 == 1:
            pool.append(None)
        n = len(pool)
        rounds: List[List[tuple]] = []
        for _ in range(n - 1):
            pairs: List[tuple] = []
            for i in range(n // 2):
                a = pool[i]
                b = pool[n - 1 - i]
                if a is not None and b is not None:
                    pairs.append((a, b))
            rounds.append(pairs)
            pool = [pool[0]] + [pool[-1]] + pool[1:-1]
        return rounds

    def _flatten_rounds(self, rounds: List[List[tuple]]) -> List[tuple]:
        schedule: List[tuple] = []
        last_players: set = set()
        for round_pairs in rounds:
            remaining = list(round_pairs)
            while remaining:
                idx = next((i for i, pair in enumerate(remaining) if last_players.isdisjoint(pair)), 0)
                pair = remaining.pop(idx)
                schedule.append(pair)
                last_players = set(pair)
        return schedule

    def record_playoff_result(self, winner: str, loser: str) -> None:
        """Record playoff result and advance bracket."""
        self.playoff_results[self.phase] = winner

        if self.phase == self.PHASE_Q1:
            # Winner → Final, Loser → Q2
            self.playoff_results["q1_winner"] = winner
            self.playoff_results["q1_loser"] = loser
            self.phase = self.PHASE_ELIM

        elif self.phase == self.PHASE_ELIM:
            # Winner → Q2, Loser OUT
            self.playoff_results["elim_winner"] = winner
            self.playoff_matches[self.PHASE_Q2] = (
                self.playoff_results["q1_loser"],
                winner,
            )
            self.phase = self.PHASE_Q2

        elif self.phase == self.PHASE_Q2:
            # Winner → Final
            self.playoff_results["q2_winner"] = winner
            self.playoff_matches[self.PHASE_FINAL] = (
                self.playoff_results["q1_winner"],
                winner,
            )
            self.phase = self.PHASE_FINAL

        elif self.phase == self.PHASE_FINAL:
            self.champion = winner
            self.phase = self.PHASE_COMPLETE

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "standings": self.get_sorted_standings(),
            "group_matches_total": len(self.group_matches),
            "group_matches_played": self.current_group_match_idx,
            "playoff_bracket": {
                k: list(v) if v else None
                for k, v in self.playoff_matches.items()
            },
            "playoff_results": self.playoff_results,
            "champion": self.champion,
        }
