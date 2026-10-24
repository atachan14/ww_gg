import copy,json,os,pickle,subprocess,sys,unittest
from dataclasses import replace,FrozenInstanceError
from fractions import Fraction as F
from unittest.mock import patch
from tests.test_joint_value_sharing import hypothesis,law
from werewolf.seer_acquisition import Hypothesis
from werewolf.seer_future_uniform import TrueScanState
from werewolf.guard_effect import GuardIntent

class ImmutableStateHashTests(unittest.TestCase):
 def original(self,state):return hash((state.hypotheses,state.rosters,state.initial_rule,state.tracked,state.observed_prefix))
 def test_same_full_hash_and_equality_with_no_warm_hypothesis_hashing(self):
  a=law((hypothesis(),));equal=law((hypothesis(),))
  expected=self.original(a);self.assertEqual(hash(a),expected);self.assertEqual(hash(equal),expected)
  with patch.object(Hypothesis,'__hash__',side_effect=AssertionError('rehashing immutable hypotheses')):
   for _ in range(100):self.assertEqual(hash(a),expected)
  self.assertEqual(a,equal);self.assertEqual({a:'original'}[equal],'original')
  self.assertNotIn('_hash_cache',repr(a))
  with self.assertRaises(FrozenInstanceError):a.observed_prefix=1

 def test_roles_histories_weights_rosters_and_metadata_remain_distinct(self):
  a=law((hypothesis(),))
  variants=[law((hypothesis(attack=4),)),law((hypothesis(target=4),)),replace(a,tracked=(2,),observed_prefix=1),replace(a,rosters=((1,2,3,4),(1,2,3))),replace(a,initial_rule='normal',observed_prefix=1)]
  guarded=law((hypothesis(roles=(1,0,2,4),guards=(GuardIntent(1,3,4),)),))
  other=law((hypothesis(roles=(1,0,2,4),guards=(GuardIntent(1,3,2),)),))
  variants.extend((guarded,other))
  for state in [a,*variants]:self.assertEqual(hash(state),self.original(state))
  self.assertEqual(len({s:i for i,s in enumerate([a,*variants])}),len(variants)+1)
  q=law((hypothesis(mass=F(1,2)),hypothesis(mass=F(1,2),roles=(4,0,2,0),target=1)))
  p=law((hypothesis(mass=F(1,3)),hypothesis(mass=F(2,3),roles=(4,0,2,0),target=1)))
  self.assertNotEqual(q,p);self.assertEqual(len({q:'Q',p:'P'}),2)

 def test_hash_collision_keeps_full_equality(self):
  a=law((hypothesis(),));b=law((hypothesis(target=4),))
  with patch.object(TrueScanState,'__hash__',return_value=7):
   mapping={a:'first',b:'second'};self.assertEqual(len(mapping),2);self.assertEqual(mapping[a],'first');self.assertEqual(mapping[b],'second')

 def test_mutable_inputs_and_subclasses_keep_original_uncached_behavior(self):
  a=law((hypothesis(),))
  mutable=replace(a,hypotheses=list(a.hypotheses))
  with self.assertRaises(TypeError):hash(mutable)
  self.assertNotIn('_hash_cache',mutable.__dict__)
  with self.assertRaises(TypeError):hash(law((hypothesis(roles=[1,0,2,0]),)))
  class Derived(TrueScanState):pass
  subclass=Derived(a.hypotheses,a.rosters,a.initial_rule,a.tracked,a.observed_prefix)
  self.assertEqual(hash(subclass),self.original(subclass));self.assertNotIn('_hash_cache',subclass.__dict__)

 def test_replace_copy_and_cross_seed_pickle_do_not_reuse_derived_hash(self):
  a=law((hypothesis(),));hash(a)
  for result in (copy.copy(a),copy.deepcopy(a),pickle.loads(pickle.dumps(a)),replace(a)):
   self.assertNotIn('_hash_cache',result.__dict__);self.assertEqual(result,a);self.assertEqual(hash(result),self.original(result))
  program="""import pickle,sys
s=pickle.loads(bytes.fromhex(sys.argv[1]))
assert '_hash_cache' not in s.__dict__
assert hash(s)==hash((s.hypotheses,s.rosters,s.initial_rule,s.tracked,s.observed_prefix))
print('PASS')
"""
  env=dict(os.environ,PYTHONHASHSEED='78213')
  result=subprocess.run([sys.executable,'-X','utf8','-c',program,pickle.dumps(a).hex()],capture_output=True,text=True,timeout=10,env=env)
  self.assertEqual(result.returncode,0,result.stderr[:500]);self.assertEqual(result.stdout.strip(),'PASS')
