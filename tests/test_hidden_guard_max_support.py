"""Regression for the declared Model A/policy-zero-support boundary."""
import unittest
from fractions import Fraction as F
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy
from werewolf.seer_acquisition import Hypothesis
from werewolf.seer_future_uniform import TrueScanState,FuturePending
from werewolf.information_set_forecast import information_forecast
from werewolf.guard_history_mixture import enumerate_guard_history_mixture
from werewolf.policy_choice import optimal_targets,uniform_policy

class HiddenGuardMaxSupportTests(unittest.TestCase):
    def test_unknown_guard_max_gj_has_public_world_without_policy_history(self):
        board=replace_worlds(initial_board(3,1,0,0,1),
            ((4,0,0,1,F(3,4)),(4,0,0,2,F(1,4))),phase='night')
        state=TrueScanState(tuple(Hypothesis(w[:-1],(),w[-1]) for w in board.worlds),
                            rosters=((1,2,3),(1,2,3)))
        scores=information_forecast(board,state,(),Rules(),Strategy(day='random',night='max'),mask=4)
        self.assertEqual(scores,((1,F(1,24)),(2,F(1,8))))
        policy=uniform_policy(optimal_targets(scores,maximize=False))
        self.assertEqual(policy,((1,F(1)),))
        # The SAME selected kernel applies to both unknown hunter placements.
        mixture=enumerate_guard_history_mixture(state,state.public_roles,1,board.alive,
                                               {(4,()):policy},deaths=())
        self.assertEqual(mixture.physical_mass,F(1,8))
        self.assertEqual(mixture.zero_support_roles,((4,0,0,1),))
        self.assertIsInstance(mixture.public,FuturePending)
        self.assertEqual(mixture.public.reason,'guard_public_history_zero_support')
        self.assertEqual({h.roles for h in mixture.physical.hypotheses},{(4,0,0,2)})
        self.assertEqual(state.public_roles,tuple(sorted(board.worlds)))
        self.assertEqual(mixture.role_prior,state.public_roles)