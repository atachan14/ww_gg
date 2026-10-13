import copy
import re
import unittest
from unittest.mock import patch
from app import create_app


class PublicModelAUiTests(unittest.TestCase):
    def test_independent_cast_comparison_does_not_call_legacy_solver(self):
        from werewolf.comparison import compare_initial
        from werewolf.exact import ClaimPolicy
        with patch('werewolf.exact.build_tree',side_effect=AssertionError('legacy comparison')):
            result=compare_initial(3,1,1,('medium',)+('latent',)*4,
                                   ClaimPolicy(medium='none'),mode='current')
        self.assertIsNotNone(result['rates'])
        self.assertEqual(sum(row['values']['wolf'] for row in result['rows']),1)

    def test_roster_overview_and_fixed_target_horizon_have_distinct_meanings(self):
        a=create_app({'TESTING':True,'SECRET_KEY':'model-a-ui'})
        c=a.test_client()
        c.post('/start',data={'players':'5','wolves':'1','allow_self_bite':'1','day':'max','night':'max'})
        def game():
            with c.session_transaction() as s:return copy.deepcopy(s['game'])
        g=game()
        c.post('/advance',data={'revision':str(g['revision']),'target':'1','day':'max','night':'max'})
        g=game()
        c.post('/strategy',data={'revision':str(g['revision']),'day':'max','night':'max','include_self_bite':'1'})
        before=game()
        with patch('werewolf.exact.build_tree',side_effect=AssertionError('legacy model must not render main')):
            h=c.get('/main').get_data(as_text=True)
        self.assertIn('id="village-rate" class="probability" data-fraction="1/3"',h)
        self.assertIn('id="cumulative-village-rate" class="probability" data-fraction="7/15"',h)
        row=re.search(r'<tr[^>]*data-player="2"[^>]*>(.*?)</tr>',h,re.S).group(1)
        dawn=re.search(r'data-value-cell="dawn"(.*?)</td>',row,re.S).group(1)
        final=re.search(r'data-value-cell="final"(.*?)</td>',row,re.S).group(1)
        self.assertIn('data-fraction="1/4"',dawn)
        self.assertIn('data-fraction="1/2"',final)
        self.assertEqual(game(),before)
