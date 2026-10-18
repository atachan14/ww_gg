import unittest
from dataclasses import replace
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_live_medium_forecast import (
    make_case,check,certificate,cold,Pending)
from werewolf.calculation_budget import calculation_budget


class LiveMediumForecastTests(unittest.TestCase):
    def test_zero_physical_public_candidate_remains_reconstructible(self):
        with calculation_budget(1000000,max_seconds=30):
            receipt=make_case(5,'white',restricted=True)
            self.assertEqual(receipt.q,F(1,15))
            self.assertEqual(receipt.p,0)
            self.assertIsNone(receipt.physical_request)
            cap=certificate(receipt,public=True)
            self.assertEqual(cold(cap,cap.request),cap.source)
            with self.assertRaises(Pending) as caught:certificate(receipt)
            self.assertIn('no_conditional_P_law',caught.exception.reason)

    def test_supported_P_is_not_replaced_with_public_Q(self):
        with calculation_budget(1000000,max_seconds=30):
            receipt=make_case(1,'black',restricted=True)
            self.assertNotEqual(receipt.physical_source.private,receipt.public_source.private)
            self.assertEqual({h.roles[0] for h in receipt.physical_source.private.hypotheses},{17})
            cap=certificate(receipt)
            self.assertEqual(cold(cap,cap.request),cap.source)

    def test_copied_stale_receipt_and_unproved_report_are_refused(self):
        receipt=make_case(5,'white',restricted=True)
        with self.assertRaises(Pending):check(replace(receipt))
        with self.assertRaises(Pending):make_case(2,'black')
        r=receipt.registry;data=r.data
        r.data=data.updated(revision=data.to_game().get('revision',0)+1)
        try:
            with self.assertRaises(Pending):certificate(receipt,public=True)
        finally:r.data=data