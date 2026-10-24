import unittest,re,json,tempfile,copy
from contextlib import ExitStack
from html.parser import HTMLParser
from unittest.mock import patch
from app import create_app
from werewolf.board_flow import BoardData,RoleState
from werewolf.navigation_current import NavigationRoleState
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.grouped_forecast import GroupedForecast
from werewolf.root_secret_flow import RootSecretEngine
from werewolf.anonymous_owned import AnonymousNode

class Rates(HTMLParser):
 def __init__(self,html):
  super().__init__();self.player=None;self.cell=None;self.roles=[];self.wins=[];self.feed(html)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='tr':self.player=a.get('data-player')
  if tag=='td':self.cell=a.get('data-value-cell')
  if self.player and self.cell and 'data-fraction' in a:
   (self.wins if self.cell in ('dawn','final') else self.roles).append((self.player,self.cell,a['data-fraction']))
 def handle_endtag(self,tag):
  if tag=='td':self.cell=None
  if tag=='tr':self.player=None

class InputCalculationOptionTests(unittest.TestCase):
 def setUp(self):self.c=create_app({'TESTING':True,'SECRET_KEY':'input-display-only','HYBRID_TABLE_PREVIEW':True}).test_client()
 def test_top_and_main_use_one_compact_default_roles_external_display_control(self):
  top=self.c.get('/').get_data(as_text=True)
  self.c.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'random','night':'random','fake_reports':'random','win_cutoff':'0'})
  main=self.c.get('/main').get_data(as_text=True)
  for html in (top,main):
   controls=re.findall(r'<select[^>]*id="display-input-calculation"[^>]*>(.*?)</select>',html,re.S)
   self.assertEqual(len(controls),1)
   self.assertIn('<option value="roles" selected>役職率まで</option>',controls[0])
   self.assertIn('value="off">Off',controls[0]);self.assertIn('value="all">全て',controls[0])
   self.assertIn('入力中に計算を進める',html);self.assertNotIn('重い配役では',html)
 def test_help_bookshelf_operations_display_and_explanation(self):
  html=self.c.get('/help/operations/display').get_data(as_text=True)
  for text in ('操作説明','data-book="operations-display"','初期設定は「役職率まで」','180ms','待機中・実行中','「更新」'):self.assertIn(text,html)
 def fixture(self,persistent,anonymous=False):
  directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
  app=create_app({'TESTING':True,'SECRET_KEY':'role-preview-only','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True,'PERSISTENT_TREE_PREVIEW':persistent,'ANONYMOUS_OWNERSHIP_PREVIEW':anonymous,'NAVIGATION_DIRECTORY':directory.name})
  c=app.test_client();c.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'random','night':'random','fake_reports':'random','win_cutoff':'0'})
  html=c.get('/main').get_data(as_text=True)
  if persistent:self.assertEqual(c.get('/navigation').status_code,200)
  seed=json.loads(re.search(r'<script type="application/json" id="public-log-seed">(.*?)</script>',html,re.S).group(1))
  form={'revision':str(seed['revision']),'board_id':seed['board_id'],'request_id':'m','payload':json.dumps({'claims':['seer','latent','latent','latent','latent'],'seers':[{'day':1,'reporter':1,'target':2,'color':'white'}],'mediums':[]})}
  return app,c,form
 def preview(self,c,form,mode,stream):
  with c.post('/table-preview',data={**form,'preview_mode':mode},headers={'Accept':'application/x-ndjson'} if stream else {}) as r:
   self.assertEqual(r.status_code,200,r.get_data(as_text=True)[:200])
   if 'application/x-ndjson' in r.content_type:
    events=[json.loads(line) for line in r.get_data(as_text=True).splitlines() if line.strip()]
    meaningful=[e for e in events if e['event'] not in ('heartbeat','position','position-unavailable')]
    if mode=='roles':self.assertEqual([e['event'] for e in meaningful],['complete'])
    return meaningful[-1]['html']
   return r.get_json()['html']
 def test_role_only_never_searches_and_matches_all_exact_role_rates(self):
  for persistent,anonymous in ((False,False),(True,False),(True,True)):
   for stream in (False,True):
    with self.subTest(persistent=persistent,anonymous=anonymous,stream=stream):
     app,c,form=self.fixture(persistent,anonymous)
     with c.session_transaction() as s:before=copy.deepcopy(s['game'])
     with ExitStack() as stack:
      for cls in (RoleState,NavigationRoleState,AnonymousNode):stack.enter_context(patch.object(cls,'forecast',side_effect=AssertionError('no role-only forecast')))
      for cls in (InformationSetForecast,GroupedForecast,RootSecretEngine):stack.enter_context(patch.object(cls,'solve',side_effect=AssertionError('no role-only solve')))
      stack.enter_context(patch('werewolf.calculation_tree.CalculationTree.expand',side_effect=AssertionError('no role-only Tree')))
      role_html=self.preview(c,form,'roles',stream)
     full_html=self.preview(c,form,'all',stream)
     roles=Rates(role_html);full=Rates(full_html)
     self.assertEqual(roles.roles,full.roles);self.assertTrue(roles.roles)
     self.assertFalse(roles.wins);self.assertTrue(full.wins)
     self.assertEqual(role_html.count('data-win-horizon="final">'+'<span class="muted">未計算</span>'),5)
     self.assertIn('id="village-rate" class="muted">未計算',role_html)
     with c.session_transaction() as s:self.assertEqual(s['game'],before)
 def test_update_still_forecasts_and_matches_in_every_mode(self):
  results=[]
  for mode in ('off','roles','all'):
   app,c,form=self.fixture(True)
   original=NavigationRoleState.forecast;calls=[]
   def forecast(owner,**kw):calls.append(True);return original(owner,**kw)
   with patch.object(NavigationRoleState,'forecast',forecast):
    with c.post('/table-publish',data={**form,'preview_mode':mode}) as r:
     self.assertEqual(r.status_code,200);html=r.get_json()['html']
   self.assertTrue(calls);self.assertTrue(Rates(html).wins)
   results.append(re.findall(r'data-fraction="([^"]+)"',html))
  self.assertEqual(results[0],results[1]);self.assertEqual(results[1],results[2])
 def test_invalid_mode_rejected_before_role_work(self):
  with patch.object(BoardData,'roles',side_effect=AssertionError('no invalid-mode calculation')):
   self.assertEqual(self.c.post('/table-preview',data={'preview_mode':'off'}).status_code,400)

 def test_day2_delayed_reports_keep_exact_role_posterior_without_future_search(self):
  app,c,_=self.fixture(True)
  for target in (3,4):
   state=c.get('/navigation').get_json()
   with c.post('/navigation/advance',json={'revision':state['revision'],'target':target}) as r:self.assertEqual(r.status_code,200)
  html=c.get('/main').get_data(as_text=True)
  seed=json.loads(re.search(r'<script type="application/json" id="public-log-seed">(.*?)</script>',html,re.S).group(1))
  self.assertEqual(seed['day'],2)
  form={'revision':str(seed['revision']),'board_id':seed['board_id'],'request_id':'day2','payload':json.dumps({'claims':['seer','latent','latent','latent','latent'],'seers':[{'day':1,'reporter':1,'target':2,'color':'white'},{'day':2,'reporter':1,'target':5,'color':'black'}],'mediums':[]})}
  with ExitStack() as stack:
   for cls in (RoleState,NavigationRoleState,AnonymousNode):stack.enter_context(patch.object(cls,'forecast',side_effect=AssertionError('no role-only forecast')))
   for cls in (InformationSetForecast,GroupedForecast,RootSecretEngine):stack.enter_context(patch.object(cls,'solve',side_effect=AssertionError('no role-only future solve')))
   roles=self.preview(c,form,'roles',False)
  full=self.preview(c,form,'all',False)
  self.assertEqual(Rates(roles).roles,Rates(full).roles);self.assertFalse(Rates(roles).wins);self.assertTrue(Rates(full).wins)
