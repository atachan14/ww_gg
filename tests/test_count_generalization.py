import unittest,tempfile,json
from fractions import Fraction as F
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree
from werewolf.closed_calculation import _forecast_scope
from werewolf.navigation_current import NavigationCurrent
from werewolf.seer_acquisition import SeerReport
from app import create_app
from dev_previews.benchmark_player_counts import data,oracle

class CountGeneralizationTests(unittest.TestCase):
 def test_three_to_nine_exact_even_odd_random_and_MAX(self):
  for n in range(3,10):
   for policy in ('random','max'):
    with self.subTest(n=n,policy=policy),calculation_budget(250000,max_seconds=12):
     doc=NavigationDocument(data(n,policy));self.assertEqual(doc.game.node.forecast().village_win,oracle(n,1,'day'))
 def test_eight_nine_stage_convergence_named_transport_and_cold_current(self):
  for n in (8,9):
   with self.subTest(n=n),calculation_budget(500000,max_seconds=25):
    doc=NavigationDocument(data(n));view=NavigationTree(doc);view.read(expand=True)
    doc.game.action(n);night=view.read(view.current_key(),True)
    self.assertEqual((night['day'],night['phase'],len(night['alive'])),(1,'night',n-1));self.assertNotIn(n,night['alive'])
    self.assertEqual(F(night['village_win']),oracle(n-1,1,'night'))
    leaves=[]
    def walk(s):
     leaves.extend(s.get('leaves',()))
     for b in s.get('branches',()):walk(b['children'])
    walk(night['night_stages']);self.assertEqual(len(leaves),6);self.assertEqual(len({r['node'] for r in leaves}),1)
    doc.game.action(2);current=view.read(view.current_key(),True);self.assertEqual((current['day'],current['phase']),(2,'day'))
    self.assertNotIn(n,current['alive']);self.assertNotIn(2,current['alive']);self.assertEqual(F(current['village_win']),oracle(n-2,1,'day'))
    cold=NavigationDocument.restore(doc.export());self.assertEqual(cold.game.node.read(),doc.game.node.read());self.assertEqual(cold.game.export(),doc.game.export())
    here=doc.game.current;doc.game.back();doc.game.forward();self.assertEqual(doc.game.current,here)
    self.assertEqual(NavigationCurrent(doc.game).source.public.alive,tuple(current['alive']))
 def test_manual_input_keeps_named_fallback_and_public_role_masses(self):
  for n in (8,9):
   with self.subTest(n=n),calculation_budget(250000,max_seconds=12):
    d=data(n).to_game();d['policy']['win_cutoff']=True
    from werewolf.board_flow import BoardData
    doc=NavigationDocument(BoardData.from_game(d));before=doc.game.node.read()
    row=doc.game.public_input(('seer','seer')+('latent',)*(n-2),(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,4,'white')))
    self.assertEqual(row.selection_weight,0);s=doc.game.node.read();self.assertEqual(s.public.role_probability(1,'seer'),F(1,2))
    self.assertEqual(sum(h.mass for h in s.public_state.hypotheses),1);self.assertEqual(sum(h.mass for h in s.private.hypotheses),1)
    self.assertEqual(doc.game.history.state('h0').source,before)
    shown=NavigationTree(doc).read('h1~0',True);self.assertEqual(shown['village_win'],'1');self.assertIsNotNone(shown['cutoff_marker'])
 def test_multiple_wolves_preserve_distinct_Q_P_after_night(self):
  for n in (8,9):
   with self.subTest(n=n),calculation_budget(500000,max_seconds=25):
    doc=NavigationDocument(data(n,'random' if n==9 else 'max',wolves=2))
    self.assertEqual(doc.game.node.forecast().village_win,oracle(n,2,'day'))
    doc.game.action(1);doc.game.action(2);s=doc.game.node.read();physical={}
    for h in s.private.hypotheses:
     w=(h.roles[0]&s.public.alive_mask).bit_count();physical[w]=physical.get(w,F())+h.mass
    self.assertNotEqual(physical,s.public.wolf_count_distribution)
    self.assertEqual(doc.game.node.forecast().village_win,sum(q*oracle(n-2,w,'day') for w,q in physical.items()))
 def test_multiple_seers_root_is_count_generic(self):
  for n in (8,9):
   with self.subTest(n=n),calculation_budget(500000,max_seconds=25):
    doc=NavigationDocument(data(n,seers=2));self.assertEqual(doc.game.node.forecast().village_win,oracle(n,1,'day'))
 def test_budget_is_resource_failure_not_unsupported_count(self):
  for n in (8,9):
   with self.subTest(n=n):
    doc=NavigationDocument(data(n));_forecast_scope(doc.game.node.read(),doc.game.node._Node__calculation._ClosedCalculation__engine)
    with self.assertRaises(CalculationBudgetExceeded),calculation_budget(1):doc.game.node.forecast()
 def test_actual_HTTP_budget_is_503_not_semantic_422(self):
  directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
  app=create_app(dict(TESTING=True,SECRET_KEY='count-resource',GAME_TREE_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory.name));c=app.test_client()
  r=c.post('/start',data=dict(citizens=6,seers=1,wolves=1,day='max',night='max',fake_reports='max'));self.assertIn(r.status_code,(302,303),r.get_data(as_text=True)[-500:])
  app.config['MANUAL_CALC_MAX_WORK']=1
  r=c.get('/game-tree?expand=1');self.assertEqual(r.status_code,503,r.json);self.assertTrue(r.json['pending']);self.assertNotIn('unsupported',r.json)
