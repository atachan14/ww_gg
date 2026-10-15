import unittest
from fractions import Fraction as F
from werewolf.policy_certificates import (certify_uniform_profiles,certify_support_profiles,
                                         uniform_options)

class SupportPartitionTests(unittest.TestCase):
    def test_full_classification_matches_exhaustive_including_nonwitness_best_response(self):
        legal=tuple((i,(1,2)) for i in range(3))
        contributions={i:tuple((p,(sum(1<<i for a,q in p if a==1),))
                              for p in uniform_options(actions)) for i,actions in legal}
        for mode in ('tie','fixed','match','cycle'):
            def evaluate(profile):
                occupied={i for i,p in profile if any(a==1 for a,q in p)}
                if mode=='tie':return {i:((1,F(1,2)),(2,F(1,2))) for i,a in legal}
                if mode=='fixed':return {i:((1,F()),(2,F(1))) for i,a in legal}
                return {i:((1,F(((i+1)%3) not in occupied if mode=='match' else ((i+1)%3) in occupied)),
                           (2,F(((i+1)%3) in occupied if mode=='match' else ((i+1)%3) not in occupied)))
                        for i,a in legal}
            expected=certify_uniform_profiles(legal,evaluate)
            actual=certify_support_profiles(legal,evaluate,contributions,(0,))
            self.assertEqual(actual.status,expected.status)
            self.assertEqual(actual.status,{'tie':'unique','fixed':'unique','match':'multiple','cycle':'no_admissible_profile'}[mode])
            self.assertEqual(actual.evaluated,27)
            self.assertEqual(set(actual.certified),set(expected.certified))
            self.assertEqual(actual.proof,'support_partition')

    def test_all_local_options_are_required_and_state_budget_never_selects(self):
        legal=(('a',(1,2)),('b',(1,2)))
        contributions={i:tuple((p,(sum((1 if i=='a' else 2) for a,q in p if a==1),))
                              for p in uniform_options(actions)) for i,actions in legal}
        def forbidden(profile):raise AssertionError('Incomplete partition cannot be evaluated')
        result=certify_support_profiles(legal,forbidden,contributions,(0,),max_profiles=1)
        self.assertEqual(result.status,'budget_unfinished');self.assertIsNone(result.selected)
        incomplete=dict(contributions);incomplete['a']=incomplete['a'][:-1]
        with self.assertRaises(ValueError):certify_support_profiles(legal,forbidden,incomplete,(0,))

    def test_real_387_million_profile_context_matches_all_common_candidate_values(self):
        import json
        from pathlib import Path
        from copy import deepcopy
        from werewolf.exact import Board,Rules,Strategy,PublicEvent
        from werewolf.seer_future_uniform import TrueScanState
        from werewolf.seer_acquisition import Hypothesis,Acquisition
        from werewolf.guard_effect import GuardIntent
        from werewolf.night_knowledge import WolfAttack
        from werewolf.wolf_profile_certificate import (WolfProfileResolver,FixedPublicWolfProfile,
                                                       wolf_candidate_profile)
        from werewolf.candidate_policy import CandidateRules
        from werewolf.actor_information import wolf_information_groups
        registry={c.__name__:c for c in (Board,Rules,Strategy,PublicEvent,TrueScanState,Hypothesis,
                                        Acquisition,GuardIntent,WolfAttack)}
        def decode(x):
            if isinstance(x,list):return tuple(decode(v) for v in x)
            if isinstance(x,dict):
                if 'fraction' in x:return F(*x['fraction'])
                return registry[x['type']](**{k:decode(v) for k,v in x['fields'].items()})
            return x
        b,state,past,rules,strategy=decode(json.loads((Path(__file__).parent/'fixtures'/'large_terminal_profile.json').read_text()))
        before=deepcopy((b,state,past));resolver=WolfProfileResolver(rules,strategy)
        result=resolver.resolve(b,state,past)
        self.assertEqual(result.status,'unique');self.assertEqual(result.proof,'support_partition')
        self.assertEqual((result.total,result.evaluated),(387420489,387420489))
        candidates=CandidateRules(b,state,past,rules,strategy)
        expected=tuple((info,tuple((target,FixedPublicWolfProfile(b,state,past,rules,strategy,
            wolf_candidate_profile(result.selected.profile,info,target,rules=candidates)).act(
                b,state,past,target,group,None))
            for target in b.alive if not info.initial_roster&(1<<(target-1))))
            for info,mass,group in wolf_information_groups(state))
        self.assertEqual(result.selected.scores,expected)
        self.assertIs(resolver.resolve(b,state,past),result)
        self.assertEqual((b,state,past),before)
