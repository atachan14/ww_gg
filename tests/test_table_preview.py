import copy,json,re,unittest
from app import create_app
from werewolf.seer_manual import replay
class TablePreviewTests(unittest.TestCase):
 def setUp(self):
  self.a=create_app({'TESTING':True,'SECRET_KEY':'table-preview','HYBRID_TABLE_PREVIEW':True});self.c=self.a.test_client();self.c.post('/start',data={'citizens':'2','seers':'1','wolves':'2','day':'max','night':'max'})
 def g(self):
  with self.c.session_transaction() as s:return copy.deepcopy(s['game'])
 def draft(self):
  g=self.g();return {'claims':g['claims'],'seers':g.get('seer_inputs',[]),'mediums':g.get('reports',[])}
 def send(self,p,commit=False,revision=None):return self.c.post('/table-publish' if commit else '/table-preview',data={'revision':str(self.g()['revision'] if revision is None else revision),'request_id':'7','payload':json.dumps(p)})
 def example(self):
  p=self.draft();p['claims'][:2]=['seer','seer'];p['seers']=[{'day':1,'reporter':1,'target':3,'color':'white'},{'day':1,'reporter':2,'target':3,'color':'black'}];return p
 def rate(self,html):return re.search(r'id="village-rate"[^>]*data-fraction="([^"]+)"',html).group(1)
 def test_ephemeral_same_batch_and_value_on_commit(self):
  old=self.g();p=self.example();r=self.send(p);self.assertEqual(r.status_code,200,r.data);d=r.get_json();self.assertEqual(d['request_id'],'7');self.assertEqual(d['batch']['mode'],'simultaneous');self.assertEqual(len(d['batch']['events']),4);self.assertEqual(self.g(),old);self.assertEqual(self.rate(d['html']),'1/2')
  self.assertEqual(self.send(p,True).status_code,200);g=self.g();self.assertEqual(g['revision'],old['revision']+1);self.assertEqual(len(g['public_log']['batches']),1);self.assertEqual(len(g['public_log']['batches'][0]['events']),4);self.assertEqual(self.rate(self.c.get('/main').get_data(as_text=True)),self.rate(d['html']))
 def test_partial_and_stale_do_not_save_or_return_old_numeric(self):
  p=self.example();p['seers'][0]['color']=None;old=self.g();r=self.send(p);self.assertEqual(r.status_code,400);self.assertNotIn('html',r.get_json());self.assertEqual(self.g(),old);self.assertEqual(self.send(self.example(),revision=old['revision']+1).status_code,409)
 def test_co_withdraw_cascades_reports_and_no_revival(self):
  self.send(self.example(),True);before=self.g();p=self.draft();p['claims'][1]='latent';r=self.send(p);self.assertEqual(r.status_code,200,r.data);events=r.get_json()['batch']['events'];self.assertEqual({e['kind'] for e in events},{'co','seer'});self.assertTrue(all(e['action']=='withdraw' for e in events));self.assertEqual(self.g(),before)
  self.assertEqual(self.send(p,True).status_code,200);g=self.g();self.assertEqual([r['reporter'] for r in g['seer_inputs']],[1]);self.assertEqual(len(g['public_log']['batches'][0]['events']),4);_,b=replay(g);self.assertTrue(any(w[0]&8 for w in b.board.worlds));self.assertTrue(any(r['player']==2 for r in g['public_log']['acquisition_provenance']))
  p=self.draft();p['claims'][1]='seer';self.assertEqual(self.send(p,True).status_code,200);self.assertEqual([r['reporter'] for r in self.g()['seer_inputs']],[1])
 def test_result_change_uses_only_new_target_not_old_constraint(self):
  self.send(self.example(),True);p=self.draft();p['seers'][0]['target']=4;r=self.send(p);self.assertEqual(r.status_code,200,r.data);self.assertEqual(self.send(p,True).status_code,200);g=self.g();self.assertEqual(len(g['public_log']['batches']),2);self.assertEqual(g['public_log']['batches'][1]['events'][0]['action'],'change');_,b=replay(g);self.assertEqual({w[0] for w in b.board.worlds},{6,18});self.assertEqual(g['public_log']['batches'][0]['events'][2]['target'],3)
 def test_deleting_referenced_item_is_atomic_rejection(self):
  self.send(self.example(),True);p=self.draft();p['seers'][0]['target']=4;self.send(p,True);old=self.g();r=self.c.post('/public-log',data={'revision':str(old['revision']),'operation':'publish','payload':json.dumps({'delete':1})});self.assertEqual(r.status_code,400);self.assertEqual(self.g(),old)
 def test_roundtrip_cookie_and_default_not_exposed(self):
  self.send(self.example(),True);p=self.draft();p['claims'][1]='latent';self.send(p,True);g=self.g();self.assertEqual(self.c.get('/main').status_code,200);self.assertEqual(self.g(),g);self.a.config['HYBRID_TABLE_PREVIEW']=False;self.assertEqual(self.send(self.draft()).status_code,404);self.assertNotIn(b'data-hybrid-table',self.c.get('/main').data)

 def test_old_cookie_migration_and_past_item_correction_preserve_followup_reference(self):
  self.send(self.example(),True);g=self.g();g.pop('public_log')
  with self.c.session_transaction() as q:q['game']=g
  p=self.draft();p['seers'][0]['target']=4;self.assertEqual(self.send(p,True).status_code,200);current=self.g();self.assertTrue(current['public_log']['legacy']);self.assertEqual(current['seer_inputs'][0]['target'],4)
  # Separate v2 item lineage; correction retains the identity referred by change.
  self.setUp();self.send(self.example(),True);p=self.draft();p['seers'][0]['target']=4;self.send(p,True);g=self.g();events=g['public_log']['batches'][0]['events'];events[2]['target']=5
  r=self.c.post('/public-log',data={'revision':str(g['revision']),'operation':'publish','payload':json.dumps({'mode':'simultaneous','events':events,'replace':1})});self.assertEqual(r.status_code,200,r.data);now=self.g();self.assertEqual(now['public_log']['batches'][1]['events'][0]['ref'],now['public_log']['batches'][0]['events'][2]['id']);self.assertEqual(now['seer_inputs'][0]['target'],4)
 def test_back_trims_later_change_and_cold_cookie_restores_projection(self):
  self.send(self.example(),True)
  for target in (2,3):
   g=self.g();self.c.post('/advance',data={'revision':str(g['revision']),'target':str(target),'day':'max','night':'max'})
  p=self.draft();p['seers'].append({'day':2,'reporter':1,'target':4,'color':'black'});self.assertEqual(self.send(p,True).status_code,200);before=self.g();cookie=self.c.get_cookie('session');cold=self.a.test_client();cold.set_cookie('session',cookie.value);self.assertEqual(cold.get('/main').status_code,200)
  with cold.session_transaction() as q:self.assertEqual(q['game'],before)
  self.c.post('/back',data={'revision':str(before['revision'])});g=self.g();self.assertEqual(len(g['public_log']['batches']),1);self.assertTrue(all(r['day']==1 for r in g['seer_inputs']))

 def test_cell_editor_page_omits_readonly_legacy_co_add_rows(self):
  html=self.c.get('/main').get_data(as_text=True)
  self.assertIn('data-hybrid-table',html)
  self.assertIn('board_table.js',html)
  self.assertIn('data-table-update',html)
  self.assertNotIn('class="co-add-row"',html)
  self.assertNotIn('id="co-add-1"',html)
