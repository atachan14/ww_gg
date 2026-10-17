import unittest
from werewolf.exact import Rules,Strategy
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,tick
class Key:
 def __init__(self):self.calls=0
 def __hash__(self):self.calls+=1;return 41
class SingleLookupTests(unittest.TestCase):
 def engine(self):return InformationSetForecast(Rules(),Strategy())
 def test_flow_hits_hash_complete_key_once_including_falsey_values(self):
  for value in [None,False,0,(),{}]:
   e=self.engine();key=Key();cache={key:value};key.calls=0
   self.assertIs(e.cached_flow(cache,key,lambda:self.fail('hit recomputed'),'action'),value)
   self.assertEqual(key.calls,1)
 def test_disabled_flow_memoization_neither_reads_nor_writes_cache(self):
  e=self.engine();e.memoize_flows=False;key=Key();cache={key:'old'};key.calls=0
  self.assertEqual(e.cached_flow(cache,key,lambda:'new','action'),'new');self.assertEqual(key.calls,0)
  self.assertEqual(cache[key],'old')
 def test_public_support_hits_preserve_none_and_statistics_with_one_hash(self):
  e=self.engine();key=Key();e.public_support_values[key]=None;key.calls=0
  self.assertIsNone(e.public_support(key,lambda:self.fail('support recomputed')))
  self.assertEqual(key.calls,1);self.assertEqual(e.public_support_stats,{'calls':1,'hits':1})
 def test_failed_computations_do_not_install_partial_results(self):
  e=self.engine();key=Key();cache={}
  def fail():raise ValueError('incomplete')
  with self.assertRaisesRegex(ValueError,'incomplete'):e.cached_flow(cache,key,fail,'action')
  self.assertNotIn(key,cache)
  with self.assertRaisesRegex(ValueError,'incomplete'):e.public_support(key,fail)
  self.assertNotIn(key,e.public_support_values)
 def test_completed_hit_still_consumes_existing_budget_tick(self):
  e=self.engine();key=Key();cache={key:0}
  with calculation_budget(1,max_seconds=20):
   tick()
   with self.assertRaises(CalculationBudgetExceeded):e.cached_flow(cache,key,lambda:1,'action')
  self.assertEqual(cache[key],0)
