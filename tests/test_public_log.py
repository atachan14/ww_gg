import unittest,json,copy
from unittest.mock import patch
from app import create_app
from werewolf.public_log import migrate,project
from werewolf.seer_manual import replay

class PublicLogTests(unittest.TestCase):
 def setUp(self):
  self.app=create_app({'TESTING':True,'SECRET_KEY':'public-log-test'});self.c=self.app.test_client()
  self.start()
 def start(self,n=5,w=2,s=1,m=0,h=0):
  self.assertEqual(self.c.post('/start',data={'citizens':str(n-w-s-m-h),'wolves':str(w),'seers':str(s),'mediums':str(m),'hunters':str(h),'seer_mode':'information-fixed-v1','day':'max','night':'max'}).status_code,303)
  self.assertEqual(self.c.post('/strategy',data=self.form(seer_likelihood='compatibility')).status_code,303)
 def g(self):
  with self.c.session_transaction() as session:return copy.deepcopy(session['game'])
 def form(self,**extra):return {'revision':str(self.g()['revision']),'day':'max','night':'max',**extra}
 def send(self,p,operation='publish',revision=None):return self.c.post('/public-log',data={'revision':str(self.g()['revision'] if revision is None else revision),'operation':operation,'payload':json.dumps(p)})
 def co(self,p,role='seer'):return {'kind':'co','player':p,'role':role}
 def report(self,p,target=3,color='white',day=1):return {'kind':'seer','player':p,'day':day,'target':target,'color':color}
 def batch(self,events,**extra):return {'mode':'single' if len(events)==1 else 'simultaneous','events':events,**extra}
 def publish(self,events,**extra):
  r=self.send(self.batch(events,**extra));self.assertEqual(r.status_code,200,r.data);return r
 def advance(self,p):self.assertEqual(self.c.post('/advance',data=self.form(target=str(p))).status_code,303)
 def test_atomic_batch_matches_direct_manual_model_and_order_invariance(self):
  baseline=self.g();events=[self.co(1),self.co(2),self.report(1),self.report(2,color='black')]
  self.publish(events);g=self.g();self.assertEqual(g['revision'],baseline['revision']+1)
  direct={**baseline,'claims':['seer','seer','latent','latent','latent'],'seer_inputs':[{'day':1,'reporter':1,'target':3,'color':'white'},{'day':1,'reporter':2,'target':3,'color':'black'}]}
  self.assertEqual(replay(g)[1],replay(direct)[1])
  self.start();self.publish(list(reversed(events)));self.assertEqual(replay(self.g())[1],replay(direct)[1])
 def test_invalid_batch_has_no_partial_claims_or_revision(self):
  old=self.g();r=self.send(self.batch([self.co(1),self.report(1,target=1)]));self.assertEqual(r.status_code,400);self.assertEqual(self.g(),old)
  r=self.send(self.batch([self.co(1),self.co(1)]));self.assertEqual(r.status_code,400);self.assertEqual(self.g(),old)
 def test_draft_cancel_restore_no_probability_calculation(self):
  old=self.g();draft=self.batch([self.co(1),{'kind':'seer','player':1}])
  with patch('app.build_tree',side_effect=AssertionError('draft evaluated')):
   self.assertEqual(self.send(draft,'draft').status_code,200)
  g=self.g();self.assertEqual(g['revision'],old['revision']);self.assertEqual(g['claims'],old['claims']);self.assertEqual(g['public_draft']['payload'],draft)
  cookie=self.c.get_cookie('session');cold=self.app.test_client();cold.set_cookie('session',cookie.value)
  self.assertIn(b'public-log-seed',cold.get('/main').data)
  self.assertEqual(self.send({},'cancel').status_code,200);self.assertNotIn('public_draft',self.g())
 def test_order_recorded_and_duplicate_submission_rejected(self):
  rev=self.g()['revision'];self.publish([self.co(1)]);old=self.g()
  self.assertEqual(self.send(self.batch([self.co(2)]),revision=rev).status_code,409);self.assertEqual(self.g(),old)
  self.publish([self.co(2)]);self.assertEqual([b['id'] for b in self.g()['public_log']['batches']],[1,2])
 def test_correction_delete_dependencies_and_duplicate_result(self):
  self.publish([self.co(1),self.co(2)]);self.publish([self.report(1),self.report(2,color='black')]);old=self.g()
  self.assertEqual(self.send({'delete':1}).status_code,400);self.assertEqual(self.g(),old)
  self.assertEqual(self.send(self.batch([self.report(1)])).status_code,400)
  self.publish([self.report(1,target=4),self.report(2,target=4,color='black')],replace=2)
  self.assertEqual(self.g()['public_log']['batches'][1]['id'],2)
  self.assertEqual(self.send({'delete':2}).status_code,200);self.assertEqual(self.g()['seer_inputs'],[])
  self.assertEqual(self.send({'delete':1}).status_code,200);self.assertEqual(self.g()['claims'],['latent']*5)
 def test_back_removes_future_batches_and_draft(self):
  self.publish([self.co(1),self.co(2),self.report(1),self.report(2,color='black')]);self.advance(2);self.advance(3)
  self.publish([self.report(1,target=4,color='black',day=2)])
  self.send(self.batch([self.co(4)]),'draft')
  self.assertEqual(self.c.post('/back',data={'revision':str(self.g()['revision'])}).status_code,303)
  g=self.g();self.assertEqual(len(g['public_log']['batches']),1);self.assertNotIn('public_draft',g);self.assertEqual({r['day'] for r in g['seer_inputs']},{1})
 def test_dead_reporter_past_correction_new_disclosure_rejected(self):
  self.publish([self.co(1),self.co(2),self.report(1),self.report(2,color='black')]);self.advance(2)
  old=self.g();self.assertEqual(self.send(self.batch([self.co(2,'wolf')])).status_code,400);self.assertEqual(self.g(),old)
  self.publish([self.co(1),self.co(2),self.report(1,target=4),self.report(2,target=4,color='black')],replace=1)
  self.assertEqual(len(self.g()['seer_inputs']),2)
 def test_delayed_and_retraction_rejected_explicitly(self):
  self.publish([self.co(1),self.co(2),self.report(1),self.report(2,color='black')]);self.advance(2);self.advance(3)
  old=self.g();r=self.send(self.batch([self.report(1)]));self.assertEqual(r.status_code,400);self.assertIn('遅延公開',r.json['error']);self.assertEqual(self.g(),old)
  r=self.send(self.batch([self.co(1,'latent')]));self.assertEqual(r.status_code,400);self.assertIn('CO撤回',r.json['error'])
 def test_legacy_migration_preserves_progress_and_unknown_order(self):
  self.assertEqual(self.c.post('/strategy',data=self.form(co_1='seer',seer_target_1_1='3',seer_color_1_1='white')).status_code,303)
  old=self.g();new=project(old,migrate(old));self.assertTrue(new['public_log']['legacy']);self.assertEqual(replay(old),replay(new));self.assertEqual(new['public_log']['batches'],[])
  self.publish([self.co(2)]);self.assertIn('旧保存：順序不明',self.c.get('/main').get_data(as_text=True))
 def test_direct_inputs_cannot_bypass_log(self):
  self.publish([self.co(1)]);old=self.g();self.assertEqual(self.c.post('/strategy',data=self.form(co_2='seer')).status_code,400);self.assertEqual(self.g(),old)
 def test_medium_and_mixed_cast_existing_opportunity(self):
  self.start(7,w=2,s=1,m=2);self.publish([self.co(1),self.co(2,'medium'),self.co(3,'medium')]);self.advance(4);self.advance(5)
  events=[{'kind':'medium','player':p,'day':2,'target':4,'color':'white'} for p in (2,3)]
  self.publish(events);self.assertEqual(len(replay(self.g())[1].board.reports),2)
 def test_cookie_restore_of_committed_log(self):
  self.publish([self.co(1),self.co(2),self.report(1),self.report(2,color='black')]);old=self.g();cold=self.app.test_client();cold.set_cookie('session',self.c.get_cookie('session').value)
  self.assertEqual(cold.get('/main').status_code,200)
  with cold.session_transaction() as s:self.assertEqual(s['game'],old)

 def test_legacy_result_correction_and_deletion_do_not_invent_batches(self):
  self.assertEqual(self.c.post('/strategy',data=self.form(co_1='seer',seer_target_1_1='3',seer_color_1_1='white')).status_code,303)
  key={'kind':'seer','player':1,'day':1,'target':3}
  r=self.send({'legacy':{'key':key,'event':self.report(1,target=4)}});self.assertEqual(r.status_code,200,r.data)
  g=self.g();self.assertEqual(g['seer_inputs'][0]['target'],4);self.assertEqual(g['public_log']['batches'],[]);self.assertTrue(g['public_log']['legacy'])
  self.assertEqual(self.send({'delete_legacy':{'key':key}}).status_code,200);self.assertEqual(self.g()['seer_inputs'],[])
 def test_large_or_invalid_publication_preserves_cookie(self):
  old=self.g();r=self.send(self.batch([self.co(1)]),revision=-1);self.assertEqual(r.status_code,409);self.assertEqual(self.g(),old)
  self.assertEqual(self.c.post('/public-log',data={'revision':str(old['revision']),'operation':'publish','payload':'bad'}).status_code,400);self.assertEqual(self.g(),old)
 def test_latent_true_seer_and_nine_player_batch(self):
  self.start(9,w=2,s=1);self.publish([self.co(9),self.report(9,target=8)]);g=self.g();b=replay(g)[1].board;self.assertEqual(b.role_probability(9,'seer'),1);self.assertEqual(b.wolf_probability(8),0)
 def test_finished_new_events_rejected_existing_batch_can_be_corrected(self):
  self.publish([self.co(1),self.co(2),self.report(1),self.report(2,color='black')]);self.advance(2);self.advance(3)
  self.publish([self.report(1,target=4,color='black',day=2)]);self.advance(4)
  old=self.g();self.assertTrue(replay(old)[1].finished)
  self.assertEqual(self.send(self.batch([self.co(5)])).status_code,400);self.assertEqual(self.g(),old)
  self.publish([self.report(1,target=4,color='black',day=2)],replace=2)

 def test_invalid_draft_structure_not_saved(self):
  old=self.g();self.assertEqual(self.send({'mode':'single','events':'bad'},'draft').status_code,400);self.assertEqual(self.g(),old)
