import unittest
from dataclasses import replace
from fractions import Fraction as F
from tests import test_fixed_actor_continuation as fixtures
from werewolf.actor_information import WolfInformation
from werewolf.fixed_actor_continuation import physical_actor_outcomes,fixed_actor_value
from werewolf.guard_model import condition_guard_observation,public_guard_branch_law
from werewolf.information_set_forecast import Pending
from werewolf.evaluation_branch import ActionInputs
from werewolf.action_flow import resolve_action

class PublicPhysicalContinuationTests(unittest.TestCase):
    def branch(self,repeat):
        b,s,e=fixtures.FixedActorContinuationTests().fixture(6,repeat)
        # A held complete public kernel, not a claim that this proposal is max.
        kernels={(mask,()):(((2,F(1,4)),(3,F(1,4)),(4,F(1,4)),(5,F(1,4)))
                 if mask==1 else ((1,F(1)),)) for mask in {h.roles[0] for h in s.hypotheses}}
        observed=replace(condition_guard_observation(b,(),e.rules,state=s),day=2,phase='day')
        public,law=public_guard_branch_law(b,e.acquire(b,s),observed,None,True,e,policies=kernels)
        self.assertEqual({w[0] for w in public.worlds},{1})
        self.assertEqual({w[3] for w in public.worlds},{2,4,8,16})
        own=WolfInformation(2).condition_public(s)
        physical=next((q,c,st) for q,c,st in physical_actor_outcomes(b,own,e,3)
                      if c.alive==b.alive)
        q,actual,private=physical
        self.assertEqual(q,F(1,4))
        self.assertEqual({h.roles[0] for h in private.hypotheses},{2})
        self.assertEqual({h.roles[3] for h in private.hypotheses},{1})
        self.assertEqual({h.attacks[-1].target for h in private.hypotheses},{3})
        self.assertEqual(public.winner,actual.winner)
        return b,s,e,public,law,actual,private

    def test_continuation_observation_has_zero_public_support(self):
        for repeat in (True,False):
            b,s,e,public,law,actual,private=self.branch(repeat)
            self.assertEqual({o.board.winner for o in e.public_children(public,1)},{'village'})
            _,outcomes=resolve_action(public,ActionInputs(law,(),private,None,actual),1,e.action_policy)
            self.assertEqual(len(outcomes),1)
            self.assertIsNone(outcomes[0].board.winner)
            self.assertIsNone(outcomes[0].context)
            # Continuing play is public evidence. Do not use the public model's
            # terminal prediction as a physical payoff or invent missing mass.
            with self.assertRaises(Pending) as stopped:
                e.act(public,law,(),1,private,None,physical=actual)
            self.assertEqual(stopped.exception.reason,'public_continuation_zero_support')

    def test_physical_terminal_payoff_and_known_actor_suffix_need_no_new_belief(self):
        for repeat,expected in ((True,F(3,10)),(False,F(43,144))):
            b,s,e,public,law,actual,private=self.branch(repeat)
            self.assertEqual({o.board.winner for o in e.public_children(public,2)},{None})
            self.assertEqual(e.act(public,law,(),2,private,None,physical=actual),1)
            # W2 already knows H1 through PUBLIC CO plus its own role; the
            # whole forced P3 candidate has a defined physical continuation.
            self.assertEqual(fixed_actor_value(b,s,e,info=WolfInformation(2),target=3),expected)
