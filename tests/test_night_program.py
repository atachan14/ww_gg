import unittest
from fractions import Fraction as F
from dataclasses import replace
from itertools import product
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.calculation_tree import CalculationTree
from werewolf.night_program import compile_night,supported
from werewolf.night_abilities import seer_paths,stage_schema,ROLE_ORDER
from werewolf.seer_acquisition import Acquisition,Hypothesis,normalize
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.evaluation_branch import ContinuationInputs,physical_board

class NightProgramTests(unittest.TestCase):
 def case(self,seers=1,mode='max',claim_none=False):
  app=create_app({'TESTING':True,'SECRET_KEY':'night-stage-tests','GAME_TREE_PREVIEW':True});client=app.test_client()
  client.post('/start',data={'citizens':str(4-seers),'wolves':'1','seers':str(seers),'mediums':'0','hunters':'0','day':mode,'night':mode,'fake_reports':mode})
  with client.session_transaction() as ss:
   game=ss['game']
   if claim_none:game['claim_policy']['seer']='none';ss['game']=game
   data=BoardData.from_game(game)
  c=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
  night=next(o.node for o in c.root.action(1) if not o.node.read().public.winner)
  composition=next(k for k,q in night._compositions() if k[2]==seers)
  return c,night._select_physical('composition',composition),client
 def walk(self,stage):
  if stage.terminal:return [()]
  return [(b.step.kind,*tail) for b in stage.branches() for tail in self.walk(b.state)]
 def test_real_all_hidden_API_has_result_stage_and_universal_target_orbits(self):
  for claim_none in (False,True):
   c,node,client=self.case(claim_none=claim_none)
   root=client.get('/game-tree?expand=1').json
   night=next(root['items'][b['node']] for a in root['actions'] for b in a['branches'] if not root['items'][b['node']]['winner'])
   key=next(x['node'] for x in night['compositions'] if x['counts']['seers']==1)
   response=client.get('/game-tree',query_string={'node':key,'expand':'1'});self.assertEqual(response.status_code,200,response.data)
   stages=response.json['night_stages'];self.assertIsNotNone(stages)
   self.assertEqual(len(stages['branches']),1);target=stages['branches'][0]
   self.assertEqual((target['actor'],target['value'],target['targets']),(2,3,[3,4,5]));self.assertEqual(target['label'],'[(2),3,4,5]\u304c[(3),4,5]\u304b\u3089\u5360\u3044')
   results=target['children']['branches'];self.assertEqual({r['label']:F(r['probability']) for r in results},{'\u767d':F(5,9),'\u9ed2':F(4,9)})
   for r in results:
    self.assertEqual(r['kind'],'seer_result');attacks=r['children']['branches'];groups=[a['targets'] for a in attacks]
    self.assertIn([2],groups)
    if r['label']=='\u767d':self.assertIn([5],groups)
    else:self.assertIn([4,5],groups)
    if r['label']=='\u767d':self.assertIn([3],groups)
    self.assertEqual(sum(F(a['probability']) for a in attacks),1)
    for a in attacks:self.assertTrue(a['children']['leaves'])
   # Exercise the real signed endpoint from a staged named leaf.
   selected=next(a for a in results[0]['children']['branches'] if a['targets']==[5])['children']['leaves'][0]['node']
   result=client.post('/game-tree/current',data={'snapshot':root['snapshot'],'node':selected});self.assertEqual(result.status_code,200,result.data)
   self.assertEqual(client.get(result.json['url']).status_code,200)
 def test_two_seers_have_target_result_pairs_and_same_named_scalar_value(self):
  c,node,client=self.case(2,'random');e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   program=compile_night(e,node.read(),node.groups)
   self.assertEqual(set(self.walk(program.root)),{('seer_target','seer_result','seer_target','seer_result','wolf_target')})
   reference=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False);reference.retain_joint_guard_history=True
   self.assertEqual(program.root.value(e),reference.solve(*node.read(),physical=node.read().physical))
   self.assertEqual(sum(x.mass for x in program.leaves),1);self.assertEqual(sum(x.counter for x in program.leaves),1)
   for leaf in program.leaves:
    actors=[s.actor for s in leaf.steps if s.kind=='seer_target'];self.assertEqual(actors,sorted(actors))
 def test_private_prefix_is_not_later_actor_information_or_public_evidence(self):
  c,node,client=self.case(2,'random');e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   program=compile_night(e,node.read(),node.groups);source=node.read();start=program.root
   pending=[start]
   while pending:
    stage=pending.pop();self.assertIs(stage.public,source.public_state)
    for actor in source.public.alive:self.assertEqual(stage.actor_information(actor),start.actor_information(actor))
    self.assertEqual(sum(h.mass for h in stage.physical_atoms),1)
    if not stage.terminal:pending.extend(b.state for b in stage.branches())
   profiles={k:v for k,v in e.policies.items() if k[0]==source.public}
   list(program.root.branches());self.assertEqual(profiles,{k:v for k,v in e.policies.items() if k[0]==source.public})
 def test_multiple_seer_generator_matches_independent_product_and_simultaneous_eligibility(self):
  h=Hypothesis((16,0,3,0),(Acquisition(1,1,3,'white'),Acquisition(1,2,4,'white')),F(1));alive=(1,2,4,5)
  paths=seer_paths(h,alive,2,'random_white')
  choices=((2,4,5),(1,5)) # dead 3 excluded; each actor reads only its own old record
  expected={tuple((a.player,a.target,a.color) for a in (Acquisition(2,1,x,'black' if x==5 else 'white'),Acquisition(2,2,y,'black' if y==5 else 'white'))):F(1,6) for x,y in product(*choices)}
  actual={tuple((a.player,a.target,a.color) for a in p.hypothesis.acquisitions if a.day==2):p.hypothesis.mass for p in paths}
  self.assertEqual(actual,expected);self.assertTrue(any(a.target==5 for p in paths for a in p.hypothesis.acquisitions if a.day==2))
  self.assertTrue(all(tuple(s.kind for s in p.steps)==('seer_target','seer_result','seer_target','seer_result') for p in paths))
 def test_result_precedes_same_night_seer_death_and_cold_named_replay(self):
  c,node,client=self.case();e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   program=compile_night(e,node.read(),node.groups)
   leaves=[r for r in program.leaves if any(s.kind=='seer_target' and s.actor==r.target for s in r.steps)]
   self.assertTrue(leaves)
   for leaf in leaves[:4]:
    self.assertEqual(tuple(s.kind for s in leaf.steps),('seer_target','seer_result','wolf_target'))
    child=node._stage_child(leaf);self.assertEqual(child.export_request().roles(),child.read())
    self.assertNotIn(leaf.target,child.read().public.alive)
    self.assertTrue(all(any(a.player==leaf.target and a.day==2 for a in h.acquisitions) for h in child.read().private.hypotheses))
    self.assertTrue(all(r.player!=leaf.target for r in child.read().past))
 def test_asymmetry_breaks_full_measure_target_group(self):
  c,node,client=self.case();s=node.read();p=replace(s.private,hypotheses=normalize(tuple(replace(h,mass=h.mass*(3 if h.roles[0]&8 else 1)) for h in s.private.hypotheses)))
  source=replace(s,private=p,physical=physical_board(s.public,p,s.physical));e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   program=compile_night(e,source,node.groups)
   self.assertTrue(all(m[3]==4 for m in program.automorphisms))
 def test_role_table_interface_has_no_invented_medium_guard_law(self):
  self.assertEqual(ROLE_ORDER,('medium','seer','hunter','wolf'))
  self.assertEqual(stage_schema(mediums=1,seers=2,hunters=1),(('medium_result',0),('seer_target',0),('seer_result',0),('seer_target',1),('seer_result',1),('guard_target',0),('wolf_target',0)))

 def test_grouped_prefix_and_outcome_images_reconstruct_each_named_joint_mass(self):
  from werewolf.night_program import NightStage
  from collections import defaultdict
  for mode in ('random','max'):
   c,node,client=self.case(mode=mode);e=c._ClosedCalculation__engine
   with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
    program=compile_night(e,node.read(),node.groups);actual=defaultdict(F)
    def expand(stage,reach):
     if stage.terminal:
      total=stage.mass or stage.counter
      for mass,counter,representative,images in stage.outcomes():
       q=(mass if stage.mass else counter)/total/F(len(images))
       for leaf,mapping in images:actual[id(leaf)]+=reach*q
      return
     self.assertEqual(sum(b.probability for b in stage.branches()),1)
     for branch in stage.branches():
      for named,leaves,mapping in branch.images:
       expand(NightStage(program,leaves,(*stage.prefix,named)),reach*branch.probability/F(len(branch.images)))
    expand(program.root,F(1))
    self.assertEqual(actual,{id(leaf):leaf.mass for leaf in program.leaves})
    self.assertTrue(any(len(a.images)>1 for b in program.root.branches() for r in b.state.branches() for a in r.state.branches()))
