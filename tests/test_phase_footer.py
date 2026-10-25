import unittest,tempfile,json,re
from types import SimpleNamespace as NS
from app import create_app
from werewolf.phase_navigation import phase_targets

class FakeHistory:
 def __init__(self,rows):self.rows={};self.children_map={};self.facts={}
 def add(self,parent,day,phase,kind='public_input'):
  key='h'+str(len(self.rows));row=NS(key=key,parent=parent,selector={'kind':kind});self.rows[key]=row;self.facts[key]=NS(source=NS(public=NS(day=day,phase=phase)));self.children_map[key]=[]
  if parent is not None:self.children_map[parent].append(row)
  return key
 def state(self,key):return self.facts[key]
 def occurrence(self,key):return self.rows[key]
 def children(self,key):return self.children_map[key]
 def path(self,key):
  rows=[]
  while key is not None:rows.append(self.rows[key]);key=self.rows[key].parent
  return tuple(reversed(rows))

class PhaseTargetTests(unittest.TestCase):
 def test_ancestry_not_newer_sibling_and_latest_reachable_adjacent_update(self):
  h=FakeHistory([]);root=h.add(None,1,'day','root');a=h.add(root,1,'day');a2=h.add(a,1,'day');night=h.add(a2,1,'night','advance');d=h.add(night,2,'day','advance');u1=h.add(d,2,'day');u2=h.add(u1,2,'day');b=h.add(root,1,'day');bn=h.add(b,1,'night','advance');bd=h.add(bn,2,'day','advance');bu=h.add(bd,2,'day')
  game=NS(history=h,occurrence=h.occurrence(night))
  self.assertEqual(phase_targets(game),{'previous':{'key':a2,'day':1,'phase':'day'},'next':{'key':u2,'day':2,'phase':'day'}})
  # Existing alternative within the current branch: last-created update wins.
  alternative=h.add(night,2,'day','advance');latest=h.add(alternative,2,'day');self.assertEqual(phase_targets(game)['next']['key'],latest)
  game.occurrence=h.occurrence(a2);self.assertIsNone(phase_targets(game)['previous']);self.assertEqual(phase_targets(game)['next']['key'],night)
  game.occurrence=h.occurrence(root);self.assertEqual(phase_targets(game)['next']['key'],bn)
 def test_start_fallback_and_no_future_materialization(self):
  h=FakeHistory([]);root=h.add(None,1,'day','root');game=NS(history=h,occurrence=h.occurrence(root));self.assertEqual(phase_targets(game),{'previous':None,'next':None});self.assertEqual(len(h.rows),1)
  start=h.add(root,1,'night','advance');self.assertEqual(phase_targets(game)['next']['key'],start)

class PhaseFooterHttpTests(unittest.TestCase):
 def setUp(self):
  self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
  self.config=dict(TESTING=True,SECRET_KEY='phase-footer-only',PERSISTENT_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,NAVIGATION_DIRECTORY=self.directory.name)
  self.app=create_app(self.config);self.c=self.app.test_client();self.c.post('/start',data=dict(citizens='3',seers='1',wolves='1',day='random',night='random',fake_reports='random',win_cutoff='0'));self.state=self.c.get('/navigation').get_json()
 def post(self,op,**kw):
  r=self.c.post('/navigation/'+op,json={'revision':self.state['revision'],**kw});self.assertEqual(r.status_code,200,(r.get_json() or {}).get('error'));self.state=r.get_json();return self.state['current']['occurrence']
 def footer(self):return self.state['html'].split('<footer class="phase-footer">',1)[1].split('</footer>',1)[0]
 def test_update_has_no_same_phase_back_and_night_back_follows_A_not_B(self):
  self.assertIsNone(self.state['current']['phase_parent']);self.assertIsNone(self.state['current']['phase_forward'])
  a=self.post('public-input',claims=['seer','latent','latent','latent','latent'],reports=[dict(acquired_day=1,published_day=1,player=1,target=3,color='white')])
  self.assertNotIn('id="back-button"',self.footer());self.assertIn('ゲーム設定に戻る',self.footer());self.assertIn('Day1・夜へ',self.footer());self.assertNotIn('footer-help',self.footer())
  a2=self.post('public-input',claims=['seer','seer','latent','latent','latent'],reports=[dict(acquired_day=1,published_day=1,player=1,target=3,color='white'),dict(acquired_day=1,published_day=1,player=2,target=4,color='white')])
  night=self.post('phase-next',target=5,reuse_forward=False)
  self.post('move',occurrence='h0');b=self.post('public-input',claims=['latent','seer','latent','latent','latent'],reports=[dict(acquired_day=1,published_day=1,player=2,target=4,color='white')]);self.assertNotEqual(a2,b)
  self.post('move',occurrence=night);self.assertEqual(self.state['current']['phase_parent']['key'],a2);self.assertNotIn('footer-help',self.footer());self.assertIn('Day2・昼へ',self.footer())
  self.assertEqual(self.post('phase-back'),a2)
  self.assertEqual(self.post('phase-next',target=0),night)
  cookie=self.c.get_cookie('session').value;other=create_app(self.config).test_client();other.set_cookie('session',cookie);restored=other.get('/navigation').get_json();self.assertEqual(restored['current']['phase_parent']['key'],a2);self.assertNotIn('footer-help',restored['html'].split('<footer class="phase-footer">')[1].split('</footer>')[0])
 def test_next_phase_uses_last_created_updates_and_preserves_occurrences(self):
  self.post('phase-next',target=3,reuse_forward=False);night=self.state['current']['occurrence'];day=self.post('phase-next',target=4,reuse_forward=False)
  seed=json.loads(re.search(r'<script type="application/json" id="public-log-seed">(.*?)</script>',self.state['html'],re.S).group(1))
  first=self.post('public-input',claims=['seer','latent','latent','latent','latent'],reports=[dict(acquired_day=1,published_day=2,player=1,target=2,color='white')])
  latest=self.post('public-input',claims=['latent']*5,reports=[dict(acquired_day=1,published_day=2,player=1,target=2,color='white')])
  count=len(self.state['occurrences']);self.post('move',occurrence=night);self.assertEqual(self.state['current']['phase_forward']['key'],latest)
  self.assertEqual(self.post('phase-next',target=0),latest);self.assertEqual(len(self.state['occurrences']),count)
