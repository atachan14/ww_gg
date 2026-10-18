import unittest
from benchmarks.player_match_groups.measure_shared_transition import worker


class SharedTransitionMeasurementTests(unittest.TestCase):
    def test_identical_named_tasks_and_separate_diagnostics(self):
        for case in ('five-owner-night','seven-owner-three'):
            ordinary=worker(case,False,True);inherited=worker(case,True,True)
            self.assertEqual(ordinary['semantic_digest'],inherited['semantic_digest'])
            self.assertEqual(ordinary['states'],inherited['states'])
            self.assertEqual(ordinary['cold_reads'],inherited['cold_reads'])
            self.assertGreater(ordinary['cold_reads'],0)
            self.assertGreater(ordinary['instrumented_calls'].get('roles',0),inherited['instrumented_calls'].get('roles',0))
            self.assertGreater(inherited['proof_counts']['group_consumptions'],0)
            self.assertTrue(inherited['profile'])
            self.assertTrue(inherited['ledger_retained_entries'])
