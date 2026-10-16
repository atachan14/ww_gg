"""Harness tests: exact encoding, censoring, exclusive phases and smoke snapshots."""
import importlib.util,sys,unittest
from pathlib import Path
from fractions import Fraction
from unittest.mock import patch
path=Path(__file__).resolve().parents[1]/'benchmarks/board_b_benchmark.py'
spec=importlib.util.spec_from_file_location('board_b_benchmark',path);bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)

class BenchmarkHarnessTests(unittest.TestCase):
 def test_exact_semantics_distinguish_inputs_and_order(self):
  self.assertEqual(bench.digest({'b':Fraction(2,4),'a':(1,2)}),bench.digest({'a':[1,2],'b':Fraction(1,2)}))
  self.assertNotEqual(bench.digest([1,2]),bench.digest([2,1]))
 def test_pending_is_censored_not_a_fast_completed_trial(self):
  rows=[{'seconds':20,'complete':False},{'seconds':1,'complete':True},{'seconds':3,'complete':True,'high_background_load':True}]
  result=bench.summarize(rows)
  self.assertEqual(result['median_seconds'],2);self.assertEqual(result['censored'],1)
  self.assertEqual(result['low_background_median_seconds'],1)
 def test_exclusive_nested_phases_do_not_double_count(self):
  with patch.object(bench.time,'perf_counter',side_effect=[0,1,3,5,8,9]):
   d=bench.Diagnostic()
   with d.scope('3b'):
    with d.scope('3a'):pass
   d.close()
  self.assertEqual(d.seconds,{'3b':5,'3a':2})
 def test_fraction_encoding_is_not_a_rounded_float(self):
  self.assertEqual(bench.canonical(Fraction(1,3)),{'fraction':'1/3'})

 def test_diagnostic_wrapper_restores_functions_and_counts_elements(self):
  import types
  owner=types.SimpleNamespace(__name__='sample',call=lambda x:sum(x))
  original=owner.call;d=bench.Diagnostic();d.wrap(owner,'call',phase='3a',elements=lambda a,k:len(a[0]))
  self.assertEqual(owner.call([2,3]),5);d.close()
  self.assertIs(owner.call,original)
  self.assertEqual(d.counts['sample.call'],1);self.assertEqual(d.elements['sample.call'],2)
 def test_both_sample_distributions_and_pending_conditions_are_preserved(self):
  from dataclasses import dataclass
  @dataclass
  class FuturePending:reason:str
  self.assertEqual(bench.census_pending(FuturePending('scope_missing')),['scope_missing'])
  self.assertNotEqual(bench.digest({'actions':[(2,Fraction(1,2)),(3,Fraction(1,2))]}),bench.digest({'actions':[(2,Fraction(1))]}))

 def test_native_role_pairs_normalize_without_changing_time_or_input(self):
  import copy
  sys.path.insert(0,str(path.parent))
  from board_b_normalize_results import normalize
  raw={'rows':[{'seconds':1.25,'semantic_digest':'original','semantic':{'public_roles':[[['wolf',{'fraction':'1/5'}],['villager',{'fraction':'4/5'}]]]}}]}
  original=copy.deepcopy(raw);result=normalize(raw)
  self.assertEqual(raw,original)
  self.assertEqual(result['rows'][0]['seconds'],1.25)
  self.assertEqual(result['rows'][0]['semantic']['public_roles'],[{'wolf':{'fraction':'1/5'},'villager':{'fraction':'4/5'}}])

 def test_ineligible_cache_calls_are_not_counted_as_misses(self):
  self.assertEqual(bench.resolution_status(0,0,None),'ineligible')
  self.assertEqual(bench.resolution_status(0,1,None),'miss')
  self.assertEqual(bench.resolution_status(0,1,object()),'hit')

 def test_partial_public_metrics_are_not_a_complete_forecast(self):
  from dataclasses import dataclass
  @dataclass
  class Forecast:pending_metrics:tuple=('by_dawn',)
  self.assertTrue(bench.census_pending(Forecast()))
  self.assertEqual(bench.census_pending({'pending_metrics':['by_dawn']}),["['by_dawn']"])
