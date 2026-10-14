import unittest
from fractions import Fraction as F
from copy import deepcopy
from werewolf.policy_dependencies import Dependency,DependencyGraph,DependencyCycle
from werewolf.policy_certificates import certify_uniform_profiles
from werewolf.information_set_forecast import Pending


class PolicyDependencyTests(unittest.TestCase):
    def test_cached_request_records_cycle_without_recomputing_or_leaking_stack(self):
        g=DependencyGraph();policy=Dependency('policy',('public',));value=Dependency('value',('candidate',))
        with g.evaluating(policy):
            with g.evaluating(value):g.request(policy)
        self.assertEqual(g.stack,[])
        self.assertEqual(set(g.cycles()[0]),{policy,value})
        with self.assertRaises(DependencyCycle):
            with g.evaluating(policy):
                with g.evaluating(value):
                    with g.evaluating(policy):pass
        self.assertEqual(g.stack,[])

    def test_contexts_remain_distinct(self):
        g=DependencyGraph();a=Dependency('policy',('Q',));b=Dependency('policy',('P',))
        with g.evaluating(a):g.request(b)
        self.assertEqual(g.cycles(),())
        self.assertEqual(len(g.components()),2)


class UniformProfileTests(unittest.TestCase):
    def test_complete_unique_certificate_keeps_all_ties(self):
        result=certify_uniform_profiles((('actor',(1,2)),),lambda k:{'actor':((1,F(1,2)),(2,F(1,2)))})
        self.assertEqual(result.status,'unique');self.assertEqual(result.evaluated,3)
        self.assertEqual(result.selected.profile, (('actor', ((1,F(1,2)),(2,F(1,2)))),))

    def test_multiple_no_admissible_and_budget_are_distinct(self):
        legal=(('actor',(1,2)),)
        def self_fulfilling(profile):
            chosen=dict(profile)['actor']
            return {'actor':tuple((a,F(0) if a in dict(chosen) else F(1)) for a in (1,2))}
        multiple=certify_uniform_profiles(legal,self_fulfilling)
        self.assertEqual(multiple.status,'multiple');self.assertEqual(len(multiple.certified),3)
        self.assertIsNone(multiple.selected)
        def no_uniform_fixed_point(profile):
            chosen=dict(profile)['actor']
            scores=((1,F(1)),(2,F(0))) if chosen==((1,F(1)),) else ((1,F(0)),(2,F(1)))
            return {'actor':scores}
        self.assertEqual(certify_uniform_profiles(legal,no_uniform_fixed_point).status,'no_admissible_profile')
        def forbidden(profile):raise AssertionError('Oversized search must not start')
        budget=certify_uniform_profiles(legal,forbidden,max_profiles=2)
        self.assertEqual((budget.status,budget.evaluated),('budget_unfinished',0))
        interrupted=certify_uniform_profiles(legal,self_fulfilling,max_work=1)
        self.assertEqual(interrupted.status,'budget_unfinished');self.assertIsNone(interrupted.selected)

    def test_nonuniform_equilibrium_is_not_invented_under_existing_tie_rule(self):
        # Explicit numeric unit fixture, not a claimed werewolf-board result.
        # The independent-mixture game [[1,0],[0,1/2]] needs (1/3,2/3);
        # no uniform-best-response profile is admissible under our contract.
        legal=(('row',(1,2)),('column',(1,2)))
        def evaluate(profile):
            k={info:dict(policy) for info,policy in profile}
            return {'row':((1,k['column'].get(1,F())),(2,k['column'].get(2,F())/2)),
                    'column':((1,k['row'].get(1,F())),(2,k['row'].get(2,F())/2))}
        result=certify_uniform_profiles(legal,evaluate,maximize={'row':True,'column':False})
        self.assertEqual((result.status,result.evaluated),('no_admissible_profile',9))
        self.assertIsNone(result.selected)

    def test_undefined_observation_and_dependency_never_become_scores(self):
        legal=(('actor',(1,2)),)
        def evaluate(profile):
            if len(dict(profile)['actor'])==1:raise Pending('public_generated_observation_zero_support')
            return {'actor':((1,F()),(2,F()))}
        result=certify_uniform_profiles(legal,evaluate)
        self.assertEqual(result.status,'undefined_observations');self.assertEqual(len(result.certified),1)
        self.assertIsNone(result.selected);self.assertEqual(len(result.issues),2)
        self.assertTrue(all(i.kind=='undefined_observation' for i in result.issues))
        def missing(profile):raise Pending('root_guard_profile_continuation_unresolved')
        self.assertEqual(certify_uniform_profiles(legal,missing).status,'dependency_unfinished')
        with self.assertRaisesRegex(ValueError,'Complete exact'):
            certify_uniform_profiles(legal,lambda k:{'actor':((1,F()),)})


