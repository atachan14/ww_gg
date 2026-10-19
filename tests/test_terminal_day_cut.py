import unittest
from fractions import Fraction as F
from unittest.mock import patch
from dataclasses import replace
from benchmarks.player_match_groups.closed_full_tree_fixture import case
from werewolf.closed_calculation import ClosedCalculation
from werewolf.actor_information import PersonalInformation,WolfInformation
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.grouped_forecast import GroupedForecast
from werewolf.exact import initial_board,Strategy,Rules


class TerminalDayCutTests(unittest.TestCase):
    def test_uniform_terminal_scalar_public_and_owners_keeps_named_actions(self):
        c=ClosedCalculation(case(3,'single').data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
        h=c.root.read().private.hypotheses[0]
        nodes=(c.root,c.root.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],c.root.personal(WolfInformation.from_hypothesis(h))[1])
        e=c._ClosedCalculation__engine
        for node in nodes:
            s=node.read()
            with patch.object(e,'act',side_effect=AssertionError('terminal scalar expands an action')):
                self.assertEqual(e.solve(*s,physical=s.physical),F(1,3))
            # Independent enumeration uses actual named physical transitions.
            exact={target:sum((r.probability*F(r.node.read().public.winner=='village') for r in node.action(target)),F()) for target in s.public.alive}
            self.assertEqual(sum(exact.values(),F())/3,F(1,3))
            self.assertEqual(set(exact.values()),{F(0),F(1)})
            f=node.forecast();self.assertEqual(f.village_win,F(1,3));self.assertEqual(dict(f.action_values),exact)

    def test_narrow_condition_and_common_fallback(self):
        e=GroupedForecast(Rules(),Strategy(day='random',night='random',fake_reports='random'))
        b=initial_board(3,1,seer_count=1)
        with patch.object(InformationSetForecast,'exchangeable',return_value=False) as fallback:
            self.assertTrue(e.exchangeable(b));self.assertEqual(fallback.call_count,0)
            for other in (replace(b,phase='night'),initial_board(5,1,seer_count=1),initial_board(3,1,hunter_count=1),initial_board(3,2,experimental_cast=True)):
                self.assertFalse(e.exchangeable(other))
            self.assertEqual(fallback.call_count,4)

    def test_max_policy_still_rejected_by_grouped_constructor(self):
        with self.assertRaises(ValueError):GroupedForecast(Rules(),replace(Strategy(),day='max'))
