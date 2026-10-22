import unittest,tempfile,json
from fractions import Fraction as F
from app import create_app
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree
from tests import test_manual_public_input as fixtures

class NavigationTreeTests(unittest.TestCase):
 def test_root_persists_and_manual_edge_does_not_change_original_expectation(self):
  doc=NavigationDocument(fixtures.ManualPublicInputTests().root().data);view=NavigationTree(doc)
  root=view.read(expand=True);before=root['village_win'];doc.game.public_input(('seer','latent','latent','latent','latent'),())
  current=view.current_key();after=view.read(expand=True)
  self.assertEqual(after['node'],root['node']);self.assertEqual(after['village_win'],before)
  self.assertEqual(after['manual_updates'],[dict(node=current,probability='0')])
  self.assertIn(current,after['items']);self.assertEqual(after['items'][current]['navigation_depth'],1)
 def test_footer_concrete_choice_is_preserved_in_tree_and_current(self):
  doc=NavigationDocument(fixtures.ManualPublicInputTests().root().data);view=NavigationTree(doc)
  before=view.read(expand=True);doc.game.action(3);after=view.read(expand=True)
  self.assertEqual(after['actions'][0]['representative'],3)
  target=view.current_key();self.assertTrue(any(b['node']==target for a in after['actions'] for b in a['branches']))
  shown=view.read(target,True);self.assertNotIn(3,shown['alive']);self.assertIn(1,shown['alive'])
  self.assertEqual(F(shown['village_win']),doc.game.node.forecast().village_win)
 def test_tree_current_cold_replay_and_back_path(self):
  doc=NavigationDocument(fixtures.ManualPublicInputTests().root().data);view=NavigationTree(doc);root=view.read(expand=True)
  child=next(b['node'] for a in root['actions'] for b in a['branches'] if not root['items'][b['node']]['winner'])
  view.select(child);self.assertNotEqual(doc.game.current,'h0');record=doc.export()
  cold=NavigationDocument.restore(json.loads(json.dumps(record)))
  self.assertEqual(cold.game.node.read(),doc.game.node.read());self.assertEqual(cold.game.export(),doc.game.export())
  self.assertEqual(doc.game.back().key,'h0')

 def test_supported_existing_history_keeps_day1_root_and_exact_saved_current(self):
  from tests.test_public_relation_orbits import PublicRelationOrbitTests
  from werewolf.board_flow import BoardData
  from werewolf.closed_calculation import ClosedCalculation
  game=PublicRelationOrbitTests().game('random');game['result_disclosure_model']='full-observed-v1'
  step={key:game[key] for key in ('policy','claims','claim_policy','seer_options','result_disclosure_model')};step['target']=1
  game['history']=[step];data=BoardData.from_game(game)
  expected=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True).root.read()
  doc=NavigationDocument(data);self.assertEqual(doc.game.node.read(),expected)
  root=doc.game.history.state(doc.game.history.root).source.public
  self.assertEqual((root.day,root.phase,len(root.history)),(1,'day',0))
  cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())));self.assertEqual(cold.game.node.read(),expected)
  doc.game.back();self.assertEqual(len(doc.game.node.read().public.history),0)

 def test_every_outcome_uses_same_chosen_representative_including_terminal(self):
  doc=NavigationDocument(fixtures.ManualPublicInputTests().root().data);view=NavigationTree(doc)
  view.read(expand=True);doc.game.action(3);after=view.read(expand=True)
  terminal=next(b['node'] for a in after['actions'] for b in a['branches'] if F(b['probability'])==F(1,5))
  shown=view.read(terminal);self.assertNotIn(3,shown['alive']);self.assertIn(1,shown['alive'])
  view.select(terminal);self.assertEqual(doc.game.occurrence.names.display(1),3)
  from werewolf.navigation_current import NavigationCurrent
  self.assertTrue(NavigationCurrent(doc.game).roles.progress.finished)
  cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
  self.assertEqual(cold.game.export(),doc.game.export())
 def test_public_day2_current_records_each_day1_phase_and_preserves_distribution(self):
  doc=NavigationDocument(fixtures.ManualPublicInputTests().root().data);view=NavigationTree(doc)
  root=view.read(expand=True)
  night=next(b['node'] for a in root['actions'] for b in a['branches'] if F(b['probability'])==F(4,5))
  result=view.read(night,True)
  day2=next(key for key,item in result['items'].items() if item.get('public_bundle') and item['day']==2 and not item['winner'])
  before=view.read(day2,analysis=True)['distribution']
  view.select(day2);self.assertEqual(view.read(view.current_key(),analysis=True)['distribution'],before)
  self.assertTrue(view.read(view.current_key())['public_bundle'])
  path=doc.game.history.path(doc.game.current)
  self.assertEqual([(doc.game.history.state(r.key).source.public.day,doc.game.history.state(r.key).source.public.phase) for r in path],[(1,'day'),(1,'night'),(2,'day')])
  cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())));self.assertEqual(cold.game.node.read(),doc.game.node.read())
  self.assertEqual(doc.game.back().key,path[-2].key)

 def test_simultaneous_manual_CO_retains_coupled_action_orbits_and_transport(self):
  from werewolf.seer_acquisition import SeerReport
  from werewolf.public_convergence import transport_source
  doc=NavigationDocument(fixtures.ManualPublicInputTests().root().data)
  doc.game.public_input(('seer','seer','latent','latent','latent'),(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,4,'white')))
  view=NavigationTree(doc);shown=view.read(view.current_key(),True)
  self.assertEqual([a['targets'] for a in shown['actions']],[[1,2],[3,4],[5]])
  before=doc.game.node;direct=before.action(2)
  row=doc.game.action(2,outcome=0)
  self.assertEqual(row.names.forward,(2,1,4,3,5))
  self.assertEqual(transport_source(doc.game.node.read(),row.names.forward),direct[0].node.read())

 def test_report_before_and_after_are_both_public_current_with_owned_sources(self):
  from tests.test_joint_action_kernel import fixture
  calculation,_,_=fixture('random');doc=NavigationDocument(calculation.data);view=NavigationTree(doc)
  root=view.read(view.current_key(),expand=True);action=next(a for a in root['actions'] if 3 in a['targets'])
  night=next(b['node'] for b in action['branches'] if not root['items'][b['node']]['winner'])
  result=view.read(night,True)
  start=next(k for k,d in result['items'].items() if d.get('day_start') and d.get('public_updates'))
  view.select(start);self.assertTrue(view.read(view.current_key())['public_updates'])
  self.assertFalse(any(r.acquired_day==2 for r in doc.game.node.read().past))
  self.assertEqual(doc.game.node.export_request().roles(),doc.game.node.read())
  current=view.read(view.current_key())
  from werewolf.navigation_current import NavigationCurrent
  if len(current['public_updates'])==1:self.assertIsNotNone(NavigationCurrent(doc.game).automatic_update())
  after=current['public_updates'][0]['node']
  view.select(after);self.assertTrue(any(r.acquired_day==2 for r in doc.game.node.read().past) or 1 not in doc.game.node.read().public.alive)
  cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())));self.assertEqual(cold.game.node.read(),doc.game.node.read())
  self.assertTrue(any(r.selector.get('kind')=='generated' and any(isinstance(s,dict) and 'public_arrival' in s for s in r.selector['route']) for r in doc.game.history.path(doc.game.current)[1:]))

 def test_recorded_initial_updates_are_editable_input_snapshots_not_likelihood_edges(self):
  from tests.test_tree_public_updates import TreePublicUpdateTests
  data=TreePublicUpdateTests().data(separate=True);doc=NavigationDocument(data);view=NavigationTree(doc)
  rows=doc.game.history.path(doc.game.current);self.assertEqual(len(rows),3)
  self.assertEqual(doc.game.history.state('h0').source.public.claims,('latent',)*5)
  self.assertEqual(doc.game.history.state('h1').source.public.role_probability(1,'wolf'),0)
  self.assertEqual(doc.game.node.read().public.role_probability(1,'wolf'),F(1,2))
  root=view.read(expand=True);self.assertIsNone(root['manual_updates'][0]['probability'])
  first=view.read('h1~0');self.assertTrue(first['public_current']);self.assertIsNone(first['manual_updates'][0]['probability'])
  cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())));self.assertEqual(cold.game.node.read(),doc.game.node.read())
  self.assertEqual(cold.game.export(),doc.game.export())

 def test_update_column_depth_is_local_to_its_phase_not_all_future_boards(self):
  from werewolf.seer_acquisition import SeerReport
  doc=NavigationDocument(fixtures.ManualPublicInputTests().root().data)
  doc.game.public_input(('seer','latent','latent','latent','latent'),(SeerReport(1,1,1,3,'white'),))
  view=NavigationTree(doc);result=view.read(view.current_key(),True)
  self.assertEqual(result['navigation_depth'],1)
  for item in result['items'].values():
   if item['column_phase']=='night':self.assertEqual(item['navigation_depth'],0)

