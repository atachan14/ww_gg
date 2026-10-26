import json,tempfile,unittest
from html.parser import HTMLParser
from app import create_app

class TargetControls(HTMLParser):
 def __init__(self,html):super().__init__();self.targets={};self.advance=None;self.feed(html)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='input' and a.get('name')=='target':self.targets[int(a['value'])]=dict(disabled='disabled'in a,checked='checked'in a)
  if tag=='button' and a.get('id')=='advance-button':self.advance='disabled'in a

class StagedTargetSubmissionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.app=create_app(dict(TESTING=True,SECRET_KEY='staged-target-only',PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=self.temp.name,CALCULATION_POSITION_ENABLED=False))
  self.c=self.app.test_client();self.c.post('/start',data=dict(citizens=4,wolves=1,day='max',night='max',fake_reports='max',win_cutoff=0))
 def complete(self):
  self.shell=self.c.get('/main',headers={'Sec-Fetch-Dest':'document'}).text
  r=self.c.get('/navigation/calculation?occurrence=h0&revision=0&request_id=1',headers={'Accept':'application/x-ndjson'})
  events=[json.loads(line) for line in r.data.splitlines()];self.assertEqual([e['event'] for e in events],['roles','complete']);self.assertTrue(events[-1]['value_complete']);return events
 def test_role_frames_and_completed_frames_define_different_legal_controls(self):
  events=self.complete();initial=TargetControls(self.shell);roles=TargetControls(events[0]['html']);done=TargetControls(events[1]['html'])
  self.assertEqual(set(done.targets),set(range(1,6)));self.assertTrue(all(t['disabled'] for t in initial.targets.values()));self.assertTrue(all(t['disabled'] for t in roles.targets.values()))
  self.assertTrue(all(not t['disabled'] for t in done.targets.values()));self.assertEqual([p for p,t in done.targets.items() if t['checked']],[1]);self.assertFalse(done.advance)
 def test_missing_disabled_target_is_rejected_but_completed_choice_advances_exactly(self):
  self.complete();before=self.c.get('/navigation').json
  bad=self.c.post('/navigation/phase-next',json=dict(revision=0,target=0,reuse_forward=True));self.assertEqual(bad.status_code,400);self.assertEqual(bad.json['error'],'Invalid player')
  self.assertEqual(self.c.get('/navigation').json['revision'],0)
  good=self.c.post('/navigation/phase-next',json=dict(revision=0,target=1,reuse_forward=False));self.assertEqual(good.status_code,200,good.json);self.assertNotIn(1,good.json['board']['alive']);self.assertEqual(good.json['village_win'],before['village_win'])
 def test_existing_phase_forward_still_needs_no_new_target(self):
  self.complete();one=self.c.post('/navigation/phase-next',json=dict(revision=0,target=1,reuse_forward=False)).json
  back=self.c.post('/navigation/phase-back',json=dict(revision=1)).json
  self.assertIn('data-navigation-phase-forward="true"',back['html'])
  again=self.c.post('/navigation/phase-next',json=dict(revision=2,target=0,reuse_forward=True))
  self.assertEqual(again.status_code,200,again.json);self.assertEqual(again.json['current']['occurrence'],one['current']['occurrence']);self.assertEqual(len(again.json['occurrences']),len(back['occurrences']))
