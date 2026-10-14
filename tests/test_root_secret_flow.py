import copy,unittest
from dataclasses import replace
from fractions import Fraction as F
from collections import defaultdict
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy
from werewolf.seer_acquisition import normalize,initial_random_white,from_board,SeerReport
from werewolf.seer_future_uniform import FuturePending
from werewolf.root_secret_flow import (prepare_root_secrets,root_actor_view,
    observe_root_public,step_root_action,root_secret_value)
from werewolf.policy_choice import optimal_targets,uniform_policy


class RootSecretTests(unittest.TestCase):
    rules=Rules(initial_seer='random_white')
    strategy=Strategy('random','random',fake_reports='random')

    def test_user_initial_white_example_and_actor_condition(self):
        b=initial_board(5,1,1,1);root=prepare_root_secrets(b,self.rules)
        self.assertEqual(len(root.public_law.hypotheses),180)
        self.assertEqual(root.public_law.tracked,None)
        own=root_actor_view(root,lambda h:h.roles[2]==1)
        self.assertEqual(len(own.belief.public_roles),12)
        self.assertEqual(len(own.belief.hypotheses),36)
        roles=normalize(tuple(h for h in from_board(b) if h.roles[2]==1))
        self.assertEqual(own.belief.hypotheses,initial_random_white(roles,b.alive))
        positions=defaultdict(F);role_mass=defaultdict(F)
        for h in own.belief.hypotheses:
            a=h.acquisitions[0];positions[a.target]+=h.mass
            role_mass['medium' if h.roles[1]&(1<<(a.target-1)) else 'villager']+=h.mass
        self.assertEqual(dict(positions),{p:F(1,4) for p in range(2,6)})
        self.assertEqual(dict(role_mass),{'medium':F(1,3),'villager':F(2,3)})
        white=root_actor_view(root,lambda h:h.roles[2]==1 and any(a.target==2 for a in h.acquisitions))
        self.assertTrue(all(not h.roles[0]&2 for h in white.belief.hypotheses))
        self.assertEqual(root.public_law.public_roles,tuple(sorted(b.worlds)))

    def fixed_root(self):
        b=replace_worlds(initial_board(7,1,1,1),((1,4,2,0,F(1)),))
        return prepare_root_secrets(b,self.rules)

    def step(self,root,target):
        branches=step_root_action(root,target,self.rules,self.strategy)
        self.assertNotIsInstance(branches,FuturePending)
        self.assertEqual(sum(q for q,_ in branches),1)
        self.assertEqual(len(branches),1)
        return branches[0][1]

    def test_latent_seer_multiple_nights_keep_owner_records_and_predeath_rosters(self):
        root=self.fixed_root();before=copy.deepcopy(root)
        for target in (7,6,5,4):root=self.step(root,target)
        self.assertEqual(root.public.day,3)
        self.assertEqual(root.public.alive,(1,2,3))
        for h in root.physical_law.hypotheses:
            self.assertEqual(tuple(a.day for a in h.acquisitions),(1,2,3))
            self.assertEqual(tuple(a.target for a in h.attacks),(6,4))
            self.assertEqual(len({a.target for a in h.acquisitions}),3)
        self.assertEqual(root.physical_law.rosters[1],(1,2,3,4,5,6))
        self.assertEqual(root.physical_law.rosters[2],(1,2,3,4))
        self.assertEqual(before,self.fixed_root())

    def test_dead_latent_seer_retains_past_secrets_without_new_acquisition(self):
        root=self.fixed_root()
        for target in (7,6,2,4):root=self.step(root,target)
        self.assertTrue(all(len(h.acquisitions)==2 for h in root.physical_law.hypotheses))
        self.assertTrue(all(len(h.attacks)==2 for h in root.physical_law.hypotheses))

    def test_model_a_world_weights_do_not_become_physical_mass(self):
        b=replace_worlds(initial_board(5,1,1,1),((1,2,4,0,F(1,4)),(1,4,2,0,F(3,4))))
        root=prepare_root_secrets(b,self.rules)
        # Public external Q is supplied independently of actual evidence mass.
        public=replace_worlds(b,((1,2,4,0,F(2,3)),(1,4,2,0,F(1,3))))
        observed=observe_root_public(root,public,lambda h:True)
        self.assertEqual(observed.public_law.public_roles,public.worlds)
        self.assertEqual(observed.physical_law.public_roles,b.worlds)
        view=root_actor_view(observed,lambda h:True)
        self.assertNotEqual(view.belief.public_roles,view.physical_law.public_roles)
        self.assertEqual(root.public_law.public_roles,b.worlds)
        self.assertEqual(observe_root_public(root,public,lambda h:h.roles[1]==2),
                         FuturePending('root_secret_public_history_zero_support'))

    def test_new_max_and_unknown_midgame_are_explicitly_pending(self):
        root=self.fixed_root()
        self.assertEqual(root_secret_value(root,self.rules,Strategy()),FuturePending('root_secret_max_unimplemented'))
        child=self.step(root,7)
        self.assertEqual(prepare_root_secrets(child.public,self.rules),FuturePending('root_secret_initial_board_required'))
        co=replace(root.public,claims=('latent','seer')+('latent',)*5)
        declared=replace(root,public=co,physical=co)
        self.assertEqual(root_secret_value(declared,self.rules,self.strategy),FuturePending('full_disclosure_truth_not_conditioned'))
        self.assertEqual(root_secret_value(root,Rules(allow_self_bite=True),self.strategy),
                         FuturePending('root_secret_self_bite_policy_support_unimplemented'))

    def test_random_continuation_public_and_actor_values_are_exact(self):
        root=prepare_root_secrets(initial_board(5,1,1,1),self.rules)
        self.assertEqual(root_secret_value(root,self.rules,self.strategy),F(7,15))
        actor=root_actor_view(root,lambda h:h.roles[2]==1)
        self.assertEqual(root_secret_value(root,self.rules,self.strategy,actor=actor),F(7,15))

    def test_public_observation_connects_existing_full_disclosure_without_rescuing_omissions(self):
        root=self.fixed_root()
        declared=replace(root.public,claims=('latent','seer')+('latent',)*5)
        observed=observe_root_public(root,declared,
            lambda h:any(a.day==1 and a.player==2 and a.target==5 for a in h.acquisitions),
            past=(SeerReport(1,1,2,5,'white'),))
        day=step_root_action(observed,7,self.rules,self.strategy)
        self.assertEqual(len(day),1)
        night=step_root_action(day[0][1],6,self.rules,self.strategy)
        self.assertNotIsInstance(night,FuturePending)
        self.assertEqual(sum(q for q,_ in night),1)
        self.assertTrue(all(len(branch.past)==2 for _,branch in night))
        self.assertTrue(all(any(a.day==1 and a.target==5 for a in h.acquisitions)
                            for _,branch in night for h in branch.physical_law.hypotheses))

    def test_shared_selector_keeps_objective_and_complete_uniform_ties(self):
        scores=((1,F(1,4)),(2,F(3,4)),(3,F(3,4)))
        self.assertEqual(uniform_policy(optimal_targets(scores,maximize=True)),((2,F(1,2)),(3,F(1,2))))
        self.assertEqual(uniform_policy(optimal_targets(scores,maximize=False)),((1,F(1)),))
