import unittest,json
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fractions import Fraction as F
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree

class AnonymousUITests(unittest.TestCase):
 def document(self):return NavigationDocument(BoardData.from_game(data(5,'random').to_game()),anonymous_owned=True)
 def test_persistent_Tree_manual_mixed_and_restore_without_names(self):
  from werewolf.seer_acquisition import SeerReport
  d=self.document();tree=NavigationTree(d)
  with patch('werewolf.anonymous_materialization.expand_laws',side_effect=AssertionError('Tree materialized named assignments')),patch('werewolf.board_future.SavedOrigin.__call__',side_effect=AssertionError('Tree named prior')):
   shown=tree.read(expand=True);self.assertEqual(shown['evaluation_trace']['representation'],'anonymous-owned')
   child=next(b['node'] for a in shown['actions'] for b in a['branches'] if not shown['items'][b['node']]['winner'])
   tree.select(child);night=tree.read(tree.current_key(),True);self.assertIsNotNone(night['night_stages'])
   self.assertFalse(night['stage_roles']['seers'])
  d.game.back();before=d.game.node.forecast().village_win
  d.game.public_input(['seer','latent','latent','latent','latent'],(SeerReport(1,1,1,2,'white'),))
  mixed=tree.read(expand=True);self.assertEqual(mixed['manual_updates'][0]['probability'],'0')
  self.assertEqual(d.game.history.state(d.game.history.root).node.forecast().village_win,before)
  cold=NavigationDocument.restore(json.loads(json.dumps(d.export())));self.assertTrue(hasattr(cold.game.history.state(cold.game.history.root).node,'owned'))
  self.assertEqual(cold.game.node.read(),d.game.node.read());NavigationTree(cold).read(expand=True)
 def test_actual_HTTP_owned_tree_and_Current(self):
  from app import create_app
  with TemporaryDirectory() as directory:
   app=create_app(dict(TESTING=True,SECRET_KEY='anonymous-ui-test',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
   c=app.test_client();r=c.post('/start',data=dict(citizens=3,seers=1,wolves=1,day='random',night='random',fake_reports='random',win_cutoff=0));self.assertIn(r.status_code,(302,303))
   with patch('werewolf.anonymous_materialization.expand_laws',side_effect=AssertionError('HTTP Tree expanded names')),patch('werewolf.board_future.SavedOrigin.__call__',side_effect=AssertionError('HTTP Tree generated named prior')):
    shown=c.get('/game-tree?expand=1')
   self.assertEqual(shown.status_code,200,shown.get_data(as_text=True)[:300]);self.assertEqual(shown.json['evaluation_trace']['representation'],'anonymous-owned')
   moved=c.post('/navigation/advance',json=dict(revision=0,target=4));self.assertEqual(moved.status_code,200,moved.get_data(as_text=True)[:300]);self.assertNotIn(4,moved.json['board']['alive'])
   page=c.get('/main');self.assertEqual(page.status_code,200)
   import re
   seed=json.loads(re.search(r'<script[^>]*id="public-log-seed"[^>]*>(.*?)</script>',moved.json['html'],re.S).group(1))
   private=c.post('/private-view',data=dict(revision=str(moved.json['revision']),board_id=seed['board_id'],payload=json.dumps(dict(role='wolf',players=[5],results=[]))))
   self.assertEqual(private.status_code,200,private.get_data(as_text=True)[:300])


 def test_HTTP_Day2_manual_exit_and_store_cold_restore(self):
  from app import create_app
  from dataclasses import asdict
  from werewolf.seer_acquisition import SeerReport
  with TemporaryDirectory() as directory:
   app=create_app(dict(TESTING=True,SECRET_KEY='anonymous-ui-test',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True,NAVIGATION_DIRECTORY=directory));c=app.test_client()
   c.post('/start',data=dict(citizens=3,seers=1,wolves=1,day='random',night='random',fake_reports='random',win_cutoff=0))
   original=c.get('/game-tree?expand=1').json
   for revision,target in ((0,1),(1,2)):
    r=c.post('/navigation/advance',json=dict(revision=revision,target=target));self.assertEqual(r.status_code,200,r.get_data(as_text=True)[:200])
   updated=c.post('/navigation/public-input',json=dict(revision=2,claims=['latent','latent','seer','latent','latent'],reports=[asdict(SeerReport(1,2,3,4,'white')),asdict(SeerReport(2,2,3,5,'black'))]))
   self.assertEqual(updated.status_code,200,updated.get_data(as_text=True)[:200]);self.assertEqual(updated.json['occurrences'][-1]['selection_weight'],'0')
   before=c.get('/game-tree?expand=1');self.assertEqual(before.status_code,200);self.assertEqual(before.json['village_win'],original['village_win'])
   app.extensions['navigation_store']._documents.clear()
   cold=c.get('/game-tree?expand=1');self.assertEqual(cold.status_code,200,cold.get_data(as_text=True)[:200]);self.assertEqual(cold.json['village_win'],original['village_win'])
   self.assertEqual(cold.json['current_node'],before.json['current_node'])

 def test_bound_history_root_includes_already_recorded_stage_children(self):
  d=self.document();tree=NavigationTree(d);shown=tree.read(expand=True)
  child=next(b['node'] for a in shown['actions'] for b in a['branches'] if not shown['items'][b['node']]['winner'])
  tree.select(child);tree.read(tree.current_key(),True);root=tree.read(expand=True)
  current=root['items'][root['current_node']];self.assertIsNotNone(current['night_stages'])
  def check(stage):
   for leaf in stage.get('leaves',[]):self.assertIn(leaf['node'],root['items'],'bound stage references an absent child')
   for branch in stage.get('branches',[]):check(branch['children'])
  check(current['night_stages'])

 def test_terminal_boards_use_post_action_phase_columns(self):
  d=self.document();shown=NavigationTree(d).read(expand=True)
  finished=next(r for r in shown['items'].values() if r['winner']=='village')
  self.assertEqual((finished['column_day'],finished['column_phase']),(1,'night'))

 def test_already_evaluated_UI_projection_does_not_rerun_anonymous_kernels(self):
  d=self.document();node=d.game.node;node.forecast();tree=NavigationTree(d)
  with patch('werewolf.anonymous_belief.Belief.execute',side_effect=AssertionError('UI reran execution')),patch.object(node.calculation.evaluator,'night_flow',side_effect=AssertionError('UI reran night')),patch.object(node.calculation.evaluator,'forced_night_flow',side_effect=AssertionError('UI reran forced night')):
   shown=tree.read(expand=True)
   child=next(b['node'] for a in shown['actions'] for b in a['branches'] if not shown['items'][b['node']]['winner'])
   tree.read(child,True)

 def test_anonymous_entry_and_UI_keep_request_work_budget(self):
  from werewolf.anonymous_owned import AnonymousCalculation
  from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded
  prepared=BoardData.from_game(data(5,'random').to_game())
  with self.assertRaises(CalculationBudgetExceeded),calculation_budget(1):AnonymousCalculation(prepared)
  d=NavigationDocument(prepared,anonymous_owned=True);tree=NavigationTree(d)
  with self.assertRaises(CalculationBudgetExceeded),calculation_budget(1):tree.read(expand=True)
