import unittest
from benchmarks.player_match_groups.cut_out_user_seven_preparation_fixture import audit

class UserSevenPreparationTests(unittest.TestCase):
    def test_real_cast_prior_batch_and_synthetic_prefix_without_full_search(self):
        r=audit()
        self.assertEqual(r['initial_worlds'],6)
        self.assertEqual(r['synthetic_prefix']['P_dead_wolf7'],'4/9')
        self.assertFalse(r['initial_max_supported'])
        self.assertEqual(r['solve_calls'],0)
