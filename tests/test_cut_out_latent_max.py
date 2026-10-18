"""Initial latent bridge preserves own information and existing public max."""
import unittest
from dataclasses import replace
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_latent_max import graph,scan_values
from benchmarks.player_match_groups.cut_out_latent_max_fixture import audit
from benchmarks.player_match_groups.cut_out_model_a import adapt_latent_max_model_a,adapt_max_model_a
from benchmarks.player_match_groups.cut_out_uniform_game import OwnView
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition
from werewolf.actor_information import condition_actor_state
from werewolf.exact import Strategy
from werewolf.seer_acquisition import Acquisition

class LatentMaxTests(unittest.TestCase):
    def test_closed_scope_preserves_twelve_roles_thirtysix_secrets_and_root_gate(self):
        from werewolf.root_secret_flow import prepare_root_secrets,root_scope
        source=graph();spec=source.engine.baseline.spec;root=source.origin()
        self.assertIsInstance(adapt_max_model_a(spec),UnsupportedPartition)
        for changed in (replace(spec,players=7),replace(spec,seers=2),replace(spec,strategy=Strategy(day='max',night='max',fake_reports='random'))):
            self.assertIsInstance(adapt_latent_max_model_a(changed),UnsupportedPartition)
        actual=prepare_root_secrets(root.public,spec.rules)
        self.assertEqual(root_scope(actual,spec.rules,spec.strategy),'root_secret_max_unimplemented')
        own=condition_actor_state(root.public_state,OwnView(1,'seer').accepts)
        self.assertEqual(len(own.public_roles),12);self.assertEqual(len(own.hypotheses),36)
        for target in (2,3,4,5):
            self.assertEqual(sum((h.mass for h in own.hypotheses if h.acquisitions[0].target==target),F()),F(1,4))
        white=condition_actor_state(own,OwnView(1,'seer',(Acquisition(1,1,3,'white'),)).accepts)
        self.assertEqual(sum((h.mass for h in white.hypotheses if h.roles[1]&4),F()),F(1,3))
        self.assertEqual(sum((h.mass for h in white.hypotheses if not (h.roles[0]|h.roles[1]|h.roles[2])&4),F()),F(2,3))

    def test_missing_own_history_is_explicit_and_other_owner_secret_rejected(self):
        self.assertEqual(tuple(v for p,v in scan_values(graph(4,0,'none'),OwnView(1,'seer'))[0]),(F(1,4),)*3)
        source=graph()
        self.assertEqual(scan_values(source,OwnView(1,'seer')).reason,'seer_view_past_private_history_unresolved')
        self.assertIsInstance(scan_values(source,OwnView(1,'seer',(Acquisition(1,2,3,'white'),))),UnsupportedPartition)

    def test_nontrivial_public_max_and_private_scan_share_policy(self):
        result=audit(5,1,'random_white','white',True)
        self.assertEqual(result['public_policy'],[2,3,4,5]);self.assertEqual(result['village_win'],'7/12')
        self.assertEqual(result['own_scan_targets'],[1,4,5])
        self.assertTrue(result['independently_generated_initial_and_terminal_joint_equal'])
