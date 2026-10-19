import unittest
from fractions import Fraction as F
from benchmarks.player_match_groups.default_max_design import moment_value, posterior_reference, oracle_moments
from benchmarks.player_match_groups.report_integral_design import make, oracle
from werewolf.actor_information import PersonalInformation, WolfInformation
from werewolf.calculation_budget import calculation_budget


class DefaultMaxDesignTests(unittest.TestCase):
    def test_named_joint_report_faces_match_normalized_reference(self):
        # The source generator has random earlier actions. These are conditional
        # terminal frames, not claimed reachable under the initial MAX policy.
        with calculation_budget(250000, max_seconds=30):
            for kind, target in [('single',3), ('dual',3), ('three',4)]:
                c, n = make(5, kind, target, 5)
                h = next(h for h in n.read().private.hypotheses if h.roles[2]&1)
                views = (n, n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1], n.personal(WolfInformation.from_hypothesis(h))[1])
                for selected in views:
                    rows, _ = oracle(selected.read())
                    events = oracle_moments(selected.read(), rows)
                    value, buckets = moment_value(events)
                    self.assertEqual(value, posterior_reference(events))
                    self.assertLessEqual(len(buckets), 7)
                    self.assertEqual(sum((sum(q.values(),F()) for q,p in events),F()),1)
                    self.assertEqual(sum((sum(p.values(),F()) for q,p in events),F()),1)

    def test_max_and_report_average_do_not_commute(self):
        events = [({1:F(1,2),2:F(0)}, {1:F(1,2),2:F(0)}),
                  ({1:F(0),2:F(1,2)}, {1:F(0),2:F(1,2)})]
        self.assertEqual(moment_value(events)[0],1)
        self.assertEqual(max(sum(q[t] for q,p in events) for t in (1,2)),F(1,2))

    def test_public_face_must_not_be_reselected_using_private_p(self):
        events = [({1:F(2,3),2:F(1,3)}, {1:F(0),2:F(1)})]
        self.assertEqual(moment_value(events)[0],0)
        self.assertEqual(max(events[0][1].values()),1)

    def test_tied_medium_instructions_must_merge_before_day_choice(self):
        # Abstract finite report frame: A wolf1, B wolf2, C wolf3.
        # Medium truth is white in A, black in C; B is the fake medium.
        white = [({1:F(1,3),2:F(1,3),3:F(0)}, {1:F(0),2:F(1),3:F(0)}),
                 ({1:F(0),2:F(0),3:F(1,3)}, {1:F(0),2:F(0),3:F(0)})]
        black = [({1:F(1,3),2:F(0),3:F(0)}, {1:F(0),2:F(0),3:F(0)}),
                 ({1:F(0),2:F(1,3),3:F(1,3)}, {1:F(0),2:F(1),3:F(0)})]
        public = lambda es: sum(max(q.values()) for q,p in es)
        self.assertEqual(public(white),F(2,3)); self.assertEqual(public(black),F(2,3))
        mixed = [({t:(a[t]+b[t])/2 for t in a}, {t:(pa[t]+pb[t])/2 for t in pa})
                 for (a,pa),(b,pb) in zip(white,black)]
        self.assertEqual((moment_value(white)[0]+moment_value(black)[0])/2,F(1,2))
        self.assertEqual(moment_value(mixed)[0],0)

    def test_future_scans_cannot_be_given_to_wolf_before_bite(self):
        # Two true seers, each has one redundant and two informative draws.
        draws = [(F(1,2) if a==0 else F(1), F(1,2) if b==0 else F(1))
                 for a in range(3) for b in range(3)]
        ex_ante = min(sum(row[t] for row in draws)/9 for t in (0,1))
        clairvoyant = sum(min(row) for row in draws)/9
        self.assertEqual(ex_ante,F(5,6)); self.assertEqual(clairvoyant,F(13,18))
        self.assertNotEqual(ex_ante,clairvoyant)

if __name__ == '__main__': unittest.main()
