import unittest,tempfile,json
from app import create_app

class BoardLogDayTests(unittest.TestCase):
 def setUp(self):
  directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
  self.app=create_app(dict(TESTING=True,SECRET_KEY='log-day',GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory.name));self.c=self.app.test_client()
  self.c.post('/start',data=dict(citizens=3,seers=1,wolves=1,day='max',night='max',disclosure_common='all'))
 def page(self):return self.c.get('/main').get_data(as_text=True)
 def seed(self,page):return json.loads(page.split('<script type="application/json" id="public-log-seed">')[1].split('</script>')[0])
 def publish(self,reports):
  seed=self.seed(self.page());response=self.c.post('/table-publish',data=dict(revision=seed['revision'],board_id=seed['board_id'],payload=json.dumps(dict(claims=['seer']+['latent']*4,seers=reports,mediums=[]))))
  self.assertEqual(response.status_code,200,response.json)
 def nav(self,op,**kwargs):
  nav=self.c.get('/navigation').json;r=self.c.post('/navigation/'+op,json=dict(revision=nav['revision'],**kwargs));self.assertEqual(r.status_code,200,r.json)
 def test_day_scope_previous_next_and_alternative_history(self):
  first=dict(day=1,reporter=1,target=3,color='white');self.publish([first]);day1=self.c.get('/navigation').json['current']['occurrence']
  self.assertIn('data-log-day="1"',self.page())
  self.nav('advance',target=3);self.assertIn('data-log-day="1"',self.page())
  self.nav('advance',target=4);before=self.c.get('/navigation').json['current']['occurrence'];parent=self.c.get('/game-tree?node='+before+'~0').json['village_win']
  page=self.page();self.assertNotIn('data-log-day="1"',page);self.assertEqual(self.seed(page)['claims'][0],'seer');self.assertEqual(self.seed(page)['seers'],[first])
  late=dict(day=2,reporter=1,target=4,color='white');self.publish([first,late]);white=self.c.get('/navigation').json['current']['occurrence']
  page=self.page();self.assertIn('data-log-day="2"',page);self.assertNotIn('data-log-day="1"',page)
  self.nav('back');self.assertNotIn('data-log-day=',self.page())
  black=dict(day=2,reporter=1,target=2,color='black');self.publish([first,black]);self.assertIn('data-log-day="2"',self.page())
  self.nav('move',occurrence=white);self.assertEqual(self.seed(self.page())['seers'],[first,late])
  self.assertEqual(self.c.get('/game-tree?node='+before+'~0').json['village_win'],parent)
  self.nav('move',occurrence=day1);self.assertIn('data-log-day="1"',self.page());self.assertNotIn('data-log-day="2"',self.page())
  self.nav('back');self.assertNotIn('data-log-day=',self.page())
 def test_delayed_day1_report_appears_on_publication_day2(self):
  self.nav('advance',target=3);self.nav('advance',target=4)
  self.publish([dict(day=1,reporter=1,target=3,color='white'),dict(day=2,reporter=1,target=4,color='white')])
  page=self.page();self.assertIn('data-log-day="2"',page);self.assertIn('data-log-acquired-day="1" data-log-published-day="2"',page)
  self.assertNotIn('data-log-day="1"',page)
