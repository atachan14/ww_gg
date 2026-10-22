import unittest,json,tempfile,html
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from concurrent.futures import ThreadPoolExecutor
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.navigation_current import NavigationCurrent
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree
from werewolf.manual_public_input import PublicInput,condition_input,ContradictoryPublicInput,UnsupportedPublicInput
from werewolf.seer_acquisition import SeerReport,normalize
from werewolf.public_convergence import transport_source
from werewolf.exact import Rules,Strategy,ClaimPolicy,initial_board
from tests import test_manual_public_input as fixtures

class DelayedCOTests(unittest.TestCase):
 def doc(self):
  doc=NavigationDocument(fixtures.ManualPublicInputTests().root().data);doc.game.action(3);doc.game.action(4);return doc
 def evidence(self,target=4,color='white'):
  return (SeerReport(1,2,1,3,'white'),SeerReport(2,2,1,target,color))
 def test_exact_private_histories_late_reports_and_independent_named_values(self):
  doc=self.doc();parent=doc.game.current;source=doc.game.node.read();value=doc.game.node.forecast();names=doc.game.occurrence.names
  actual=transport_source(source,names.forward);claims=('seer',)+('latent',)*4
  row=doc.game.public_input(claims,self.evidence());after=transport_source(doc.game.node.read(),row.names.forward)
  self.assertEqual([(r.acquired_day,r.published_day) for r in after.past],[(1,2),(2,2)])
  # Independent support filter: a fake sole CO is possible if the true seer is dead.
  for before,law in [(actual.public_state,after.public_state),(actual.private,after.private)]:
   kept=[]
   for h in before.hypotheses:
    records={(a.day,a.player):(a.target,a.color) for a in h.acquisitions}
    true=bool(h.roles[2]&1);dead_seer=not(h.roles[2]&actual.public.alive_mask)
    if (true and records.get((1,1))==(3,'white') and records.get((2,1))==(4,'white')) or (h.roles[0]&1 and dead_seer):kept.append(h)
   prior={r:sum(h.mass for h in before.hypotheses if h.roles==r) for r in {h.roles for h in kept}}
   support={r:sum(h.mass for h in kept if h.roles==r) for r in prior}
   expected=normalize(tuple(replace(h,mass=h.mass*prior[h.roles]/support[h.roles]) for h in kept))
   self.assertEqual(law.hypotheses,expected);self.assertEqual(sum(h.mass for h in law.hypotheses),1)
  self.assertEqual(row.selection_weight,0)
  from werewolf.information_set_forecast import InformationSetForecast
  e=InformationSetForecast(doc.game.node.data.game_data.rules,Strategy(**doc.game.node.data.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False)
  e.retain_joint_guard_history=True
  self.assertEqual(dict(doc.game.node.forecast().action_values),dict(e.day_scores(doc.game.node.read().public,doc.game.node.read().public_state,doc.game.node.read().past)))
  self.assertEqual(doc.game.history.state(parent).source,source);self.assertEqual(doc.game.history.state(parent).node.forecast(),value)
  cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
  self.assertEqual(cold.game.node.read(),doc.game.node.read());self.assertEqual(cold.game.export(),doc.game.export())
  current=NavigationCurrent(doc.game)
  self.assertEqual([r['day'] for r in current.data.to_game()['seer_inputs']],[1,2])
  self.assertEqual([e['published_day'] for b in current.public_log for e in b['events'] if e['kind']=='seer'],[2,2])
 def test_back_and_alternative_update_keep_both_branches_and_source_value(self):
  doc=self.doc();source=doc.game.node.read();parent=doc.game.current;value=doc.game.node.forecast()
  first=doc.game.public_input(('seer',)+('latent',)*4,self.evidence());first_source=doc.game.node.read()
  doc.game.back();self.assertEqual(doc.game.current,parent)
  second=doc.game.public_input(('seer',)+('latent',)*4,self.evidence(2,'black'))
  self.assertNotEqual(first.key,second.key);self.assertEqual(doc.game.history.state(first.key).source,first_source)
  self.assertEqual(doc.game.history.state(parent).source,source);self.assertEqual(doc.game.history.state(parent).node.forecast(),value)
  self.assertEqual([c.selection_weight for c in doc.game.history.children(parent)],[0,0])
  # A dead true seer still permits a lying claimant; black is not certain truth.
  self.assertEqual(doc.game.node.forecast().village_win,F(2,3))
  tree=NavigationTree(doc);shown=tree.read(tree.current_key());self.assertIn('Day1',shown['navigation_label'])
 def test_targets_use_acquisition_roster_and_reject_dead_reporter_or_future(self):
  from werewolf.seer_manual import report_slots
  doc=self.doc();s=transport_source(doc.game.node.read(),doc.game.occurrence.names.forward)
  slots=report_slots(s.public,doc.data.game_data.rules,s.public_state.rosters)
  self.assertIn(3,slots[0]['players']);self.assertNotIn(3,slots[1]['players']);self.assertIn(4,slots[1]['players'])
  for report in [SeerReport(2,2,1,3,'white'),SeerReport(2,3,1,4,'white'),SeerReport(2,2,4,1,'white')]:
   with self.assertRaises((ValueError,UnsupportedPublicInput)) as error:condition_input(s,PublicInput(('seer',)+('latent',)*4,(report,)),doc.data.game_data.rules,ClaimPolicy())
   self.assertIsNotNone(error.exception)
 def test_day3_addition_retains_original_day2_publication_dates(self):
  from werewolf.seer_future_uniform import TrueScanState,acquire_uniform
  from werewolf.seer_acquisition import from_board
  from werewolf.evaluation_branch import ContinuationInputs,ActionInputs
  from werewolf.action_flow import resolve_action
  from werewolf.information_set_forecast import InformationSetForecast
  b=initial_board(7,1,0,1);rules=Rules();policy=Strategy()
  state=acquire_uniform(TrueScanState(from_board(b),(),initial_rule='random_white'),b.alive)
  source=ContinuationInputs(b,state,(),state,None,b);e=InformationSetForecast(rules,policy,retire_uninformative_scans=False);e.retain_joint_guard_history=True
  def step(source,target):
   acquired,rows=resolve_action(source.public,ActionInputs(source.public_state,source.past,source.private,None,source.physical),target,e.action_policy)
   return e.action_policy.project(source.public,acquired,next(o for o in rows if o.board.winner is None),target)
  source=step(step(source,3),4)
  old=self.evidence();claims=('seer',)+('latent',)*6
  source=condition_input(source,PublicInput(claims,old),rules,ClaimPolicy()).source
  source=step(step(source,5),6);before=source
  updated=condition_input(source,PublicInput(claims,(*old,SeerReport(3,3,1,6,'white'))),rules,ClaimPolicy()).source
  self.assertEqual([(r.acquired_day,r.published_day) for r in updated.past],[(1,2),(2,2),(3,3)])
  self.assertEqual(source,before);self.assertEqual(sum(h.mass for h in updated.private.hypotheses),1)
 def test_initial_none_has_no_day1_result_and_same_night_scan_still_possible(self):
  from werewolf.seer_future_uniform import TrueScanState,acquire_uniform
  from werewolf.seer_acquisition import from_board
  from werewolf.evaluation_branch import ContinuationInputs,ActionInputs
  from werewolf.action_flow import resolve_action
  from werewolf.information_set_forecast import InformationSetForecast
  from werewolf.seer_manual import report_slots
  b=initial_board(5,1,0,1);rules=Rules(initial_seer='none');policy=Strategy()
  state=acquire_uniform(TrueScanState(from_board(b),(),initial_rule='none'),b.alive)
  source=ContinuationInputs(b,state,(),state,None,b);e=InformationSetForecast(rules,policy,retire_uninformative_scans=False);e.retain_joint_guard_history=True
  for target in (3,4):
   b=source.public;payload=ActionInputs(source.public_state,source.past,source.private,None,source.physical)
   acquired,outcomes=resolve_action(b,payload,target,e.action_policy)
   outcome=next(o for o in outcomes if o.board.winner is None);source=e.action_policy.project(b,acquired,outcome,target)
  self.assertFalse(report_slots(source.public,rules,source.public_state.rosters)[0]['available'])
  self.assertFalse(any(a.day==1 for h in source.private.hypotheses for a in h.acquisitions))
  with self.assertRaises(ValueError):condition_input(source,PublicInput(('seer',)+('latent',)*4,(SeerReport(1,2,1,3,'white'),)),rules,ClaimPolicy())
  updated=condition_input(source,PublicInput(('seer',)+('latent',)*4,(SeerReport(2,2,1,4,'white'),)),rules,ClaimPolicy()).source
  self.assertEqual(updated.past,(SeerReport(2,2,1,4,'white'),))

class DelayedCOHTTPTests(unittest.TestCase):
 def setUp(self):
  self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
  self.app=create_app(dict(TESTING=True,SECRET_KEY='late-http',GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=self.directory.name));self.client=self.app.test_client()
  self.client.post('/start',data=dict(citizens=3,seers=1,wolves=1,day='max',night='max',win_cutoff='1'))
  for revision,target in [(0,3),(1,4)]:self.assertEqual(self.client.post('/navigation/advance',json=dict(revision=revision,target=target,reuse_forward=False)).status_code,200)
 def seed(self):
  text=self.client.get('/main').get_data(as_text=True);return json.loads(text.split('<script type="application/json" id="public-log-seed">',1)[1].split('</script>',1)[0]),text
 def payload(self):return dict(claims=['seer']+['latent']*4,seers=[dict(day=1,reporter=1,target=3,color='white'),dict(day=2,reporter=1,target=4,color='white')],mediums=[])
 def test_real_table_preview_publish_readonly_log_and_next_update(self):
  seed,_=self.seed();data=dict(revision=str(seed['revision']),board_id=seed['board_id'],request_id='late',payload=json.dumps(self.payload()))
  preview=self.client.post('/table-preview',data=data);self.assertEqual(preview.status_code,200,preview.json);self.assertEqual(preview.json['revision'],seed['revision']);self.assertEqual(preview.json['board_id'],seed['board_id'])
  saved=self.client.post('/table-publish',data=data);self.assertEqual(saved.status_code,200,saved.json)
  seed,page=self.seed();self.assertEqual([r['day'] for r in seed['seers']],[1,2]);self.assertIn('data-log-acquired-day="1" data-log-published-day="2"',page)
  for old in ['data-public-open','data-public-edit','data-public-delete','data-legacy-open','id="board-log-dialog"']:self.assertNotIn(old,page)
  self.assertIn('data-log-readonly',page);self.assertIn('id="back-button"',page)
  repeated=self.client.post('/table-publish',data=dict(revision=str(seed['revision']),board_id=seed['board_id'],payload=json.dumps(self.payload())))
  self.assertEqual(repeated.status_code,200,repeated.json)
  self.assertEqual(self.client.post('/table-publish',data=data).status_code,409)
  bad=self.client.post('/table-preview',data=dict(revision=str(seed['revision']+1),board_id='other-board',payload=json.dumps(self.payload())))
  self.assertEqual(bad.status_code,409)
 def test_genuine_concurrent_late_CO_commits_once(self):
  seed,_=self.seed()
  with self.client.session_transaction() as session:base=deepcopy(dict(session))
  data=dict(revision=str(seed['revision']),board_id=seed['board_id'],payload=json.dumps(self.payload()))
  def publish(_):
   with self.app.test_client() as c:
    with c.session_transaction() as session:session.update(deepcopy(base))
    return c.post('/table-publish',data=data).status_code
  with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(publish,range(2)))
  self.assertEqual(sorted(codes),[200,409]);self.assertEqual(len(self.client.get('/navigation').json['occurrences']),4)
