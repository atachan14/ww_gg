import copy,unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from app import create_app
from werewolf.exact import initial_board,Rules,Strategy
from werewolf.model_a_public import evaluate_public_game,clear_public_cache,public_cache_info
from werewolf.root_secret_flow import root_screen_eligible,prepare_root_secrets
from werewolf.seer_future_uniform import FuturePending


class RootSecretScreenTests(unittest.TestCase):
    def setUp(self):clear_public_cache()

    def test_existing_screen_entry_generates_full_latent_state_and_all_metrics(self):
        b=initial_board(5,1,1,1)
        with patch('werewolf.root_secret_flow.prepare_root_secrets',wraps=prepare_root_secrets) as generated:
            result=evaluate_public_game({},b,Rules(),Strategy('random','random'))
        generated.assert_called_once()
        self.assertEqual(result.village_win,F(7,15))
        self.assertEqual(dict(result.action_values),{p:F(7,15) for p in b.alive})
        self.assertEqual(len(result.by_dawn_values),5)
        self.assertTrue(all(v.village_win==F(1,5) for _,v in result.by_dawn_values))
        self.assertIs(evaluate_public_game({'viewer':1,'secret_results':'fixture'},b,Rules(),Strategy('random','random')),result)

    def test_max_fixed_co_midgame_and_hunter_keep_existing_entry(self):
        b=initial_board(5,1,1,1);r=Rules();s=Strategy('random','random')
        for board,strategy in ((b,Strategy()),(replace(b,claims=('seer',)+('latent',)*4),s),
                               (replace(b,phase='night'),s),(initial_board(5,1,0,1,1),s)):
            self.assertFalse(root_screen_eligible(board,r,strategy))
        with patch('werewolf.root_secret_flow.root_screen_forecast',side_effect=AssertionError('No random replacement')):
            self.assertEqual(evaluate_public_game({},b,r,Strategy()).village_win,F(7,15))

    def test_generation_budget_pending_is_not_replaced_or_cached(self):
        for _ in range(2):
            result=evaluate_public_game({},initial_board(5,1,1,1),Rules(),Strategy('random','random'),max_work=1)
            self.assertIsInstance(result,FuturePending)
        self.assertEqual(public_cache_info().currsize,0)

    def test_web_main_uses_new_entry_without_saving_secrets_or_changing_game(self):
        app=create_app({'TESTING':True,'SECRET_KEY':'root-screen-fixture',
                        'HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True,'SEER_FUTURE_UNIFORM':True})
        c=app.test_client()
        c.post('/start',data={'citizens':'2','mediums':'1','seers':'1','wolves':'1',
                             'day':'random','night':'random','initial_seer':'random_white'})
        with c.session_transaction() as session:before=copy.deepcopy(session['game'])
        with patch('werewolf.root_secret_flow.prepare_root_secrets',wraps=prepare_root_secrets) as generated:
            response=c.get('/main',follow_redirects=True)
        self.assertEqual(response.status_code,200)
        self.assertIn(b'id="village-rate"',response.data)
        self.assertEqual(generated.call_count,1)
        with c.session_transaction() as session:self.assertEqual(session['game'],before)
