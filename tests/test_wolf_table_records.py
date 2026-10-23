import json,unittest
from fractions import Fraction as F
from unittest.mock import patch
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.actor_information import WolfInformation,WolfObserver,condition_personal
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.public_convergence import state_key
from werewolf.personal_convergence import transport_source
from werewolf.calculation_tree import CalculationTree
from werewolf.calculation_budget import calculation_budget
from werewolf.night_knowledge import WolfAttack

class WolfTableRecordTests(unittest.TestCase):
 def case(self):
  game=data(6,'random').to_game();game.update(claims=['seer',*['latent']*5],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
  c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  node=next(r.node for r in c.root.action(3) if not r.node.read().public.winner)
  return c,node
 def test_pack_observer_records_keep_Q_and_named_values_without_replay(self):
  with calculation_budget(4000000,max_seconds=90):
   c,public=self.case();_,node=public.personal(WolfObserver(1<<3));s=node.read();e=c._ClosedCalculation__engine;g=e.evaluation_graph
   self.assertIs(s.public_state,public.read().public_state)
   self.assertLess(s.public.role_probability(4,'wolf'),1)
   self.assertTrue(all(h.roles[0]==1<<3 for h in s.private.hypotheses))
   value=e.solve(*s,physical=s.physical)
   oracle=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True
   expected=oracle.evaluate(s.public,s.public_state,s.past,mask=1<<3,private_board=s.physical)
   self.assertEqual(value,sum(v for t,v in expected)/len(expected))
   for target,v in expected:self.assertEqual(e.act(*s[:3],target,s.private,s.observer,physical=s.physical),v)
   with e.group_scope(node.groups),node.relation_scope():g.personal_program(s,node.groups,evaluate=True)
   with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('wolf Tree reran transitions')),patch.object(e,'solve',side_effect=AssertionError('wolf Tree solved')),patch.object(e,'wolf_policy',side_effect=AssertionError('wolf Tree reselected')):
    projection=g.personal_projection(s,node.groups);shown=CalculationTree.from_node(node).read('0',True)
   self.assertIsNotNone(projection);self.assertEqual(sum(r.probability for r in projection.edges),1)
   from tests.test_personal_recorded_projection import PersonalRecordedProjectionTests
   expected_law=PersonalRecordedProjectionTests().oracle(e,s,node.groups,True)
   self.assertTrue({state_key(r.source):r.probability for r in projection.edges}==expected_law,'pack named event Q/P law differs')
   self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
   self.assertTrue(all(r.source.observer.initial_roster==1<<3 for r in projection.edges))
   self.assertTrue(all(h.attacks for r in projection.edges for h in r.source.private.hypotheses))
 def test_pack_transport_and_no_future_attack_knowledge(self):
  c,public=self.case();_,node=public.personal(WolfObserver(1<<3));source=node.read();mapping=(1,2,3,5,4,6)
  moved=transport_source(source,mapping);self.assertEqual(moved.observer.initial_roster,1<<4)
  self.assertTrue(state_key(transport_source(moved,mapping))==state_key(source))
  with self.assertRaises(ValueError):public.personal(WolfObserver(1<<3,(WolfAttack(1,1),)))
  _,legacy=public.personal(WolfInformation(1<<3));self.assertIsNone(legacy.read().observer)

 def document(self):
  from werewolf.navigation_store import NavigationDocument
  c,node=self.case();doc=NavigationDocument(c.data);doc.game.action(3);return doc
 def test_Table_pack_values_and_horizon_equal_existing_root_evaluator(self):
  from werewolf.wolf_view_document import WolfViewDocument
  from werewolf.root_secret_flow import RootSecretBranch,root_wolf_forecast
  from werewolf.navigation_store import NavigationDocument
  with calculation_budget(4000000,max_seconds=90):
   public=self.document();before=public.export();view=WolfViewDocument(public,public.game.current,[4],[]);result=view.result()
   s=public.game.node.read();e=view.root._Node__calculation._ClosedCalculation__engine
   expected=root_wolf_forecast(RootSecretBranch(s.public,s.public_state,s.physical,s.private,s.past),(4,),(),e.rules,e.strategy)
   self.assertTrue(isinstance(expected,tuple),'legacy root wolf path rejected supported input')
   values,dawn,belief=expected
   self.assertEqual({p['id']:F(p['final']['village']) for p in result['players'] if p.get('final')},dict(values))
   self.assertNotIn(4,view.targets());self.assertEqual(view.root.read().observer.initial_roster,1<<3)
   for p in result['players']:
    if p.get('dawn'):self.assertEqual((F(p['dawn']['village']),F(p['dawn']['wolf'])),(dawn[p['id']].village_win,dawn[p['id']].wolf_win))
   tree=view.tree();shown=tree.read(tree.current_key(),True);self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
   choice=next(k for k,r in shown['items'].items() if r.get('day_start') and len(r['alive'])==4 and 1 in r['alive'] and 4 in r['alive'])
   tree.select(choice);current=view.game.node.read();self.assertTrue(all(h.roles[0]==1<<3 and h.attacks for h in current.private.hypotheses))
   cold=WolfViewDocument.restore(NavigationDocument.restore(json.loads(json.dumps(public.export()))),json.loads(json.dumps(view.export())))
   self.assertTrue(state_key(cold.game.node.read())==state_key(current),'pack Current/cold state differs')
   self.assertEqual(public.export(),before)
 def test_real_HTTP_pack_Table_view_and_cold_restore(self):
  from app import create_app
  from tempfile import TemporaryDirectory
  from werewolf.navigation_current import NavigationCurrent
  from werewolf.public_log import migrate
  with TemporaryDirectory() as directory,calculation_budget(4000000,max_seconds=90):
   public=self.document();before=public.export()
   app=create_app(dict(TESTING=True,SECRET_KEY='wolf-record-test',PERSISTENT_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
   client=app.test_client();client.post('/start',data=dict(citizens='4',seers='1',wolves='1',day='random',night='random',fake_reports='random',win_cutoff='0'))
   app.extensions['navigation_store'].get=lambda *_:public
   board_id=migrate(NavigationCurrent(public.game).data.to_game())['board_id']
   r=client.post('/private-view',data=dict(revision=str(public.revision),board_id=board_id,payload=json.dumps(dict(role='wolf',players=[4],results=[]))))
   self.assertEqual(r.status_code,200);self.assertEqual(r.json['private_view']['role'],'wolf');self.assertFalse(next(p for p in r.json['players'] if p['id']==4)['legal'])
   tree=client.post('/private-navigation',json=dict(public_revision=public.revision,view=r.json['private_view'],operation='tree',expand=True))
   self.assertEqual(tree.status_code,200);self.assertEqual(tree.json['evaluation_trace']['owner'],'evaluator')
   public.private_views={}
   restored=client.post('/private-navigation',json=dict(public_revision=public.revision,view=tree.json['private_view'],operation='restore'))
   self.assertEqual(restored.status_code,200);self.assertIn('人狼 4 の視点',restored.json['html']);self.assertEqual(public.export(),before)
 def test_pack_members_are_joint_knowledge_not_independent_roles(self):
  from werewolf.exact import legal_targets
  game=data(7,'random',wolves=2).to_game();game.update(claims=['seer',*['latent']*6],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
  c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_reports=True,anonymous=True)
  public=next(r.node for r in c.root.action(3) if not r.node.read().public.winner)
  _,node=public.personal(WolfObserver((1<<3)|(1<<4)));s=node.read();e=c._ClosedCalculation__engine
  self.assertTrue(all(h.roles[0]==(1<<3)|(1<<4) for h in s.private.hypotheses))
  self.assertFalse({4,5}&set(legal_targets(s.physical,e.rules,e.strategy)))
  mapping=(1,2,3,6,7,4,5);moved=transport_source(s,mapping)
  self.assertEqual(moved.observer.initial_roster,(1<<5)|(1<<6))
  self.assertTrue(state_key(transport_source(moved,(1,2,3,6,7,4,5)))==state_key(s))

 def test_past_pack_attack_input_matches_generated_history(self):
  from werewolf.wolf_view_document import WolfViewDocument
  from werewolf.navigation_tree import NavigationTree
  with calculation_budget(4000000,max_seconds=90):
   public=self.document();tree=NavigationTree(public);shown=tree.read(tree.current_key(),True)
   choice=next(k for k,r in shown['items'].items() if r.get('day_arrival') and set(r['alive'])=={1,4,5,6} and any(a['acquired_day']==2 and a['target']==4 and a['color']=='black' for a in r['reports']))
   tree.select(choice);public.game.action(6)
   view=WolfViewDocument(public,public.game.current,[4],[dict(day=1,target=2,color=None)])
   self.assertEqual(view.root.read().observer.attacks,(WolfAttack(1,2),))
   moved=transport_source(view.root.read(),(2,1,3,4,5,6));self.assertEqual(moved.observer.attacks,(WolfAttack(1,1),))
   self.assertTrue(state_key(transport_source(moved,(2,1,3,4,5,6)))==state_key(view.root.read()),'pack attack transport roundtrip differs')
   self.assertTrue(all(h.attacks==(WolfAttack(1,2),) for h in view.root.read().private.hypotheses))
   without=WolfViewDocument(public,public.game.current,[4],[])
   self.assertTrue(state_key(without.root.read())==state_key(view.root.read()),'observed corpse did not retain unique pack attack')
   with self.assertRaises(ValueError):WolfViewDocument(public,public.game.current,[4],[dict(day=1,target=1,color=None)])
