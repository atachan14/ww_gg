import json
import unittest
from copy import deepcopy
from fractions import Fraction
from app import create_app
from werewolf.strategy_ui import co_editor, resolve_co_editor
from werewolf.exact import ClaimPolicy, VILLAGE_ROLES

class StrategyEditorTests(unittest.TestCase):
    def setUp(self):
        self.c=create_app({'TESTING':True,'SECRET_KEY':'strategy-ui'}).test_client()
        self.c.post('/start',data={'citizens':'3','mediums':'1','wolves':'1','day':'max','night':'max','cco_medium':'none'})
    def state(self):
        with self.c.session_transaction() as s:return deepcopy(s['game'])
    def form(self,editor=None,**extra):
        s=self.state();d={'revision':str(s['revision']),'day':s['policy']['day'],'night':s['policy']['night'],'strategy_ui':json.dumps(editor or s.get('strategy_ui',co_editor(s['claim_policy'])))};d.update(extra);return d
    def test_legacy_adapter_preserves_every_condition_combination(self):
        for value in ('none','filled','counter',[],['filled','counter']):
            policy={r:value for r in VILLAGE_ROLES}
            _,resolved=resolve_co_editor(co_editor(policy))
            for r in VILLAGE_ROLES:self.assertEqual(set(ClaimPolicy(**resolved).conditions(r)),set(ClaimPolicy(**policy).conditions(r)))
    def test_common_and_individual_exception_history_and_back(self):
        editor=co_editor(self.state()['claim_policy']);editor['common']=['filled','counter'];editor['roles']['medium']={'local':[],'disabled':['filled','counter']}
        self.assertEqual(self.c.post('/strategy',data=self.form(editor,target='2')).status_code,303)
        self.assertEqual(self.state()['claim_policy']['medium'],[])
        self.assertEqual(self.state()['claim_policy']['villager'],['counter','filled'])
        self.assertEqual(self.c.post('/advance',data=self.form(target='2')).status_code,303)
        step=self.state()['history'][0]
        other=deepcopy(editor);other['roles']['medium']['disabled']=[]
        self.assertEqual(self.c.post('/strategy',data=self.form(other)).status_code,303)
        self.assertEqual(self.state()['history'][0],step)
        self.c.post('/back',data={'revision':str(self.state()['revision'])})
        self.assertEqual(self.state()['strategy_ui'],resolve_co_editor(editor)[0])
        self.assertEqual(self.state()['selection'],2)
    def test_unsupported_and_duplicate_configuration_rejected_atomically(self):
        original=self.state()
        for bad in ({'common':['dayX'],'roles':co_editor(original['claim_policy'])['roles']}, {'common':['filled','filled'],'roles':co_editor(original['claim_policy'])['roles']}, {'fakeable':['all']}):
            self.assertEqual(self.c.post('/strategy',data=self.form(bad)).status_code,400)
            self.assertEqual(self.state(),original)
        self.assertEqual(self.c.post('/strategy',data=self.form(disclose='white')).status_code,400)
        self.assertEqual(self.state(),original)
    def test_adapter_does_not_change_exact_values_or_legacy_model(self):
        import re
        before=self.c.get('/main').get_data(as_text=True)
        self.c.post('/strategy',data=self.form())
        after=self.c.get('/main').get_data(as_text=True)
        values=lambda h:re.findall('data-fraction="([^"]+)"',h)
        self.assertEqual(values(before),values(after))
        with self.c.session_transaction() as session:
            state=session['game'];state['model']='equal';session['game']=state
        self.c.post('/strategy',data=self.form())
        self.assertEqual(self.state()['model'],'equal')
    def test_model_switch_only_before_history_and_policy_roundtrip(self):
        self.assertEqual(self.c.post('/strategy',data=self.form(model='equal',day='random',fake_reports='random')).status_code,303)
        self.assertEqual(self.state()['policy']['fake_reports'],'random')
        self.assertEqual(self.c.post('/advance',data=self.form(target='2')).status_code,303)
        before=self.state()
        self.assertEqual(self.c.post('/strategy',data=self.form(model='group')).status_code,400)
        self.assertEqual(self.state(),before)
