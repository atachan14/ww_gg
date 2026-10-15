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

    def test_six_player_unknown_actor_requires_complete_common_flow_certificate(self):
        for repeat,row in ((True,F(1151,3840)),(False,F(383,1280))):
            g=self.game(repeat,players=6);rules,p=replay(g);s=Strategy(**g['policy'])
            branch=prepare_root_entry(g,p.board,rules,s)
            e=RootSecretEngine(rules,s)
            kernel=e.public_night_policies(branch.public,branch.public_law)
            self.assertEqual(kernel[1,()],tuple((i,F(1,4)) for i in range(2,6)))
            self.assertIn((branch.public,branch.public_law,()),e.verified_actor_kernels)
            self.assertIsNone(e.verifying_actor_mask)
            value=evaluate_public_game(g,p.board,rules,s)
            self.assertNotIsInstance(value,FuturePending)
            self.assertEqual(value.village_win,F(1199,4320))
            self.assertEqual(dict(value.action_values)[2],row)
            view=evaluate_private_table(p.board,'wolf',[1],[],rules,s,game_state=g)
            self.assertTrue(all(r['final']['village']=='719/2400' for r in view['players'][1:5]))
            self.assertEqual(g['policy']['night'],'max')

    def test_all_latent_six_player_initial_and_night_fit_existing_budget(self):
        for repeat,night in ((True,F(719,2400)),(False,F(719,2400))):
            g=self.game(repeat,players=6)
            g['claims']=['latent']*6;g['history'][0]['claims']=['latent']*6
            for initial in (True,False):
                current=migrate_game({**g,'history':[] if initial else g['history']})
                before=deepcopy(current);rules,p=replay(current);s=Strategy(**current['policy'])
                clear_public_cache()
                value=evaluate_public_game(current,p.board,rules,s)
                self.assertNotIsInstance(value,FuturePending)
                expected=F(1,6)+F(5,6)*night if initial else night
                self.assertEqual(value.village_win,expected)
                self.assertTrue(all(v==expected for t,v in value.action_values))
                self.assertTrue(all(h.village_win==(F(1,6) if initial else 0) and h.wolf_win==0
                                    for t,h in value.by_dawn_values))
                self.assertEqual(current,before)

    def test_root_payoff_cache_separates_certificate_mode_and_identity_fallback(self):
        from unittest.mock import patch
        g=self.game(players=4);rules,p=replay(g);s=Strategy(**g['policy'])
        branch=prepare_root_entry(g,p.board,rules,s);e=RootSecretEngine(rules,s)
        args=(branch.public,branch.public_law,(),branch.physical_law,None)
        ordinary=e.full_renamed_key(*args,target=2)
        e.verifying_actor_mask=1
        self.assertNotEqual(ordinary,e.full_renamed_key(*args,target=2))
        with patch('werewolf.exact_renaming.canonical_key',return_value=None):
            e.exact_keys.clear()
            self.assertIsNotNone(e.full_renamed_key(*args,target=2))
            self.assertNotEqual(e.full_renamed_key(*args,target=2),e.full_renamed_key(*args,target=3))

    def test_unknown_actor_proposal_divergence_is_never_returned_or_cached(self):
        from unittest.mock import patch
        import werewolf.fixed_actor_continuation as continuation
        from werewolf.information_set_forecast import Pending
        g=self.game(False,players=6);rules,p=replay(g);s=Strategy(**g['policy'])
        branch=prepare_root_entry(g,p.board,rules,s);e=RootSecretEngine(rules,s)
        original=continuation.fixed_actor_value
        def changed(*args,**kw):
            value=original(*args,**kw)
            return value+F(1,100000) if value is not None and kw.get('allow_actor_only') else value
        with patch.object(continuation,'fixed_actor_value',side_effect=changed):
            with self.assertRaises(Pending) as stopped:e.public_night_policies(branch.public,branch.public_law)
        self.assertEqual(stopped.exception.reason,'root_actor_continuation_belief_divergence')
        self.assertNotIn((branch.public,branch.public_law,()),e.night_kernels)
        self.assertNotIn((branch.public,branch.public_law,()),e.verified_actor_kernels)
        self.assertIsNone(e.verifying_actor_mask)


    def test_saved_max_observation_children_match_full_unfiltered_joint_laws(self):
        from werewolf.root_secret_flow import step_root_action
        from werewolf.fixed_actor_continuation import fixed_uniform_action_value
        for repeat in (True,False):
            g=self.game(repeat,players=6);rules,p=replay(g);strategy=Strategy(**g['policy'])
            branch=prepare_root_entry(g,p.board,rules,strategy);before=deepcopy(branch)
            engine=RootSecretEngine(rules,strategy)
            for target in branch.public.alive:
                self.assertIsNone(fixed_uniform_action_value(branch.public,branch.public_law,
                    branch.physical_law,engine,target))
                complete=step_root_action(branch,target,rules,strategy,publish=False,_engine=engine)
                self.assertNotIsInstance(complete,FuturePending)
                for alive in (branch.public.alive,tuple(x for x in branch.public.alive if x!=target)):
                    selected=step_root_action(branch,target,rules,strategy,publish=False,
                        _engine=engine,_observed_alive=alive)
                    self.assertEqual(selected,tuple((q,c) for q,c in complete if c.public.alive==alive))
            self.assertEqual(branch,before)

    def test_saved_max_and_uniform_gj_two_night_actor_support(self):
        from werewolf.night_knowledge import WolfAttack
        expected={(True,'max'):F(23,72),(False,'max'):F(23,72),
                  (True,'random'):F(79,252),(False,'random'):F(13,42)}
        for repeat in (True,False):
            for saved in ('max','random'):
                g=self.game(repeat,players=6)
                gj={'target':None,'claims':g['claims'],'claim_policy':g['claim_policy'],
                    'policy':{**g['policy'],'night':saved},'observation':'night-deaths-v1','deaths':[]}
                day={'target':3,'claims':g['claims'],'claim_policy':g['claim_policy'],'policy':g['policy']}
                g=migrate_game({**g,'history':[g['history'][0],gj,day]})
                r,p=replay(g);branch=prepare_root_entry(g,p.board,r,Strategy(**g['policy']))
                self.assertNotIsInstance(branch,FuturePending)
                self.assertEqual(len(p.board.worlds),4 if saved=='max' else 7)
                actor=WolfInformation(1,(WolfAttack(1,2),)).condition_public(branch.public_law)
                self.assertEqual({h.roles[3] for h in actor.hypotheses},{4,8,16})
                self.assertTrue(all(h.guards[0].target==2 for h in actor.hypotheses))
                value=evaluate_public_game(g,p.board,r,Strategy(**g['policy']))
                self.assertNotIsInstance(value,FuturePending)
                self.assertEqual(value.village_win,expected[repeat,saved])
                self.assertEqual(g['history'][1]['policy']['night'],saved)
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
