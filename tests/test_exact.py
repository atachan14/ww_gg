from fractions import Fraction
import unittest

from werewolf.exact import (
    AnalysisState, Belief, WeightedWorld, World, apply_execution,
    attack_world, evaluate_execution, initial_belief, legal_attacks,
)


class ExactCalculationTests(unittest.TestCase):
    def test_initial_roles_are_complete_exact_and_normalized_for_three_to_five(self):
        for count in (3, 4, 5):
            with self.subTest(count=count):
                belief = initial_belief(count)
                self.assertEqual(len(belief.worlds), count)
                self.assertEqual({item.world.wolves for item in belief.worlds}, {frozenset({player}) for player in belief.players})
                self.assertEqual(sum(item.probability for item in belief.worlds), 1)
                for player in belief.players:
                    self.assertEqual(belief.role_probability(player, "wolf"), Fraction(1, count))
                    self.assertEqual(belief.role_probability(player, "village"), Fraction(count - 1, count))
                self.assertEqual(sum(belief.role_probability(player, "wolf") for player in belief.players), 1)

    def test_three_player_targets_are_independent_terminal_evaluations(self):
        prior = initial_belief()
        evaluations = tuple(evaluate_execution(prior, target) for target in prior.alive)
        self.assertEqual(tuple(item.target_id for item in evaluations), (1, 2, 3))
        for action in evaluations:
            self.assertEqual((action.village_win, action.wolf_win, action.unresolved), (Fraction(1, 3), Fraction(2, 3), 0))
            self.assertEqual(sum(outcome.probability for outcome in action.outcomes), 1)

    def test_each_fixed_target_preserves_nonterminal_mass_in_four_and_five(self):
        for count in (4, 5):
            prior = initial_belief(count)
            for target in prior.alive:
                with self.subTest(count=count, target=target):
                    action = evaluate_execution(prior, target)
                    self.assertEqual(action.village_win, Fraction(1, count))
                    self.assertEqual(action.wolf_win, 0)
                    self.assertEqual(action.unresolved, Fraction(count - 1, count))
                    by_role = {outcome.removed_role: outcome for outcome in action.outcomes}
                    self.assertEqual(by_role["wolf"].winner, "village")
                    self.assertIsNone(by_role["village"].winner)
                    self.assertEqual(by_role["village"].counts, (count - 2, 1))

    def test_action_candidates_do_not_become_a_random_policy(self):
        prior = initial_belief(3)
        world = next(item.world for item in prior.worlds if item.world.wolves == frozenset({2}))
        known = Belief((WeightedWorld(world, Fraction(1)),))
        values = {target: evaluate_execution(known, target).village_win for target in known.alive}
        self.assertEqual(values, {1: 0, 2: 1, 3: 0})

    def test_execution_removes_target_from_every_outcome_without_revealing_one_truth(self):
        result = evaluate_execution(initial_belief(5), 2)
        self.assertEqual(sum(len(outcome.posterior.worlds) for outcome in result.outcomes), 5)
        for outcome in result.outcomes:
            self.assertEqual(outcome.posterior.alive, (1, 3, 4, 5))

    def test_role_conditioning_keeps_remaining_uncertainty(self):
        result = evaluate_execution(initial_belief(), 2)
        branches = {outcome.removed_role: outcome for outcome in result.outcomes}
        self.assertEqual(len(branches["wolf"].posterior.worlds), 1)
        self.assertEqual(len(branches["village"].posterior.worlds), 2)
        for player in (1, 3):
            self.assertEqual(branches["village"].posterior.role_probability(player, "wolf"), Fraction(1, 2))

    def test_absolute_mass_and_conditional_distribution_are_distinct(self):
        state = apply_execution(AnalysisState(initial_belief(5)), 1)
        self.assertEqual((state.village_win, state.wolf_win, state.active_mass), (Fraction(1, 5), 0, Fraction(4, 5)))
        self.assertEqual(len(state.settled), 1)
        self.assertEqual(len(state.active.worlds), 4)
        for player in (2, 3, 4, 5):
            self.assertEqual(state.active.role_probability(player, "wolf"), Fraction(1, 4))
        self.assertEqual(sum(item.probability for item in state.all_worlds), 1)
        self.assertEqual({item.probability for item in state.all_worlds}, {Fraction(1, 5)})

    def test_next_action_preserves_stopped_world_and_uses_supplied_belief(self):
        # A supplied next-day belief, not an assumed nighttime policy.
        players = (1, 2, 3, 4, 5)
        stopped = WeightedWorld(World(players, frozenset({1}), (2, 3, 4, 5)), Fraction(1, 5))
        active = Belief(tuple(WeightedWorld(World(players, frozenset({wolf}), (2, 3, 4)), probability)
                              for wolf, probability in ((2, Fraction(1, 2)), (3, Fraction(1, 3)), (4, Fraction(1, 6)))))
        state = AnalysisState(active, (stopped,))
        result = apply_execution(state, 2)
        self.assertTrue(result.finished)
        self.assertEqual(result.village_win, Fraction(3, 5))
        self.assertEqual(result.wolf_win, Fraction(2, 5))
        self.assertIn(stopped, result.settled)
        self.assertEqual(stopped.world.alive, (2, 3, 4, 5))
        self.assertEqual(sum(item.probability for item in result.all_worlds), 1)
        alternative = apply_execution(state, 4)
        self.assertEqual(alternative.village_win, Fraction(1, 3))
        self.assertEqual(state.active.alive, (2, 3, 4))

    def test_three_player_state_retains_all_terminal_worlds(self):
        result = apply_execution(AnalysisState(initial_belief()), 2)
        self.assertTrue(result.finished)
        self.assertEqual(len(result.settled), 3)
        self.assertEqual((result.village_win, result.wolf_win, result.active_mass), (Fraction(1, 3), Fraction(2, 3), 0))
        with self.assertRaises(ValueError):
            apply_execution(result, 1)

    def test_night_candidates_obey_each_possible_world_without_weighting_actions(self):
        for count in (4, 5):
            state = apply_execution(AnalysisState(initial_belief(count)), 1)
            for item in state.active.worlds:
                choices = legal_attacks(item.world)
                self.assertEqual(len(choices), count - 2)
                self.assertTrue(set(choices).isdisjoint(item.world.wolves))
                for target in choices:
                    child = attack_world(item.world, target)
                    self.assertEqual(child.counts, (count - 3, 1))
                    self.assertEqual(child.winner, "wolf" if count == 4 else None)
                with self.assertRaises(ValueError):
                    attack_world(item.world, next(iter(item.world.wolves)))
            for item in state.settled:
                self.assertEqual(legal_attacks(item.world), ())

    def test_multiwolf_first_step_has_exact_marginals_and_terminal_partition(self):
        prior = initial_belief(9, 4)
        self.assertEqual(len(prior.worlds), 126)
        for player in prior.players:
            self.assertEqual(prior.role_probability(player, "wolf"), Fraction(4, 9))
        result = evaluate_execution(prior, 1)
        self.assertEqual((result.village_win, result.wolf_win, result.unresolved), (0, Fraction(5, 9), Fraction(4, 9)))
        advanced = apply_execution(AnalysisState(prior), 1)
        self.assertEqual(advanced.wolf_win, Fraction(5, 9))
        self.assertEqual(len(advanced.all_worlds), 126)

    def test_victory_uses_exact_alive_role_counts(self):
        players = (1, 2, 3, 4, 5)
        self.assertEqual(World(players, frozenset({1, 2}), (3, 4, 5)).winner, "village")
        self.assertEqual(World(players, frozenset({1, 2}), (1, 2, 3)).winner, "wolf")
        self.assertIsNone(World(players, frozenset({1}), (1, 2, 3)).winner)

    def test_invalid_target_and_cast_are_rejected(self):
        prior = initial_belief()
        for target in (0, 4, -1, True, 1.0, "1", None):
            with self.subTest(target=target), self.assertRaises(ValueError):
                evaluate_execution(prior, target)
        for count, wolves in ((2, 1), (10, 1), (3, 0), (4, 2), (True, 1), (5, True)):
            with self.subTest(count=count, wolves=wolves), self.assertRaises(ValueError):
                initial_belief(count, wolves)

    def test_invalid_probabilities_and_mixed_public_histories_are_rejected(self):
        worlds = tuple(item.world for item in initial_belief().worlds)
        with self.assertRaises(ValueError):
            WeightedWorld(worlds[0], 0.5)
        with self.assertRaises(ValueError):
            Belief((WeightedWorld(worlds[0], Fraction(1, 2)),))
        with self.assertRaises(ValueError):
            Belief((WeightedWorld(worlds[0], Fraction(1, 2)), WeightedWorld(worlds[0], Fraction(1, 2))))
        with self.assertRaises(ValueError):
            Belief((WeightedWorld(worlds[0].remove(1), Fraction(1, 2)), WeightedWorld(worlds[1].remove(2), Fraction(1, 2))))
        with self.assertRaises(ValueError):
            AnalysisState(None)

    def test_repeated_evaluation_is_deterministic_and_does_not_mutate_input(self):
        prior = initial_belief(5)
        before = prior.worlds
        result = evaluate_execution(prior, 1)
        for _ in range(10):
            self.assertEqual(evaluate_execution(prior, 1), result)
            self.assertEqual(prior.worlds, before)


if __name__ == "__main__":
    unittest.main()
