import unittest
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_joint_reports import audit_distribution,make_case
from benchmarks.player_match_groups.cut_out_joint_reports_fixture import negatives
from benchmarks.player_match_groups.cut_out_live_medium_forecast import certificate,Pending
from werewolf.calculation_budget import calculation_budget


class JointReportsTests(unittest.TestCase):
    def test_structural_patterns_all_labels_and_complete_private_laws(self):
        with calculation_budget(1000000,max_seconds=30):row=audit_distribution()
        self.assertEqual((row['representatives'],row['literal_public_vectors']),(13,64))
        self.assertEqual(sum(row['multiplicities']),64)
        self.assertEqual(row['variants']['private_scan5white']['zero_P'],56)
        self.assertEqual(row['variants']['roster17']['zero_P'],24)

    def test_different_targets_same_black_color_keep_joint_correlation(self):
        receipt=make_case(((5,'black'),(6,'black')))
        self.assertEqual(receipt.q,F(1,120))
        self.assertEqual({h.roles[0] for h in receipt.public_source.public_state.hypotheses},{18,33})
        self.assertTrue(all(h.mass==F(1,2) for h in receipt.public_source.public_state.hypotheses))
        self.assertNotEqual(receipt.public_source.public_state.hypotheses[0].acquisitions,
            receipt.public_source.public_state.hypotheses[1].acquisitions)

    def test_own_scan_changes_only_P_and_zero_keeps_public_receipt(self):
        receipt=make_case(((6,'black'),(5,'white')),private='private_scan5white')
        self.assertEqual((receipt.q,receipt.p),(F(1,80),F(1,8)))
        self.assertNotEqual(receipt.public_source.private,receipt.physical_source.private)
        zero=make_case(((5,'white'),(6,'black')),private='private_scan5white')
        self.assertGreater(zero.q,0)
        self.assertEqual(zero.p,0)
        self.assertIsNotNone(certificate(zero,public=True))
        with self.assertRaises(Pending):certificate(zero)

    def test_refusal_receipts_laws_and_hidden_history_symmetry(self):
        row=negatives()
        self.assertEqual(len(row['rejected']),8)