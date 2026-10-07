import unittest
from fractions import Fraction

from werewolf.exact import Belief, PLAYERS, WeightedWorld, World, evaluate_execution, evaluate_uniform_strategy, initial_belief


class ThreePlayerExactTests(unittest.TestCase):
    def test_prior_keeps_every_compatible_assignment(self):
        belief = initial_belief()
        self.assertEqual({item.world.wolf_id for item in belief.worlds}, {1, 2, 3})
        self.assertEqual({item.probability for item in belief.worlds}, {Fraction(1, 3)})

    def test_role_marginals_are_exact_and_conserve_the_cast(self):
        belief = initial_belief()
        for player in PLAYERS:
            self.assertEqual(belief.role_probability(player, "wolf"), Fraction(1, 3))
            self.assertEqual(belief.role_probability(player, "village"), Fraction(2, 3))
        self.assertEqual(sum(belief.role_probability(p, "wolf") for p in PLAYERS), 1)
        self.assertEqual(sum(belief.role_probability(p, "village") for p in PLAYERS), 2)

    def test_every_target_has_the_agreed_exact_value(self):
        for target in PLAYERS:
            result = evaluate_execution(initial_belief(), target)
            self.assertEqual(result.village_win, Fraction(1, 3))
            self.assertEqual(result.wolf_win, Fraction(2, 3))
            self.assertEqual(sum(outcome.probability for outcome in result.outcomes), 1)

    def test_execution_returns_both_terminal_outcomes_without_a_draw(self):
        result = evaluate_execution(initial_belief(), 2)
        by_role = {outcome.removed_role: outcome for outcome in result.outcomes}
        self.assertEqual(by_role["wolf"].probability, Fraction(1, 3))
        self.assertEqual(by_role["wolf"].counts, (2, 0))
        self.assertEqual(by_role["wolf"].winner, "village")
        self.assertEqual(by_role["village"].probability, Fraction(2, 3))
        self.assertEqual(by_role["village"].counts, (1, 1))
        self.assertEqual(by_role["village"].winner, "wolf")
        self.assertTrue(all(outcome.posterior.finished for outcome in result.outcomes))

    def test_conditioning_preserves_uncertainty_in_the_villager_outcome(self):
        result = evaluate_execution(initial_belief(), 2)
        wolf_branch, village_branch = result.outcomes
        self.assertEqual(len(wolf_branch.posterior.worlds), 1)
        self.assertEqual(len(village_branch.posterior.worlds), 2)
        for player in (1, 3):
            self.assertEqual(village_branch.posterior.role_probability(player, "wolf"), Fraction(1, 2))
            self.assertEqual(wolf_branch.posterior.role_probability(player, "wolf"), 0)

    def test_dead_target_is_removed_in_every_world(self):
        result = evaluate_execution(initial_belief(), 2)
        for outcome in result.outcomes:
            self.assertEqual(outcome.posterior.alive, (1, 3))

    def test_decision_value_and_random_policy_value_are_separate(self):
        # An asymmetric belief verifies the distinction; it is not a new UI input.
        known_assignment = Belief((WeightedWorld(World(2), Fraction(1)),))
        self.assertEqual(evaluate_execution(known_assignment, 2).village_win, 1)
        self.assertEqual(evaluate_execution(known_assignment, 1).village_win, 0)
        self.assertEqual(evaluate_uniform_strategy(known_assignment).village_win, Fraction(1, 3))

    def test_uniform_policy_matches_the_baseline(self):
        result = evaluate_uniform_strategy(initial_belief())
        self.assertEqual(result.village_win, Fraction(1, 3))
        self.assertEqual(result.wolf_win, Fraction(2, 3))

    def test_terminal_outcomes_cannot_advance(self):
        for outcome in evaluate_execution(initial_belief(), 1).outcomes:
            for target in outcome.posterior.alive:
                with self.assertRaises(ValueError):
                    evaluate_execution(outcome.posterior, target)

    def test_invalid_target_rejected_without_mutating_the_prior(self):
        prior = initial_belief()
        for target in (0, 4, -1, True, 1.0, "1", None):
            with self.subTest(target=target), self.assertRaises(ValueError):
                evaluate_execution(prior, target)
        self.assertEqual(prior, initial_belief())

    def test_invalid_probability_distribution_rejected(self):
        invalid = (
            (),
            (WeightedWorld(World(1), Fraction(1, 2)),),
            (WeightedWorld(World(1), Fraction(0)),),
            (WeightedWorld(World(1), Fraction(-1)),),
            (WeightedWorld(World(1), 1.0),),
            (WeightedWorld(World(1), Fraction(1, 2)), WeightedWorld(World(1), Fraction(1, 2))),
        )
        for worlds in invalid:
            with self.subTest(worlds=worlds), self.assertRaises(ValueError):
                Belief(worlds)

    def test_terminal_judgment_uses_role_counts_not_marginal_rounding(self):
        self.assertEqual(World(1, (2, 3)).winner, "village")
        self.assertEqual(World(1, (1, 3)).winner, "wolf")
        self.assertIsNone(World(1).winner)

    def test_repeated_evaluation_is_deterministic(self):
        prior = initial_belief()
        result = evaluate_execution(prior, 1)
        for _ in range(12):
            self.assertEqual(evaluate_execution(prior, 1), result)
        self.assertEqual(prior, initial_belief())


if __name__ == "__main__":
    unittest.main()
