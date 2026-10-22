import unittest,json
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree
from werewolf.navigation_current import NavigationCurrent
from werewolf.calculation_budget import calculation_budget
from werewolf.public_convergence import state_key,public_key,digest,legacy_digest,matches_digest,public_transport,transport_source
from werewolf.evaluation_branch import physical_board
from werewolf.seer_acquisition import normalize
from werewolf.public_relation_orbits import initial_orbits,initial_transport

class DayActionQuotientTests(unittest.TestCase):
 def data(self,n=7,mediums=1,hunters=0,seers=1,wolves=2):
  g=data(n,'random',wolves=wolves,seers=seers).to_game();g.update(mediums=mediums,hunters=hunters)
  if not seers:g['seer_mode']='';g.pop('seer_options',None)
  return BoardData.from_game(g)
 def test_seven_player_one_execution_one_night_and_exact_medium_results(self):
  with calculation_budget(1500000,max_seconds=120):
   doc=NavigationDocument(self.data());view=NavigationTree(doc);root_node=doc.game.node;original=type(root_node).action;calls=[]
   def action(node,target):
    if node is root_node:calls.append(target)
    return original(node,target)
   with patch.object(type(root_node),'action',action):root=view.read(expand=True)
   self.assertEqual(calls,[1]);self.assertEqual(root['village_win'],'8/35')
   self.assertEqual(len(root['actions']),1);choice=root['actions'][0]
   self.assertEqual(choice['targets'],list(range(1,8)));self.assertEqual(choice['multiplicity'],7);self.assertEqual(choice['policy_probability'],'1')
   self.assertEqual(len(choice['branches']),1);self.assertEqual(choice['branches'][0]['probability'],'1')
   night=choice['branches'][0]['node'];shown=view.read(night,True);stages=shown['night_stages']['branches']
   colors={b['value'][1]:F(b['probability']) for b in stages if b['kind']=='medium_result'}
   self.assertEqual(colors,{'black':F(2,7),'white':F(4,7)})
   self.assertEqual(sum(F(b['probability']) for b in stages if b['kind']=='ability_dead' and b['value']=='medium_result'),F(1,7))
   self.assertEqual(sum(F(b['probability']) for b in stages),1)
 def test_every_named_execution_has_the_same_full_transported_state(self):
  with calculation_budget(200000,max_seconds=15):
   doc=NavigationDocument(self.data());node=doc.game.node;before=node.read();canonical=None
   for target in range(1,8):
    child=node.action(target)[0].node.read();moved=transport_source(child,public_transport(before,child,node.groups))
    if canonical is None:canonical=state_key(moved)
    self.assertEqual(state_key(moved),canonical)
 def test_other_supported_role_mixes_use_constructed_initial_action_orbits(self):
  for n,m,h,s,w in [(4,0,1,0,1),(5,1,0,0,1),(5,1,0,1,1),(7,0,0,1,2),(8,1,0,1,2),(9,0,1,0,2)]:
   with self.subTest(n=n,m=m,h=h),calculation_budget(200000,max_seconds=15):
    doc=NavigationDocument(self.data(n,m,h,s,w));self.assertEqual(doc.game.node.action_orbits(),(tuple(range(1,n+1)),))
    target,names=doc.game.node.representative_action(n);self.assertEqual(target,1);self.assertEqual(names.display(1),n)
 def test_nonrepresentative_footer_choice_and_cold_history_remain_named(self):
  with calculation_budget(1500000,max_seconds=120):
   doc=NavigationDocument(self.data());view=NavigationTree(doc);view.read(expand=True);row=doc.game.action(6)
   self.assertEqual(row.selector['target'],1);self.assertEqual(row.selector['requested'],6);self.assertEqual(row.names.display(1),6)
   rendered=view.read(expand=True);branch=rendered['actions'][0]['branches'][0];self.assertEqual(branch['node'],view.current_key())
   shown=view.read(view.current_key());self.assertNotIn(6,shown['alive']);self.assertIn(1,shown['alive'])
   current=NavigationCurrent(doc.game);self.assertEqual(current.source.public.history[-1].target,6)
   self.assertEqual(doc.game.node.export_request().roles(),doc.game.node.read())
   restored=NavigationDocument.restore(json.loads(json.dumps(doc.export())));self.assertEqual(restored.game.export(),doc.game.export());self.assertEqual(NavigationCurrent(restored.game).source,current.source)
 def test_distribution_order_is_ignored_but_private_memories_are_not(self):
  with calculation_budget(200000,max_seconds=15):
   doc=NavigationDocument(self.data());s=doc.game.node.action(1)[0].node.read()
   shuffled=replace(s,public=replace(s.public,world_belief=tuple(reversed(s.public.world_belief))),physical=replace(s.physical,world_belief=tuple(reversed(s.physical.world_belief))))
   self.assertEqual(state_key(s),state_key(shuffled));self.assertEqual(public_key(s),public_key(shuffled));self.assertEqual(digest(s),digest(shuffled));self.assertTrue(matches_digest(shuffled,legacy_digest(shuffled)))
   a=s.private.hypotheses[0];b=next(h for h in s.private.hypotheses if h.roles==a.roles and h.acquisitions!=a.acquisitions)
   def part(h):
    law=replace(s.private,hypotheses=normalize((h,)))
    return replace(s,private=law,physical=physical_board(s.public,law,s.physical))
   self.assertNotEqual(state_key(part(a)),state_key(part(b)))
 def test_public_relations_and_timing_remain_distinct_for_medium_cast(self):
  from tests.test_public_relation_orbits import PublicRelationOrbitTests
  g=PublicRelationOrbitTests().game('random');g['mediums']=1
  self.assertEqual(initial_orbits(g),((1,2),(3,4),(5,)));self.assertEqual(initial_transport(g,1,2),(2,1,4,3,5))
  g['seer_inputs'][1]['color']='black';self.assertEqual(initial_orbits(g),tuple((p,) for p in range(1,6)))

 def test_old_literal_execution_journal_replays_and_binds_to_new_representative(self):
  with calculation_budget(300000,max_seconds=20):
   with patch('werewolf.public_relation_orbits.initial_orbits',return_value=((1,),(2,),(3,),(4,))):
    old=NavigationDocument(self.data(4,0,1,0,1));old.game.action(3)
   self.assertEqual(old.game.occurrence.selector['target'],3);saved=json.loads(json.dumps(old.export()));before=NavigationCurrent(old.game).source
   doc=NavigationDocument.restore(saved);self.assertEqual(doc.game.export(),old.game.export());self.assertEqual(NavigationCurrent(doc.game).source,before)
   view=NavigationTree(doc);shown=view.read(expand=True)
   branch=next(b for b in shown['actions'][0]['branches'] if not shown['items'][b['node']]['winner'])
   self.assertEqual(branch['node'],view.current_key());self.assertNotIn(3,shown['items'][branch['node']]['alive'])
 def test_forged_saved_action_transport_is_still_rejected(self):
  with calculation_budget(300000,max_seconds=20):
   doc=NavigationDocument(self.data(4,0,1,0,1));doc.game.action(3);saved=json.loads(json.dumps(doc.export()))
   # A different person's map describes neither the constructed representative
   # action nor a historical literal action under its unchanged parent map.
   def visit(value):
    if isinstance(value,dict):
     if (value.get('selector') or {}).get('kind')=='advance':value['names']=[2,1,3,4]
     for child in value.values():visit(child)
    elif isinstance(value,list):
     for child in value:visit(child)
   visit(saved)
   with self.assertRaises(ValueError):NavigationDocument.restore(saved)

 def test_private_root_selection_does_not_reuse_public_action_orbits(self):
  with calculation_budget(200000,max_seconds=15):
   node=NavigationDocument(self.data(5,0,0,1,1)).game.node
   h=node.read().private.hypotheses[0]
   chosen=node._select_physical('hypothesis',(h.roles,tuple((a.day,a.player,a.target,a.color) for a in h.acquisitions)))
   self.assertEqual(chosen.action_orbits(),tuple((p,) for p in range(1,6)))
   self.assertEqual(node.action_orbits(),((1,2,3,4,5),))
