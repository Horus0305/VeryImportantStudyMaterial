"""Unit tests for the new frequency-based CPU strategy engine logic (no DB required)."""

import unittest
from backend.cpu.cpu_strategy_engine import CPUStrategyEngine, FLOOR_PROB, PEAK_CAP, UNIFORM, get_learning_phase

class TestCPUStrategyV3(unittest.TestCase):
    def setUp(self):
        self.engine = CPUStrategyEngine(db_session_factory=lambda: None)

    def test_learning_phases(self):
        """Test the learning phase weight transitions."""
        # Global Phase
        phase = get_learning_phase(30)
        self.assertEqual(phase['phase'], 'global')
        self.assertEqual(phase['global_weight'], 1.0)
        self.assertEqual(phase['user_weight'], 0.0)

        # Transition Phase
        phase = get_learning_phase(180)
        self.assertEqual(phase['phase'], 'transition')
        self.assertTrue(0.2 < phase['global_weight'] < 0.8)
        self.assertTrue(0.2 < phase['user_weight'] < 0.8)

        # Personalized Phase
        phase = get_learning_phase(600)
        self.assertEqual(phase['phase'], 'personalized')
        self.assertEqual(phase['global_weight'], 0.2)
        self.assertEqual(phase['user_weight'], 0.8)

    def test_local_frequency(self):
        """Test build_local_frequency behavior."""
        # Empty history -> uniform distribution
        freq = self.engine._build_local_frequency([])
        for n in range(7):
            self.assertAlmostEqual(freq[n], 1/7)

        # Spamming a single number
        freq = self.engine._build_local_frequency([6] * 5)
        self.assertEqual(freq[6], 1.0)
        self.assertEqual(freq[0], 0.0)

        # Mixed history
        freq = self.engine._build_local_frequency([6, 6, 6, 4, 4])
        self.assertAlmostEqual(freq[6], 0.6)
        self.assertAlmostEqual(freq[4], 0.4)

    def test_blend_signals(self):
        """Test signal blending weights and redistribution."""
        # Cold start (0 balls played) -> local weight should be 0
        local = {0: 1.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0}
        global_p = {0: 0.0, 1: 1.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0}
        trans = {0: 0.0, 1: 0.0, 2: 1.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0}

        blend = self.engine._blend_signals(
            local_freq=local,
            global_freq=global_p, global_n=100,
            transition_pred=trans, trans_n=50,
            balls_played=0
        )
        # With 0 balls, local weight is 0.0. Weights are: global = 0.80, trans = 0.20
        self.assertAlmostEqual(blend[0], 0.0)
        self.assertAlmostEqual(blend[1], 0.80)
        self.assertAlmostEqual(blend[2], 0.20)

        # Active game (10 balls played) -> local weight = 0.50, global = 0.15, trans = 0.35
        blend = self.engine._blend_signals(
            local_freq=local,
            global_freq=global_p, global_n=100,
            transition_pred=trans, trans_n=50,
            balls_played=10
        )
        self.assertAlmostEqual(blend[0], 0.50)
        self.assertAlmostEqual(blend[1], 0.15)
        self.assertAlmostEqual(blend[2], 0.35)

    def test_floor_and_cap(self):
        """Ensure no number falls below FLOOR_PROB or exceeds PEAK_CAP."""
        # Heavily skewed input
        skewed = {0: 0.99, 1: 0.01, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0}
        processed = self.engine._floor_and_cap(skewed)

        self.assertAlmostEqual(sum(processed.values()), 1.0)
        for n in range(7):
            self.assertTrue(processed[n] >= FLOOR_PROB - 1e-9)
            self.assertTrue(processed[n] <= PEAK_CAP + 1e-9)

    def test_bowling_strategy(self):
        """Test that bowling strategy aligns with predictions (targeting) and applies cap/floor."""
        prediction = {0: 0.8, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.1, 5: 0.1, 6: 0.0}
        context = {
            'match_format': '5over', 'role': 'bowling', 'current_over': 2,
            'total_overs': 5, 'current_score': 15, 'target': 30,
            'wickets_lost': 1, 'balls_left': 18, 'batting_first': False,
            'last_3_results': []
        }
        
        # High confidence should sharpen the prediction
        bowled = self.engine._bowling_strategy(prediction, context, confidence=0.8)
        self.assertAlmostEqual(bowled[0], PEAK_CAP) # Cap should limit it to PEAK_CAP
        self.assertTrue(bowled[1] >= FLOOR_PROB)

    def test_batting_strategy(self):
        """Test that batting strategy inverts predictions (avoidance)."""
        prediction = {0: 0.8, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.1, 5: 0.1, 6: 0.0}
        context = {
            'match_format': '5over', 'role': 'batting', 'current_over': 2,
            'total_overs': 5, 'current_score': 15, 'target': 30,
            'wickets_lost': 1, 'balls_left': 18, 'batting_first': False,
            'last_3_results': []
        }
        
        batted = self.engine._batting_strategy(prediction, context, confidence=0.8)
        # Avoid 0 (highest predicted) -> should have low probability in batted distribution
        self.assertTrue(batted[0] < batted[1])

if __name__ == '__main__':
    unittest.main()
