import unittest
from fractions import Fraction as F
from app import create_app
from werewolf.comparison import compare_initial
from werewolf.exact import ClaimPolicy

class TrialTests(unittest.TestCase):
    def run_trial(self,k,**kwargs):
        return compare_initial(5,2,2,('medium',)*k+('latent',)*(9-k),ClaimPolicy(medium='none'),**kwargs)
    def test_one_two_three_claim_residuals(self):
        for k,residual in ((1,F(11,72)),(2,F(4,63)),(3,F(-1,18))):
            result=self.run_trial(k)
            self.assertEqual(result['rows'][0]['values']['medium'],F(7,9))
            self.assertEqual(result['rows'][k]['values']['medium'],residual)
            self.assertEqual(result['totals'],{'villager':5,'medium':2,'wolf':2})
            self.assertTrue(all(row['total']==1 for row in result['rows']))
            self.assertEqual(result['valid'],k<3)
            self.assertIsNone(result['rates'])
        self.assertTrue(any('-1/18' in issue for issue in self.run_trial(3)['issues']))
    def test_ccos_are_validated_without_repairing_trial(self):
        claims=('medium','medium')+('latent',)*7
        result=compare_initial(5,2,2,claims)
        self.assertFalse(result['valid'])
        self.assertTrue(any('CCO' in issue for issue in result['issues']))
        self.assertEqual(result['rows'][2]['values']['medium'],F(4,63))
        result=compare_initial(5,2,2,('medium',)+('latent',)*8,ClaimPolicy(medium='counter'))
        self.assertFalse(result['valid'])
        self.assertTrue(any('両立' in issue for issue in result['issues']))
    def test_no_candidate_absent_role_and_forbidden_residual(self):
        result=self.run_trial(9)
        self.assertFalse(result['valid'])
        self.assertTrue(any('候補がありません' in issue for issue in result['issues']))
        result=compare_initial(4,0,1,('medium',)+('latent',)*4)
        self.assertTrue(any('配役にない' in issue for issue in result['issues']))
        result=compare_initial(5,2,2,('villager',)+('latent',)*8,ClaimPolicy(villager='none',medium='none'))
        self.assertTrue(any('両立しない霊能' in issue for issue in result['issues']))
    def test_current_model_stays_exact(self):
        result=self.run_trial(1,mode='current')
        self.assertEqual(result['rows'][0]['values']['medium'],F(1,2))
        self.assertEqual(result['rows'][0]['values']['wolf'],F(1,2))
        self.assertIsNotNone(result['rates'])

class ComparisonWebTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SECRET_KEY':'comparison-test'})
        self.client=self.app.test_client()
        self.client.post('/start',data={'citizens':'5','mediums':'2','wolves':'2','day':'max','night':'max','cco_medium':'none'})
    def state(self):
        with self.client.session_transaction() as s:return dict(s['game'])
    def data(self,k=1,mode='trial'):
        return {'citizens':'5','mediums':'2','wolves':'2','mode':mode,'cco_medium':'none',
                **{f'co_{i}':'medium' if i<=k else 'latent' for i in range(1,10)}}
    def test_compare_inputs_and_formats_do_not_mutate_game(self):
        before=self.state()
        for k in (1,2,3):
            response=self.client.post('/comparison',data=self.data(k),headers={'X-Comparison':'partial'})
            self.assertEqual(response.status_code,200)
            html=response.get_data(as_text=True)
            self.assertIn('data-fraction="7/9"',html)
            self.assertIn('data-percent="77.78%"',html)
            self.assertIn('試案の勝率：未定義',html)
            self.assertEqual(self.state(),before)
        self.assertIn('data-fraction="-1/18"',html)
        html=self.client.post('/comparison',data=self.data(mode='current')).get_data(as_text=True)
        self.assertIn('data-fraction="1/2"',html)
        self.assertIn('現行計算の村勝率',html)
        self.assertEqual(self.state(),before)
    def test_history_is_independent_initial_comparison(self):
        self.client.post('/advance',data={'revision':str(self.state()['revision']),'target':'1','day':'max','night':'max'})
        before=self.state()
        self.assertEqual(len(before['history']),1)
        html=self.client.get('/comparison').get_data(as_text=True)
        self.assertIn('死亡者・過去履歴は適用しません',html)
        self.assertNotIn('option value="medium" selected',html)
        self.client.post('/comparison',data=self.data(2))
        self.assertEqual(self.state(),before)
    def test_invalid_cast_and_co_no_repair_or_mutation(self):
        before=self.state()
        for changes in ({'citizens':'9'},{'co_1':'bogus'},{'mode':'bogus'},{'co_1':['medium','wolf']}):
            response=self.client.post('/comparison',data={**self.data(),**changes},headers={'X-Comparison':'partial'})
            self.assertIn('不成立／未対応',response.get_data(as_text=True))
            self.assertEqual(self.state(),before)

if __name__=='__main__':unittest.main()
