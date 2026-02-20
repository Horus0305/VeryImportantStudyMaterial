from typing import Dict


class BattingCard:
    """Per-player batting stats for one innings."""
    def __init__(self, player_name: str):
        self.name = player_name
        self.runs = 0
        self.balls = 0
        self.fours = 0
        self.sixes = 0
        self.dismissal = "not out"
        self.is_out = False

    @property
    def strike_rate(self) -> float:
        return (self.runs / self.balls * 100) if self.balls > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name, "runs": self.runs, "balls": self.balls,
            "fours": self.fours, "sixes": self.sixes,
            "sr": round(self.strike_rate, 1), "dismissal": self.dismissal,
            "is_out": self.is_out,
        }


class BowlingCard:
    """Per-player bowling stats for one innings."""
    def __init__(self, player_name: str):
        self.name = player_name
        self.overs_completed = 0
        self.balls_bowled_in_over = 0
        self.runs_conceded = 0
        self.wickets = 0

    @property
    def total_balls(self) -> int:
        return self.overs_completed * 6 + self.balls_bowled_in_over

    @property
    def overs_display(self) -> str:
        if self.balls_bowled_in_over == 0:
            return str(self.overs_completed)
        return f"{self.overs_completed}.{self.balls_bowled_in_over}"

    @property
    def economy(self) -> float:
        total_overs = self.overs_completed + self.balls_bowled_in_over / 6
        return (self.runs_conceded / total_overs) if total_overs > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name, "overs": self.overs_display,
            "runs": self.runs_conceded, "wickets": self.wickets,
            "econ": round(self.economy, 1),
        }
