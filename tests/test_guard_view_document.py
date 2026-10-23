import json,unittest
from copy import deepcopy
from fractions import Fraction as F
from dataclasses import replace
from tests import test_hunter_evaluated_flow_record as fixture
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree
from werewolf.navigation_current import NavigationCurrent
from werewolf.guard_view_document import GuardViewDocument
from werewolf.actor_information import GuardInformation,GuardSelection
from werewolf.guard_effect import GuardIntent
from werewolf.guard_view_forecast import guard_forecast
from werewolf.root_secret_flow import RootSecretEngine
from werewolf.exact import replace_worlds
from werewolf.seer_future_uniform import FuturePending
from werewolf.public_convergence import state_key
from werewolf.personal_convergence import transport_source
from werewolf.calculation_budget import calculation_budget

class GuardViewDocumentTests(unittest.TestCase):
 def public(self,repeat=True):
  c,n=fixture.HunterEvaluatedFlowRecordTests().case(repeat=repeat)
  doc=NavigationDocument(c.data);doc.game.action(3);return doc
 def oracle(self,view):
  s=view.root.read();e=view.root._Node__calculation._ClosedCalculation__engine
  result=guard_forecast(s.public,s.observer.actor,replace_worlds(s.public,view.belief.public_roles),s.public_state,s.past,e.rules,e.strategy,guards=s.observer.guards,private_state=s.private,engine_factory=RootSecretEngine,max_work=4000000,max_seconds=75)
  self.assertNotIsInstance(result,FuturePending);return result
 def test_Table_guard_inputs_use_exact_owned_Node_and_old_semantics(self):
  for repeat in (True,False):
   with self.subTest(repeat=repeat),calculation_budget(4000000,max_seconds=75):
    public=self.public(repeat);before=deepcopy(public.export())
    view=GuardViewDocument(public,public.game.current,[4],[]);result=view.result();values,dawn=self.oracle(view)
    actual={p['id']:F(p['final']['village']) for p in result['players'] if p.get('final')}
    expected={view.names.display(p):q for p,q in values.items()};self.assertEqual(actual,expected)
    for p in result['players']:
     if p.get('dawn'):
      h=dawn[view.names.canonical(p['id'])];self.assertEqual((F(p['dawn']['village']),F(p['dawn']['wolf'])),(h.village_win,h.wolf_win))
    self.assertEqual(public.export(),before)
    self.assertIs(view.root.read().public_state,public.game.node.read().public_state)
    self.assertTrue(all(h.roles[3]&(1<<3) for h in view.root.read().private.hypotheses))
    for target in view.targets():
     selected=GuardViewDocument(public,public.game.current,[4],[],target=target)
     e=selected.root._Node__calculation._ClosedCalculation__engine;s=selected.root.read();value=e.solve(*s,physical=s.physical)
     self.assertEqual(value,expected[target]);record=e.evaluation_graph.personal_program(s,selected.root.groups)
     if record is not None:
      for leaf in record.program.leaves:
       for h in leaf.source.private.hypotheses:self.assertIn(GuardIntent(1,4,target),h.guards)
 def later(self,repeat):
  public=self.public(repeat);tree=NavigationTree(public);shown=tree.read(tree.current_key(),True)
  chosen=next(k for k,r in shown['items'].items() if r.get('day_arrival') and len(r['alive'])==4 and any(x['player']==1 and x['acquired_day']==2 and x['target']==4 and x['color']=='white' for x in r['reports']))
  tree.select(chosen);public.game.action(2);return public
 def test_past_guard_repetition_and_saved_view_rebuild_from_public_history(self):
  for repeat in (True,False):
   with self.subTest(repeat=repeat),calculation_budget(4000000,max_seconds=75):
    public=self.later(repeat);before=deepcopy(public.export())
    inputs=[dict(day=1,target=1,color=None)]
    view=GuardViewDocument(public,public.game.current,[4],inputs)
    self.assertEqual(set(view.targets()),{1,5} if repeat else {5})
    result=view.result();values,dawn=self.oracle(view)
    actual={p['id']:F(p['final']['village']) for p in result['players'] if p.get('final')}
    self.assertEqual(actual,{view.names.display(p):q for p,q in values.items()})
    cold_public=NavigationDocument.restore(json.loads(json.dumps(public.export())))
    cold=GuardViewDocument.restore(cold_public,json.loads(json.dumps(view.export())))
    self.assertTrue(state_key(cold.root.read())==state_key(view.root.read()),'cold guard knowledge/P differs')
    self.assertEqual(cold.tree().snapshot,view.tree().snapshot);self.assertEqual(public.export(),before)
    with self.assertRaises(ValueError):GuardViewDocument(public,public.game.current,[4],[dict(day=1,target=4,color=None)])
    if not repeat:
     with self.assertRaises(ValueError):GuardViewDocument(public,public.game.current,[4],inputs,target=1)
 def test_guard_bijection_and_documents_do_not_accept_posterior_or_weight(self):
  with calculation_budget(4000000,max_seconds=75):
   public=self.public();view=GuardViewDocument(public,public.game.current,[4],[],target=2);s=view.root.read();mapping=(1,2,3,5,4)
   moved=transport_source(s,mapping);self.assertEqual(moved.observer.actor,5);self.assertEqual(moved.observer.target,2)
   self.assertTrue(state_key(transport_source(moved,mapping))==state_key(s))
   saved=view.export();saved['posterior']=[]
   with self.assertRaises(ValueError):GuardViewDocument.restore(public,saved)
   saved=view.export();saved['history']['rows'][0]['selection_weight']='0'
   with self.assertRaises(ValueError):GuardViewDocument.restore(public,saved)

