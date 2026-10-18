import unittest,copy
from dataclasses import replace
from unittest.mock import patch
from benchmarks.player_match_groups.late_seven import fixture
from benchmarks.player_match_groups.general_reuse import GeneralReuseForecast
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.local_reuse import reuse_scope,make_view_engine,late_seven_admitted
from werewolf.calculation_budget import calculation_budget
from werewolf.seer_view_forecast import seer_forecast
from werewolf.model_a_public import public_forecast

class LateSevenTests(unittest.TestCase):
    def test_admission_is_public_and_keeps_unmeasured_cases_original(self):
        b,s,rules,strategy=fixture()
        self.assertTrue(late_seven_admitted(b,rules,strategy))
        from werewolf.exact import initial_board,action_outcomes
        later=next(o.board for o in action_outcomes(b,5,rules,strategy)if o.board.winner is None)
        cases=[fixture(True)[0],later,initial_board(7,1,0,1),initial_board(7,1,0,0,1)]
        with reuse_scope(True):
            self.assertIs(type(make_view_engine(InformationSetForecast,b,rules,strategy)),GeneralReuseForecast)
            for other in cases:
                self.assertIs(type(make_view_engine(InformationSetForecast,other,rules,strategy)),InformationSetForecast)
            self.assertIs(type(make_view_engine(InformationSetForecast,b,rules,replace(strategy,day='max'))),InformationSetForecast)
        with reuse_scope(False):self.assertIs(type(make_view_engine(InformationSetForecast,b,rules,strategy)),InformationSetForecast)

    def test_complete_action_table_and_branch_laws_match_corrected_original(self):
        for asymmetric in(False,True):
            b,s,rules,strategy=fixture(asymmetric);before=copy.deepcopy((b,s));results=[]
            for mode in(False,True):
                with reuse_scope(mode):e=make_view_engine(InformationSetForecast,b,rules,strategy)
                with calculation_budget(1000000,max_seconds=8):
                    results.append((e.scalar(b,s,()),tuple((t,e.act(b,s,(),t,s,None))for t in b.alive),tuple((t,e.public_children(b,t))for t in b.alive)))
            forecasts=[]
            for mode in(False,True):
                with reuse_scope(mode):forecasts.append(public_forecast(b,s,(),rules,strategy,max_seconds=8))
            self.assertEqual(*forecasts)
            self.assertEqual(*results);self.assertEqual((b,s),before)
            self.assertTrue(all(sum(o.probability for o in outcomes)==1 for t,outcomes in results[0][2]))

    def test_owner_secret_and_dead_scan_targets_remain_in_common_flow(self):
        b,s,rules,strategy=fixture();s=InformationSetForecast(rules,strategy).acquire(b,s)
        own=next(tuple(h.acquisitions)for h in s.hypotheses if any(a.target==6 and a.color=='white'for a in h.acquisitions))
        before=copy.deepcopy((b,s));values=[]
        for mode in(False,True):
            with reuse_scope(mode):values.append(seer_forecast(b,1,own,rules,strategy,scan_state=s,max_seconds=8))
        self.assertIsInstance(values[0],tuple);self.assertEqual(*values)
        self.assertIn(7,dict(values[0]));self.assertNotIn(6,dict(values[0]))
        self.assertEqual((b,s),before)