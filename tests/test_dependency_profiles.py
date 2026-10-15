import unittest
from fractions import Fraction as F
from werewolf.policy_certificates import certify_uniform_profiles,certify_dependency_profiles
from werewolf.information_set_forecast import Pending

class DependencyProfileTests(unittest.TestCase):
    def test_total_classification_matches_exhaustive(self):
        legal=tuple((i,(1,2)) for i in range(3))
        for mode in ('tie','fixed','match','cycle'):
            dependencies={i:set() if mode in ('tie','fixed') else {(i+1)%3} for i,a in legal}
            def scores(profile):
                occupied={i for i,p in profile if any(a==1 for a,q in p)}
                if mode=='tie':return {i:((1,F(1,2)),(2,F(1,2))) for i,a in legal}
                if mode=='fixed':return {i:((1,F()),(2,F(1))) for i,a in legal}
                return {i:((1,F(((i+1)%3) not in occupied if mode=='match' else ((i+1)%3) in occupied)),
                           (2,F(((i+1)%3) in occupied if mode=='match' else ((i+1)%3) not in occupied)))
                        for i,a in legal}
            expected=certify_uniform_profiles(legal,scores)
            actual=certify_dependency_profiles(legal,lambda p,requested:{i:r for i,r in scores(p).items() if i in requested},dependencies)
            self.assertEqual(actual.status,expected.status)
            self.assertEqual(set(actual.certified),set(expected.certified))
            self.assertEqual(actual.evaluated,27)

    def test_downstream_constraints_can_remove_an_upstream_solution(self):
        legal=tuple((i,(1,2)) for i in range(4));dependencies={0:{1},1:{0},2:{3},3:{0,2}}
        def scores(profile):
            occupied={i for i,p in profile if any(a==1 for a,q in p)}
            desired={0:1 in occupied,1:0 in occupied,2:3 in occupied,
                     3:True if 0 in occupied else 2 not in occupied}
            return {i:((1,F(not desired[i])),(2,F(desired[i]))) for i,a in legal}
        expected=certify_uniform_profiles(legal,scores)
        actual=certify_dependency_profiles(legal,lambda p,requested:{i:r for i,r in scores(p).items() if i in requested},dependencies)
        self.assertEqual(actual.status,'unique');self.assertEqual(actual.certified,expected.certified)
        self.assertEqual(actual.evaluated,81)

    def test_unproved_feedback_and_required_undefined_rows_never_select(self):
        legal=(('a',(1,2)),('b',(1,2)));deps={'a':{'b'},'b':{'a'}}
        def forbidden(profile,requested):raise AssertionError('Feedback limit must stop before values')
        result=certify_dependency_profiles(legal,forbidden,deps,max_profiles=1)
        self.assertEqual(result.status,'budget_unfinished');self.assertIsNone(result.selected)
        def undefined(profile,requested):raise Pending('public_generated_observation_zero_support')
        result=certify_dependency_profiles(legal,undefined,deps)
        self.assertEqual(result.status,'undefined_observations');self.assertIsNone(result.selected)

    def test_game_roster_quotient_is_bounded_and_never_applied_to_public_max(self):
        from unittest.mock import patch
        from dataclasses import replace
        from tests import test_root_guard_max as fixtures
        from werewolf.seer_manual import replay
        from werewolf.exact import Strategy
        from werewolf.root_secret_flow import prepare_root_entry
        from werewolf.wolf_profile_certificate import WolfProfileResolver
        from werewolf.policy_certificates import ProfileSearch
        for players,day,expect_cross in ((6,'random',True),(5,'random',False),(5,'max',True)):
            g=fixtures.RootGuardMaxTests().game(players=players);rules,p=replay(g)
            strategy=Strategy(**g['policy']);root=prepare_root_entry(g,p.board,rules,strategy)
            seen=[]
            def capture(legal,evaluate,dependencies,**kwargs):
                seen.append(dependencies);return ProfileSearch('budget_unfinished',1,0)
            with patch('werewolf.policy_certificates.certify_dependency_profiles',side_effect=capture):
                WolfProfileResolver(rules,replace(strategy,day=day)).resolve(root.public,root.public_law)
            self.assertTrue(seen)
            cross=any(other.initial_roster!=info.initial_roster for info,rows in seen[0].items() for other in rows)
            self.assertEqual(cross,expect_cross,(players,day))
