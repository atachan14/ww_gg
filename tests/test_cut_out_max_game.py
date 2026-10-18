"""Max policy sharing must survive private conditioning and cut-out evaluation."""
import unittest
from dataclasses import replace
from benchmarks.player_match_groups.cut_out_max_game import graph
from benchmarks.player_match_groups.cut_out_max_fixture import audit
from benchmarks.player_match_groups.cut_out_model_a import adapt_model_a,adapt_max_model_a
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition
from werewolf.exact import Strategy

class MaxCutOutTests(unittest.TestCase):
    def test_scope_is_sealed_and_uniform_entry_stays_uniform(self):
        from fractions import Fraction as F
        from werewolf.seer_acquisition import Hypothesis,Acquisition
        from benchmarks.player_match_groups.cut_out_uniform_game import evaluate as uniform
        source=graph(5,1)
        expected=tuple(sorted((Hypothesis((1<<(w-1),1<<(m-1),1,0),(Acquisition(1,1,3,'white'),),F(1,9))
            for w in (2,4,5) for m in (2,3,4,5) if m!=w),key=lambda h:h.roles))
        self.assertEqual(source.origin().public_state.hypotheses,expected)
        self.assertIsInstance(uniform(source),UnsupportedPartition)
        spec=graph().engine.baseline.spec
        self.assertIsInstance(adapt_model_a(spec),UnsupportedPartition)
        for changed in (replace(spec,players=7),replace(spec,seers=2),replace(spec,reports=()),
                        replace(spec,strategy=Strategy(day='random',night='random',fake_reports='random'))):
            self.assertIsInstance(adapt_max_model_a(changed),UnsupportedPartition)

    def test_private_medium_does_not_select_private_best_or_reveal_role_to_wolf(self):
        result=audit(5,1,'max',True)
        self.assertEqual(result['public_policy'],[2,4,5])
        self.assertEqual(result['village_win'],'2/3')
        self.assertEqual(result['private_best'],'3/4')
        self.assertGreater(result['unknown_medium_wolf_information_sets'],0)
