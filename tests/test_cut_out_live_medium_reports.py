import unittest
from fractions import Fraction as F
from dataclasses import replace
from benchmarks.player_match_groups.cut_out_live_medium_reports import (
    audit, prepublication, single_truth_orbits, Pending)
from werewolf.exact import random_report_outcomes
from werewolf.seer_acquisition import normalize


class LiveMediumReportsTests(unittest.TestCase):
    def test_medium_first_QP_and_all_labelled_secret_histories(self):
        result=audit()
        self.assertEqual((result['black_Q'],result['medium_black_P']),('1/2','4/9'))
        self.assertEqual((result['representative_vectors'],result['restored_black_vectors']),(4,8))
        self.assertEqual(result['private_roster17_positive_Q_zero_P'],13)
        self.assertTrue(result['complete_public_and_private_histories_equal'])

    def test_private_history_bias_with_unchanged_role_marginals_is_not_receipt(self):
        e,source,_=prepublication()
        outcome=next(o for o in random_report_outcomes(source.public)
            if any(r.color=='black' for r in o.board.reports))
        law=e.project(source.public_state,outcome.board)
        entries=[]
        for roles in {h.roles for h in law.hypotheses}:
            selected=tuple(h for h in law.hypotheses if h.roles==roles)
            total=sum((h.mass for h in selected),F())
            biased=normalize(tuple(replace(h,mass=h.mass*(2 if any(a.day==2 and a.target==5 for a in h.acquisitions) else 1)) for h in selected))
            entries.extend(replace(h,mass=h.mass*total) for h in biased)
        changed=replace(law,hypotheses=normalize(tuple(entries)))
        marginal=lambda s:{r:sum(h.mass for h in s.hypotheses if h.roles==r) for r in {h.roles for h in s.hypotheses}}
        self.assertEqual(marginal(law),marginal(changed))
        with self.assertRaises(Pending) as caught:
            single_truth_orbits(outcome.board,changed,source.past,((1,),(2,),(3,),(4,),(5,6,7)))
        self.assertEqual(caught.exception.reason,'live_medium_complete_history_Q_not_exchangeable')