import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.exact import initial_board,condition_claims,ClaimPolicy,Rules,Strategy
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.evaluation_projection import project_evaluation
from werewolf.model_a_public import public_forecast,horizon_for_action


class EvaluationProjectionTests(unittest.TestCase):
    def test_projection_and_medium_memo_match_general_model_a_values(self):
        for cast,claims in (((5,1,1,1,1),('medium','hunter')+('latent',)*3),
                            ((5,2,2,0,0),('medium','medium')+('latent',)*3),
                            ((5,1,4,0,0),('medium',)*5),
                            ((5,2,3,0,0),('medium',)*5)):
            b=condition_claims(initial_board(*cast),claims,ClaimPolicy(medium='none',seer='none',hunter='filled'))
            s=TrueScanState(from_board(b),(b.alive,),initial_rule='none',tracked=())
            for fake in ('random','max'):
                policy=Strategy('max','max',fake_reports=fake);rules=Rules(initial_seer='none')
                before=(b,s);projected,ps=project_evaluation(b,s,policy)
                self.assertEqual(sum(q for *_,q in projected.worlds),1)
                self.assertEqual(projected.belief,b.belief)
                fast=public_forecast(b,s,(),rules,policy)
                with patch('werewolf.medium_value_key.public_descriptor',return_value=None):
                    general=InformationSetForecast(rules,policy)
                    general.equivalent_targets=lambda *args:False
                    self.assertEqual(fast.village_win,general.scalar(b,s,()))
                    for t in b.alive:
                        self.assertEqual(dict(fast.action_values)[t],general.act(b,s,(),t,s,None))
                        self.assertEqual(dict(fast.by_dawn_values)[t],horizon_for_action(general,b,s,(),t))
                self.assertEqual((b,s),before)

    def test_live_seer_truth_is_retained_when_latent_medium_locations_are_projected(self):
        b=replace(initial_board(5,1,1,1),claims=('seer','latent','latent','latent','latent'))
        s=TrueScanState(from_board(b),(b.alive,),initial_rule='none',tracked=())
        projected,joint=project_evaluation(b,s,Strategy())
        self.assertEqual(projected.belief,b.belief)
        self.assertEqual(projected.role_probability(1,'seer'),b.role_probability(1,'seer'))
        self.assertEqual(joint.public_roles,tuple(sorted(projected.worlds)))
        self.assertEqual((joint.rosters,joint.initial_rule),(s.rosters,s.initial_rule))
        self.assertEqual(joint.tracked,s.tracked)
