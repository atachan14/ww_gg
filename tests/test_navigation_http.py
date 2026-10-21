import tempfile,unittest
from fractions import Fraction as F
from app import create_app

class NavigationHttpTests(unittest.TestCase):
 def setUp(self):
  self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
  self.app=create_app(dict(TESTING=True,SECRET_KEY='navigation-http-tests',PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=self.directory.name))
  self.client=self.app.test_client()
  self.client.post('/start',data=dict(citizens='3',wolves='1',seers='1',day='max',night='max',fake_reports='max'))
 def post(self,operation,revision,**values):return self.client.post('/navigation/'+operation,json=dict(revision=revision,**values))
 def test_navigation_keeps_day1_root_old_futures_and_revision(self):
  root=self.client.get('/navigation');self.assertEqual(root.status_code,200);before=root.json
  child=self.post('advance',0,target=3);self.assertEqual(child.status_code,200);self.assertNotIn(3,child.json['board']['alive'])
  back=self.post('back',1);self.assertEqual(back.json['current']['occurrence'],'h0')
  stale=self.post('advance',1,target=4);self.assertEqual(stale.status_code,409)
  restored=self.post('forward',2);self.assertEqual(restored.json['current']['occurrence'],'h1')
  self.assertEqual(restored.json['root'],before['root']);self.assertEqual(len(restored.json['occurrences']),2)
 def test_manual_input_is_zero_selection_not_impossible_evidence(self):
  before=self.client.get('/navigation').json
  update=self.post('public-input',0,claims=['seer','seer','latent','latent','latent'],reports=[dict(acquired_day=1,published_day=1,player=1,target=3,color='white'),dict(acquired_day=1,published_day=1,player=2,target=4,color='white')])
  self.assertEqual(update.status_code,200,update.json)
  self.assertEqual(update.json['occurrences'][-1]['selection_weight'],'0')
  back=self.post('back',1);self.assertEqual(back.json['village_win'],before['village_win'])
  rejected=self.post('public-input',2,claims=['seer','latent','latent','latent','latent'],reports=[dict(acquired_day=1,published_day=1,player=1,target=3,color='black')])
  self.assertEqual(rejected.status_code,400);self.assertEqual(self.client.get('/navigation').json['revision'],2)
 def test_clients_cannot_supply_weights_or_transport(self):
  response=self.post('advance',0,target=3,selection_weight='1/3',names=[1,3,2,4,5])
  self.assertEqual(response.status_code,400);self.assertEqual(self.client.get('/navigation').json['revision'],0)
