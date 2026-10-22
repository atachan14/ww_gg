import unittest,json,tempfile
from dataclasses import replace
from fractions import Fraction as F
from itertools import combinations
from unittest.mock import patch
from app import create_app
from werewolf.exact import Rules,Strategy,initial_board,replace_worlds
from werewolf.seer_acquisition import from_board,Hypothesis
from werewolf.night_knowledge import WolfAttack
from werewolf.seer_future_uniform import TrueScanState
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.win_certificate import certify,bound
from werewolf.closed_calculation import ClosedCalculation
from werewolf.board_flow import BoardData
from tests import test_public_relation_orbits as relations

class WinCertificateTests(unittest.TestCase):
 def source(self,n,m,w=1,phase='day'):
  rosters=list(combinations(range(m),w))
  b=replace_worlds(initial_board(n,w),tuple((sum(1<<p for p in roster),0,0,0,F(1,len(rosters))) for roster in rosters))
  b=replace(b,phase=phase)
  return b,TrueScanState(from_board(b),(tuple(range(1,n+1)),),initial_rule='none',tracked=())
 def engine(self,on,night='max'):
  return InformationSetForecast(Rules(initial_seer='none'),Strategy('max',night,win_cutoff=on),exact_renaming=False)
 def test_bounds_phase_and_person_count_not_group_count(self):
  for phase,extra in [('day',1),('night',2)]:
   for m in (1,2,3):
    self.assertIsNone(bound(range(1,m+1),range(1,2*m+extra),phase))
    self.assertIsNotNone(bound(range(1,m+1),range(1,2*m+extra+1),phase))
  b,s=self.source(5,5);self.assertIsNone(certify(b,s,s,Strategy(win_cutoff=True),Rules()))
 def test_analytic_hit_never_calls_future_search_or_completes_scores(self):
  b,s=self.source(5,2);e=self.engine(True)
  with patch.object(e,'act',side_effect=AssertionError('recursive action')),patch.object(e,'day_scores',side_effect=AssertionError('score vector')):
   self.assertEqual(e.solve(b,s,(),s,None),1)
  self.assertEqual(e.cutoff_hits,1);self.assertEqual(e.expansions['values'],0);self.assertFalse(e.scores)
 def test_analytic_support_scan_respects_existing_work_budget(self):
  from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded
  b,s=self.source(5,2)
  with self.assertRaises(CalculationBudgetExceeded),calculation_budget(1):
   certify(b,s,s,Strategy(win_cutoff=True),Rules())
 def test_named_differential_phase_boundaries_multiple_wolves_and_search_counts(self):
  evidence=[]
  for n,m,w,phase in [(3,1,1,'day'),(3,2,1,'day'),(4,1,1,'night'),(4,2,1,'night'),(5,2,1,'day'),(5,3,1,'day'),(6,2,1,'night'),(5,2,2,'day'),(6,2,2,'night'),(7,3,2,'day')]:
   b,s=self.source(n,m,w,phase)
   for night in ('max','random'):
    off,on=self.engine(False,night),self.engine(True,night)
    expected=off.solve(b,s,(),s,None);actual=on.solve(b,s,(),s,None)
    self.assertEqual(actual,expected,(n,m,w,phase,night))
    evidence.append(dict(n=n,m=m,w=w,phase=phase,night=night,value=str(actual),off=off.expansions['values'],on=on.expansions['values'],hits=getattr(on,'cutoff_hits',0)))
  self.assertTrue(any(row['on']<row['off'] for row in evidence))
  from pathlib import Path
  Path('.artifacts').mkdir(exist_ok=True);Path('.artifacts/cutoff-benchmark.json').write_text(json.dumps(evidence,indent=2))
 def test_fail_closed_private_support_observer_roles_rules_and_random(self):
  b,s=self.source(5,2);policy=Strategy(win_cutoff=True);rules=Rules()
  outsider=replace(s,hypotheses=(Hypothesis((16,0,0,0),(),F(1)),))
  self.assertIsNone(certify(b,s,outsider,policy,rules))
  self.assertIsNone(certify(b,s,s,policy,rules,object()))
  self.assertIsNone(certify(b,s,s,policy,Rules(allow_self_bite=True)))
  self.assertIsNone(certify(b,s,s,Strategy(),rules))
  for medium,hunter in [(1,0),(0,1)]:
   other=initial_board(5,1,medium,0,hunter)
   self.assertIsNone(certify(other,s,s,policy,rules))
  with self.assertRaises(ValueError):Strategy('random','max',win_cutoff=True)
 def test_private_certainty_never_replaces_public_candidates(self):
  b,q=self.source(5,5);private=replace(q,hypotheses=(Hypothesis((1,0,0,0),(),F(1)),))
  self.assertIsNone(certify(b,q,private,Strategy(win_cutoff=True),Rules()))
  b,q=self.source(5,2);private=replace(q,hypotheses=(replace(q.hypotheses[0],mass=F(1),attacks=(WolfAttack(1,3),)),),rosters=(q.rosters[0],q.rosters[0]))
  self.assertIsNone(certify(b,q,private,Strategy(win_cutoff=True),Rules()))
 def test_anonymous_count_owner_uses_same_person_bound_and_exact_values(self):
  from werewolf.anonymous_belief import Belief
  from werewolf.anonymous_value import Evaluator
  from werewolf.win_certificate import certify_anonymous
  b=Belief.initial(((1,2),(3,4,5)),dict(wolf=1,villager=4),'none')
  self.assertIsNone(certify_anonymous(b,True))
  _,law=b.q.condition(lambda a:sum(c.count for c in a.population.cells if c.group==0 and c.role=='wolf')+sum(p.group==0 and p.role=='wolf' for p in a.population.people)==1)
  b=replace(b,q=law,p=law)
  self.assertEqual(certify_anonymous(b,True).candidates,(1,2))
  on,off=Evaluator('max','max',True),Evaluator('max','max',False)
  self.assertEqual(on.value(b),off.value(b));self.assertEqual(on.value(b),1);self.assertGreater(on.cutoff_hits,0)
 def test_independent_named_scores_match_grouped_on(self):
  game=relations.PublicRelationOrbitTests().game();game['policy']['win_cutoff']=True
  c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True);s=c.root.read()
  oracle=InformationSetForecast(c.data.game_data.rules,replace(Strategy(**game['policy']),win_cutoff=False),exact_renaming=False,retire_uninformative_scans=False)
  oracle.retain_joint_guard_history=True
  self.assertEqual(dict(c.root.forecast().action_values),dict(oracle.day_scores(s.public,s.public_state,s.past)))
 def test_full_action_values_and_MAX_ties_still_exact(self):
  results=[]
  for on in (False,True):
   game=relations.PublicRelationOrbitTests().game();game['policy']['win_cutoff']=on
   c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
   self.assertEqual(bool(c.root.win_certificate()),on)
   before=c.root.read();forecast=c.root.forecast();self.assertEqual(c.root.read(),before)
   self.assertEqual(dict(forecast.action_values),{1:F(1),2:F(1),3:F(1,2),4:F(1,2),5:F(1,2)})
   from werewolf.calculation_tree import CalculationTree
   tree=CalculationTree.from_node(c.root);tree.expand(tree.root)
   results.append((forecast,[(a['targets'],a['policy_probability']) for a in tree.summary(tree.root,True)['actions']]))
  self.assertEqual(results[0],results[1])
 def test_option_owns_distinct_cache_and_fixed_policy_identity(self):
  nodes=[]
  for on in (False,True):
   game=relations.PublicRelationOrbitTests().game();game['policy']['win_cutoff']=on
   c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True);nodes.append(c.root)
  self.assertNotEqual(nodes[0].data.inputs,nodes[1].data.inputs)
  self.assertNotEqual(nodes[0].solver_identity,nodes[1].solver_identity)
  from werewolf.navigation_history import NavigationHistory
  history=NavigationHistory(nodes[0]);child=history.append(history.root,nodes[1],{},kind='manual_public',selection_weight=0)
  self.assertNotEqual(history.occurrence(history.root).state,child.state)
 def test_tree_stops_but_manual_current_and_cold_history_survive(self):
  from werewolf.navigation_store import NavigationDocument
  from werewolf.navigation_tree import NavigationTree
  game=relations.PublicRelationOrbitTests().game();game['policy']['win_cutoff']=True
  doc=NavigationDocument(BoardData.from_game(game));view=NavigationTree(doc)
  key=view.current_key();root=view.read(key,True)
  self.assertIsNotNone(root['win_certificate']);self.assertIsNone(root['actions']);self.assertIsNone(root['winner']);self.assertEqual(root['village_win'],'1')
  doc.game.action(3);shown=view.read(view.current_key())
  self.assertEqual(shown['village_win'],'1/2');self.assertIsNone(shown['win_certificate'])
  cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
  self.assertEqual(cold.game.node.read(),doc.game.node.read());self.assertEqual(cold.game.node.solver_identity,doc.game.node.solver_identity)
  self.assertTrue(cold.game.node.data.to_game()['policy']['win_cutoff'])
  doc.game.back();self.assertEqual(view.read(key)['village_win'],'1')
 def test_default_UI_interlock_legacy_and_lazy_public_details(self):
  with tempfile.TemporaryDirectory() as directory:
   app=create_app(dict(TESTING=True,SECRET_KEY='cutoff-test',GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
   client=app.test_client();self.assertIn('name="win_cutoff" data-setup-cutoff><option value="1" selected',client.get('/').get_data(as_text=True))
   response=client.post('/start',data=dict(citizens='3',seers='1',wolves='1',day='random',night='max',fake_reports='max',win_cutoff='1'))
   self.assertEqual(response.status_code,303)
   with client.session_transaction() as ss:
    self.assertTrue(ss['game']['policy']['win_cutoff']);self.assertEqual(ss['game']['policy']['day'],'max')
   from dataclasses import asdict
   from werewolf.seer_acquisition import SeerReport
   published=client.post('/navigation/public-input',json=dict(revision=0,claims=['seer','seer','latent','latent','latent'],reports=[asdict(SeerReport(1,1,1,3,'white')),asdict(SeerReport(1,1,2,4,'white'))]))
   self.assertEqual(published.status_code,200,published.json)
   response=client.get('/main');self.assertEqual(response.status_code,200);self.assertIn('data-cutoff-details',response.get_data(as_text=True))
   details=client.get('/main?details=1');self.assertEqual(details.status_code,200);self.assertNotIn('data-cutoff-details',details.get_data(as_text=True))
   client.post('/start',data=dict(citizens='3',seers='1',wolves='1',day='random',night='random',fake_reports='random',win_cutoff='0'))
   with client.session_transaction() as ss:self.assertFalse(ss['game']['policy']['win_cutoff']);self.assertEqual(ss['game']['policy']['day'],'random')
   client.post('/start',data=dict(citizens='3',seers='1',wolves='1',day='random',night='random',fake_reports='random'))
   with client.session_transaction() as ss:self.assertFalse(ss['game']['policy']['win_cutoff']);self.assertEqual(ss['game']['policy']['day'],'random')