class GuardViewHttpTests(unittest.TestCase):
 def test_real_private_endpoint_uses_Current_owner_and_preserves_public_document(self):
  from app import create_app
  from tempfile import TemporaryDirectory
  from unittest.mock import patch
  from werewolf.navigation_current import NavigationCurrent
  with TemporaryDirectory() as directory:
   public=GuardViewDocumentTests().public();public.revision=7
   app=create_app(dict(TESTING=True,SECRET_KEY='guard-http-tests',PERSISTENT_TREE_PREVIEW=True,DAWN_BOARD_PREVIEW=False,HYBRID_TABLE_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
   client=app.test_client()
   started=client.post('/start',data=dict(citizens='2',seers='1',hunters='1',wolves='1',day='random',night='random',win_cutoff='0'))
   self.assertEqual(started.status_code,303)
   state=NavigationCurrent(public.game).data.updated(revision=7).to_game()
   from werewolf.public_log import migrate
   form=dict(revision='7',board_id=migrate(state)['board_id'],payload=json.dumps(dict(role='hunter',players=[4],results=[])))
   before=deepcopy(public.export())
   with patch.object(app.extensions['navigation_store'],'get',return_value=public):
    stale=client.post('/private-view',data={**form,'revision':'6'});self.assertEqual(stale.status_code,409)
    response=client.post('/private-view',data=form)
    self.assertEqual(response.status_code,200,response.get_data(as_text=True)[:500])
    result=response.get_json();self.assertEqual(result['revision'],7)
    restored=GuardViewDocument.restore(public,result['private_view'])
    self.assertTrue(state_key(restored.root.read())==state_key(GuardViewDocument(public,public.game.current,[4],[]).root.read()))
    streamed=client.post('/private-view',data=form,headers={'Accept':'application/x-ndjson'})
    self.assertEqual(streamed.status_code,200)
    events=[json.loads(line) for line in streamed.get_data(as_text=True).splitlines() if line]
    completed=next(row for row in events if row.get('event')=='complete')
    self.assertEqual(completed['players'],result['players'])
    record=result['private_view']
    def nav(operation='tree',**extra):
     response=client.post('/private-navigation',json=dict(operation=operation,view=record,public_revision=7,**extra))
     self.assertEqual(response.status_code,200,response.get_data(as_text=True)[:500]);return response.get_json()
    shown=nav(expand=True);self.assertIn('evaluation_trace',shown)
    arrival=next(row for row in shown['items'].values() if row.get('day_start') and len(row['alive'])==4)
    stale_record=deepcopy(record)
    invalid=client.post('/private-navigation',json=dict(operation='current',view=record,public_revision=7,node='missing~0',snapshot=shown['snapshot']))
    self.assertEqual(invalid.status_code,400)
    moved=nav('current',node=arrival['node'],snapshot=shown['snapshot']);record=moved['private_view']
    stale=client.post('/private-navigation',json=dict(operation='tree',view=stale_record,public_revision=7))
    self.assertEqual(stale.status_code,409)
    other=client.post('/private-navigation',json=dict(operation='tree',view=record,public_revision=6))
    self.assertEqual(other.status_code,409)
    self.assertIn('personal-navigation-seed',moved['html']);self.assertIn('data-personal-scope',moved['html'])
    cold=GuardViewDocument.restore(public,record)
    self.assertEqual(cold.game.current,record['history']['current'])
    # Forget the server cache: restore user inputs/selectors, not solved posteriors.
    public.private_views={}
    restored=nav('restore');record=restored['private_view']
    backed=nav('back');record=backed['private_view']
    forwarded=nav('forward');record=forwarded['private_view']
    self.assertEqual(forwarded['current_node'],moved['current_node'])
    normal=nav('public');self.assertIsNone(normal['private_view'])

   self.assertEqual(public.export(),before)

 def test_missing_past_guard_stream_is_explicit_pending_then_edit_recovers(self):
  from app import create_app
  from tempfile import TemporaryDirectory
  from unittest.mock import patch
  from werewolf.public_log import migrate
  with TemporaryDirectory() as directory:
   public=GuardViewDocumentTests().later(False)
   app=create_app(dict(TESTING=True,SECRET_KEY='guard-pending',PERSISTENT_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
   client=app.test_client();client.post('/start',data=dict(citizens='2',seers='1',hunters='1',wolves='1',day='random',night='random',win_cutoff='0'))
   state=NavigationCurrent(public.game).data.to_game();form=dict(revision='0',board_id=migrate(state)['board_id'])
   def submit(results,stream=False):
    return client.post('/private-view',data={**form,'payload':json.dumps(dict(role='hunter',players=[4],results=results))},headers={'Accept':'application/x-ndjson'} if stream else {})
   with patch.object(app.extensions['navigation_store'],'get',return_value=public):
    response=submit([],True);events=[json.loads(line) for line in response.get_data(as_text=True).splitlines() if line]
    self.assertTrue(any(e.get('event')=='error' and e.get('error')=='guard_view_target_generation_support_unresolved' for e in events))
    self.assertEqual(submit([]).status_code,422)
    recovered=submit([dict(day=1,target=1,color=None)],True)
    events=[json.loads(line) for line in recovered.get_data(as_text=True).splitlines() if line]
    self.assertTrue(any(e.get('event')=='complete' and e.get('private_view') for e in events))
