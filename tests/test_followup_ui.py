import re
import unittest
from copy import deepcopy
from app import create_app
from werewolf.exact import ClaimPolicy, initial_board, condition_claims

class FollowupUITests(unittest.TestCase):
    def setUp(self):
        self.client=create_app({'TESTING':True,'SECRET_KEY':'ui-tests'}).test_client()
        self.client.post('/start',data={'citizens':'3','mediums':'1','wolves':'1','day':'max','night':'max','cco_medium':'none'})
    def state(self):
        with self.client.session_transaction() as s:return deepcopy(s['game'])
    def form(self,**changes):
        s=self.state(); data={'revision':str(s['revision']),'day':s['policy']['day'],'night':s['policy']['night']};data.update(changes);return data
    def selected(self,html):
        return re.findall(r'<input type="radio" name="target" value="(\d+)"[^>]* checked',html)
    def test_default_max_tie_and_manual_preservation(self):
        html=self.client.get('/main').get_data(as_text=True)
        self.assertEqual(self.selected(html),['1'])
        self.assertIsNone(self.state()['selection'])
        self.client.post('/strategy',data=self.form(co_1='wolf'))
        html=self.client.get('/main').get_data(as_text=True)
        self.assertEqual(self.selected(html),['1']) # known wolf is the optimal public action
        self.client.post('/strategy',data=self.form(target='3'))
        self.client.post('/strategy',data=self.form(day='random'))
        self.assertEqual(self.selected(self.client.get('/main').get_data(as_text=True)),['3'])
        self.assertEqual(self.state()['selection'],3)
    def test_random_has_no_new_automatic_choice(self):
        self.client.post('/strategy',data=self.form(day='random'))
        self.assertEqual(self.selected(self.client.get('/main').get_data(as_text=True)),[])
        self.assertIsNone(self.state()['selection'])
    def test_condition_collection_and_board_history_are_preserved(self):
        data=self.form(target='2',cco_present_medium='1',cco_conditions_medium=['filled','counter'],co_1='medium')
        self.assertEqual(self.client.post('/advance',data=data).status_code,303)
        first=deepcopy(self.state()['history'][0])
        self.assertEqual(first['claim_policy']['medium'],['counter','filled'])
        self.assertEqual(self.client.post('/strategy',data=self.form(day='random',night='random',cco_present_medium='1')).status_code,303)
        self.assertEqual(self.state()['claim_policy']['medium'],[])
        self.assertEqual(self.state()['history'][0],first)
        self.client.post('/back',data={'revision':str(self.state()['revision'])})
        self.assertEqual(self.state()['policy'],first['policy'])
        self.assertEqual(self.state()['claim_policy'],first['claim_policy'])
        self.assertEqual(self.state()['selection'],2)
    def test_existing_conditions_are_or_and_invalid_collections_rejected(self):
        board=initial_board(5,1,1);claims=('medium','latent','latent','latent','latent')
        one=condition_claims(board,claims,ClaimPolicy(medium='counter'))
        both=condition_claims(board,claims,ClaimPolicy(medium=['counter','filled']))
        self.assertEqual(one.role_belief,both.role_belief)
        for values in (['counter','counter'],['black'],['none','filled']):
            before=self.state()
            self.assertEqual(self.client.post('/strategy',data=self.form(cco_present_medium='1',cco_conditions_medium=values)).status_code,400)
            self.assertEqual(before,self.state())
        before=self.state()
        self.assertEqual(self.client.post('/strategy',data=self.form(cco_conditions_medium=['counter'])).status_code,400)
        self.assertEqual(before,self.state())
        self.assertIn('current-rate-tip',self.client.get('/main').get_data(as_text=True))
        self.assertIn('data-disclosure',self.client.get('/main').get_data(as_text=True))

if __name__=='__main__':unittest.main()
