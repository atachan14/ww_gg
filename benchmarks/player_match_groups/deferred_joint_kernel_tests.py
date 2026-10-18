import unittest
from fractions import Fraction as F
from dataclasses import replace
from werewolf.exact import Rules,Strategy,initial_board
from werewolf.wolf_profile_certificate import WolfProfileResolver
from werewolf.seer_future_uniform import TrueScanState
from werewolf.seer_acquisition import Hypothesis
from werewolf.information_set_forecast import Pending

class JointKernelLRUTests(unittest.TestCase):
    def fixture(self):
        s=TrueScanState((Hypothesis((1,0,0,0),(),F(1)),))
        return WolfProfileResolver(Rules(),Strategy(),joint_kernel_reuse=True),initial_board(6,1),s
    def test_acquisition_full_source_lru_and_budget(self):
        e,b,s=self.fixture()
        for i in range(64):self.assertIs(e.acquisition((e.rules,e.strategy,b,s,i),lambda:s),s)
        e.acquisition((e.rules,e.strategy,b,s,0),lambda:None)
        e.acquisition((e.rules,e.strategy,b,s,64),lambda:s)
        self.assertIn((e.rules,e.strategy,b,s,0),e.joint_kernels['acquisition'])
        self.assertNotIn((e.rules,e.strategy,b,s,1),e.joint_kernels['acquisition'])
        self.assertEqual(len(e.joint_kernels['acquisition']),64)
        self.assertEqual(e.joint_kernel_costs['acquisition'],128)
        self.assertLessEqual(e.joint_kernel_costs['acquisition'],8000)
    def test_support_preserves_board_and_complete_joint(self):
        e,b,s=self.fixture();value=(b,s);key=(e.rules,e.strategy,b,s)
        self.assertIs(e.public_support(key,lambda:value),value)
        self.assertIs(e.public_support(key,lambda:None),value)
        self.assertEqual(e.support_stats,{'calls':2,'hits':1})
        self.assertEqual(e.joint_kernel_costs['support'],2)
        changed=replace(s,initial_rule='none')
        self.assertIs(e.public_support((e.rules,e.strategy,b,changed),lambda:(b,changed))[1],changed)
        self.assertEqual(e.support_stats['hits'],1)
    def test_failure_is_not_cached_and_other_sizes_keep_legacy_cache(self):
        e,b,s=self.fixture();key=(e.rules,e.strategy,b,s)
        def failure():raise Pending('unfinished')
        with self.assertRaises(Pending):e.acquisition(key,failure)
        self.assertNotIn(key,e.joint_kernels['acquisition'])
        small=initial_board(5,1);old=(e.rules,e.strategy,small,s)
        self.assertIs(e.acquisition(old,lambda:s),s)
        self.assertIn(old,e.acquisition_cache)
        self.assertEqual(len(e.joint_kernels['acquisition']),0)

    def test_six_player_real_gj_transition_matches_legacy_joint_law(self):
        from dataclasses import replace
        from tests.test_root_guard_max import RootGuardMaxTests
        from werewolf.seer_manual import replay
        from werewolf.root_secret_flow import prepare_root_entry
        from werewolf.wolf_profile_certificate import FixedPublicWolfProfile
        from werewolf.actor_information import wolf_information_groups
        from werewolf.policy_choice import uniform_policy
        from werewolf.guard_model import condition_guard_observation,public_guard_branch_law
        for repeat in(False,True):
            g=RootGuardMaxTests().game(repeat,players=6);r,p=replay(g);strategy=Strategy(**g['policy']);root=prepare_root_entry(g,p.board,r,strategy)
            b,state=root.public,root.public_law
            # A fully specified legal counterfactual profile, not an equilibrium choice.
            profile=tuple((info,uniform_policy(tuple(t for t in b.alive if not info.initial_roster&(1<<(t-1)))))for info,mass,law in wolf_information_groups(state))
            kernel={(info.initial_roster,info.attacks):row for info,row in profile};values=[]
            for enabled in(False,True):
                resolver=WolfProfileResolver(r,strategy,joint_kernel_reuse=enabled)
                engine=FixedPublicWolfProfile(b,state,(),r,strategy,profile,resolver=resolver)
                acquired=engine.acquire(b,state)
                child=replace(condition_guard_observation(b,(),r,state=acquired),day=b.day+1,phase='day')
                value=public_guard_branch_law(b,acquired,child,2,True,engine,policies=kernel)
                self.assertIs(value,public_guard_branch_law(b,acquired,child,3,True,engine,policies=kernel))
                self.assertEqual(len(value[0].worlds),8)
                self.assertEqual(len(value[1].hypotheses),24)
                self.assertEqual({h.mass for h in value[1].hypotheses},{F(1,24)})
                self.assertEqual(value[1].public_roles,tuple(sorted(value[0].worlds)))
                values.append(value)
            self.assertEqual(values[0],values[1])
