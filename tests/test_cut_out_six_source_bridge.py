import unittest
from benchmarks.player_match_groups.cut_out_six_source_bridge_fixture import audit_source,audit_edits,audit_rejections

class SixSourceBridgeTests(unittest.TestCase):
    def test_replayed_public_and_physical_sources_stay_separate_and_bound(self):
        r=audit_source()
        self.assertTrue(r['public_physical_separate'])
        self.assertEqual(r['canonical_calls'],0)

    def test_old_witness_and_actor_do_not_cross_edit_cancel_redo(self):
        self.assertTrue(audit_edits()['old_witness_reuse_refused'])

    def test_unissued_unknown_CO_and_invalid_revision_are_refused(self):
        self.assertGreaterEqual(len(audit_rejections()['rejected']),10)
