import unittest
from dataclasses import replace
from fractions import Fraction as F
from collections import defaultdict
from werewolf.anonymous_belief import Belief,initial_law,Law
from werewolf.anonymous_materialization import expand,representative
from werewolf.public_convergence import public_observation_orbits
from tests import test_anonymous_night as native

class AnonymousBeliefTests(unittest.TestCase):
 def case(self,seers=1,wolves=1,citizens=3):
  c,node=native.AnonymousNightTests().case(seers=seers,wolves=wolves,citizens=citizens)
  groups=(tuple(range(1,seers+wolves+citizens+1)),)
  return c,node,Belief.initial(groups,dict(seer=seers,wolf=wolves,villager=citizens))
 def test_count_native_initial_prior_matches_independent_named_reconstruction(self):
  for s,w,cit in ((1,1,3),(2,1,2),(1,2,3)):
   c,node,b=self.case(s,w,cit)
   self.assertEqual(expand(b.q,b.groups),c.root.read().public_state.hypotheses)
   self.assertEqual(sum(m for m,a in b.q.rows),1)
 def test_execution_branches_exact_roles_and_private_histories(self):
  c,node,b=self.case()
  rows=b.execute(1)
  self.assertEqual({key:mass for mass,key,child in rows},{'village':F(1,5),None:F(4,5)})
  for mass,key,child in rows:
   named=next(o.node.read() for o in c.root.action(1) if o.node.read().public.winner==key)
   self.assertEqual(expand(child.q,child.groups),named.public_state.hypotheses)
   self.assertEqual(expand(child.p,child.groups),named.private.hypotheses)
 def test_public_night_Q_uses_compatibility_P_uses_committed_policy(self):
  for seers in (1,2):
   c,node,b=self.case(seers=seers,citizens=4-seers)
   b=next(child for mass,key,child in b.execute(1) if key is None).refine(node.groups)
   flow=b.night();e=c._ClosedCalculation__engine
   self.assertEqual(sum(row.mass for row in flow.rows),1)
   with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
    for observation in flow.observations():
     mass,child=flow.branch(observation)
     expected=next(s for q,s in public_observation_orbits(e,node.read(),observation[0],node.groups) if s.public.winner==observation[1])
     self.assertEqual(expand(child.q,child.groups),expected.public_state.hypotheses)
     self.assertEqual(expand(child.p,child.groups),expected.private.hypotheses)
 def test_refining_public_names_preserves_complete_joint_measure(self):
  c,node,b=self.case(seers=2,citizens=2)
  for groups in (((1,),(2,3,4,5)),((1,2),(3,),(4,5)),tuple((p,) for p in range(1,6))):
   refined=b.refine(groups)
   self.assertEqual(expand(refined.q,groups),expand(b.q,b.groups))
 def test_counts_scale_without_named_assignments(self):
  b=Belief.initial((tuple(range(1,1003)),),dict(seer=1,wolf=1,villager=1000))
  self.assertEqual(len(b.q.rows),1)
  rows=b.execute(1);self.assertEqual(sum(m for m,key,child in rows),1)
  self.assertLess(sum(len(child.p.rows) for m,key,child in rows),10)

 def test_actual_native_path_owns_belief_and_never_ingests_named_prior(self):
  from unittest.mock import patch
  from werewolf.closed_calculation import ClosedCalculation
  from werewolf.anonymous_night import compile_anonymous
  c,unused,b=self.case()
  owned=ClosedCalculation(c.data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  node=next(o.node for o in owned.root.action(1) if not o.node.read().public.winner)
  e=owned._ClosedCalculation__engine
  with owned._ClosedCalculation__kernel(),e.group_scope(node.groups),patch('werewolf.anonymous_night.ingest',side_effect=AssertionError('named prior ingested')),patch.object(e,'acquire',side_effect=AssertionError('named acquisition generated')):
   program=compile_anonymous(e,node.read(),node.groups)
   self.assertTrue(program.stats['belief_owned']);self.assertEqual(program.stats['named_prior_atoms'],0)
   self.assertEqual(sum(row.mass for row in program.leaves),1)
   self.assertIsNotNone(program.belief_flow)
 def test_true_public_API_uses_owned_posterior_not_named_acquisition_generation(self):
  from unittest.mock import patch
  from werewolf.calculation_tree import CalculationTree
  c,unused,b=self.case();r=c.data.roles();tree=CalculationTree(c.data,r.board,r.forecast(),anonymous=True)
  root=tree.read(tree.root,True)
  key=next(br['node'] for a in root['actions'] for br in a['branches'] if not root['items'][br['node']]['winner'])
  with patch('werewolf.public_convergence.public_observation_orbits',side_effect=AssertionError('named posterior kernel used')):
   night=tree.read(key,True)
  self.assertTrue(night['night_stages']['stats']['belief_owned'])
  self.assertTrue(tree.nodes[key]['public_bundles'])
  for entry in tree.nodes[key]['public_bundles'].values():
   self.assertIn('owned',entry)
   for counter,(mass,source) in entry['sources'].items():
    self.assertIn(source,tree.engine.anonymous_beliefs)

 def test_nonuniform_and_zero_policy_public_updates_keep_Q_distinct_from_P(self):
  from unittest.mock import patch
  for zero in (False,True):
   c,node,b=self.case();b=next(child for mass,key,child in b.execute(1) if key is None)
   groups=((1,),(2,),(3,4,5));b=b.refine(groups);e=c._ClosedCalculation__engine;calls=[]
   def policy(board,state,past,mask,history=()):
    legal=[p for p in board.alive if not mask&(1<<(p-1))]
    weights={p:(int(p==2) if zero and 2 in legal else (3 if p==2 else 1)) for p in legal}
    total=sum(weights.values());return tuple((p,F(w,total)) for p,w in weights.items())
   def factory(atom):
    calls.append(atom);h,transport=representative(atom,groups)
    committed=dict(policy(node.read().public,None,None,h.roles[0]))
    def selected(choice,bindings):
     extra=((choice.target,choice.fresh_cell),) if choice.fresh_cell is not None else ()
     names=transport.apply((*bindings,*extra));return committed.get(names[choice.target],F())
    return selected
   flow=b.night(factory);self.assertEqual(len(calls),len(b.p.rows));different=False
   with c._ClosedCalculation__kernel(),e.group_scope(groups),patch.object(e,'wolf_policy',side_effect=policy):
    for observation in flow.observations():
     for counter in (False,True):
      try:mass,child=flow.branch(observation,counter=counter)
      except ValueError:continue
      expected=next(s for q,s in public_observation_orbits(e,node.read(),observation[0],groups,counter=counter) if s.public.winner==observation[1])
      self.assertEqual(expand(child.q,groups),expected.public_state.hypotheses)
      self.assertEqual(expand(child.p,groups),expected.private.hypotheses)
      different|=expand(child.q,groups)!=expand(child.p,groups)
   self.assertTrue(different)
 def test_owned_MAX_value_and_second_public_transition_match_named_solver(self):
  from werewolf.closed_calculation import ClosedCalculation
  from werewolf.anonymous_night import compile_anonymous
  from werewolf.information_set_forecast import InformationSetForecast
  c,unused=native.AnonymousNightTests().case(mode='max')
  owned=ClosedCalculation(c.data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  night=next(o.node for o in owned.root.action(1) if not o.node.read().public.winner);e=owned._ClosedCalculation__engine
  with owned._ClosedCalculation__kernel(),e.group_scope(night.groups):
   p=compile_anonymous(e,night.read(),night.groups)
   oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True
   self.assertTrue(p.stats['belief_owned'])
   self.assertEqual(p.root.value(e),oracle.solve(*night.read(),physical=night.read().physical))
   for observation in p.belief_flow.observations():
    try:mass,child=p.belief_flow.branch(observation)
    except ValueError:continue
    for victim in (3,4,5):self.assertEqual(sum(q for q,key,after in child.execute(victim)),1)

 def test_two_complete_nights_preserve_old_private_relations_and_dead_target_legality(self):
  from werewolf.action_flow import resolve_action
  from werewolf.evaluation_branch import ActionInputs
  from werewolf.group_partition import _fix
  c,node,b=self.case(citizens=5);b=next(child for mass,key,child in b.execute(1) if key is None).refine(node.groups)
  e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   flow=b.night();mass,b=flow.branch((2,None))
   source=next(s for q,s in public_observation_orbits(e,node.read(),2,node.groups) if s.public.winner is None)
   payload=ActionInputs(source.public_state,source.past,source.private,None,source.physical)
   acquired,outcomes=resolve_action(source.public,payload,3,e.action_policy,terminal_payoffs=False)
   after=next(e.action_policy._project_roles(source.public,acquired,o,3) for o in outcomes if o.board.winner is None)
   b=next(child for mass,key,child in b.execute(3) if key is None)
   groups=_fix(node.groups,(2,3));b=b.refine(groups);second=b.night()
   self.assertEqual(sum(row.mass for row in second.rows),1)
   for observation in second.observations():
    mass,child=second.branch(observation)
    expected=next(s for q,s in public_observation_orbits(e,after,observation[0],groups) if s.public.winner==observation[1])
    self.assertEqual(expand(child.q,groups),expected.public_state.hypotheses)
    self.assertEqual(expand(child.p,groups),expected.private.hypotheses)
    for weight,atom in child.p.rows:
     for scan in atom.population.scans:
      if scan.day==3:self.assertNotIn(dict((ref,name) for name,ref in atom.pins).get(scan.target),(1,2,3))
 def test_private_prefix_keeps_public_Q_and_multiple_actor_records(self):
  c,node,b=self.case(seers=2,citizens=2);b=next(child for m,key,child in b.execute(1) if key is None).refine(node.groups)
  flow=b.night();self.assertTrue(flow.rows)
  for observation in flow.observations():
   mass,all_paths=flow.branch(observation)
   for row in flow.rows:
    if row.observation!=observation:continue
    mass,conditioned=flow.branch(observation,row.steps[:2])
    self.assertIs(conditioned.q,all_paths.q)
    self.assertEqual(sum(w for w,a in conditioned.p.rows),1)
