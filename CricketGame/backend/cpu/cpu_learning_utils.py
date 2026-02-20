"""
CPU Learning Utilities - Context detection and helper functions
"""
from typing import Optional, List, Dict


def get_game_phase(current_over: int, total_overs: int) -> str:
    """
    Determine game phase based on current over.
    
    Args:
        current_over: Current over number (0-indexed)
        total_overs: Total overs in the match
        
    Returns:
        'powerplay', 'middle', or 'death'
    """
    if current_over <= 1:
        return 'powerplay'
    elif current_over >= total_overs - 2:
        return 'death'
    else:
        return 'middle'


def get_score_situation(
    batting_first: bool,
    current_score: int,
    target: Optional[int],
    wickets_lost: int,
    balls_left: int,
    total_overs: int
) -> str:
    """
    Determine score pressure situation.
    
    Args:
        batting_first: True if batting in first innings
        current_score: Current runs scored
        target: Target to chase (None if batting first)
        wickets_lost: Wickets fallen
        balls_left: Balls remaining in innings
        total_overs: Total overs in match
        
    Returns:
        Score situation string like 'chasing_desperate', 'defending_tight', etc.
    """
    if batting_first:
        # Batting first - assess run rate and wicket situation
        overs_bowled = total_overs - (balls_left / 6.0)
        run_rate = current_score / overs_bowled if overs_bowled > 0 else 0
        
        if wickets_lost >= 7:
            return 'defending_collapse'
        elif run_rate >= 10:
            return 'defending_safe'
        elif run_rate >= 7:
            return 'defending_comfortable'
        elif run_rate >= 5:
            return 'defending_moderate'
        else:
            return 'defending_tight'
    else:
        # Chasing - calculate required rate
        runs_needed = target - current_score
        
        if runs_needed <= 0:
            return 'chasing_won'
        
        required_rate = (runs_needed / balls_left * 6.0) if balls_left > 0 else 999
        
        if wickets_lost >= 8 or required_rate > 15:
            return 'chasing_desperate'
        elif required_rate > 12:
            return 'chasing_very_tight'
        elif required_rate > 9:
            return 'chasing_tight'
        elif required_rate > 6:
            return 'chasing_moderate'
        else:
            return 'chasing_comfortable'


def get_recent_event(last_results: List[Dict]) -> str:
    """
    Analyze last 3 ball results to determine recent event.
    
    Args:
        last_results: List of recent ball result dicts with 'runs' and 'is_out' keys
        
    Returns:
        'just_out', 'hit_six', 'dot_ball', 'hot_streak', or 'normal'
    """
    if not last_results:
        return 'normal'
    
    # Check last ball
    last = last_results[-1]
    if last.get('is_out'):
        return 'just_out'
    if last.get('runs') == 6:
        return 'hit_six'
    if last.get('runs') == 0:
        return 'dot_ball'
    
    # Check for hot streak (all last 3 balls were 4+)
    if len(last_results) >= 3:
        recent_3 = last_results[-3:]
        if all(r.get('runs', 0) >= 4 for r in recent_3):
            return 'hot_streak'
    
    return 'normal'


def get_match_format_key(total_overs: int) -> str:
    """
    Convert total overs to match format key.
    
    Args:
        total_overs: Total overs in the match
        
    Returns:
        Format key like '2over', '5over', '10over'
    """
    return f"{total_overs}over"


def get_user_id_from_username(username: str, db_session) -> int:
    """
    Get user ID from username. Returns -1 for CPU.
    
    Args:
        username: Player username
        db_session: Database session
        
    Returns:
        User ID or -1 for CPU
    """
    if username in ('CPU', 'CPU Bot'):
        return -1
    
    from ..data.models import Player
    player = db_session.query(Player).filter(Player.username == username).first()
    return player.id if player else -1


def calculate_learning_phase(total_balls: int) -> tuple[str, float]:
    """
    Calculate learning phase and confidence score based on total balls tracked.
    
    Args:
        total_balls: Total balls tracked for this user
        
    Returns:
        Tuple of (phase, confidence_score)
        - phase: 'global' (<60), 'transition' (60-300), 'personalized' (300+)
        - confidence_score: 0.0-0.95
    """
    if total_balls < 60:
        phase = 'global'
        confidence = min(total_balls / 60.0 * 0.3, 0.3)  # 0.0 to 0.3
    elif total_balls < 300:
        phase = 'transition'
        progress = (total_balls - 60) / 240.0  # 0.0 to 1.0
        confidence = 0.3 + (progress * 0.4)  # 0.3 to 0.7
    else:
        phase = 'personalized'
        # Asymptotic approach to 0.95
        excess = total_balls - 300
        confidence = 0.7 + (0.25 * (1 - (1 / (1 + excess / 200.0))))  # 0.7 to 0.95
    
    return phase, round(confidence, 3)


def normalize_frequencies(freqs: List[float]) -> List[float]:
    """
    Normalize a list of frequencies to sum to 1.0.
    
    Args:
        freqs: List of 7 frequency values
        
    Returns:
        Normalized list summing to 1.0
    """
    total = sum(freqs)
    if total <= 0:
        return [1.0 / 7] * 7  # Equal distribution if all zeros
    return [f / total for f in freqs]


def exponential_moving_average_update(
    old_freqs: List[float],
    observed_move: int,
    total_samples: int,
    max_samples: int
) -> tuple[List[float], int]:
    """
    Update frequencies using exponential moving average.
    
    Args:
        old_freqs: Current frequency distribution (7 values)
        observed_move: The move that was just observed (0-6)
        total_samples: Current sample count
        max_samples: Maximum samples for alpha calculation
        
    Returns:
        Tuple of (new_freqs, new_total_samples)
    """
    alpha = 1.0 / min(total_samples + 1, max_samples)
    
    new_freqs = list(old_freqs)
    for i in range(7):
        if i == observed_move:
            new_freqs[i] = old_freqs[i] * (1 - alpha) + alpha
        else:
            new_freqs[i] = old_freqs[i] * (1 - alpha)
    
    # Normalize to ensure sum = 1.0
    new_freqs = normalize_frequencies(new_freqs)
    
    return new_freqs, total_samples + 1


# Constants for EMA
MAX_SAMPLES_GLOBAL = 1000  # Slower adaptation, more stable
MAX_SAMPLES_USER = 500  # Faster personalization
MAX_SAMPLES_SITUATIONAL = 200  # Most adaptive to recent behavior
