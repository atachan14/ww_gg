import unittest
from dataclasses import asdict
from fractions import Fraction as F
from copy import deepcopy
from werewolf.exact import Rules,Strategy
from werewolf.seer_manual import migrate_game,replay
from werewolf.root_secret_flow import prepare_root_entry,RootSecretEngine
from werewolf.model_a_public import evaluate_public_game,clear_public_cache,public_cache_info
from werewolf.private_adapter import evaluate_private_table
from werewolf.actor_information import WolfInformation
from werewolf.seer_future_uniform import FuturePending

class RootGuardMaxTests(unittest.TestCase):
    def game(self,repeat=True,night='max',players=4):
        policy=asdict(Strategy(day='random',night=night,fake_reports='random',disclosure_common='none'))
        claims=['hunter']+['latent']*(players-1)
        return migrate_game({'players':players,'wolves':1,'hunters':1,'mediums':0,'seers':0,
            'claims':claims,'claim_policy':{'hunter':'none'},'policy':policy,
            'rules':asdict(Rules(allow_repeat_guard=repeat)),
            'seer_mode':'information-fixed-v1','seer_inputs':[],
            'history':[{'target':players,'claims':claims,'claim_policy':{'hunter':'none'},'policy':policy}]})

    def test_unknown_wolf_kernel_public_and_owner_payoff(self):
        for repeat in (True,False):
            g=self.game(repeat);rules,p=replay(g);before=deepcopy(g)
            branch=prepare_root_entry(g,p.board,rules,Strategy(**g['policy']))
            self.assertNotIsInstance(branch,FuturePending)
            e=RootSecretEngine(rules,Strategy(**g['policy']))
            kernel=e.public_night_policies(branch.public,branch.public_law)
            self.assertEqual(kernel[1,()],((2,F(1,2)),(3,F(1,2))))
            self.assertEqual(kernel[2,()],((1,F(1)),))
            self.assertEqual(kernel[4,()],((1,F(1)),))
            clear_public_cache()
            result=evaluate_public_game(g,p.board,rules,Strategy(**g['policy']))
            self.assertNotIsInstance(result,FuturePending)
            self.assertEqual(result.village_win,F(1,30))
            view=evaluate_private_table(p.board,'wolf',[1],[],rules,Strategy(**g['policy']),game_state=g)
            self.assertEqual(view['players'][1]['final']['village'],'1/18')
            self.assertEqual(view['players'][2]['final']['village'],'1/18')
            self.assertIsNone(view['players'][0]['final'])
            self.assertEqual(g,before)
            self.assertEqual(evaluate_public_game(g,p.board,rules,Strategy(**g['policy'])),result)
            self.assertGreaterEqual(public_cache_info().hits,1)

    def test_guard_owner_secret_does_not_change_public_wolf_kernel(self):
        for repeat in (True,False):
            g=self.game(repeat);rules,p=replay(g);before=deepcopy(g)
            branch=prepare_root_entry(g,p.board,rules,Strategy(**g['policy']))
            e=RootSecretEngine(rules,Strategy(**g['policy']))
            kernel=deepcopy(e.public_night_policies(branch.public,branch.public_law))
            guard=evaluate_private_table(p.board,'hunter',[2],[],rules,Strategy(**g['policy']),game_state=g)
            self.assertEqual(guard['players'][0]['final']['village'],'0')
            self.assertEqual(guard['players'][2]['final']['village'],'1/6')
            self.assertEqual(e.public_night_policies(branch.public,branch.public_law),kernel)
            self.assertEqual(g,before)

    def test_saved_policy_support_and_past_uniform_are_distinct(self):
        for repeat in (True,False):
            g=self.game(repeat);step={'target':None,'claims':g['claims'],
                'claim_policy':g['claim_policy'],'policy':g['policy'],
                'observation':'night-deaths-v1','deaths':[]}
            observed=migrate_game({**g,'history':[g['history'][0],step]})
            rules,p=replay(observed)
            self.assertEqual({w[0] for w in p.board.worlds},{1})
            self.assertEqual({w[-1] for w in p.board.worlds},{F(1,2)})
            branch=prepare_root_entry(observed,p.board,rules,Strategy(**g['policy']))
            self.assertNotIsInstance(branch,FuturePending)
            self.assertEqual(branch.public,p.board)
            old={**step,'policy':{**g['policy'],'night':'random'}}
            uniform=migrate_game({**g,'history':[g['history'][0],old]})
            _,q=replay(uniform)
            self.assertEqual(len(q.board.worlds),4)
            self.assertEqual(uniform['policy']['night'],'max')
            self.assertEqual(uniform['history'][1]['policy']['night'],'random')
            self.assertNotIsInstance(prepare_root_entry(uniform,q.board,rules,Strategy(**g['policy'])),FuturePending)
            switched=migrate_game({**observed,'policy':{**observed['policy'],'day':'max'}})
            _,old_scope=replay(switched)
            self.assertEqual(old_scope.board.worlds,p.board.worlds)
            self.assertEqual(switched['history'][1]['policy']['day'],'random')

    def test_known_public_hunter_six_player_rows_do_not_need_off_path_public_updates(self):
        g=self.game(players=6)
        g['claim_policy']={'hunter':'filled'}
        g['history'][0]['claim_policy']={'hunter':'filled'}
        rules,p=replay(g)
        result=evaluate_public_game(g,p.board,rules,Strategy(**g['policy']))
        self.assertNotIsInstance(result,FuturePending)
        self.assertEqual(result.village_win,F(1,4))
        self.assertEqual(dict(result.action_values)[3],F(3,10))
        self.assertTrue(all(h.village_win==h.wolf_win==0 for t,h in result.by_dawn_values))
        view=evaluate_private_table(p.board,'wolf',[2],[],rules,Strategy(**g['policy']),game_state=g)
        self.assertEqual(view['players'][2]['final']['village'],'3/10')

    def test_unresolved_six_player_unknown_actor_stays_explicit(self):
        g=self.game(players=6);rules,p=replay(g)
        value=evaluate_public_game(g,p.board,rules,Strategy(**g['policy']))
        self.assertIsInstance(value,FuturePending)
        self.assertEqual(value.reason,'root_guard_max_unknown_continuation')
        self.assertEqual(g['policy']['night'],'max')


