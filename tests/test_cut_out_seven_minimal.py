"""Seven-player tiny-support entry and exact private continuation regression."""
from dataclasses import replace
from fractions import Fraction as F
import unittest
from benchmarks.player_match_groups.cut_out_seven_minimal import spec,graph
from benchmarks.player_match_groups.cut_out_model_a import adapt_model_a,adapt_six_model_a,adapt_seven_model_a
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition
from benchmarks.player_match_groups.cut_out_seven_minimal_fixture import audit
from werewolf.exact import Rules,Strategy
from werewolf.seer_acquisition import Hypothesis


class SevenMinimalTests(unittest.TestCase):
    def test_closed_scope_and_independently_enumerated_initial_joint(self):
        source=spec(latent=True)
        self.assertIsInstance(adapt_model_a(source),UnsupportedPartition)
        self.assertIsInstance(adapt_six_model_a(source),UnsupportedPartition)
        for changed in (replace(source,claims=('latent',)*7),replace(source,mediums=1),
                        replace(source,rules=Rules(initial_seer='random_white')),replace(source,strategy=Strategy())):
            self.assertIsInstance(adapt_seven_model_a(changed),UnsupportedPartition)
        public=graph(latent=True).origin().public_state
        expected=tuple(sorted((Hypothesis((2,0,1<<(p-1),0),(),F(1,6)) for p in (1,3,4,5,6,7)),key=lambda h:h.roles))
        self.assertEqual(public.hypotheses,expected)
        self.assertEqual(graph().origin().public_state.hypotheses,(Hypothesis((2,0,1,0),(),F(1)),))

    def test_conditional_private_table_joint_mass_and_history_match_labelled_reference(self):
        result=audit('private-latent')
        self.assertTrue(result['complete_table_joint_history_branch_mass_equal'])
        self.assertTrue(result['independent_win_action_horizon_equal'])
        self.assertGreater(result['third_day_terminals'],0)
        self.assertGreater(result['slot3_terminal_witnesses'],0)
