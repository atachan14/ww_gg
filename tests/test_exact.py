import unittest
from dataclasses import fields
from fractions import Fraction as F

from werewolf.exact import (Action, Board, Progress, Rules, Strategy, Values,
                            action_outcomes, advance, aggregate_values,
                            build_tree, evaluate_tree, initial_board)


class PublicBoardTests(unittest.TestCase):
    def value(self, n, rules=Rules(), strategy=Strategy()):
        root = build_tree(initial_board(n), rules, strategy)
        return root, evaluate_tree(root, strategy)

    def test_complete_tree_all_candidates_and_exact_chance_mass(self):
        for n in (3, 4, 5):
            for include in (False, True):
                strategy = Strategy(include_self_bite=include)
                root, evaluation = self.value(n, Rules(True), strategy)
                def visit(node):
                    self.assertEqual(evaluation.board_value(node).village_win + evaluation.board_value(node).wolf_win, 1)
                    if node.board.winner:
                        self.assertEqual(node.actions, ())
                        return
                    self.assertEqual(tuple(a.target for a in node.actions), node.board.alive)
                    for action in node.actions:
                        self.assertEqual(sum(c.probability for c in action.outcomes), 1)
                        for chance in action.outcomes:
                            self.assertIsInstance(chance.probability, F)
                            visit(chance.child)
                visit(root)

    def test_initial_final_win_probabilities(self):
        for n, expected, included in ((3, F(1, 3), F(1, 3)), (4, F(1, 4), F(1, 2)), (5, F(7, 15), F(3, 5))):
            for mode in ('max', 'random'):
                root, evaluation = self.value(n, strategy=Strategy(mode, mode))
                self.assertEqual(evaluation.board_value(root).village_win, expected)
                self.assertTrue(all(evaluation.action_value(root, a.target).village_win == expected for a in root.actions))
                root, evaluation = self.value(n, Rules(True), Strategy(mode, mode, True))
                self.assertEqual(evaluation.board_value(root).village_win, included)

    def test_max_and_random_aggregate_different_asymmetric_values(self):
        candidates = (Values(F(1, 5), F(4, 5)), Values(F(3, 5), F(2, 5)))
        self.assertEqual(aggregate_values('day', candidates, Strategy()).village_win, F(3, 5))
        self.assertEqual(aggregate_values('night', candidates, Strategy()).village_win, F(1, 5))
        self.assertEqual(aggregate_values('day', candidates, Strategy('random', 'random')).village_win, F(2, 5))
        self.assertEqual(aggregate_values('night', candidates, Strategy('random', 'random')).village_win, F(2, 5))

    def test_max_ties_keep_all_candidates_and_no_action_probability(self):
        root, _ = self.value(5)
        self.assertEqual(len(root.actions), 5)
        self.assertEqual({f.name for f in fields(Action)}, {'target', 'outcomes'})
        self.assertNotIn('role', {f.name for f in fields(Board)})
        self.assertNotIn('worlds', {f.name for f in fields(Board)})

    def test_five_player_manual_progression_conditions_current_board(self):
        rules, strategy = Rules(), Strategy()
        progress = advance(Progress(initial_board(5)), 1, rules, strategy)
        self.assertEqual((progress.board.day, progress.board.phase, progress.board.alive), (1, 'night', (2, 3, 4, 5)))
        self.assertEqual(progress.settled_village, F(1, 5))
        self.assertEqual(progress.active_mass, F(4, 5))
        self.assertEqual(progress.board.wolf_probability(1), 0)
        self.assertEqual(progress.board.wolf_probability(2), F(1, 4))
        root = build_tree(progress.board, rules, strategy)
        current = evaluate_tree(root, strategy).board_value(root)
        self.assertEqual(current.village_win, F(1, 3))
        self.assertEqual(progress.total_values(current).village_win, F(7, 15))
        progress = advance(progress, 2, rules, strategy)
        self.assertEqual((progress.board.day, progress.board.phase), (2, 'day'))
        self.assertEqual(progress.active_mass, F(4, 5))
        progress = advance(progress, 3, rules, strategy)
        self.assertTrue(progress.finished)
        self.assertEqual(progress.total_values(), Values(F(7, 15), F(8, 15)))
        self.assertEqual(tuple(o.board.winner for o in progress.last_outcomes), ('village', 'wolf'))

    def test_self_bite_rule_and_strategy_are_independent(self):
        initial = Progress(initial_board(5))
        progress = advance(initial, 1, Rules(True), Strategy())
        self.assertEqual(len(action_outcomes(progress.board, 2, Rules(True), Strategy())), 1)
        self.assertEqual(len(action_outcomes(progress.board, 2, Rules(True), Strategy(include_self_bite=True))), 2)
        with self.assertRaises(ValueError):
            build_tree(initial.board, Rules(), Strategy(include_self_bite=True))
        strategy = Strategy(include_self_bite=True)
        progress = advance(initial, 1, Rules(True), strategy)
        progress = advance(progress, 2, Rules(True), strategy)
        self.assertEqual(progress.settled_village, F(2, 5))
        self.assertEqual(progress.active_mass, F(3, 5))
        progress = advance(progress, 3, Rules(True), strategy)
        self.assertEqual(progress.total_values().village_win, F(3, 5))

    def test_four_player_night_finishes_without_self_bite(self):
        progress = advance(Progress(initial_board(4)), 1, Rules(), Strategy())
        outcomes = action_outcomes(progress.board, 2, Rules(), Strategy())
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0].probability, 1)
        self.assertEqual(outcomes[0].board.winner, 'wolf')
        progress = advance(progress, 2, Rules(), Strategy())
        self.assertEqual(progress.total_values().village_win, F(1, 4))
        self.assertEqual(progress.last_outcomes[0].board.wolf_probability(2), 0)

    def test_invalid_inputs_and_terminal_cannot_advance(self):
        for count in (0, 10, True, '5'):
            with self.assertRaises(ValueError): initial_board(count)
        for target in (0, 6, True, '1'):
            with self.assertRaises(ValueError): action_outcomes(initial_board(5), target, Rules(), Strategy())
        progress = advance(Progress(initial_board(3)), 1, Rules(), Strategy())
        with self.assertRaises(ValueError): advance(progress, 2, Rules(), Strategy())
        with self.assertRaises(ValueError): Strategy('minimum', 'max')
        with self.assertRaises(ValueError): Board(3, (1, 1, 2))


if __name__ == '__main__':
    unittest.main()