class RootGuardMaxRouteTests(unittest.TestCase):
    def test_unknown_wolf_normal_routes_reentry_and_back(self):
        import json
        from app import create_app
        for repeat in ('1','0'):
            app=create_app({'TESTING':True,'SECRET_KEY':'root-max-ui',
                            'HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True})
            c=app.test_client()
            form={'citizens':'2','hunters':'1','wolves':'1','day':'random','night':'max',
                  'fake_reports':'random','disclosure_common':'none','allow_repeat_guard':repeat,
                  'seer_mode':'information-fixed-v1'}
            self.assertEqual(c.post('/start',data=form).status_code,303)
            self.assertIn(b'data-fraction="7/24"',c.get('/main').data)
            def game():
                with c.session_transaction() as session:return deepcopy(session['game'])
            g=game()
            self.assertEqual(c.post('/advance',data={'revision':str(g['revision']),'target':'4',
                'day':'random','night':'max'}).status_code,303)
            g=game();self.assertEqual(g['policy']['night'],'max')
            before=deepcopy(g)
            own=c.post('/private-view',data={'revision':str(g['revision']),
                'board_id':g['public_log']['board_id'],
                'payload':json.dumps({'role':'wolf','players':[1],'results':[]})})
            self.assertEqual(own.status_code,200,own.data)
            self.assertEqual(own.json['players'][1]['final']['village'],'1/18')
            self.assertEqual(own.json['players'][2]['final']['village'],'1/18')
            self.assertEqual(game(),before)
            self.assertEqual(c.post('/dawn-report',data={'revision':str(g['revision']),
                'board_id':g['public_log']['board_id'],'mode':'none'}).status_code,303)
            g=game()
            response=c.post('/dawn-advance',data={'revision':str(g['revision']),
                'board_id':g['public_log']['board_id']})
            self.assertEqual(response.status_code,303,response.data)
            saved=game();self.assertEqual(saved['history'][-1]['policy']['night'],'max')
            with c.session_transaction() as session:stored=deepcopy(dict(session))
            reopened=app.test_client()
            with reopened.session_transaction() as session:session.update(stored)
            self.assertIn(b'data-fraction="1/3"',reopened.get('/main').data)
            self.assertEqual(c.post('/back',data={'revision':str(saved['revision'])}).status_code,303)
            self.assertEqual(game()['policy']['night'],'max')
