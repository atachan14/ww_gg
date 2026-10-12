import unittest,copy,json,re
from app import create_app
class BoardOwnedLogTests(unittest.TestCase):
 def setUp(self):
  self.a=create_app({'TESTING':True,'SECRET_KEY':'board-owned','HYBRID_TABLE_PREVIEW':True});self.c=self.a.test_client();self.c.post('/start',data={'citizens':'5','seers':'1','wolves':'1','day':'max','night':'max'})
 def g(self):
  with self.c.session_transaction() as q:return copy.deepcopy(q['game'])
 def bid(self):return self.g()['public_log']['board_id']
 def payload(self):
  g=self.g();return {'claims':g['claims'],'seers':g['seer_inputs'],'mediums':g.get('reports',[])}
 def table(self,p,preview=False,board_id=None):
  g=self.g();return self.c.post('/table-preview' if preview else '/table-publish',data={'revision':str(g['revision']),'board_id':board_id or g['public_log']['board_id'],'request_id':'4','payload':json.dumps(p)})
 def advance(self,target):
  g=self.g();r=self.c.post('/advance',data={'revision':str(g['revision']),'target':str(target),'day':'max','night':'max'});self.assertEqual(r.status_code,303,r.data)
 def back(self):
  g=self.g();self.assertEqual(self.c.post('/back',data={'revision':str(g['revision'])}).status_code,303)
 def root_report(self):
  p=self.payload();p['claims'][0]='seer';p['seers']=[{'day':1,'reporter':1,'target':3,'color':'white'}];self.assertEqual(self.table(p).status_code,200)
 def test_local_log_inherited_table_and_stable_same_day_phase_ids(self):
  self.root_report();root=self.bid();self.advance(2);night=self.bid();self.assertNotEqual(root,night);g=self.g();self.assertEqual(g['public_log']['board_graph']['nodes'][night]['day'],1);self.assertEqual(g['public_log']['local_batches'],[]);self.assertEqual(len(g['seer_inputs']),1)
  self.advance(3);day2=self.bid();p=self.payload();p['seers'].append({'day':2,'reporter':1,'target':4,'color':'white'});self.assertEqual(self.table(p).status_code,200);g=self.g();self.assertEqual(len(g['public_log']['batches']),2);self.assertEqual(len(g['public_log']['local_batches']),1);self.assertEqual(g['public_log']['local_batches'][0]['board_id'],day2);html=self.c.get('/main').get_data(as_text=True);self.assertNotIn('data-public-batch="1"',html);self.assertIn('data-public-batch="2"',html);self.assertEqual(len(g['seer_inputs']),2)
 def test_same_day_sibling_branch_isolation_and_revisit_restores_local_events(self):
  self.root_report();self.advance(2);night=self.bid();self.advance(3);a=self.bid();p=self.payload();p['seers'].append({'day':2,'reporter':1,'target':4,'color':'white'});self.table(p);self.back();self.assertEqual(self.bid(),night);self.advance(4);b=self.bid();g=self.g();self.assertNotEqual(a,b);self.assertNotEqual(g['public_log']['board_graph']['nodes'][a]['branch'],g['public_log']['board_graph']['nodes'][b]['branch']);self.assertEqual(g['public_log']['local_batches'],[]);self.assertTrue(all(r['day']==1 for r in g['seer_inputs']));self.back();self.advance(3);self.assertEqual(self.bid(),a);self.assertEqual(len(self.g()['public_log']['local_batches']),1);self.assertTrue(any(r['day']==2 for r in self.g()['seer_inputs']))
 def test_late_co_day1_result_published_day2_preview_commit_back_and_restore(self):
  root=self.bid();self.advance(2);self.advance(3);day2=self.bid();p=self.payload();p['claims'][0]='seer';p['seers']=[{'day':1,'reporter':1,'target':3,'color':'white'},{'day':2,'reporter':1,'target':4,'color':'white'}];before=self.g();r=self.table(p,True);self.assertEqual(r.status_code,200,r.data);self.assertEqual(self.g(),before);preview=r.get_json()['html'];self.assertEqual(self.table(p).status_code,200);g=self.g();self.assertEqual(g['public_log']['report_publications']['seer:1:1']['board_id'],day2);self.assertEqual(g['public_log']['report_publications']['seer:1:1']['slot'],2);self.assertIn('占い Day1：Player3＝白',self.c.get('/main').get_data(as_text=True));rate=lambda h:re.search(r'id="village-rate"[^>]*data-fraction="([^"]+)"',h).group(1);self.assertEqual(rate(preview),rate(self.c.get('/main').get_data(as_text=True)))
  cookie=self.c.get_cookie('session');cold=self.a.test_client();cold.set_cookie('session',cookie.value);self.assertEqual(cold.get('/main').status_code,200)
  with cold.session_transaction() as q:self.assertEqual(q['game']['public_log']['board_id'],day2)
  self.back();self.assertEqual(self.g()['seer_inputs'],[]);self.back();self.assertEqual(self.bid(),root);self.advance(2);self.advance(3);self.assertEqual(self.bid(),day2);self.assertEqual(len(self.g()['seer_inputs']),2)
 def test_late_co_day3_all_past_days_and_current_owner_withdraw_keeps_parent_events(self):
  self.advance(2);self.advance(3);self.advance(4);self.advance(5);day3=self.bid();p=self.payload();p['claims'][0]='seer';p['seers']=[{'day':1,'reporter':1,'target':2,'color':'white'},{'day':2,'reporter':1,'target':3,'color':'white'},{'day':3,'reporter':1,'target':6,'color':'black'}];r=self.table(p);self.assertEqual(r.status_code,200,r.data);self.assertEqual({v['board_id'] for v in self.g()['public_log']['report_publications'].values()},{day3})
 def test_wrong_board_draft_rejected_without_mutation(self):
  self.root_report();root=self.bid();self.advance(2);before=self.g();self.assertEqual(self.table(self.payload(),True,root).status_code,409);self.assertEqual(self.g(),before)
 def test_child_withdraw_does_not_erase_parent_owned_log(self):
  self.root_report();root=self.bid();self.advance(2);self.advance(3);child=self.bid();p=self.payload();p['claims'][0]='latent';p['seers']=[];self.assertEqual(self.table(p).status_code,200);g=self.g();self.assertEqual(g['seer_inputs'],[]);self.assertTrue(g['public_log']['board_graph']['nodes'][root]['local_batches'][0]['events']);self.assertTrue(all(e['action']=='withdraw' for e in g['public_log']['local_batches'][0]['events']));self.back();self.back();self.assertEqual(self.bid(),root);self.assertEqual(len(self.g()['seer_inputs']),1)
 def test_parent_commit_retires_descendants_and_forward_regenerates_without_old_input(self):
  self.root_report();root=self.bid();self.advance(2);self.advance(3);child=self.bid();p=self.payload();p['seers'].append({'day':2,'reporter':1,'target':4,'color':'white'});self.table(p);before=self.g()['public_log']['board_graph']['nodes'][child]['input_revision'];self.back();self.back();p=self.payload();p['seers'][0]['target']=5;self.assertEqual(self.table(p).status_code,200);g=self.g();self.assertGreater(g['public_log']['board_graph']['nodes'][child]['input_revision'],before);self.assertFalse(g['public_log']['board_graph']['nodes'][child]['active']);self.assertTrue(g['public_log']['board_graph']['archives']);self.advance(2);self.advance(3);self.assertNotEqual(self.bid(),child);self.assertEqual(self.g()['seer_inputs'][0]['target'],5);self.assertEqual(len(self.g()['seer_inputs']),1);self.assertEqual(self.g()['public_log']['local_batches'],[])
  from werewolf.seer_manual import replay
  from fractions import Fraction
  self.assertEqual(replay(self.g())[1].board.wolf_probability(4),Fraction(1,3))

 def test_initial_none_allows_fake_past_report_without_blanket_input_ban(self):
  self.c.post('/start',data={'citizens':'5','seers':'1','wolves':'1','initial_seer':'none','day':'max','night':'max'});self.advance(2);self.advance(3);p=self.payload();p['claims'][0]=p['claims'][3]='seer';p['seers']=[{'day':1,'reporter':1,'target':3,'color':'black'},{'day':2,'reporter':4,'target':5,'color':'white'}];r=self.table(p);self.assertEqual(r.status_code,200,r.data)
  from werewolf.seer_manual import replay
  _,progress=replay(self.g());self.assertTrue(all(w[2]&(1<<3) and not w[2]&1 for w in progress.board.worlds))
 def test_late_medium_co_generates_acquisition_days_from_executions(self):
  self.c.post('/start',data={'citizens':'5','mediums':'1','wolves':'1','day':'max','night':'max'});self.advance(2);self.advance(3);self.advance(4);self.advance(5);p=self.payload();p['claims'][0]='medium';p['mediums']=[{'day':2,'reporter':1,'target':2,'color':'white'},{'day':3,'reporter':1,'target':4,'color':'white'}];r=self.table(p,True);self.assertEqual(r.status_code,200,r.data);self.assertEqual(self.table(p).status_code,200);self.assertEqual(len(self.g()['reports']),2)

 def test_preview_noop_and_failed_commit_keep_descendants(self):
  self.root_report();self.advance(2);self.advance(3);child=self.bid();self.back();self.back();before=self.g();p=self.payload();p['seers'][0]['target']=5;self.assertEqual(self.table(p,True).status_code,200);self.assertEqual(self.g(),before);self.assertEqual(self.table(self.payload()).status_code,400);self.assertEqual(self.g(),before);p['seers'][0]['color']=None;self.assertEqual(self.table(p).status_code,400);self.assertEqual(self.g(),before);p=self.payload();p['seers'][0]['color']='black';self.assertEqual(self.table(p).status_code,400);self.assertEqual(self.g(),before);self.assertTrue(self.g()['public_log']['board_graph']['nodes'][child]['active'])
 def test_sibling_unaffected_and_owner_only_correction(self):
  self.root_report();root=self.bid();self.advance(2);self.advance(3);a=self.bid();p=self.payload();p['seers'].append({'day':2,'reporter':1,'target':4,'color':'white'});self.table(p);self.advance(6);child=self.bid();self.back();self.back();self.advance(4);b=self.bid();self.back();self.advance(3);self.assertEqual(self.bid(),a);p=self.payload();p['seers'][1]['target']=5;self.assertEqual(self.table(p).status_code,200);graph=self.g()['public_log']['board_graph'];self.assertFalse(graph['nodes'][child]['active']);self.assertTrue(graph['nodes'][b]['active']);self.assertEqual(graph['nodes'][graph['nodes'][a]['parent']]['children'],[a,b])
  old=self.g();r=self.c.post('/public-log',data={'revision':str(old['revision']),'board_id':a,'operation':'publish','payload':json.dumps({'delete':1})});self.assertEqual(r.status_code,400);self.assertEqual(self.g(),old)
 def test_owner_log_correction_and_delete_commit_retire_child_generations(self):
  self.root_report();self.advance(2);child=self.bid();self.back();g=self.g();events=copy.deepcopy(g['public_log']['local_batches'][0]['events']);events[1]['target']=5
  r=self.c.post('/public-log',data={'revision':str(g['revision']),'board_id':self.bid(),'operation':'publish','payload':json.dumps({'replace':1,'mode':'simultaneous','events':events})});self.assertEqual(r.status_code,200,r.data);self.assertFalse(self.g()['public_log']['board_graph']['nodes'][child]['active']);self.advance(2);new=self.bid();self.back();g=self.g();r=self.c.post('/public-log',data={'revision':str(g['revision']),'board_id':self.bid(),'operation':'publish','payload':json.dumps({'delete':1})});self.assertEqual(r.status_code,200,r.data);self.assertFalse(self.g()['public_log']['board_graph']['nodes'][new]['active']);self.assertEqual(len(self.g()['public_log']['board_graph']['archives']),3)

 def test_same_content_log_correction_keeps_children_and_no_archive(self):
  self.root_report();self.advance(2);child=self.bid();self.back();before=self.g();events=copy.deepcopy(before['public_log']['local_batches'][0]['events']);r=self.c.post('/public-log',data={'revision':str(before['revision']),'board_id':self.bid(),'operation':'publish','payload':json.dumps({'replace':1,'mode':'simultaneous','events':events})});self.assertEqual(r.status_code,200,r.data);g=self.g();self.assertEqual(g['public_log']['board_graph']['nodes'][child],before['public_log']['board_graph']['nodes'][child]);self.assertEqual(g['public_log']['board_graph'].get('archives'),before['public_log']['board_graph'].get('archives'))
