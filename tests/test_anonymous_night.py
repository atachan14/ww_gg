import unittest
from fractions import Fraction as F
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.anonymous_night import compile_anonymous
from werewolf.information_set_forecast import InformationSetForecast

class AnonymousNightTests(unittest.TestCase):
 def case(self,seers=1,wolves=1,citizens=3,mode='random'):
  app=create_app({'TESTING':True,'SECRET_KEY':'anonymous-night'});client=app.test_client()
  client.post('/start',data={'citizens':str(citizens),'wolves':str(wolves),'seers':str(seers),'mediums':'0','hunters':'0','day':mode,'night':mode,'fake_reports':mode})
  with client.session_transaction() as session:data=BoardData.from_game(session['game'])
  calculation=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
  night=next(o.node for o in calculation.root.action(1) if not o.node.read().public.winner)
  return calculation,night
 def test_actual_kernel_matches_named_scalar_and_mass(self):
  for seers in (1,2):
   c,node=self.case(seers=seers,citizens=4-seers);e=c._ClosedCalculation__engine
   with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
    program=compile_anonymous(e,node.read(),node.groups)
    self.assertEqual(sum(leaf.mass for leaf in program.leaves),1);self.assertEqual(sum(leaf.counter for leaf in program.leaves),1)
    oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True
    self.assertEqual(program.root.value(e),oracle.solve(*node.read(),physical=node.read().physical))
    self.assertEqual(program.stats['permutation_checks'],0)
    self.assertLessEqual(program.stats['relational_families'],program.stats['named_prior_atoms'])
 def test_actor_information_and_public_Q_are_frozen_at_every_prefix(self):
  c,node=self.case();e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   program=compile_anonymous(e,node.read(),node.groups);pending=[program.root]
   while pending:
    stage=pending.pop();self.assertIs(stage.public,node.read().public_state)
    for actor in node.read().public.alive:self.assertEqual(stage.actor_information(actor),program.root.actor_information(actor))
    if not stage.terminal:pending.extend(branch.state for branch in stage.branches())
 def test_native_stage_aliases_and_death_order(self):
  c,node=self.case();e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   program=compile_anonymous(e,node.read(),node.groups)
   for leaf in program.leaves:
    kinds=[s.kind for s in leaf.steps];attack=kinds.index('wolf_target');self.assertEqual(kinds[attack+1],'death_notice')
    if 'publication' in kinds:self.assertGreater(kinds.index('publication'),attack+1)
   self.assertTrue(any('のa]が[' in b.step.label() for b in program.root.branches()))
 def test_two_wolf_population_remains_collective(self):
  c,node=self.case(seers=1,wolves=2,citizens=4);e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   program=compile_anonymous(e,node.read(),node.groups)
   self.assertEqual(sum(leaf.mass for leaf in program.leaves),1)
   for leaf in program.leaves:
    attack=next(s for s in leaf.steps if s.kind=='wolf_target');expected=sum(1 for p in node.read().public.alive if leaf.information.initial_roster&(1<<(p-1)));self.assertEqual(len(attack.actors),expected);self.assertEqual(attack.label().startswith('狼集合'),expected>1)

 def test_MAX_committed_policy_zero_mass_and_named_value(self):
  from tests.test_joint_action_kernel import fixture
  c,node,client=fixture('max');e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   program=compile_anonymous(e,node.read(),node.groups)
   oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True
   self.assertEqual(sum(leaf.mass for leaf in program.leaves),1);self.assertEqual(sum(leaf.counter for leaf in program.leaves),1)
   self.assertEqual(program.root.value(e),oracle.solve(*node.read(),physical=node.read().physical))
   self.assertTrue(any(leaf.mass==0 and leaf.counter>0 for leaf in program.leaves))

 def test_cold_named_component_reconstruction_preserves_Q_P_and_history(self):
  c,node=self.case();e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   program=compile_anonymous(e,node.read(),node.groups)
   for leaf in program.leaves[::max(1,len(program.leaves)//5)]:
    request=node._stage_child(leaf).export_request();cold=request.roles()
    self.assertEqual(tuple(cold),tuple(leaf.source));self.assertEqual(cold.physical,leaf.source.physical)
 def test_actual_API_uses_symbol_objects_and_no_legacy_action_product(self):
  app=create_app({'TESTING':True,'SECRET_KEY':'native-api','GAME_TREE_PREVIEW':True,'ANONYMOUS_NIGHT_PREVIEW':True});client=app.test_client()
  client.post('/start',data={'citizens':'3','wolves':'1','seers':'1','day':'random','night':'random','fake_reports':'random'})
  root=client.get('/game-tree?expand=1').json
  night=next(root['items'][branch['node']] for action in root['actions'] for branch in action['branches'] if not root['items'][branch['node']]['winner'])
  key=next(c['node'] for c in night['compositions'] if c['counts']['seers']==1)
  response=client.get('/game-tree',query_string={'node':key,'expand':'1'});self.assertEqual(response.status_code,200,response.data)
  data=response.json;self.assertEqual(data['night_stages']['method'],'anonymous-relational-v1');self.assertEqual(data['actions'],[])
  self.assertTrue(all('symbols' in b for b in data['night_stages']['branches']))

 def test_distinguishable_prior_uses_refined_classes_and_named_exact_value(self):
  from dataclasses import replace
  from werewolf.seer_acquisition import normalize
  from werewolf.evaluation_branch import physical_board
  c,node=self.case();e=c._ClosedCalculation__engine;s=node.read()
  own=replace(s.private,hypotheses=normalize(tuple(replace(h,mass=h.mass*(3 if h.roles[0]&8 else 1)) for h in s.private.hypotheses)))
  source=replace(s,private=own,physical=physical_board(s.public,own,s.physical))
  groups=tuple((p,) for p in range(1,s.public.player_count+1))
  with c._ClosedCalculation__kernel(),e.group_scope(groups):
   p=compile_anonymous(e,source,groups)
   oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True
   self.assertEqual(sum(l.mass for l in p.leaves),1)
   self.assertEqual(p.root.value(e),oracle.solve(*source,physical=source.physical))
   self.assertEqual(p.stats['permutation_checks'],0)
