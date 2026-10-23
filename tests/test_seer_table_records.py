import unittest
from fractions import Fraction as F
from unittest.mock import patch
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.actor_information import PersonalInformation
from werewolf.seer_intervention import SeerObserver
from werewolf.calculation_budget import calculation_budget
from werewolf.calculation_tree import CalculationTree
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.public_convergence import state_key

class SeerTableRecordTests(unittest.TestCase):
 def case(self,players=6):
  game=data(players,'random').to_game()
  game.update(claims=['seer',*['latent']*(players-1)],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
  c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  node=next(x.node for x in c.root.action(3) if not x.node.read().public.winner)
  acquisitions=tuple(a for a in node.read().private.hypotheses[0].acquisitions if a.player==1)
  _,node=node.personal(SeerObserver(1,acquisitions,2,4))
  return c,node
 def test_no_hunter_seer_recorded_projection_and_named_value(self):
  with calculation_budget(4000000,max_seconds=90):
   c,node=self.case();e=c._ClosedCalculation__engine;s=node.read()
   value=e.solve(*s,physical=s.physical)
   oracle=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False)
   self.assertEqual(value,oracle.solve(*s,physical=s.physical))
   g=e.evaluation_graph
   with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('projection reran transition')),patch.object(e,'solve',side_effect=AssertionError('projection solved')):
    program=g.personal_program(s,node.groups);projection=g.personal_projection(s,node.groups)
   self.assertIsNotNone(program);self.assertIsNotNone(projection)
   self.assertEqual(projection.value,value);self.assertEqual(sum(r.probability for r in projection.edges),1)
   from tests.test_personal_recorded_projection import PersonalRecordedProjectionTests
   for publish,rows in ((False,projection.arrivals),(True,projection.edges)):
    expected=PersonalRecordedProjectionTests().oracle(e,s,node.groups,publish)
    self.assertTrue({state_key(r.source):r.probability for r in rows}==expected,'named public event Q/P law differs')
   self.assertTrue(all(r.source.observer==s.observer for r in projection.edges))
   with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('Tree reran transition')),patch.object(e,'solve',side_effect=AssertionError('Tree solved')):
    shown=CalculationTree.from_node(node).read('0',True)
   self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')

 def document(self):
  from werewolf.navigation_store import NavigationDocument
  c,node=self.case();public=NavigationDocument(c.data);public.game.action(3)
  return public
 def test_Table_document_values_owned_history_and_cold_restore(self):
  import json
  from werewolf.seer_view_document import SeerViewDocument
  from werewolf.navigation_store import NavigationDocument
  with calculation_budget(4000000,max_seconds=90):
   public=self.document();before=public.export();inputs=[dict(day=1,target=2,color='white')]
   view=SeerViewDocument(public,public.game.current,[1],inputs)
   result=view.result();s=view.root.read();e=view.root._Node__calculation._ClosedCalculation__engine
   oracle=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False)
   for row in result['players']:
    if not row.get('final'):continue
    target=view.names.canonical(row['id'])
    selected=SeerViewDocument(public,public.game.current,[1],inputs,target=row['id']);child=selected.root.read()
    self.assertEqual(F(row['final']['village']),oracle.solve(*child,physical=child.physical))
    self.assertEqual(child.observer.target,target);self.assertIs(child.public_state,public.game.node.read().public_state)
   cold_public=NavigationDocument.restore(json.loads(json.dumps(public.export())))
   cold=SeerViewDocument.restore(cold_public,json.loads(json.dumps(view.export())))
   self.assertTrue(state_key(cold.root.read())==state_key(s),'cold seer evidence changed')
   self.assertEqual(cold.tree().snapshot,view.tree().snapshot);self.assertEqual(public.export(),before)
 def test_real_HTTP_seer_Table_and_scoped_Current_restore(self):
  import json
  from app import create_app
  from tempfile import TemporaryDirectory
  from werewolf.navigation_current import NavigationCurrent
  from werewolf.public_log import migrate
  with TemporaryDirectory() as directory,calculation_budget(4000000,max_seconds=90):
   public=self.document();before=public.export()
   app=create_app(dict(TESTING=True,SECRET_KEY='seer-table-test',PERSISTENT_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
   client=app.test_client();client.post('/start',data=dict(citizens='4',seers='1',wolves='1',day='random',night='random',fake_reports='random',win_cutoff='0'))
   app.extensions['navigation_store'].get=lambda *_:public
   current=NavigationCurrent(public.game);board_id=migrate(current.data.to_game())['board_id']
   r=client.post('/private-view',data=dict(revision=str(public.revision),board_id=board_id,payload=json.dumps(dict(role='seer',players=[1],results=[dict(day=1,target=2,color='white')]))))
   self.assertEqual(r.status_code,200);record=r.json['private_view'];self.assertEqual(record['role'],'seer')
   r=client.post('/private-navigation',json=dict(public_revision=public.revision,view=record,operation='tree',expand=True))
   self.assertEqual(r.status_code,200);self.assertEqual(r.json['evaluation_trace']['owner'],'evaluator')
   record=r.json['private_view'];public.private_views={}
   restored=client.post('/private-navigation',json=dict(public_revision=public.revision,view=record,operation='restore'))
   self.assertEqual(restored.status_code,200);self.assertIn('personal-navigation-seed',restored.json['html']);self.assertIn('占い師 1 の視点',restored.json['html'])
   self.assertEqual(public.export(),before)

 def test_display_bijection_maps_owner_acquisitions_and_intervention(self):
  from werewolf.seer_view_document import SeerViewDocument
  from werewolf.navigation_history import NameMap
  from werewolf.navigation_game import NavigationGame
  public=self.document();public.game=NavigationGame(public.game.node,names=NameMap((2,1,3,4,6,5)))
  view=SeerViewDocument(public,public.game.current,[2],[dict(day=1,target=1,color='white')],target=6)
  observer=view.root.read().observer
  self.assertEqual(observer.actor,1);self.assertEqual(observer.target,5)
  self.assertTrue(any(a.player==1 and a.target==2 for a in observer.acquisitions))
  self.assertEqual(view.export()['players'],[2]);self.assertEqual(view.export()['target'],6)

 def test_scalar_report_reduction_does_not_invent_private_continuations(self):
  c,node=self.case(5);s=node.read();e=c._ClosedCalculation__engine
  value=e.solve(*s,physical=s.physical);g=e.evaluation_graph
  self.assertEqual(value,F(1,3))
  self.assertIsNone(g.personal_program(s,node.groups))
  self.assertIsNone(g.personal_program(s,node.groups,evaluate=True))
