import unittest
from unittest.mock import patch
from fractions import Fraction as F
from werewolf.exact import initial_board,condition_claims,ClaimPolicy,Rules,Strategy,replace_worlds
from werewolf.public_prior import prepare_public_prior
from werewolf.model_a_public import public_forecast
from werewolf.information_set_forecast import InformationSetForecast,Pending


def fixture(n,w,m,claims):
    b=condition_claims(initial_board(n,w,m,1),claims,ClaimPolicy(medium='none',seer='none'))
    rules=Rules(initial_seer='none')
    game={'players':n,'rules':{'initial_seer':'none'},'seer_options':{'initial_rule':'none'},'seer_inputs':[],'public_log':{'version':2}}
    s,past=prepare_public_prior(game,b,rules)
    return b,s,past,rules


class MixedFlowMemoTests(unittest.TestCase):
    def test_fixed_seven_player_case_completes_all_rows_under_default_budget(self):
        b,s,past,rules=fixture(7,2,2,('seer','medium','medium')+('latent',)*4)
        result=public_forecast(b,s,past,rules,Strategy())
        self.assertEqual(len(result.action_values),7)
        self.assertEqual(len(result.by_dawn_values),7)
        self.assertEqual(len({dict(result.action_values)[p] for p in (4,5,6,7)}),1)
        self.assertTrue(all(v.village_win==v.wolf_win==0 for _,v in result.by_dawn_values))

    def general(self,b,s,past,rules,strategy):
        def engine(*args,**kwargs):
            e=InformationSetForecast(*args,**kwargs,memoize_flows=False,retire_uninformative_scans=False)
            e.equivalent_targets=lambda *args:False
            return e
        with patch('werewolf.model_a_public.InformationSetForecast',side_effect=engine), \
             patch('werewolf.model_a_public.project_evaluation',side_effect=lambda b,s,p:(b,s)):
            return public_forecast(b,s,past,rules,strategy)

    def test_small_mixed_full_disclosure_matches_general_information_set_model(self):
        for n,w,m,claims in ((5,1,1,('seer','medium')+('latent',)*3),
                             (6,2,2,('seer','medium','medium')+('latent',)*3)):
            b,s,past,rules=fixture(n,w,m,claims)
            if n==6:
                # A small asymmetric homotype: retain both true/fake seer
                # worlds and repeated latent placements, without a large
                # exhaustive oracle hiding behind a raised production budget.
                worlds=tuple(world for mask in (3,5,6)
                             for world in tuple(world for world in b.worlds if world[0]==mask)[:2])
                mass=sum(world[-1] for world in worlds)
                b=replace_worlds(b,tuple((*world[:-1],world[-1]/mass) for world in worlds),wolf_count=None)
                from dataclasses import replace
                from werewolf.seer_acquisition import from_board
                s=replace(s,hypotheses=from_board(b))
            for fake in ('random','max'):
                strategy=Strategy(fake_reports=fake)
                before=(b,s,past)
                fast=public_forecast(b,s,past,rules,strategy)
                general=self.general(b,s,past,rules,strategy)
                self.assertEqual(fast,general)
                self.assertEqual(len(fast.action_values),n)
                self.assertEqual((b,s,past),before)

    def test_publicly_known_single_fake_noise_does_not_change_values(self):
        b,s,past,rules=fixture(5,2,1,('seer','medium')+('latent',)*3)
        worlds=tuple(w for w in b.worlds if not w[2]&1)
        mass=sum(w[-1] for w in worlds)
        b=replace_worlds(b,tuple((*w[:-1],w[-1]/mass) for w in worlds),wolf_count=None)
        from werewolf.seer_acquisition import from_board
        from dataclasses import replace
        s=replace(s,hypotheses=from_board(b))
        for fake in ('random','max'):
            strategy=Strategy(fake_reports=fake)
            self.assertEqual(public_forecast(b,s,past,rules,strategy),self.general(b,s,past,rules,strategy))

    def test_public_flow_caches_never_install_failed_branches(self):
        b,s,past,rules=fixture(5,1,1,('seer','medium')+('latent',)*3)
        e=InformationSetForecast(rules,Strategy())
        with patch.object(e,'generate_publications',side_effect=Pending('test-incomplete')):
            for _ in range(2):
                with self.assertRaises(Pending):e.publications(b,s,past)
        self.assertEqual(e.publication_values,{})
        self.assertEqual(e.mornings,{})

    def test_published_scan_history_and_target_asymmetry_match_general_model(self):
        b,s,past,_=fixture(5,1,1,('seer','medium')+('latent',)*3)
        worlds=tuple(w for w in b.worlds if not (w[2]&1 and w[0]&8))
        mass=sum(w[-1] for w in worlds)
        b=replace_worlds(b,tuple((*w[:-1],w[-1]/mass) for w in worlds),wolf_count=None)
        rules=Rules(initial_seer='normal')
        game={'players':5,'rules':{'initial_seer':'normal'},'seer_options':{'initial_rule':'normal'},
              'seer_inputs':[{'day':1,'reporter':1,'target':4,'color':'white'}],'public_log':{'version':2}}
        s,past=prepare_public_prior(game,b,rules)
        from werewolf.evaluation_projection import project_evaluation
        projected,joint=project_evaluation(b,s,Strategy())
        self.assertEqual({a for h in joint.hypotheses for a in h.acquisitions},
                         {a for h in s.hypotheses for a in h.acquisitions})
        self.assertFalse(InformationSetForecast(rules,Strategy()).equivalent_targets(projected,joint,4,5,past))
        for policy in (('uniform',),('noncontradictory','uniform')):
            strategy=Strategy(fake_seer_policy=policy)
            self.assertEqual(public_forecast(b,s,past,rules,strategy),self.general(b,s,past,rules,strategy))

    def test_multiple_fake_joint_law_is_not_replaced_with_single_fake_retirement(self):
        b,s,past,rules=fixture(5,2,1,('seer','seer')+('latent',)*3)
        self.assertTrue(InformationSetForecast(rules,Strategy()).informative_seer(b))

    def test_known_fake_with_unspecified_initial_declaration_is_not_retired(self):
        b,s,past,rules=fixture(5,2,1,('seer','medium')+('latent',)*3)
        worlds=tuple(w for w in b.worlds if not w[2]&1)
        mass=sum(w[-1] for w in worlds)
        b=replace_worlds(b,tuple((*w[:-1],w[-1]/mass) for w in worlds),wolf_count=None)
        from dataclasses import replace
        from werewolf.seer_acquisition import from_board
        s=replace(s,hypotheses=from_board(b),initial_rule='normal')
        e=InformationSetForecast(rules,Strategy())
        self.assertFalse(e.informative_seer(b))
        self.assertFalse(e.can_retire_scans(b,s,past))
        self.assertFalse(e.exchangeable(b))
