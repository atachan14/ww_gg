import unittest
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_joint_night_prototype_fixture import audit,negatives

class JointNightPrototypeTests(unittest.TestCase):
    def test_uniform_joint_generation_and_full_labelled_one_night_readback(self):
        r=audit()
        self.assertEqual(r['representative_flow_generations'],3)
        self.assertEqual(r['old_labelled_flow_generations'],24)
        self.assertEqual(r['existing_grouped_flow_calls'],18)
        self.assertEqual(r['labelled_joint_leaves'],720)
    def test_distinct_Q_P_class_weights_never_change_the_actor_policy(self):
        r=audit(1,(F(2,3),F(1,3)))
        self.assertTrue(r['Q_P_different'])
        self.assertNotEqual(r['Q_orbit_masses'],r['P_orbit_masses'])
        self.assertEqual(r['representative_flow_generations'],7)
        self.assertEqual(r['old_labelled_flow_generations'],27)
        self.assertTrue(r['physical_branch_mass_equal'])
    def test_unproved_skew_substitutions_max_and_illegal_targets_are_refused(self):
        self.assertEqual(len(negatives()),11)
