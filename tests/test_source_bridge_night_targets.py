import unittest
from benchmarks.player_match_groups.cut_out_six_registry_fixture import setup
from benchmarks.player_match_groups.cut_out_six_source_bridge import issue,SourceWitness
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition
from werewolf.calculation_budget import calculation_budget

class SourceBridgeNightTargetTests(unittest.TestCase):
 def test_old_dead_target_is_rejected_before_any_source_bridge(self):
  with calculation_budget(300000,max_seconds=15):
   _,registry=setup(day2_target=2)
   self.assertIn('alive at night start',registry.problem.reason)
   result=issue(registry)
   self.assertIsInstance(result,UnsupportedPartition);self.assertEqual(result.reason,'source_bridge_registry_required')
 def test_legal_fixture_preserves_history_QP_and_complete_source_binding(self):
  with calculation_budget(300000,max_seconds=15):
   _,registry=setup(day2_target=4);self.assertIsNone(registry.problem)
   source=registry.read();before=registry.data.inputs
   self.assertEqual(tuple(e.target for e in source.public.history),(2,3))
   # Independent chronology: execution2 happens before the night; bite3 at
   # its end.4 is legal and unvisited,2 is not;3 was alive when actions began.
   night_start=tuple(p for p in range(1,7)if p!=2)
   self.assertIn(4,night_start);self.assertIn(3,night_start);self.assertNotIn(2,night_start)
   self.assertEqual(tuple((r.acquired_day,r.target) for r in source.past),((1,3),(2,4)))
   self.assertEqual(sum(h.mass for h in source.public_state.hypotheses),1)
   self.assertEqual(sum(h.mass for h in source.private.hypotheses),1)
   self.assertNotEqual(source.public_state,source.private)
   witness=issue(registry);self.assertIsInstance(witness,SourceWitness);self.assertEqual(witness.source,source)
   self.assertEqual(registry.data.inputs,before);self.assertEqual(registry.read(),source)
