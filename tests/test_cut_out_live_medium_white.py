import unittest
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_live_medium_reports import (
    prepublication,single_report_orbits,restore_reports,Pending)
from benchmarks.player_match_groups.cut_out_live_medium_forecast import make_case,certificate,cold
from werewolf.exact import random_report_outcomes
from werewolf.morning_publications import public_report_branches
from werewolf.calculation_budget import calculation_budget

GROUPS=((1,),(2,),(3,),(4,),(5,6,7))


class LiveMediumWhiteTests(unittest.TestCase):
    def test_black_and_white_share_reducer_with_complete_QP_history_equality(self):
        with calculation_budget(1000000,max_seconds=30):
            e,source,_=prepublication();rows=[];counts={}
            for outcome in random_report_outcomes(source.public):
                law=e.project(source.public_state,outcome.board)
                orbits=single_report_orbits(outcome.board,law,source.past,GROUPS)
                restored=public_report_branches(outcome.board,source.past,restore_reports(orbits))
                color=outcome.board.reports[0].color
                counts[color]=(len(orbits),len(restored))
                rows.extend((outcome.probability*q,b,s,p) for q,b,s,p in restored)
            old=e.morning(source.public,source.public_state,source.past)
            key=lambda rr:{(b,p):(q,s) for q,b,s,p in rr}
            self.assertEqual(key(rows),key(old))
            own=lambda rr:{(b,p):(q,s,private) for q,b,s,p,private in rr}
            self.assertEqual(own(e.push(source.public_state,source.private,tuple(rows))),own(e.push(source.public_state,source.private,old)))
            self.assertEqual(counts,{'black':(4,8),'white':(6,10)})

    def test_exposed_fake_keeps_false_reports_without_own_secret_filter(self):
        white=make_case(5,'white',medium='white',restricted=True)
        black=make_case(5,'black',medium='white',restricted=True)
        dead=make_case(1,'black',medium='white',restricted=True)
        self.assertEqual((white.q,white.p),(F(1,20),F(1,10)))
        self.assertEqual(white.physical_source.private,black.physical_source.private)
        self.assertEqual(dead.p,F(1,10))
        self.assertTrue(all(h.roles[0]==18 for h in white.physical_source.private.hypotheses))
        self.assertTrue(all(a.player!=2 for h in white.physical_source.private.hypotheses for a in h.acquisitions))
        for target in (2,4):
            with self.assertRaises(Pending):make_case(target,'white',medium='white')

    def test_impossible_physical_medium_white_retains_public_Q_and_cold(self):
        with calculation_budget(1000000,max_seconds=30):
            receipt=make_case(5,'white',medium='white',restricted=True,roster=17)
            self.assertEqual((receipt.q,receipt.p),(F(1,20),0))
            cap=certificate(receipt,public=True)
            self.assertEqual(cold(cap,cap.request),cap.source)
            with self.assertRaises(Pending):certificate(receipt)