import random
from typing import Optional, List
from .innings import Innings


class Match:
    """Full match container: toss, 2 innings, result."""
    def __init__(self, match_id: str, mode: str,
                 side_a: List[str], side_b: List[str],
                 total_overs: int, total_wickets: int):
        self.id = match_id
        self.mode = mode
        self.side_a = side_a
        self.side_b = side_b
        self.total_overs = total_overs
        self.total_wickets = total_wickets
        self.toss_caller: Optional[str] = None
        self.toss_winner: Optional[str] = None
        self.toss_choice: Optional[str] = None
        self.batting_first: Optional[List[str]] = None
        self.bowling_first: Optional[List[str]] = None
        self.innings_1: Optional[Innings] = None
        self.innings_2: Optional[Innings] = None
        self.innings_3: Optional[Innings] = None
        self.innings_4: Optional[Innings] = None
        self.is_super_over: bool = False
        self.current_innings: int = 0
        self.winner: Optional[str] = None
        self.result_text = ""
        self.is_finished = False

    def do_toss(self, caller: Optional[str] = None) -> dict:
        if caller:
            self.toss_caller = caller
        else:
            all_players = self.side_a + self.side_b
            self.toss_caller = random.choice(all_players)
        return {"caller": self.toss_caller}

    def resolve_toss(self, call: str, other_side_chooser: Optional[str] = None) -> dict:
        coin = random.choice(["heads", "tails"])
        won = (call == coin)
        if won:
            self.toss_winner = self.toss_caller
        else:
            self.toss_winner = other_side_chooser if other_side_chooser else self._other_side_player(self.toss_caller)
        return {
            "coin": coin, "call": call, "won": won,
            "winner": self.toss_winner,
        }

    def apply_toss_choice(self, choice: str) -> None:
        self.toss_choice = choice
        winner_side = self.side_a if self.toss_winner in self.side_a else self.side_b
        loser_side = self.side_b if winner_side == self.side_a else self.side_a

        if choice == "bat":
            self.batting_first = winner_side
            self.bowling_first = loser_side
        else:
            self.batting_first = loser_side
            self.bowling_first = winner_side

    def start_innings_1(self) -> None:
        self.current_innings = 1
        self.innings_1 = Innings(
            batting_side=self.batting_first,
            bowling_side=self.bowling_first,
            total_overs=self.total_overs,
            total_wickets=self.total_wickets,
            is_team_mode=(self.mode == "team"),
        )

    def start_innings_2(self) -> None:
        self.current_innings = 2
        target = self.innings_1.total_runs + 1
        self.innings_2 = Innings(
            batting_side=self.bowling_first,
            bowling_side=self.batting_first,
            total_overs=self.total_overs,
            total_wickets=self.total_wickets,
            target=target,
            is_team_mode=(self.mode == "team"),
        )

    def start_innings_3(self) -> None:
        self.is_super_over = True
        self.current_innings = 3
        # team that batted 2nd (the chasing team) gets to bat 1st in Super Over
        self.innings_3 = Innings(
            batting_side=self.bowling_first,
            bowling_side=self.batting_first,
            total_overs=1,
            total_wickets=2,
            is_team_mode=(self.mode == "team"),
        )

    def start_innings_4(self) -> None:
        self.current_innings = 4
        target = self.innings_3.total_runs + 1
        self.innings_4 = Innings(
            batting_side=self.batting_first,
            bowling_side=self.bowling_first,
            total_overs=1,
            total_wickets=2,
            target=target,
            is_team_mode=(self.mode == "team"),
        )

    @property
    def active_innings(self) -> Optional[Innings]:
        if self.current_innings == 1:
            return self.innings_1
        elif self.current_innings == 2:
            return self.innings_2
        elif self.current_innings == 3:
            return self.innings_3
        elif self.current_innings == 4:
            return self.innings_4
        return None

    def determine_result(self) -> dict:
        bat_first_label = ", ".join(self.batting_first)
        bat_second_label = ", ".join(self.bowling_first)

        if not self.is_super_over:
            s1 = self.innings_1.total_runs
            s2 = self.innings_2.total_runs

            if s2 > s1:
                remaining_wickets = self.total_wickets - self.innings_2.wickets_fallen
                self.winner = bat_second_label
                self.result_text = f"{bat_second_label} won by {remaining_wickets} wicket(s)"
            elif s1 > s2:
                margin = s1 - s2
                self.winner = bat_first_label
                self.result_text = f"{bat_first_label} won by {margin} run(s)"
            else:
                self.winner = "TIE"
                self.result_text = "Match Tied!"
        else:
            s3 = self.innings_3.total_runs
            s4 = self.innings_4.total_runs if getattr(self, "innings_4", None) else 0

            if s4 > s3:
                self.winner = bat_first_label
                self.result_text = f"SUPER OVER: {bat_first_label} won!"
            elif s3 > s4:
                self.winner = bat_second_label
                self.result_text = f"SUPER OVER: {bat_second_label} won!"
            else:
                bound_team1 = self.innings_1.get_boundary_count() + (self.innings_4.get_boundary_count() if getattr(self, "innings_4", None) else 0)
                bound_team2 = self.innings_2.get_boundary_count() + (self.innings_3.get_boundary_count() if getattr(self, "innings_3", None) else 0)

                if bound_team1 > bound_team2:
                    self.winner = bat_first_label
                    self.result_text = f"{bat_first_label} won on boundary count ({bound_team1}-{bound_team2})"
                elif bound_team2 > bound_team1:
                    self.winner = bat_second_label
                    self.result_text = f"{bat_second_label} won on boundary count ({bound_team2}-{bound_team1})"
                else:
                    self.winner = bat_first_label
                    self.result_text = f"{bat_first_label} won by tiebreaker"

        self.is_finished = True
        result = {
            "winner": self.winner,
            "result_text": self.result_text,
            "scorecard_1": self.innings_1.get_scorecard() if getattr(self, "innings_1", None) else {},
            "scorecard_2": self.innings_2.get_scorecard() if getattr(self, "innings_2", None) else {},
            "side_a": self.side_a,
            "side_b": self.side_b,
            "bat_team_1": self.batting_first,
            "bat_team_2": self.bowling_first,
        }

        if self.is_super_over:
            result["scorecard_3"] = self.innings_3.get_scorecard() if getattr(self, "innings_3", None) else {}
            result["scorecard_4"] = self.innings_4.get_scorecard() if getattr(self, "innings_4", None) else {}
            result["bat_team_3"] = self.bowling_first
            result["bat_team_4"] = self.batting_first

        return result

    def get_nrr_data(self) -> dict:
        return {
            "runs_scored_1": self.innings_1.total_runs if self.innings_1 else 0,
            "overs_faced_1": self.innings_1.overs_completed + self.innings_1.balls_in_over / 6 if self.innings_1 else 0,
            "runs_scored_2": self.innings_2.total_runs if self.innings_2 else 0,
            "overs_faced_2": self.innings_2.overs_completed + self.innings_2.balls_in_over / 6 if self.innings_2 else 0,
            "batting_first_player": self.batting_first[0] if self.batting_first else None,
        }

    def _other_side_player(self, player: str) -> str:
        if player in self.side_a:
            return self.side_b[0]
        return self.side_a[0]
