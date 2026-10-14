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
    def test_legal_four_player_board_global_support_and_past_policy(self):
        from dataclasses import asdict
        from werewolf.seer_manual import migrate_game,replay
        from werewolf.seer_acquisition import from_board
        from werewolf.root_secret_flow import RootSecretBranch,observe_root_public
        from werewolf.evaluation_branch import physical_board
        claims=['hunter','latent','latent','latent']
        cp={'hunter':'none'}
        policy=asdict(Strategy(day='random',night='max',fake_reports='random',disclosure_common='none'))
        game=migrate_game({'players':4,'wolves':1,'hunters':1,'mediums':0,'seers':0,
            'history':[{'target':4,'claims':claims,'claim_policy':cp,'policy':policy}],
            'claims':claims,'claim_policy':cp,'policy':policy,'rules':asdict(Rules()),
            'seer_mode':'information-fixed-v1','seer_inputs':[]})
        rules,before=replay(game)
        board=before.board
        self.assertEqual(board.alive,(1,2,3))
        source=TrueScanState(from_board(board),rosters=((1,2,3,4),(1,2,3)))
        policies={}
        for mask in {h.roles[0] for h in source.hypotheses}:
            values=information_forecast(board,source,(),rules,Strategy(**policy),mask=mask)
            policies[mask,()]=uniform_policy(optimal_targets(values,maximize=False))
        self.assertEqual(policies,{(1,()):((2,F(1,2)),(3,F(1,2))),
                                   (2,()):((1,F(1)),),(4,()):((1,F(1)),)})
        gj={'target':None,'claims':claims,'claim_policy':cp,'policy':policy,
            'observation':'night-deaths-v1','deaths':[]}
        observed=migrate_game({**game,'history':[game['history'][0],gj]})
        _,max_after=replay(observed)
        self.assertEqual({w[0] for w in max_after.board.worlds},{1})
        self.assertEqual({w[-1] for w in max_after.board.worlds},{F(1,2)})
        # The previous compatibility-only reference is now an actual RANDOM
        # night; a saved max night uses the approved generated support filter.
        _,after=replay(migrate_game({**game,'history':[game['history'][0],
            {**gj,'policy':{**policy,'night':'random'}}]}))
        self.assertEqual(len(after.board.worlds),4)
        self.assertEqual({w[-1] for w in after.board.worlds},{F(1,4)})
        mixture=enumerate_guard_history_mixture(source,after.board.worlds,1,board.alive,policies,deaths=())
        self.assertEqual(mixture.physical_mass,F(1,10))
        self.assertEqual(set(mixture.zero_support_roles),{(2,0,0,1),(4,0,0,1)})
        # Proposal only: public support over ALL wolf rosters, no owner predicate.
        supported={roles for roles,likelihood in mixture.role_support if likelihood>0}
        kept=tuple(w for w in after.board.worlds if w[:-1] in supported)
        total=sum((w[-1] for w in kept),F())
        support_board=replace_worlds(after.board,tuple((*w[:-1],w[-1]/total) for w in kept))
        self.assertEqual({w[0] for w in support_board.worlds},{1})
        self.assertEqual({w[-1] for w in support_board.worlds},{F(1,2)})
        # Existing world reweighting accepts the support-filtered public Board.
        own=mixture.physical
        physical=physical_board(support_board,own)
        projected=observe_root_public(RootSecretBranch(physical,own,physical,own),support_board,lambda h:True)
        self.assertNotIsInstance(projected,FuturePending)
        self.assertEqual(projected.public_law.public_roles,tuple(sorted(support_board.worlds)))
        from werewolf.guard_model import public_guard_branch_law
        from werewolf.information_set_forecast import InformationSetForecast,Pending
        engine=InformationSetForecast(rules,Strategy(**policy))
        actual_board,actual_law=public_guard_branch_law(board,source,after.board,None,True,engine,policies=policies)
        self.assertEqual(actual_board,support_board)
        self.assertEqual(actual_law.public_roles,tuple(sorted(support_board.worlds)))
        from unittest.mock import patch
        from werewolf.actor_information import WolfInformation
        import werewolf.guard_model as guard_module
        # A nonselected private action does NOT change the public kernel.
        held=InformationSetForecast(rules,Strategy(**policy),memoize_flows=False)
        held.retain_joint_guard_history=True
        private=WolfInformation(2).condition_public(source)
        original=guard_module.public_guard_branch_law
        def selected_kernel(b,st,child,attack,blocked,e,**kw):
            return original(b,st,child,attack,blocked,e,policies=policies)
        with patch.object(guard_module,'public_guard_branch_law',selected_kernel), \
             patch.object(held,'wolf_policy',side_effect=AssertionError('No future wolf decision is needed')):
            value=held.act(board,source,(),3,private,None)
        # P3 is guarded with 1/2; then random execution wins with 1/3.
        self.assertEqual(value,F(1,6))
        self.assertEqual(actual_law.public_roles,tuple(sorted(support_board.worlds)))

        with self.assertRaises(Pending) as missing:
            public_guard_branch_law(board,source,after.board,None,True,engine,policies={(1,()):policies[1,()]})
        self.assertEqual(missing.exception.reason,'guard_public_kernel_incomplete')
        with self.assertRaises(Pending) as unresolved:
            public_guard_branch_law(board,source,after.board,None,True,engine)
        self.assertEqual(unresolved.exception.reason,'guard_max_public_kernel_unresolved')

        # Current max must not retroactively replace an earlier random night.
        old_random={**gj,'policy':{**policy,'night':'random'}}
        historical=migrate_game({**game,'history':[game['history'][0],old_random]})
        self.assertEqual(historical['policy']['night'],'max')
        self.assertEqual(historical['history'][1]['policy']['night'],'random')
        _,random_after=replay(historical)
        random_kernels={(mask,()):uniform_policy(tuple(p for p in board.alive if not mask&(1<<(p-1))))
                        for mask in {h.roles[0] for h in source.hypotheses}}
        random_mix=enumerate_guard_history_mixture(source,random_after.board.worlds,1,board.alive,random_kernels,deaths=())
        self.assertEqual(random_mix.zero_support_roles,())
        self.assertEqual(random_mix.physical_mass,F(1,5))
        self.assertEqual(random_mix.public.public_roles,tuple(sorted(random_after.board.worlds)))


    def test_public_support_keeps_role_weights_despite_unequal_likelihoods(self):
        from dataclasses import replace
        from werewolf.public_observation_support import condition_generated_support
        from werewolf.seer_acquisition import normalize
        from werewolf.guard_effect import GuardIntent
        from werewolf.night_knowledge import WolfAttack
        board=replace_worlds(initial_board(3,1,0,0,1),
            ((4,0,0,1,F(3,4)),(4,0,0,2,F(1,4))),phase='night')
        source=TrueScanState(tuple(Hypothesis(w[:-1],(),w[-1]) for w in board.worlds),
                            rosters=((1,2,3),(1,2,3)))
        # A public GJ leaves both roles; 1/8 vs 3/8 likelihood is NOT a Q weight.
        entries=(Hypothesis((4,0,0,1),(),F(3,32),(GuardIntent(1,1,2),),(WolfAttack(1,2),)),
                 Hypothesis((4,0,0,2),(),F(3,32),(GuardIntent(1,2,1),),(WolfAttack(1,1),)))
        child=replace(board,phase='day',day=2)
        public,joint=condition_generated_support(child,source,entries)
        self.assertEqual(public.worlds,child.worlds)
        self.assertEqual(joint.public_roles,source.public_roles)
        bayes=replace(source,hypotheses=normalize(entries))
        self.assertEqual({w[-1] for w in bayes.public_roles},{F(1,2)})
        self.assertNotEqual(bayes.public_roles,joint.public_roles)
        with self.assertRaisesRegex(ValueError,'public_generated_observation_zero_support'):
            condition_generated_support(child,source,())
