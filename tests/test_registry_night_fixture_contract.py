"""Independent chronology and support checks for three registry fixtures."""
import unittest
from fractions import Fraction
from benchmarks.player_match_groups.cut_out_six_registry_fixture import setup, medium_case
from werewolf.calculation_budget import calculation_budget

class RegistryNightFixtureContractTests(unittest.TestCase):
 def test_legal_correction_still_eliminates_the_old_wolf_actor(self):
  # Execute2 before night, bite3 at its end. Initial scan3 is visited;
  # both new scan5 and correction4 are alive and unvisited at night start.
  night_start=set(range(1,7))-{2}
  self.assertTrue({3,4,5} <= night_start)
  self.assertNotIn(2,night_start)
  with calculation_budget(300000,max_seconds=15):
   _,before=setup(day2_target=5);_,after=setup(day2_target=4)
   self.assertIsNone(before.problem);self.assertIsNone(after.problem)
   old=before.read();new=after.read()
   # A white5 permits wolf4; white4 rules it out. This is the intended
   # invalidation test, not merely replacement with any legal target.
   mass=lambda source: sum((h.mass for h in source.private.hypotheses if h.roles[0]==1<<3),Fraction())
   self.assertGreater(mass(old),0);self.assertEqual(mass(new),0)
   for source in (old,new):
    self.assertEqual(sum(h.mass for h in source.public_state.hypotheses),1)
    self.assertEqual(sum(h.mass for h in source.private.hypotheses),1)
 def test_medium_victim_and_simultaneous_seer_victim_are_distinct(self):
  # Execute5, then bite6. Medium reports concern5; scan6 remains legal.
  night_start=set(range(1,7))-{5}
  self.assertNotIn(5,night_start);self.assertIn(6,night_start)
  with calculation_budget(300000,max_seconds=15):
   self.assertTrue(medium_case()['medium_reports_preserved'])
