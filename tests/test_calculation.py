import unittest

from app.core.calculation import evaluate_count_state, get_terminal_winner


class CalculationTests(unittest.TestCase):
    def test_terminal_winner_rules(self) -> None:
        self.assertEqual(get_terminal_winner(3, 0), "village")
        self.assertEqual(get_terminal_winner(1, 1), "wolf")
        self.assertEqual(get_terminal_winner(2, 2), "wolf")
        self.assertIsNone(get_terminal_winner(3, 1))

    def test_basic_day_win_rates(self) -> None:
        self.assertEqual(evaluate_count_state(2, 1, "day"), (33.3, 66.7))
        self.assertEqual(evaluate_count_state(3, 2, "day"), (13.3, 86.7))

    def test_basic_night_win_rates(self) -> None:
        self.assertEqual(evaluate_count_state(2, 1, "night"), (0.0, 100.0))
        self.assertEqual(evaluate_count_state(4, 1, "night"), (25.0, 75.0))


if __name__ == "__main__":
    unittest.main()
