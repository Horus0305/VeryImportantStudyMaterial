from typing import Optional, Dict, List
from .cards import BattingCard, BowlingCard


class Innings:
    """Represents one innings of a match."""
    def __init__(self, batting_side: List[str], bowling_side: List[str],
                 total_overs: int, total_wickets: int, target: Optional[int] = None,
                 is_team_mode: bool = False):
        self.batting_side = batting_side
        self.bowling_side = bowling_side
        self.total_overs = total_overs
        self.total_wickets = total_wickets
        self.target = target
        self.is_team_mode = is_team_mode  # Enables captain selection pauses
        self.batting_cards: Dict[str, BattingCard] = {
            name: BattingCard(name) for name in batting_side
        }
        self.striker_idx = 0
        self.non_striker_idx = 1 if len(batting_side) > 1 else None
        self.wickets_fallen = 0
        self.bowling_cards: Dict[str, BowlingCard] = {
            name: BowlingCard(name) for name in bowling_side
        }
        self.current_bowler_idx = 0
        self.overs_completed = 0
        self.balls_in_over = 0
        self.total_runs = 0
        self.ball_log: List[dict] = []
        self.is_complete = False

        # Captain selection state (team mode only)
        self.last_batter_out: Optional[str] = None
        self.last_bowler: Optional[str] = None
        self.needs_batter_choice = (is_team_mode and len(batting_side) > 1)
        self.needs_bowler_choice = (is_team_mode and len(bowling_side) > 1)

    @property
    def striker(self) -> str:
        return self.batting_side[self.striker_idx]

    @property
    def non_striker(self) -> Optional[str]:
        if self.non_striker_idx is not None:
            return self.batting_side[self.non_striker_idx]
        return None

    @property
    def current_bowler(self) -> str:
        return self.bowling_side[self.current_bowler_idx]

    @property
    def overs_display(self) -> str:
        if self.balls_in_over == 0:
            return str(self.overs_completed)
        return f"{self.overs_completed}.{self.balls_in_over}"

    def resolve_ball(self, bat_move: int, bowl_move: int) -> dict:
        if self.is_complete:
            return {"error": "Innings is already complete"}

        result = {
            "ball_num": self.overs_completed * 6 + self.balls_in_over + 1,
            "over_display": f"{self.overs_completed}.{self.balls_in_over + 1}",
            "striker": self.striker,
            "bowler": self.current_bowler,
            "bat_move": bat_move,
            "bowl_move": bowl_move,
            "runs": 0,
            "is_out": False,
            "is_four": False,
            "is_six": False,
            "innings_runs": 0,
            "innings_wickets": 0,
            "innings_overs": "",
            "over_complete": False,
            "innings_complete": False,
            "target_chased": False,
            "milestone": None,    # 50 or 100 when batter crosses the threshold
            "hat_trick": False,   # True when same bowler takes 3 consecutive wickets
        }

        bat_card = self.batting_cards[self.striker]
        bowl_card = self.bowling_cards[self.current_bowler]

        bat_card.balls += 1
        bowl_card.balls_bowled_in_over += 1
        self.balls_in_over += 1

        if bat_move == bowl_move:
            result["is_out"] = True
            result["runs"] = 0
            bat_card.is_out = True
            bat_card.dismissal = f"b {self.current_bowler}"
            bowl_card.wickets += 1
            self.wickets_fallen += 1
            # Hat-trick detection: did current bowler just take their 3rd consecutive wicket?
            if len(self.ball_log) >= 2:
                prev1 = self.ball_log[-1]
                prev2 = self.ball_log[-2]
                if (prev1.get("is_out") and prev1.get("bowler") == self.current_bowler
                        and prev2.get("is_out") and prev2.get("bowler") == self.current_bowler):
                    result["hat_trick"] = True
            self._handle_wicket_fall(result)
        else:
            runs = bowl_move if bat_move == 0 else bat_move
            result["runs"] = runs
            old_runs = bat_card.runs
            bat_card.runs += runs
            bowl_card.runs_conceded += runs
            self.total_runs += runs

            # Milestone detection: did batter just cross 50 or 100?
            if old_runs < 50 <= bat_card.runs:
                result["milestone"] = 50
            elif old_runs < 100 <= bat_card.runs:
                result["milestone"] = 100

            if runs == 4:
                result["is_four"] = True
                bat_card.fours += 1
            elif runs == 6:
                result["is_six"] = True
                bat_card.sixes += 1

            if runs in (1, 3):
                self._rotate_strike()

        if self.balls_in_over >= 6:
            result["over_complete"] = True
            self.overs_completed += 1
            self.balls_in_over = 0
            bowl_card.overs_completed += 1
            bowl_card.balls_bowled_in_over = 0
            self._rotate_strike()
            self._next_bowler(result)

        result["innings_runs"] = self.total_runs
        result["innings_wickets"] = self.wickets_fallen
        result["innings_overs"] = self.overs_display

        if self._check_innings_complete():
            result["innings_complete"] = True
            self.is_complete = True
            if self.target and self.total_runs >= self.target:
                result["target_chased"] = True

        self.ball_log.append(result)
        return result

    def _handle_wicket_fall(self, result: dict) -> None:
        """Advance to the next batter. In team mode, sets needs_batter_choice instead."""
        if self.wickets_fallen >= self.total_wickets:
            return

        # Record who just got out (consecutive re-entry blocked in team mode)
        out_batter = self.batting_side[self.striker_idx]
        self.last_batter_out = out_batter

        # Non-striker automatically becomes striker
        if self.non_striker_idx is not None:
            self.striker_idx = self.non_striker_idx
            self.non_striker_idx = None

        # In team mode: captain picks the new non-striker
        if self.is_team_mode and len(self.batting_side) > 1:
            self.needs_batter_choice = True
            result["needs_batter_choice"] = True
            result["available_batters"] = self.available_next_batters()
        else:
            # Auto-advance: pick first available player
            available = [
                i for i, name in enumerate(self.batting_side)
                if not self.batting_cards[name].is_out
                and i != self.striker_idx
                and (self.non_striker_idx is None or i != self.non_striker_idx)
            ]
            if available:
                self.non_striker_idx = available[0]

    def _next_bowler(self, result: Optional[dict] = None) -> None:
        """Rotate bowling. In team mode, sets needs_bowler_choice for captain."""
        last = self.current_bowler
        if self.is_team_mode and len(self.bowling_side) > 1:
            self.last_bowler = last
            self.needs_bowler_choice = True
            if result is not None:
                result["needs_bowler_choice"] = True
                result["available_bowlers"] = self.available_next_bowlers()
        elif len(self.bowling_side) > 1:
            self.current_bowler_idx = (self.current_bowler_idx + 1) % len(self.bowling_side)

    def _rotate_strike(self) -> None:
        if self.non_striker_idx is not None:
            self.striker_idx, self.non_striker_idx = self.non_striker_idx, self.striker_idx

    def available_next_batters(self) -> List[dict]:
        """List of players who can come in next, with disabled flag for consecutive block."""
        striker_name = self.batting_side[self.striker_idx]
        non_striker_name = self.batting_side[self.non_striker_idx] if self.non_striker_idx is not None else None
        options = []
        for name in self.batting_side:
            if not self.needs_batter_choice and (name == striker_name or name == non_striker_name):
                continue  # Already at crease
            is_out = self.batting_cards[name].is_out
            # Allow re-batting if wickets allow (innings not over), but block consecutive
            consecutive_blocked = (name == self.last_batter_out)
            # An out batter can re-bat if wickets allow; disabled if consecutive
            options.append({"player": name, "disabled": consecutive_blocked or is_out})
        # If ALL options are disabled, remove the consecutive block (no other choice)
        if options and all(o["disabled"] for o in options):
            for o in options:
                if o["player"] == self.last_batter_out:
                    o["disabled"] = False  # Force allow; it's the only option
        return options

    def available_next_bowlers(self) -> List[dict]:
        """List of bowlers captain can pick, with disabled flag for consecutive blocker."""
        options = []
        for name in self.bowling_side:
            options.append({"player": name, "disabled": (name == self.last_bowler)})
        # If only 1 bowler or all disabled, remove the block
        if len(options) <= 1 or all(o["disabled"] for o in options):
            for o in options:
                o["disabled"] = False
        return options

    def apply_batter_choice(self, player: str) -> None:
        """Captain confirmed next batter. Sets them as striker if it's ball 1, else non-striker."""
        if player not in self.batting_side:
            return
        idx = self.batting_side.index(player)
        
        # Determine if we are picking for the very first ball
        is_first_ball = (self.overs_completed == 0 and self.balls_in_over == 0 and self.wickets_fallen == 0)
        
        if is_first_ball:
            # We are picking the opening striker. The other slot defaults to the second guy.
            self.striker_idx = idx
            # Ensure the non-striker isn't accidentally overlapping with the picked striker
            if self.non_striker_idx == idx:
                self.non_striker_idx = (idx + 1) % len(self.batting_side)
        else:
            self.non_striker_idx = idx
        
        self.needs_batter_choice = False

    def apply_bowler_choice(self, player: str) -> None:
        """Captain confirmed next bowler. Updates current_bowler_idx."""
        if player not in self.bowling_side:
            return
        self.current_bowler_idx = self.bowling_side.index(player)
        self.needs_bowler_choice = False

    def _check_innings_complete(self) -> bool:
        if self.wickets_fallen >= self.total_wickets:
            return True
        if self.overs_completed >= self.total_overs and self.balls_in_over == 0:
            return True
        if self.target and self.total_runs >= self.target:
            return True
        return False

    def get_scorecard(self) -> dict:
        return {
            "batting": [self.batting_cards[n].to_dict() for n in self.batting_side],
            "bowling": [self.bowling_cards[n].to_dict() for n in self.bowling_side],
            "total_runs": self.total_runs,
            "wickets": self.wickets_fallen,
            "overs": self.overs_display,
            "target": self.target,
        }
