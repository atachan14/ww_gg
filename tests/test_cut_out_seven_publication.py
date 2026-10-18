import unittest
from benchmarks.player_match_groups.cut_out_seven_publication_fixture import audit

class SevenPublicationTests(unittest.TestCase):
    def test_derived_count_changes_from_deceased_result_with_fixed_event_groups(self):
        result=audit()
        self.assertEqual([c['wolf_count'] for c in result['cases']],[1,2])
        self.assertEqual(result['morning_vectors'],18)
        self.assertEqual(len(result['rejected']),6)
        self.assertEqual(result['recursive_forecasts'],0)