class NavigationIntegratedHttpTests(unittest.TestCase):
 def setUp(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
  self.app=create_app(dict(TESTING=True,SECRET_KEY='navigation-integrated',GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=temp.name))
  self.client=self.app.test_client();self.client.post('/start',data=dict(citizens='3',wolves='1',seers='1',day='max',night='max',fake_reports='max'))
 def test_normal_main_footer_and_CO_preview_publish_use_same_owner(self):
  page=self.client.get('/main');self.assertEqual(page.status_code,200)
  self.assertIn(b'data-navigation-occurrence="h0"',page.data);self.assertNotIn(b'generated-current-fields',page.data)
  root=self.client.get('/game-tree?expand=1');self.assertEqual(root.status_code,200)
  payload=dict(claims=['seer','latent','latent','latent','latent'],seers=[dict(day=1,reporter=1,target=3,color='white')],mediums=[])
  preview=self.client.post('/table-preview',data=dict(revision='0',payload=json.dumps(payload),request_id='1'))
  self.assertEqual(preview.status_code,200,preview.json);self.assertEqual(self.client.get('/navigation').json['current']['occurrence'],'h0')
  changed=self.client.post('/table-publish',data=dict(revision='0',payload=json.dumps(payload)))
  self.assertEqual(changed.status_code,200,changed.json);self.assertEqual(changed.json['collapse_owner'],'h0~0')
  self.assertIn('data-navigation-occurrence="h1"',changed.json['html'])
  advance=self.client.post('/navigation/advance',json=dict(revision=1,target=3));self.assertEqual(advance.status_code,200,advance.json)
  self.assertIn('data-navigation-occurrence="h2"',advance.json['html'])
  after=self.client.get('/game-tree?expand=1').json
  self.assertEqual(after['node'],root.json['node']);self.assertEqual(after['village_win'],root.json['village_win'])
 def test_tree_current_button_moves_public_cursor_without_readonly_projection(self):
  root=self.client.get('/game-tree?expand=1').json
  child=next(b['node'] for a in root['actions'] for b in a['branches'] if not root['items'][b['node']]['winner'])
  moved=self.client.post('/game-tree/current',data=dict(snapshot=root['snapshot'],node=child,revision=0))
  self.assertEqual(moved.status_code,200,moved.json)
  self.assertIn('data-navigation-occurrence=',moved.json['html']);self.assertNotIn('generated-current-fields',moved.json['html'])
  self.assertIn('id="advance-button"',moved.json['html'])

 def test_incomplete_CO_is_editable_pending_then_report_can_complete(self):
  payload=dict(claims=['seer','latent','latent','latent','latent'],seers=[],mediums=[])
  changed=self.client.post('/table-publish',data=dict(revision='0',payload=json.dumps(payload)))
  self.assertEqual(changed.status_code,200,changed.json)
  tree=self.client.get('/game-tree?expand=1');self.assertEqual(tree.status_code,200,tree.json)
  current=tree.json['current_node'];self.assertTrue(tree.json['items'][current]['pending'])
  payload['seers']=[dict(day=1,reporter=1,target=3,color='white')]
  fixed=self.client.post('/table-publish',data=dict(revision='1',payload=json.dumps(payload)))
  self.assertEqual(fixed.status_code,200,fixed.json)
  self.assertIsNone(self.client.get('/navigation').json['pending'])

 def test_unsupported_saved_MAX_history_retains_original_board_and_input(self):
  from tests.test_public_relation_orbits import PublicRelationOrbitTests
  from copy import deepcopy
  game=PublicRelationOrbitTests().game();game['result_disclosure_model']='full-observed-v1'
  step={key:deepcopy(game[key]) for key in ('policy','claims','claim_policy','seer_options','result_disclosure_model')};step['target']=1
  game['history']=[step]
  with self.client.session_transaction() as ss:ss['game']=game
  page=self.client.get('/main');self.assertEqual(page.status_code,200)
  self.assertIn('saved_action_uniform_H0_only',page.get_data(as_text=True));self.assertNotIn('data-navigation-occurrence=',page.get_data(as_text=True))
  with self.client.session_transaction() as ss:self.assertEqual(ss['game']['history'],game['history']);self.assertEqual(ss['game']['claims'],game['claims'])
  self.assertEqual(self.client.get('/navigation').status_code,422)

 def test_duplicate_concurrent_CO_publish_commits_once(self):
  from concurrent.futures import ThreadPoolExecutor
  from copy import deepcopy
  with self.client.session_transaction() as session:base=deepcopy(dict(session))
  payload=dict(claims=['seer','latent','latent','latent','latent'],seers=[dict(day=1,reporter=1,target=3,color='white')],mediums=[])
  def publish():
   with self.app.test_client() as client:
    with client.session_transaction() as session:session.update(deepcopy(base))
    return client.post('/table-publish',data=dict(revision='0',payload=json.dumps(payload))).status_code
  with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(lambda _:publish(),range(2)))
  self.assertEqual(sorted(statuses),[200,409])
  self.assertEqual(len(self.client.get('/navigation').json['occurrences']),2)
