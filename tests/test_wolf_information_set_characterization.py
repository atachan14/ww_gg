"""Information-set reference oracles and model-A regression."""
import unittest
from collections import defaultdict
from fractions import Fraction as F
from werewolf.exact import (initial_board,replace_worlds,condition_claims,ClaimPolicy,
                            action_outcomes,legal_targets,Rules,Strategy)
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState,FuturePending
from werewolf.seer_future_forecast import project_private
from werewolf.seer_view_forecast import seer_forecast


def roster_random_kernel(board):
    """Test-only reference: W is known; no role/acquisition metadata is read."""
    masses=defaultdict(F)
    for w in board.worlds:masses[w[0]]+=w[-1]
    policies={mask:{p:F(1,len([t for t in board.alive if not mask&(1<<(t-1))]))
                    for p in board.alive if not mask&(1<<(p-1))} for mask in masses}
    return masses,policies


class WolfInformationSetCharacterizationTests(unittest.TestCase):
    def test_minimal_three_alive_counterexample_is_resolved(self):
        seed=replace_worlds(initial_board(4,1,0,1),((2,0,1,0,F(1,2)),(1,0,4,0,F(1,2))))
        seed=condition_claims(seed,('seer','latent','latent','latent'),ClaimPolicy(seer='none'))
        b=next(o.board for o in action_outcomes(seed,4,Rules(initial_seer='none'),Strategy()) if o.board.winner is None)
        s=project_private(TrueScanState(from_board(seed),((1,2,3,4),),initial_rule='none',tracked=(1,)),b)
        self.assertEqual(legal_targets(b,Rules(),Strategy()),(1,2,3))
        result=seer_forecast(b,1,(),Rules(initial_seer='none'),Strategy('max','random'),scan_state=s)
        self.assertEqual(dict(result),{2:F(0),3:F(0),4:F(0)})  # corpse4 remains scannable
        masses,policies=roster_random_kernel(b);actual=defaultdict(F)
        for mask,policy in policies.items():
            for p,q in policy.items():actual[p]+=masses[mask]*q
        self.assertEqual(dict(actual),{1:F(1,4),2:F(1,4),3:F(1,2)})
        for mask,policy in policies.items():
            actual_worlds=tuple(w for w in b.worlds if w[0]==mask)
            private=replace_worlds(b,tuple((*w[:-1],w[-1]/masses[mask]) for w in actual_worlds))
            self.assertEqual(sum(policy.values()),1)
            for target in policy:
                self.assertFalse(mask&(1<<(target-1)))
                self.assertTrue(all(o.board.winner=='wolf' for o in action_outcomes(private,target,Rules(),Strategy())))

    def test_same_roster_uniform_kernel_cannot_read_hidden_true_seer(self):
        b=initial_board(4,1,0,1)
        first=replace_worlds(b,((2,0,1,0,F(1,2)),(1,0,4,0,F(1,2))))
        split=replace_worlds(b,((2,0,1,0,F(1,4)),(2,0,4,0,F(1,4)),(1,0,2,0,F(1,2))))
        self.assertEqual(roster_random_kernel(first),roster_random_kernel(split))

    def test_action_selection_likelihood_is_a_distinct_public_update_choice(self):
        from dataclasses import replace
        # Same initial wolf count2, but dead7 makes live counts1 vs2.
        seed=replace_worlds(initial_board(7,2),((65,0,0,0,F(1,2)),(3,0,0,0,F(1,2))))
        b=next(o.board for o in action_outcomes(seed,7,Rules(),Strategy()) if o.board.winner is None)
        self.assertEqual(b.wolf_count_distribution,{1:F(1,2),2:F(1,2)})
        masses,policies=roster_random_kernel(b)
        weights={mask:masses[mask]*policy[3] for mask,policy in policies.items()}
        total=sum(weights.values())
        self.assertEqual({mask:q/total for mask,q in weights.items()},{65:F(4,9),3:F(5,9)})
        # The existing forced-target law deliberately preserves the count prior.
        self.assertEqual(action_outcomes(b,3,Rules(),Strategy())[0].board.wolf_count_distribution,
                         {1:F(1,2),2:F(1,2)})
