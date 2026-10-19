import unittest
from dataclasses import asdict
from unittest.mock import patch
from app import create_app
from benchmarks.player_match_groups.closed_full_tree_fixture import case
from werewolf.closed_calculation import ClosedCalculation
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.grouped_forecast import GroupedForecast
from werewolf.exact import Strategy
from werewolf.local_reuse import reuse_scope,enabled,make_public_engine,make_root_engine,make_view_engine


class OptInBoundaryReviewTests(unittest.TestCase):
    def test_disabled_factories_and_default_web_never_construct_grouped_consumer(self):
        data=case(5,'dual').data.updated(policy=asdict(Strategy(day='random',night='random',fake_reports='random')))
        base=ClosedCalculation(data);s=base.root.read();rules=data.game_data.rules;strategy=Strategy()
        with patch.object(GroupedForecast,'__init__',side_effect=AssertionError('Grouped consumer reached from default')),reuse_scope(False):
            self.assertFalse(enabled())
            engines=(make_public_engine(InformationSetForecast,s.public,s.public_state,s.past,rules,strategy),
                     make_root_engine(InformationSetForecast,s.public,rules,strategy),
                     make_view_engine(InformationSetForecast,s.public,rules,strategy))
            self.assertTrue(all(type(e)is InformationSetForecast for e in engines))
            app=create_app({'TESTING':True,'SECRET_KEY':'boundary-test-only'})
            self.assertFalse(app.config['EXACT_FUTURE_REUSE_PREVIEW'])
            client=app.test_client();self.assertEqual(client.get('/').status_code,200)
            self.assertEqual(client.post('/start',data={'players':'5','day':'max','night':'max'}).status_code,303)
            self.assertEqual(client.get('/').status_code,200)

    def test_closed_uniform_default_and_MAX_flags_keep_distinct_admission(self):
        data=case(5,'dual').data
        random=asdict(Strategy(day='random',night='random',fake_reports='random'))
        c=ClosedCalculation(data.updated(policy=random))
        self.assertIs(type(c._ClosedCalculation__engine),InformationSetForecast)
        data=data.updated(policy=asdict(Strategy()))
        with self.assertRaises(Pending):ClosedCalculation(data)
        with self.assertRaises(Pending):ClosedCalculation(data,grouped=True)
        report=ClosedCalculation(data,grouped=True,aggregate_reports=True)
        full=ClosedCalculation(data,grouped=True,aggregate_reports=True,aggregate_wolf=True)
        self.assertFalse(report._ClosedCalculation__engine.max_grouped)
        self.assertTrue(full._ClosedCalculation__engine.max_grouped)

if __name__=='__main__':unittest.main()
