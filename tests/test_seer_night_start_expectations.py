import unittest
from fractions import Fraction as F
from tests.seer_night_rule_oracle import known_seer_forced_bite
from werewolf.seer_acquisition import Hypothesis, Acquisition
from werewolf.seer_future_uniform import TrueScanState, acquire_uniform, true_reports

class SeerNightStartExpectationTests(unittest.TestCase):
    def test_independent_public_execution_oracle_for_both_wolf_locations(self):
        for wolf, other in ((4,5),(5,4)):
            values={victim:known_seer_forced_bite(wolf,victim)[0] for victim in (1,3,other)}
            self.assertEqual(values,{1:F(1,2),3:F(1),other:F(1)})
            _, rows=known_seer_forced_bite(wolf,1)
            self.assertTrue(all(row['report'] is None and row['executions']==(4,5) for row in rows))
            self.assertEqual(sum(row['probability'] for row in rows),1)
            with self.assertRaises(ValueError):known_seer_forced_bite(wolf,2)
            with self.assertRaises(ValueError):known_seer_forced_bite(wolf,wolf)

    def test_acquisition_and_publication_follow_night_start_not_morning_roster(self):
        claims=('seer','seer','latent','latent','latent')
        past=(Acquisition(1,1,3,'white'),)
        for wolf in (4,5):
            state=TrueScanState((Hypothesis((2|(1<<(wolf-1)),0,1,0),past,F(1)),),((1,2,3,4,5),))
            acquired=acquire_uniform(state,(1,3,4,5))
            self.assertEqual({h.acquisitions[-1].target for h in acquired.hypotheses},{4,5})
            self.assertEqual({h.mass for h in acquired.hypotheses},{F(1,2)})
            self.assertEqual(sum(h.mass for h in acquired.hypotheses),1)
            for victim in (1,3,9-wolf):
                _, expected=known_seer_forced_bite(wolf,victim)
                morning=tuple(p for p in (1,3,4,5) if p!=victim)
                for h in acquired.hypotheses:
                    a=h.acquisitions[-1]
                    row=next(row for row in expected if row['target']==a.target)
                    self.assertEqual(a.color,row['color'])
                    reports=true_reports(h,(),morning,claims,2)
                    latest=tuple((r.target,r.color) for r in reports if r.acquired_day==2)
                    self.assertEqual(latest,() if row['report'] is None else (row['report'],))
                    self.assertEqual(len(h.acquisitions),2)  # acquisition survives simultaneous actor death
                    self.assertNotEqual(a.target,2)  # previous execution cannot be scanned
                    if a.target==victim:
                        self.assertIn((a.target,a.color),latest)  # simultaneous victim still reportable

if __name__=='__main__':unittest.main()

