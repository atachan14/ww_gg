import unittest,re,copy
from urllib.parse import urlparse,parse_qs
from fractions import Fraction as F
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.generated_current import GeneratedCurrent

class GeneratedCurrentTests(unittest.TestCase):
 def setUp(self):
  self.app=create_app({'TESTING':True,'SECRET_KEY':'generated-current-test','GAME_TREE_PREVIEW':True})
  self.c=self.app.test_client();self.c.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'max','night':'max'})
  self.root=self.c.get('/game-tree?expand=1').json
  night=self.c.get('/game-tree?node=2&expand=1').json
  self.day=night['actions'][0]['branches'][0]['node']
  self.day_result=self.c.get('/game-tree',query_string={'node':self.day,'expand':'1'}).json
  with self.c.session_transaction() as s:self.saved=copy.deepcopy(s['game']);self.game_id=s['co_display_game']
  runtime=self.app.extensions['board_game_runtimes'].get(self.game_id,self.saved)
  data=BoardData.from_game(self.saved,runtime=runtime)
  self.tree=runtime.get(('calculation-tree',data.inputs))[1]
 def navigate(self,key):
  response=self.c.post('/game-tree/current',data={'snapshot':self.root['snapshot'],'node':key});self.assertEqual(response.status_code,200,response.json)
  page=self.c.get(response.json['url']);self.assertEqual(page.status_code,200)
  return response.json,page.data.decode()
 def fraction(self,html,id):return re.search(r'id="'+id+r'"[^>]*data-fraction="([^"]+)"',html).group(1)
 def unchanged(self):
  with self.c.session_transaction() as s:self.assertEqual(s['game'],self.saved)
 def test_exact_terminal_values_arrival_phases_rows_and_idempotent_navigation(self):
  targets={'1':F(1)}
  for key,row in self.day_result['items'].items():
   if row['winner']:targets[key]=F(row['village_win'])
  self.assertEqual(set(targets.values()),{F(),F(1)})
  for key,value in targets.items():
   result,html=self.navigate(key);self.assertEqual(self.fraction(html,'village-rate'),str(value))
   self.assertEqual(self.fraction(html,'cumulative-village-rate'),'7/15')
   self.assertIn('起点の累積勝率',html);self.assertIn('data-current-board="'+key+'"',html)
   self.assertEqual(result,self.navigate(key)[0]);self.unchanged()
 def test_full_public_private_recipe_and_owner_information_survive_cold_restore(self):
  for key in ['1',self.day,*[k for k,v in self.day_result['items'].items() if v['winner']]]:
   before=self.tree.nodes[key]['node'].read();route=self.tree.route(key)
   fresh=type(self.tree)(self.tree.data,self.tree.calculation.root.read().public,self.tree.data.roles().forecast())
   restored=fresh.restore(route);self.assertEqual(fresh.nodes[restored]['node'].read(),before)
   current=GeneratedCurrent(fresh,restored);self.assertEqual(current.source,before)
   for player in range(1,6):self.assertEqual(current.roles.probabilities(player)['wolf'],before.public.role_probability(player,'wolf'))
   if not before.public.winner:
    physical={p:sum((h.mass for h in before.private.hypotheses if h.roles[0]&(1<<(p-1))),F()) for p in before.public.alive}
    self.assertIn(F(1),physical.values())
    self.assertTrue(all(current.roles.probabilities(p)['wolf']==F(1,3) for p in before.public.alive))
   self.assertEqual(current.source.private,before.private)
  self.unchanged()
 def test_refresh_cache_eviction_and_back_use_exact_cursor_without_saved_game_writes(self):
  key=next(k for k,v in self.day_result['items'].items() if v['winner']=='wolf')
  result,html=self.navigate(key);identity=result['current']['identity']
  self.app.extensions['board_game_runtimes'].get(self.game_id,self.saved).clear()
  html=self.c.get(result['url']).data.decode();self.assertIn('data-current-identity="'+identity+'"',html)
  self.assertEqual(self.fraction(html,'village-rate'),'0');self.unchanged()
  token=parse_qs(urlparse(result['url']).query)['current'][0]
  response=self.c.post('/back',data={'revision':self.saved['revision'],'current':token});self.assertEqual(response.status_code,303)
  parent=self.c.get(response.location).data.decode();self.assertEqual(self.fraction(parent,'village-rate'),'1/3');self.unchanged()
 def test_nonrepresentative_member_has_its_own_history_and_current_identity(self):
  one,html1=self.navigate('1');other,html2=self.navigate('3')
  self.assertNotEqual(one['current']['identity'],other['current']['identity'])
  token=parse_qs(urlparse(other['url']).query)['current'][0]
  data=self.c.get('/game-tree',query_string={'current':token,'node':'3'}).json
  self.assertEqual(data['history'][-1]['target'],2)
  self.assertEqual(self.fraction(html2,'village-rate'),'1');self.unchanged()
 def test_tampered_stale_and_cross_game_cursors_cannot_replace_current_or_saved_inputs(self):
  result,_=self.navigate('1');token=parse_qs(urlparse(result['url']).query)['current'][0]
  self.assertEqual(self.c.get('/main',query_string={'current':token+'bad'}).status_code,409);self.unchanged()
  self.assertEqual(self.c.post('/game-tree/current',data={'snapshot':'stale','node':'1'}).status_code,409);self.unchanged()
  with self.c.session_transaction() as session:g=session['game'];g['policy']['day']='random';g['revision']+=1;session['game']=g
  self.assertEqual(self.c.get(result['url']).status_code,409)
  self.c.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'max','night':'max'})
  self.assertEqual(self.c.get(result['url']).status_code,409)

if __name__=='__main__':unittest.main()
