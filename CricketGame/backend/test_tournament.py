"""
Test script for Tournament and NRR Calculation
Run this to verify StandingsEntry NRR and Tournament updates.
"""
import sys
import os

# Ensure backend is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game.tournament import Tournament, StandingsEntry

def test_standings_entry_nrr_calculation():
    """Test NRR calculation in StandingsEntry."""
    print("\n🧪 Testing StandingsEntry NRR Calculation...")

    # Case 1: Initialization (0 values)
    entry = StandingsEntry("Player A")
    assert entry.nrr == 0.0
    print("  ✓ Initialization (0/0 - 0/0): NRR = 0.0")

    # Case 2: Simple Positive NRR
    # Scored 100 in 10 overs, Conceded 50 in 10 overs
    # Rate: 10.0 - 5.0 = 5.0
    entry.runs_scored = 100
    entry.overs_faced = 10.0
    entry.runs_conceded = 50
    entry.overs_bowled = 10.0
    assert abs(entry.nrr - 5.0) < 0.0001
    print("  ✓ Positive NRR (100/10 - 50/10): NRR = 5.0")

    # Case 3: Negative NRR
    # Scored 50 in 10 overs, Conceded 100 in 10 overs
    # Rate: 5.0 - 10.0 = -5.0
    entry.runs_scored = 50
    entry.runs_conceded = 100
    assert abs(entry.nrr - (-5.0)) < 0.0001
    print("  ✓ Negative NRR (50/10 - 100/10): NRR = -5.0")

    # Case 4: Decimal Overs (Float Division)
    # Scored 100 in 10.5 overs (10.5 decimal)
    # Rate: 100 / 10.5 = 9.5238...
    entry.runs_scored = 100
    entry.overs_faced = 10.5
    entry.runs_conceded = 0
    entry.overs_bowled = 0 # Division by zero protection check
    expected_nrr = 100 / 10.5
    assert abs(entry.nrr - expected_nrr) < 0.0001
    print(f"  ✓ Decimal Overs (100/10.5 - 0): NRR = {entry.nrr:.4f}")

    # Case 5: Division by Zero Protection
    entry.overs_faced = 0
    entry.overs_bowled = 0
    assert entry.nrr == 0.0
    print("  ✓ Division by Zero Protection: NRR = 0.0")


def test_tournament_integration():
    """Test Tournament standings update."""
    print("\n🧪 Testing Tournament Integration...")

    players = ["A", "B", "C"]
    tournament = Tournament(players, overs=5, wickets=5)

    # Initial state
    assert tournament.standings["A"].played == 0
    assert tournament.standings["A"].points == 0
    assert tournament.standings["A"].nrr == 0.0

    # Simulate a match result: A beats B
    # A batted first: 50 runs in 5 overs
    # B batted second: 40 runs in 5 overs
    nrr_data = {
        "runs_scored_1": 50, # A
        "overs_faced_1": 5.0,
        "runs_scored_2": 40, # B
        "overs_faced_2": 5.0
    }

    tournament.record_group_result(player_a="A", player_b="B", winner="A", nrr_data=nrr_data)

    # Check A's stats
    # Scored 50/5 = 10.0
    # Conceded 40/5 = 8.0
    # NRR = 2.0
    entry_a = tournament.standings["A"]
    assert entry_a.played == 1
    assert entry_a.won == 1
    assert entry_a.points == 2
    assert abs(entry_a.nrr - 2.0) < 0.0001
    print("  ✓ Player A stats updated correctly (Points=2, NRR=2.0)")

    # Check B's stats
    # Scored 40/5 = 8.0
    # Conceded 50/5 = 10.0
    # NRR = -2.0
    entry_b = tournament.standings["B"]
    assert entry_b.played == 1
    assert entry_b.lost == 1
    assert entry_b.points == 0
    assert abs(entry_b.nrr - (-2.0)) < 0.0001
    print("  ✓ Player B stats updated correctly (Points=0, NRR=-2.0)")

    # Test sorting
    sorted_standings = tournament.get_sorted_standings()
    assert sorted_standings[0]["player"] == "A"
    assert sorted_standings[1]["player"] == "C" or sorted_standings[1]["player"] == "B"
    # C has 0 points, B has 0 points but B has -2.0 NRR, C has 0.0 NRR. So C should be ahead of B.
    # C: 0 points, 0 NRR
    # B: 0 points, -2.0 NRR
    # Order: A, C, B
    assert sorted_standings[1]["player"] == "C"
    assert sorted_standings[2]["player"] == "B"
    print("  ✓ Standings sorting correct (A > C > B)")


def run_all_tests():
    print("=" * 60)
    print("TOURNAMENT NRR TEST SUITE")
    print("=" * 60)

    try:
        test_standings_entry_nrr_calculation()
        test_tournament_integration()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: Assertion Error")
        print("=" * 60)
        raise e
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        raise e

if __name__ == "__main__":
    run_all_tests()
