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

 def multi_document(self):
  from werewolf.navigation_store import NavigationDocument
  game=data(7,'random',wolves=2).to_game();game.update(claims=['seer',*['latent']*6],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
  public=NavigationDocument(BoardData.from_game(game));public.game.action(3);return public
 def test_multiwolf_Table_named_parity_shared_attack_and_view_isolation(self):
  from werewolf.wolf_view_document import WolfViewDocument
  from werewolf.root_secret_flow import RootSecretBranch,root_wolf_forecast
  from werewolf.navigation_store import NavigationDocument
  from werewolf.personal_navigation_http import key
  with calculation_budget(4000000,max_seconds=90):
   public=self.multi_document();before=public.export();views=[];snapshots=[]
   for incomplete in ([4],[4,4]):
    with self.assertRaises(ValueError):WolfViewDocument(public,public.game.current,incomplete,[])
   for pack in ((4,5),(4,6),(3,4)):
    view=WolfViewDocument(public,public.game.current,pack,[]);views.append(view)
    result=view.result();s=view.root.read();base=public.game.node.read();e=view.root._Node__calculation._ClosedCalculation__engine
    reverse=WolfViewDocument(public,public.game.current,list(reversed(pack)),[])
    self.assertTrue(state_key(reverse.root.read())==state_key(s),'pack click order changed owned state')
    self.assertEqual(key(reverse.export()),key(view.export()))
    expected=root_wolf_forecast(RootSecretBranch(base.public,base.public_state,base.physical,base.private,base.past),pack,(),e.rules,e.strategy)
    self.assertTrue(isinstance(expected,tuple),'existing evaluator rejected multiple-wolf pack')
    actual={p['id']:F(p['final']['village']) for p in result['players'] if p.get('final')}
    self.assertEqual(actual,dict(expected[0]));self.assertFalse(set(pack)&set(actual))
    self.assertTrue(all(h.roles[0]==sum(1<<(p-1) for p in pack) for h in s.private.hypotheses))
    self.assertIs(s.public_state,base.public_state)
    info=WolfInformation(s.observer.initial_roster,s.observer.attacks)
    policy=e.wolf_policy(s.public,s.public_state,s.past,info.initial_roster,info.attacks)
    self.assertEqual(dict(policy),{view.names.canonical(p):F(1,len(actual)) for p in actual})
    with e.group_scope(view.root.groups),view.root.relation_scope():e.evaluation_graph.personal_program(s,view.root.groups,evaluate=True)
    from tests.test_personal_recorded_projection import PersonalRecordedProjectionTests
    named=PersonalRecordedProjectionTests().oracle(e,s,view.root.groups,True)
    with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('multiwolf projection replayed')),patch.object(e,'solve',side_effect=AssertionError('multiwolf projection solved')),patch.object(e,'wolf_policy',side_effect=AssertionError('multiwolf policy reselected')):
     projection=e.evaluation_graph.personal_projection(s,view.root.groups)
     self.assertTrue({state_key(r.source):r.probability for r in projection.edges}==named,'multiwolf event Q/P law differs')
     shown=view.tree().read(view.tree().current_key(),True)
    snapshots.append(view.tree().snapshot)
    self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
    self.assertEqual(sum(r.probability for r in projection.edges),1)
    self.assertTrue(all(all(len(h.attacks)==1 for h in r.source.private.hypotheses) for r in projection.edges),'pack generated more than one attack')
    choice=next(k for k,r in shown['items'].items() if r.get('day_start') and len(r['alive'])==5)
    view.tree().select(choice);current=view.game.node.read()
    cold=WolfViewDocument.restore(NavigationDocument.restore(json.loads(json.dumps(public.export()))),json.loads(json.dumps(view.export())))
    self.assertTrue(state_key(cold.game.node.read())==state_key(current),'multiwolf Current/cold state differs')
   self.assertEqual(len(set(snapshots)),3)
   self.assertEqual(len({key(v.export()) for v in views}),3)
   self.assertEqual(public.export(),before)

 def test_multiple_fake_CO_joint_reporting_remains_unsupported(self):
  from werewolf.information_set_forecast import Pending
  game=data(7,'random',wolves=2).to_game();game.update(claims=['seer','seer','seer',*['latent']*4],seer_inputs=[dict(day=1,reporter=p,target=4,color='white') for p in (1,2,3)])
  c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  with self.assertRaises(Pending) as failure:c.root.forecast()
  self.assertEqual(failure.exception.reason,'multiple_fake_report_correlation_unselected')

 def test_multiwolf_noncanonical_execution_lifts_full_pack_and_cold_history(self):
  from werewolf.navigation_store import NavigationDocument
  from werewolf.wolf_view_document import WolfViewDocument
  from werewolf.navigation_current import NavigationCurrent
  with calculation_budget(4000000,max_seconds=90):
   game=data(7,'random',wolves=2).to_game();game.update(claims=['seer',*['latent']*6],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
   public=NavigationDocument(BoardData.from_game(game));public.game.action(7)
   view=WolfViewDocument(public,public.game.current,[3,4],[]);s=view.root.read()
   self.assertEqual(s.observer.initial_roster,sum(1<<(view.names.canonical(p)-1) for p in (3,4)))
   displayed=NavigationCurrent(view.game).source
   self.assertEqual(displayed.observer.initial_roster,(1<<2)|(1<<3))
   self.assertNotIn(7,displayed.public.alive);self.assertFalse({3,4}&set(view.targets()))
   shown=view.tree().read(view.tree().current_key(),True);self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
   self.assertTrue(all(p['physical_wolf_probability']=='1' for p in shown['players'] if p['player'] in (3,4)))
   cold=WolfViewDocument.restore(NavigationDocument.restore(json.loads(json.dumps(public.export()))),json.loads(json.dumps(view.export())))
   self.assertTrue(state_key(cold.root.read())==state_key(s),'selected representative changed pack in cold history')

 def hunter_document(self,repeat=True):
  from tests.test_hunter_evaluated_flow_record import HunterEvaluatedFlowRecordTests
  from werewolf.navigation_store import NavigationDocument
  c,node=HunterEvaluatedFlowRecordTests().case(repeat=repeat)
  public=NavigationDocument(c.data);public.game.action(3);return public
 def test_hunter_random_pack_values_joint_records_and_no_death(self):
  from werewolf.wolf_view_document import WolfViewDocument
  from werewolf.root_secret_flow import RootSecretBranch,root_wolf_forecast
  from tests.test_personal_recorded_projection import PersonalRecordedProjectionTests
  from werewolf.navigation_store import NavigationDocument
  with calculation_budget(4000000,max_seconds=90):
   for repeat in (True,False):
    public=self.hunter_document(repeat);before=public.export()
    view=WolfViewDocument(public,public.game.current,[4],[]);result=view.result();s=view.root.read()
    e=view.root._Node__calculation._ClosedCalculation__engine;g=e.evaluation_graph;base=public.game.node.read()
    expected=root_wolf_forecast(RootSecretBranch(base.public,base.public_state,base.physical,base.private,base.past),(4,),(),e.rules,e.strategy)
    self.assertTrue(isinstance(expected,tuple),'existing hunter/wolf evaluator rejected supported random input')
    self.assertEqual({p['id']:F(p['final']['village']) for p in result['players'] if p.get('final')},dict(expected[0]))
    for p in result['players']:
     if p.get('dawn'):self.assertEqual((F(p['dawn']['village']),F(p['dawn']['wolf'])),(expected[1][p['id']].village_win,expected[1][p['id']].wolf_win))
    with e.group_scope(view.root.groups),view.root.relation_scope():g.personal_program(s,view.root.groups,evaluate=True)
    named=PersonalRecordedProjectionTests().oracle(e,s,view.root.groups,True)
    with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('hunter wolf projection replayed')),patch.object(e,'solve',side_effect=AssertionError('hunter wolf projection solved')),patch.object(e,'wolf_policy',side_effect=AssertionError('hunter wolf policy reselected')):
     projection=g.personal_projection(s,view.root.groups)
     self.assertTrue({state_key(r.source):r.probability for r in projection.edges}==named,'hunter pack Q/P law differs')
     shown=view.tree().read(view.tree().current_key(),True)
    self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
    self.assertTrue(any(len(r.source.public.alive)==4 for r in projection.edges),'guard-success branch missing')
    self.assertTrue(any(len(r.source.public.alive)==3 for r in projection.edges),'death branch missing')
    self.assertTrue(all(h.guards or h.roles[3]&(1<<2) for r in projection.edges for h in r.source.private.hypotheses),'guard memory lost')
    chosen=next(k for k,r in shown['items'].items() if r.get('day_start') and len(r['alive'])==4)
    view.tree().select(chosen);current=view.game.node.read()
    cold=WolfViewDocument.restore(NavigationDocument.restore(json.loads(json.dumps(public.export()))),json.loads(json.dumps(view.export())))
    self.assertTrue(state_key(cold.game.node.read())==state_key(current),'guard-success pack Current/cold state differs')
    self.assertEqual(public.export(),before)

 def test_hunter_no_death_attack_input_retains_private_guard_correlation(self):
  from werewolf.wolf_view_document import WolfViewDocument
  from werewolf.navigation_tree import NavigationTree
  from werewolf.information_set_forecast import Pending
  with calculation_budget(4000000,max_seconds=90):
   public=self.hunter_document(False);tree=NavigationTree(public);shown=tree.read(tree.current_key(),True)
   choice=next(k for k,r in shown['items'].items() if r.get('day_arrival') and len(r['alive'])==4 and any(a['acquired_day']==2 and a['target']==4 and a['color']=='black' for a in r['reports']))
   tree.select(choice);public.game.action(2);before=public.export()
   with self.assertRaises(Pending) as missing:WolfViewDocument(public,public.game.current,[4],[])
   self.assertEqual(missing.exception.reason,'wolf_view_past_attack_history_unresolved')
   view=WolfViewDocument(public,public.game.current,[4],[dict(day=1,target=1,color=None)])
   s=view.root.read();self.assertEqual(s.observer.attacks,(WolfAttack(1,1),))
   self.assertTrue(all(h.attacks==(WolfAttack(1,1),) for h in s.private.hypotheses))
   self.assertTrue(all(any(g.night==1 and g.target==1 for g in h.guards) for h in s.private.hypotheses),'protected victim correlation lost')
   self.assertTrue(any(h.attacks!=(WolfAttack(1,1),) for h in s.public_state.hypotheses),'pack attack leaked into public Q')
   result=view.result();self.assertTrue(any(p.get('final') for p in result['players']))
   self.assertEqual(public.export(),before)

 def test_two_wolves_with_hunter_keep_shared_attack_and_exact_values(self):
  from werewolf.wolf_view_document import WolfViewDocument
  from werewolf.navigation_store import NavigationDocument
  from werewolf.root_secret_flow import RootSecretBranch,root_wolf_forecast
  with calculation_budget(4000000,max_seconds=90):
   game=data(5,'random',wolves=2).to_game();game['hunters']=1
   game.update(claims=['seer',*['latent']*4],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
   public=NavigationDocument(BoardData.from_game(game));public.game.action(3)
   for pack in ((3,4),(3,5)):
    view=WolfViewDocument(public,public.game.current,pack,[]);result=view.result();s=public.game.node.read();e=view.root._Node__calculation._ClosedCalculation__engine
    expected=root_wolf_forecast(RootSecretBranch(s.public,s.public_state,s.physical,s.private,s.past),pack,(),e.rules,e.strategy)
    self.assertTrue(isinstance(expected,tuple),'existing random hunter evaluator rejected known pack')
    self.assertEqual({p['id']:F(p['final']['village']) for p in result['players'] if p.get('final')},dict(expected[0]));self.assertFalse(set(pack)&set(view.targets()))
    shown=view.tree().read(view.tree().current_key(),True);self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
    graph=e.evaluation_graph;projection=graph.personal_projection(view.root.read(),view.root.groups)
    self.assertEqual(sum(r.probability for r in projection.edges),1)
    self.assertTrue(all(len(h.attacks)==1 for r in projection.edges for h in r.source.private.hypotheses),'pack produced independent attacks')

 def max_document(self):
  from werewolf.navigation_store import NavigationDocument
  game=data(6,'max').to_game();game.update(claims=['seer',*['latent']*5],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
  public=NavigationDocument(BoardData.from_game(game));public.game.action(3);return public
 def test_MAX_pack_records_selected_and_inspection_laws(self):
  from werewolf.wolf_view_document import WolfViewDocument
  from tests.test_max_seer_records import MaxSeerRecordTests
  from werewolf.information_set_forecast import InformationSetForecast
  with calculation_budget(4000000,max_seconds=90):
   public=self.max_document();policies={}
   for pack in ([4],[5]):
    view=WolfViewDocument(public,public.game.current,pack,[]);result=view.result();s=view.root.read();e=view.root._Node__calculation._ClosedCalculation__engine;g=e.evaluation_graph
    oracle=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False)
    self.assertIs(s.public_state,public.game.node.read().public_state)
    with e.group_scope(view.root.groups),view.root.relation_scope():
     self.assertEqual(e.solve(*s,physical=s.physical),oracle.solve(*s,physical=s.physical))
     record=g.personal_program(s,view.root.groups,evaluate=True)
    self.assertIsNotNone(record)
    self.assertEqual(sum(r.mass for r in record.program.leaves),1);self.assertEqual(sum(r.counter for r in record.program.leaves),1)
    self.assertTrue(any(r.mass==0 and r.counter>0 for r in record.program.leaves),'fixture lacks zero-policy inspected branch')
    for player in result['players']:
     if player.get('final'):self.assertEqual(F(player['final']['village']),oracle.act(*s[:3],view.names.canonical(player['id']),s.private,s.observer,physical=s.physical))
    expected={counter:MaxSeerRecordTests().named_night(e,s,view.root.groups,counter) for counter in (False,True)}
    with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('MAX pack projection replayed')),patch.object(e,'solve',side_effect=AssertionError('MAX pack projection solved')),patch.object(e,'wolf_policy',side_effect=AssertionError('MAX pack policy reselected')):
     for counter in (False,True):
      projection=g.personal_projection(s,view.root.groups,counter=counter)
      self.assertTrue({state_key(r.source):r.probability for r in projection.edges}==expected[counter],'MAX pack selected/inspection law differs')
     shown=view.tree().read(view.tree().current_key(),True);self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
    policies.update({k:v for k,v in e.policies.items() if k[:3]==(s.public,s.public_state,s.past)})
   self.assertEqual(policies,{k:v for k,v in e.policies.items() if k[:3]==(s.public,s.public_state,s.past)})

 def test_MAX_pack_Current_inspection_cold_and_public_day_policy(self):
  from werewolf.wolf_view_document import WolfViewDocument
  from werewolf.navigation_store import NavigationDocument
  from werewolf.calculation_tree import CalculationTree
  with calculation_budget(4000000,max_seconds=90):
   public=self.max_document();before=public.export();view=WolfViewDocument(public,public.game.current,[4],[]);view.result()
   tree=view.tree();shown=tree.read(tree.current_key(),True);self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
   self.assertTrue(any(r.get('counterfactual') for r in shown['items'].values()))
   raw,_=tree.view('h0');checked=0
   for key,row in tuple(raw.nodes.items()):
    if not row.get('public_bundle'):continue
    cold=CalculationTree.from_node(view.root);restored=cold.restore(raw.route(key))
    self.assertTrue(state_key(cold.nodes[restored]['node'].read())==state_key(row['node'].read()),'MAX pack selected/inspection cold state differs');checked+=1
   self.assertGreater(checked,1)
   target=next(k for k,r in shown['items'].items() if r.get('day_start') and not r.get('counterfactual'))
   tree.select(target);current=view.game.node.read();e=view.root._Node__calculation._ClosedCalculation__engine;g=e.evaluation_graph
   self.assertTrue(g.personal_max_scope(current.public,current))
   if not current.public.winner:
    decision=g.day_decision(current,evaluate=True);self.assertIsNotNone(decision)
    from dataclasses import replace
    self.assertEqual(decision,g.day_decision(replace(current,private=current.public_state,observer=None),evaluate=True))
   cold=WolfViewDocument.restore(NavigationDocument.restore(json.loads(json.dumps(public.export()))),json.loads(json.dumps(view.export())))
   self.assertTrue(state_key(cold.game.node.read())==state_key(current),'MAX pack Current/cold differs');self.assertEqual(public.export(),before)
 def test_MAX_full_original_pack_excludes_dead_and_live_teammates(self):
  from werewolf.wolf_view_document import WolfViewDocument
  from werewolf.navigation_store import NavigationDocument
  game=data(5,'max',wolves=2).to_game();game.update(claims=['seer',*['latent']*4],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
  with calculation_budget(4000000,max_seconds=90):
   public=NavigationDocument(BoardData.from_game(game));public.game.action(3)
   view=WolfViewDocument(public,public.game.current,[3,4],[]);result=view.result()
   self.assertFalse({3,4}&set(view.targets()));self.assertTrue(all(h.roles[0]==(1<<2)|(1<<3) for h in view.root.read().private.hypotheses))
   shown=view.tree().read(view.tree().current_key(),True);self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')

 def test_MAX_pack_prior_attack_and_mixed_policy_boundary(self):
  from werewolf.wolf_view_document import WolfViewDocument
  from werewolf.navigation_tree import NavigationTree
  with calculation_budget(4000000,max_seconds=90):
   public=self.max_document();tree=NavigationTree(public);shown=tree.read(tree.current_key(),True)
   choice=next(k for k,r in shown['items'].items() if r.get('day_arrival') and set(r['alive'])=={1,4,5,6} and any(a['acquired_day']==2 and a['target']==4 and a['color']=='black' for a in r['reports']))
   tree.select(choice);public.game.action(6)
   view=WolfViewDocument(public,public.game.current,[4],[dict(day=1,target=2,color=None)])
   self.assertEqual(view.root.read().observer.attacks,(WolfAttack(1,2),));view.result()
   self.assertTrue(all(h.attacks==(WolfAttack(1,2),) for h in view.root.read().private.hypotheses))
   with self.assertRaises(ValueError):WolfViewDocument(public,public.game.current,[4],[dict(day=1,target=1,color=None)])
   from types import SimpleNamespace
   e=view.root._Node__calculation._ClosedCalculation__engine;b=view.root.read().public
   from dataclasses import replace
   mixed=SimpleNamespace(strategy=replace(e.strategy,day='random'))
   self.assertFalse(WolfViewDocument.policy_scope(b,mixed))
