import copy,unittest
from app import create_app
class HelpTests(unittest.TestCase):
 def setUp(self):
  self.c=create_app({'TESTING':True,'SECRET_KEY':'help','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True}).test_client();self.c.post('/start',data={'citizens':'2','seers':'1','wolves':'2','day':'max','night':'max'})
 def g(self):
  with self.c.session_transaction() as q:return copy.deepcopy(q['game'])
 def test_top_help_button_is_inside_cast_panel_and_specs_removed(self):
  h=self.c.get('/').get_data(as_text=True);self.assertIn('id="help-button" href="/help"',h);self.assertLess(h.index('id="help-button"'),h.index('class="panel rules-panel"'));self.assertNotIn('data-future-preview-top',h)
 def test_help_routes_preserve_game_and_explain_full_disclosure_consistency(self):
  before=self.g();h=self.c.get('/help').get_data(as_text=True);self.assertIn('5 人村の例',h);self.assertIn('仕様の補足',h);s=self.c.get('/help/specs').get_data(as_text=True);self.assertIn('未公開なら真候補から外します',s);self.assertIn('不整合',s);self.assertIn('共通',s);self.assertEqual(self.g(),before)
 def test_existing_five_example_and_only_required_assets_served(self):
  before=self.g();response=self.c.get('/help/five/');h=response.get_data(as_text=True);response.close();self.assertIn('id="stepnav"',h);self.assertIn('id="rootvalue"',h);self.assertIn('id="next"',h);self.assertIn('tree-prototype.js',h)
  for name in ('tree-prototype.css','tree-prototype.js'):
   response=self.c.get('/help/five/'+name);self.assertEqual(response.status_code,200);response.close()
  self.assertEqual(self.c.get('/help/five/hunter-example.html').status_code,404);self.assertEqual(self.g(),before)
 def test_board_does_not_regrow_permanent_scope_text(self):
  h=self.c.get('/main').get_data(as_text=True);self.assertNotIn('入力済み結果を真結果との整合性で条件付けます',h);self.assertNotIn('data-future-uniform-scope',h);self.assertNotIn('data-information-fixed-scope',h);self.assertIn('data-seer-future="all"',h)
 def test_game_tree_reserved_for_actual_branches_not_sample_link(self):
  h=self.c.get('/main').get_data(as_text=True)
  tree=h.split('id="tree-reserved"',1)[1].split('</section>',1)[0]
  self.assertIn('GameTree',tree);self.assertNotIn('<a ',tree)
  self.assertIn('/help/five/',self.c.get('/help').get_data(as_text=True))