class WolfCommonCertificateTests(unittest.TestCase):
    def test_four_player_day_max_complete_exact_profile(self):
        from dataclasses import replace
        from tests.test_root_guard_max import RootGuardMaxTests
        from werewolf.seer_manual import replay
        from werewolf.exact import Strategy
        from werewolf.root_secret_flow import prepare_root_entry,RootSecretEngine
        from werewolf.wolf_profile_certificate import certify_wolf_profiles,FixedPublicWolfProfile
        from werewolf.actor_information import WolfInformation
        g=RootGuardMaxTests().game();rules,p=replay(g);old=Strategy(**g['policy'])
        branch=prepare_root_entry(g,p.board,rules,old);before=deepcopy(branch);s=replace(old,day='max')
        result=certify_wolf_profiles(branch.public,branch.public_law,(),rules,s)
        self.assertEqual((result.total,result.evaluated),(27,27))
        self.assertEqual(result.status,'unique')
        self.assertEqual(result.selected,result.certified[0])
        self.assertEqual(len(result.certified),1);self.assertEqual(len(result.issues),0)
        cert=result.certified[0]
        self.assertTrue(all(len(policy)==2 and all(q==F(1,2) for t,q in policy) for info,policy in cert.profile))
        scores=dict(cert.scores)
        self.assertEqual(dict(scores[WolfInformation(1)]),{2:F(1,6),3:F(1,6)})
        self.assertTrue(all(v==0 for info,row in cert.scores if info.initial_roster!=1 for t,v in row))
        e=FixedPublicWolfProfile(branch.public,branch.public_law,(),rules,s,cert.profile)
        self.assertEqual(e.solve(branch.public,branch.public_law,(),branch.physical_law,None),F(1,10))
        self.assertNotEqual(e.full_renamed_key(branch.public,branch.public_law,(),branch.physical_law,None,target=2),
                            e.full_renamed_key(branch.public,branch.public_law,(),branch.physical_law,None,target=3))
        changed=list(cert.profile);info,policy=changed[0];changed[0]=(info,((policy[0][0],F(1)),))
        other=FixedPublicWolfProfile(branch.public,branch.public_law,(),rules,s,tuple(changed))
        key_args=(branch.public,branch.public_law,(),branch.physical_law,None)
        self.assertNotEqual(e.full_renamed_key(*key_args,target=2),other.full_renamed_key(*key_args,target=2))
        self.assertEqual(branch,before)
        # Existing daytime-random policy production keeps its exact values,
        # while recorded dependencies expose the cached-kernel proof cycle.
        original=RootSecretEngine(rules,old)
        original.public_night_policies(branch.public,branch.public_law)
        self.assertTrue(original.policy_dependencies.cycles())
        self.assertEqual(original.policy_dependencies.stack,[])


    def test_terminal_payoff_skips_belief_but_state_resolution_still_validates_support(self):
        from dataclasses import replace
        from tests.test_root_guard_max import RootGuardMaxTests
        from werewolf.seer_manual import replay
        from werewolf.exact import Strategy
        from werewolf.root_secret_flow import prepare_root_entry
        from werewolf.wolf_profile_certificate import FixedPublicWolfProfile
        from werewolf.actor_information import wolf_information_groups
        from werewolf.evaluation_branch import ActionInputs,physical_board
        from werewolf.action_flow import resolve_action
        g=RootGuardMaxTests().game();r,p=replay(g);old=Strategy(**g['policy'])
        b=prepare_root_entry(g,p.board,r,old);s=replace(old,day='max')
        groups=wolf_information_groups(b.public_law)
        profile=tuple((info,((next(t for t in b.public.alive if not info.initial_roster&(1<<(t-1))),F(1)),))
                      for info,mass,group in groups)
        info,mass,own=groups[0];e=FixedPublicWolfProfile(b.public,b.public_law,(),r,s,profile)
        self.assertEqual(e.act(b.public,b.public_law,(),3,own,None),F(1,6))
        physical=physical_board(b.public,own)
        with self.assertRaises(Pending) as stopped:
            resolve_action(b.public,ActionInputs(b.public_law,(),own,None,physical),3,e.action_policy)
        self.assertEqual(stopped.exception.reason,'public_generated_observation_zero_support')
        self.assertEqual(e.policy_dependencies.stack,[])

    def test_continuing_gj_zero_support_remains_undefined_without_belief_fill(self):
        from tests.test_root_guard_max import RootGuardMaxTests
        from werewolf.seer_manual import replay
        from werewolf.exact import Strategy
        from werewolf.root_secret_flow import prepare_root_entry
        from werewolf.wolf_profile_certificate import FixedPublicWolfProfile
        from werewolf.actor_information import wolf_information_groups
        g=RootGuardMaxTests().game(players=5)
        g['claim_policy']=g['history'][0]['claim_policy']={'hunter':'filled'}
        r,p=replay(g);s=Strategy(**g['policy']);b=prepare_root_entry(g,p.board,r,s)
        groups=wolf_information_groups(b.public_law)
        # All selected attacks hit the public known hunter P1, which cannot
        # guard itself. A forced other attack can GJ, but has no public support.
        profile=tuple((info,((1,F(1)),)) for info,mass,group in groups)
        e=FixedPublicWolfProfile(b.public,b.public_law,(),r,s,profile)
        own=next(group for info,mass,group in groups if info.initial_roster==2)
        before=deepcopy(b)
        with self.assertRaises(Pending) as stopped:e.act(b.public,b.public_law,(),3,own,None)
        self.assertEqual(stopped.exception.reason,'public_generated_observation_zero_support')
        self.assertEqual(b,before);self.assertEqual(e.policy_dependencies.stack,[])
