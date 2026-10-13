import unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import initial_board,Rules,Strategy,build_tree,evaluate_tree
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState,FuturePending
from werewolf.model_a_public import public_forecast
from werewolf.by_dawn import HorizonValues
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.model_a_public import horizon_for_action
from werewolf.model_a_public import evaluate_public_game,clear_public_cache,public_cache_info,public_history_key


def joint(board):
    return TrueScanState(from_board(board),(tuple(range(1,board.player_count+1)),),
                         initial_rule='none',tracked=(),observed_prefix=1)


class PublicModelATests(unittest.TestCase):
    def setUp(self):clear_public_cache()
    def test_small_symmetric_public_final_matches_independent_known_fixtures(self):
        for n,expected in ((3,F(1,3)),(4,F(1,4)),(5,F(7,15))):
            b=initial_board(n,1);before=(b,joint(b));s=before[1]
            result=public_forecast(b,s,(),Rules(initial_seer='none'),Strategy())
            self.assertEqual(result.village_win,expected)
            self.assertEqual(dict(result.action_values),{p:expected for p in b.alive})
            self.assertEqual((b,s),before)

    def test_horizon_counts_only_victory_through_dawn_not_final_expectation(self):
        for n,expected in ((4,HorizonValues(F(1,4),F(3,4))),
                           (5,HorizonValues(F(1,5),F(0)))):
            b=initial_board(n,1)
            result=public_forecast(b,joint(b),(),Rules(initial_seer='none'),Strategy('max','random'))
            self.assertEqual(dict(result.by_dawn_values),{p:expected for p in b.alive})

    def test_non_disclosure_uses_public_prior_and_preserves_medium_strategy_scope(self):
        b=initial_board(5,1,1);b=replace(b,claims=('medium','latent','latent','latent','latent'))
        # Use none here to test the existing no-report option without hidden
        # acquisition histories or viewer data being needed by the facade.
        strategy=Strategy('random','random',disclosure_common='none')
        result=public_forecast(b,joint(b),(),Rules(initial_seer='none'),strategy)
        self.assertNotIsInstance(result,FuturePending)
        self.assertEqual(result.village_win,F(7,15))
        self.assertEqual(evaluate_tree(build_tree(b,Rules(),strategy),strategy).board_value(build_tree(b,Rules(),strategy)).village_win,result.village_win)

    def test_budget_returns_no_partial_public_table_and_night_contract_is_not_invented(self):
        b=initial_board(5,1)
        self.assertIsInstance(public_forecast(b,joint(b),(),Rules(),Strategy(),max_work=1),FuturePending)
        b=replace(b,phase='night')
        result=public_forecast(b,joint(b),(),Rules(initial_seer='none'),Strategy())
        self.assertEqual(result.village_win,F(1,4))
        self.assertEqual(result.action_values,())
        self.assertEqual(result.by_dawn_values,())
        self.assertEqual(result.pending_metrics,('night_actions','night_horizon'))

    def test_count_fast_path_matches_uncompressed_model_a_with_ability_free_roles(self):
        b=initial_board(5,1,1,1,1);s=joint(b)
        for included in (False,True):
            for mode in ('random','max'):
                strategy=Strategy('max',mode,include_self_bite=included,disclosure_common='none')
                rules=Rules(True,initial_seer='none')
                fast=public_forecast(b,s,(),rules,strategy)
                engine=InformationSetForecast(rules,strategy)
                engine.exchangeable=lambda b:False
                self.assertEqual(fast.village_win,engine.scalar(b,s,()))
                for target in b.alive:
                    self.assertEqual(dict(fast.action_values)[target],engine.act(b,s,(),target,s,None))
                    self.assertEqual(dict(fast.by_dawn_values)[target],horizon_for_action(engine,b,s,(),target))

    def test_public_cache_ignores_viewer_data_and_changes_with_strategy_and_board(self):
        b=initial_board(5,1);r=Rules();s=Strategy()
        before=evaluate_public_game({},b,r,s)
        self.assertIs(evaluate_public_game({'secret_results':'hidden','viewer':3},b,r,s),before)
        self.assertEqual(public_cache_info().hits,1)
        self.assertNotIn('hidden',public_history_key({'secret_results':'hidden'}))
        changed=replace(b,phase='night')
        self.assertEqual(evaluate_public_game({},changed,r,s).village_win,F(1,4))
        self.assertEqual(public_cache_info().misses,2)
        evaluate_public_game({},b,Rules(True),Strategy(include_self_bite=True))
        self.assertEqual(public_cache_info().misses,3)

    def test_public_cache_never_saves_pending_and_history_key_preserves_publication_defaults(self):
        b=initial_board(5,1)
        for _ in range(2):
            self.assertIsInstance(evaluate_public_game({},b,Rules(),Strategy(),max_work=1),FuturePending)
        self.assertEqual(public_cache_info().currsize,0)
        self.assertEqual(public_cache_info().misses,2)
        import json
        key=json.loads(public_history_key({'public_log':{'report_publications':{'seer:1:1':{'owner':'old'}}},
                                          'seer_options':{'initial_rule':'normal'}}))
        self.assertNotIn('initial_seer',key['rules'])
        self.assertEqual(key['public_log']['report_publications']['seer:1:1'],{})

    def test_real_public_acquisition_inputs_and_private_request_do_not_change_public_snapshot(self):
        import copy,json
        from app import create_app
        from werewolf.seer_manual import replay
        a=create_app({'TESTING':True,'SECRET_KEY':'public-a-snapshot','HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True})
        c=a.test_client();c.post('/start',data={'citizens':'3','seers':'1','wolves':'1','initial_seer':'normal','day':'max','night':'random'})
        def game():
            with c.session_transaction() as session:return copy.deepcopy(session['game'])
        g=game()
        payload={'claims':['seer','latent','latent','latent','latent'],
                 'seers':[{'day':1,'reporter':1,'target':2,'color':'white'}],'mediums':[]}
        self.assertEqual(c.post('/table-publish',data={'revision':str(g['revision']),'payload':json.dumps(payload)}).status_code,200)
        g=game();rules,progress=replay(g);strategy=Strategy(**g['policy'])
        public=evaluate_public_game(g,progress.board,rules,strategy)
        self.assertNotIsInstance(public,FuturePending)
        self.assertEqual(len(public.action_values),5)
        g=game();c.post('/advance',data={'revision':str(g['revision']),'target':'5','day':'max','night':'random'})
        g=game();rules,progress=replay(g);strategy=Strategy(**g['policy'])
        before=evaluate_public_game(g,progress.board,rules,strategy)
        response=c.post('/private-view',data={'revision':str(g['revision']),'board_id':g['public_log']['board_id'],
            'payload':json.dumps({'role':'seer','players':[1],'results':[{'day':1,'target':2,'color':'white'}]})})
        self.assertEqual(response.status_code,200)
        self.assertEqual(game(),g)
        self.assertIs(evaluate_public_game(game(),progress.board,rules,strategy),before)
