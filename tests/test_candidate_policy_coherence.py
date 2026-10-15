import unittest
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from tests import test_root_guard_max as fixtures
from werewolf.exact import Strategy
from werewolf.seer_manual import replay
from werewolf.root_secret_flow import prepare_root_entry
from werewolf.actor_information import wolf_information_groups
from werewolf.wolf_profile_certificate import FixedPublicWolfProfile,wolf_candidate_profile,certify_wolf_profiles
from werewolf.policy_choice import uniform_policy
from werewolf.candidate_policy import CandidateRules

class CandidatePolicyCoherenceTests(unittest.TestCase):
    def test_candidate_bite_and_public_kernel_are_same_policy_not_public_fact(self):
        for repeat in (True,False):
            g=fixtures.RootGuardMaxTests().game(repeat)
            g['claim_policy']=g['history'][0]['claim_policy']={'hunter':'filled'}
            r,p=replay(g);old=Strategy(**g['policy']);root=prepare_root_entry(g,p.board,r,old)
            s=replace(old,day='max');before=deepcopy(root)
            groups=wolf_information_groups(root.public_law)
            candidates=CandidateRules(root.public,root.public_law,(),r,s)
            base=tuple((info,uniform_policy((1,))) for info,mass,group in groups)
            info,mass,group=next(row for row in groups if row[0].initial_roster==2)
            # H1 cannot guard H1. Under the chosen attack-H1 policy no GJ
            # exists. Candidate attack3 MUST be used in public support too.
            candidate=wolf_candidate_profile(base,info,3,rules=candidates)
            engine=FixedPublicWolfProfile(root.public,root.public_law,(),r,s,candidate)
            self.assertEqual(engine.act(root.public,root.public_law,(),3,group,None),F(1,4))
            attack_hunter=wolf_candidate_profile(base,info,1,rules=candidates)
            e=FixedPublicWolfProfile(root.public,root.public_law,(),r,s,attack_hunter)
            self.assertEqual(e.act(root.public,root.public_law,(),1,group,None),F())
            self.assertEqual(dict(candidate)[info],((3,F(1)),))
            self.assertEqual({i.initial_roster: policy for i,policy in candidate}, {2:((3,F(1)),),4:((2,F(1)),)})
            self.assertEqual(root,before)

    def test_profile_search_does_not_reject_legal_candidates_as_off_path(self):
        g=fixtures.RootGuardMaxTests().game()
        g['claim_policy']=g['history'][0]['claim_policy']={'hunter':'filled'}
        r,p=replay(g);old=Strategy(**g['policy']);root=prepare_root_entry(g,p.board,r,old)
        result=certify_wolf_profiles(root.public,root.public_law,(),r,replace(old,day='max'))
        self.assertEqual(result.status,'unique');self.assertEqual(result.evaluated,9)
        self.assertEqual(result.issues,())
        self.assertTrue(all(policy==((1,F(1)),) for info,policy in result.selected.profile))
        self.assertTrue(all(dict(row)[1]==0 and max(v for a,v in row)==F(1,4)
                            for info,row in result.selected.scores))

    def test_same_owned_information_ignores_hidden_hunter_and_no_history_is_published(self):
        g=fixtures.RootGuardMaxTests().game();r,p=replay(g);strategy=Strategy(**g['policy'])
        root=prepare_root_entry(g,p.board,r,strategy);before=deepcopy(root)
        groups=wolf_information_groups(root.public_law)
        candidates=CandidateRules(root.public,root.public_law,(),r,strategy)
        base=tuple((i,uniform_policy(tuple(t for t in root.public.alive if not i.initial_roster&(1<<(t-1)))))
                   for i,m,law in groups)
        info,mass,group=next(row for row in groups if row[0].initial_roster==1)
        self.assertGreater(len({h.roles[3] for h in group.hypotheses}),1)
        from werewolf.actor_information import WolfInformation
        for h in group.hypotheses:
            self.assertEqual(wolf_candidate_profile(base,WolfInformation.from_hypothesis(h),2,rules=candidates),
                             wolf_candidate_profile(base,info,2,rules=candidates))
        candidate=wolf_candidate_profile(base,info,2,rules=candidates)
        e=FixedPublicWolfProfile(root.public,root.public_law,(),r,strategy,candidate)
        kernel=e.public_night_policies(root.public,root.public_law)
        self.assertEqual(len(kernel),len(groups));self.assertEqual(kernel[1,()],((2,F(1,2)),(3,F(1,2))))
        self.assertEqual(root,before)

    def test_exact_renaming_maps_candidate_policy_and_all_information_keys_together(self):
        from werewolf.exact_renaming import canonical_key
        g=fixtures.RootGuardMaxTests().game();r,p=replay(g);strategy=Strategy(**g['policy'])
        root=prepare_root_entry(g,p.board,r,strategy);groups=wolf_information_groups(root.public_law)
        candidates=CandidateRules(root.public,root.public_law,(),r,strategy)
        base=tuple((i,uniform_policy(tuple(t for t in root.public.alive if not i.initial_roster&(1<<(t-1)))))
                   for i,m,law in groups)
        info,mass,group=next(row for row in groups if row[0].initial_roster==1)
        first=wolf_candidate_profile(base,info,2,rules=candidates);second=wolf_candidate_profile(base,info,3,rules=candidates)
        def key(profile,target):
            return canonical_key(root.public,root.public_law,(),group,None,r,strategy,target=target,
                wolf_profiles=((root.public,root.public_law,(),profile),),actor_mask=1)
        self.assertIsNotNone(key(first,2));self.assertEqual(key(first,2),key(second,3))
        other=next(i for i,m,law in groups if i.initial_roster==2)
        changed=wolf_candidate_profile(first,other,1,rules=candidates)
        self.assertNotEqual(key(first,2),key(changed,2))
