import unittest,copy,json
from unittest.mock import patch
from werkzeug.datastructures import MultiDict
from app import create_app
from werewolf.seer_manual import replay,MODE
from werewolf.setup import GameConfig,SetupDraft,complete_rules,RULE_PRESETS
from werewolf.exact import initial_board,Progress,advance,Rules,Strategy,condition_claims,group_initial_board,ClaimPolicy

class SeerGameRuleTests(unittest.TestCase):
 def setUp(self):self.app=create_app({'TESTING':True,'SECRET_KEY':'seer-rule-test'});self.c=self.app.test_client()
 def g(self):
  with self.c.session_transaction() as s:return copy.deepcopy(s.get('game'))
 def start(self,initial='random_white',seers=1):return self.c.post('/start',data={'citizens':str(3-seers),'seers':str(seers),'wolves':'2','initial_seer':initial,'day':'max','night':'max'})
 def publish(self,events):return self.c.post('/public-log',data={'revision':str(self.g()['revision']),'operation':'publish','payload':json.dumps({'mode':'simultaneous','events':events})})
 def test_three_choices_snapshot_and_main_readonly_top_editable(self):
  for initial in ('normal','random_white','none'):
   self.assertEqual(self.start(initial).status_code,303);g=self.g();self.assertEqual(g['rules']['initial_seer'],initial);self.assertEqual(g['seer_options'],{'initial_rule':initial,'likelihood':'compatibility'});self.assertEqual(g['seer_mode'],MODE)
   top=self.c.get('/').data;main=self.c.get('/main').data
   self.assertIn(b'id="first-seer" name="initial_seer"',top);self.assertNotIn(b'id="seer-mode"',top)
   self.assertIn(b'id="view-first-seer" disabled',main);self.assertNotIn(b'name="seer_initial_rule"',main);self.assertNotIn(b'name="seer_likelihood"',main)
   self.assertEqual(GameConfig.from_game(g).draft().initial_seer,initial)
 def test_black_report_is_allowed_but_random_white_true_assignment_eliminated(self):
  for initial,color in (('normal','black'),('random_white','black'),('none','white')):
   self.start(initial);r=self.publish([{'kind':'co','player':1,'role':'seer'},{'kind':'co','player':2,'role':'seer'},{'kind':'seer','player':1,'day':1,'target':3,'color':color}]);self.assertEqual(r.status_code,200,r.data)
   b=replay(self.g())[1].board
   self.assertGreater(b.role_probability(1,'seer'),0) if initial=='normal' else self.assertEqual(b.role_probability(1,'seer'),0)
   self.assertEqual(self.g()['seer_inputs'][0]['color'],color)
   if initial=='none':self.assertIn(b'name="seer_color_1_1"',self.c.get('/main').data)
 def test_rule_cannot_be_changed_from_main_even_before_action(self):
  self.start();old=self.g();r=self.c.post('/strategy',data={'revision':str(old['revision']),'day':'max','night':'max','seer_initial_rule':'normal'});self.assertEqual(r.status_code,400);self.assertEqual(self.g(),old)
 def test_legacy_unselected_and_unset_mode_migrate_without_inventing_reports(self):
  for oldmode in (MODE,None):
   self.start('normal');g=self.g();g['rules'].pop('initial_seer');g['seer_options']={'initial_rule':None,'likelihood':None}
   if oldmode is None:g.pop('seer_mode');g.pop('seer_options');g.pop('seer_inputs')
   with self.c.session_transaction() as s:s['game']=g
   self.assertEqual(self.c.get('/main').status_code,200);new=self.g();self.assertEqual(new['seer_mode'],MODE);self.assertEqual(new['seer_options'],{'initial_rule':'random_white','likelihood':'compatibility'});self.assertEqual(new['seer_inputs'],[])
 def test_legacy_selected_rule_and_history_snapshots_preserved(self):
  self.start('normal');g=self.g();self.c.post('/advance',data={'revision':str(g['revision']),'day':'max','night':'max','target':'1'});g=self.g();old=replay(g)[1]
  g['rules'].pop('initial_seer');g['seer_options']['likelihood']=None
  for step in g['history']:step['seer_options']['likelihood']=None
  with self.c.session_transaction() as s:s['game']=g
  self.c.get('/main');new=self.g();self.assertEqual(new['rules']['initial_seer'],'normal');self.assertEqual(replay(new)[1],old)
  self.assertEqual(self.c.post('/back',data={'revision':str(new['revision'])}).status_code,303);self.assertEqual(self.g()['rules']['initial_seer'],'normal')
 def test_legacy_abilityless_seer_progress_projection_unchanged_without_reports(self):
  self.start();g=self.g();self.c.post('/advance',data={'revision':str(g['revision']),'day':'max','night':'max','target':'2'});g=self.g()
  g.pop('seer_mode');g.pop('seer_options');g.pop('seer_inputs');g['rules'].pop('initial_seer')
  for s in g['history']:s.pop('seer_options')
  seed=initial_board(g['players'],g['wolves'],g.get('mediums',0),g.get('seers',0),g.get('hunters',0));p=Progress.initial(seed)
  for i,s in enumerate(g['history']):
   b=group_initial_board(p.board,tuple(s['claims']),ClaimPolicy(**s['claim_policy'])) if i==0 else condition_claims(p.board,tuple(s['claims']),ClaimPolicy(**s['claim_policy']))
   p=advance(Progress(b,p.settled_village,p.settled_wolf,p.last_board,p.last_outcomes),s['target'],Rules(),Strategy(**s['policy']))
  with self.c.session_transaction() as s:s['game']=g
  self.c.get('/main');new=replay(self.g())[1];self.assertEqual(new.board.worlds,p.board.worlds);self.assertEqual(new.settled_village,p.settled_village);self.assertEqual(new.settled_wolf,p.settled_wolf)
 def test_nonseer_games_keep_ordinary_route_and_value(self):
  for initial in ('normal','random_white','none'):
   self.start(initial,seers=0);g=self.g();self.assertNotIn('seer_mode',g)
   self.assertIn(b'data-fraction="2/15"',self.c.get('/main').data)
 def test_preset_independent_and_saved_rule_survives_definition_changes(self):
  self.start('normal');g=self.g();draft=GameConfig.from_game(g).draft();self.assertEqual(draft.rule_preset,'custom')
  with patch.dict(RULE_PRESETS,{'sample':{'label':'changed','values':{'allow_self_bite':False,'initial_seer':'none'}}},clear=True):self.assertEqual(GameConfig.from_game(g).draft().initial_seer,'normal')
  self.assertEqual(complete_rules({}).initial_seer,'random_white')
 def test_invalid_and_duplicate_rule_preserves_existing_game(self):
  self.start();old=self.g()
  for value in ('','bad'):
   r=self.start(value);self.assertEqual(r.status_code,400);self.assertEqual(self.g(),old)
  form=MultiDict([('citizens','2'),('seers','1'),('wolves','2'),('day','max'),('night','max'),('initial_seer','normal'),('initial_seer','none')]);self.assertEqual(self.c.post('/start',data=form).status_code,400);self.assertEqual(self.g(),old)

 def test_unknown_saved_model_is_not_silently_migrated(self):
  self.start();g=self.g();g['seer_mode']='unknown-mode'
  with self.c.session_transaction() as session:session['game']=g
  self.assertEqual(self.c.get('/main').status_code,303);self.assertEqual(self.g(),g)

 def test_draft_controls_belong_to_separate_inert_form(self):
  self.start();html=self.c.get('/main').data
  self.assertIn(b'id="public-log-draft-form"',html);self.assertIn(b'data-public-mode form="public-log-draft-form"',html)
