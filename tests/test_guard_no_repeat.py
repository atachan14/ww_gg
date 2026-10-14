import unittest
from dataclasses import asdict,replace
from fractions import Fraction as F
from copy import deepcopy
from werewolf.exact import Rules,Strategy,initial_board,replace_worlds,PublicEvent
from werewolf.guard_effect import GuardIntent
from werewolf.guard_night import guard_targets,resolve_fixed_guard_night
from werewolf.guard_model import condition_guard_observation
from werewolf.seer_manual import replay,migrate_game
from werewolf.root_secret_flow import (prepare_root_secrets,replay_root_secrets,step_root_action,
    root_guard_night_priors,root_actor_view,root_branch_forecast)
from werewolf.seer_future_uniform import FuturePending
from werewolf.dawn import OBSERVATION
from werewolf.model_a_public import evaluate_public_game,clear_public_cache
from werewolf.public_prior import public_history_key
from werewolf.private_adapter import evaluate_private_table


class NoRepeatGuardTests(unittest.TestCase):
    def fixture(self,repeat=False,seers=0,two=True):
        policy={'day':'random','night':'random','fake_reports':'random','disclosure_common':'none'}
        claims=['latent']*5
        steps=[{'target':5,'policy':policy,'claims':claims,'claim_policy':{}},
               {'target':None,'policy':policy,'claims':claims,'claim_policy':{},'observation':OBSERVATION,'deaths':[]}]
        if two:steps += [{'target':4,'policy':policy,'claims':claims,'claim_policy':{}},
                         {'target':None,'policy':policy,'claims':claims,'claim_policy':{},'observation':OBSERVATION,'deaths':[]}]
        game=migrate_game({'players':5,'wolves':1,'mediums':0,'seers':seers,'hunters':1,
              'history':steps,'claims':claims,'claim_policy':{},'policy':policy,
              'rules':asdict(Rules(allow_repeat_guard=repeat)),'seer_mode':'information-fixed-v1','seer_inputs':[]})
        return game

    def test_legal_targets_initial_previous_dead_and_empty(self):
        b=replace(initial_board(5,1,0,0,1),phase='night')
        r=Rules(allow_repeat_guard=False)
        self.assertEqual(guard_targets(b,1,r),(2,3,4,5))
        second=replace(b,day=2)
        self.assertEqual(guard_targets(second,1,r,GuardIntent(1,1,2)),(3,4,5))
        self.assertEqual(guard_targets(second,1,Rules(),GuardIntent(1,1,2)),(2,3,4,5))
        self.assertEqual(guard_targets(replace_worlds(second,second.worlds,wolf_count=None,alive=(1,3,4),history=(PublicEvent(1,'day',5),PublicEvent(2,'day',2))),1,r,2),(3,4))
        self.assertEqual(guard_targets(replace_worlds(second,second.worlds,wolf_count=None,alive=(1,2),history=(PublicEvent(1,'day',5),PublicEvent(1,'night',3),PublicEvent(2,'day',4))),1,r,2),())
        with self.assertRaises(ValueError):guard_targets(second,1,r)
        with self.assertRaises(ValueError):guard_targets(replace_worlds(second,second.worlds,wolf_count=None,alive=(2,3),history=(PublicEvent(1,'day',5),PublicEvent(1,'night',1),PublicEvent(2,'day',4))),1,r,2)

    def test_fixed_night_rejects_repeat_and_keeps_default(self):
        b=replace_worlds(initial_board(4,1,0,0,1),((2,0,0,1,F(1)),),phase='night',day=2)
        previous=GuardIntent(1,1,3)
        with self.assertRaises(ValueError):resolve_fixed_guard_night(b,GuardIntent(2,1,3),3,Rules(allow_repeat_guard=False),previous=previous)
        out,=resolve_fixed_guard_night(b,GuardIntent(2,1,4),4,Rules(allow_repeat_guard=False),previous=previous)
        self.assertEqual(out.board.alive,b.alive)
        old,=resolve_fixed_guard_night(b,GuardIntent(2,1,3),3,Rules(),previous=previous)
        self.assertEqual(old.board.alive,b.alive)

    def test_two_gj_joint_replay_retains_guard_history_and_excludes_repeat(self):
        for seers in (0,1):
            game=self.fixture(seers=seers);before=deepcopy(game)
            rules,p=replay(game)
            root=replay_root_secrets(game,p.board,rules,Strategy(**game['policy']),max_work=1000000)
            self.assertNotIsInstance(root,FuturePending)
            self.assertEqual(root.public,p.board)
            self.assertEqual(root.public_law.public_roles,tuple(sorted(p.board.worlds)))
            for h in root.public_law.hypotheses:
                self.assertEqual(tuple(g.night for g in h.guards),(1,2))
                self.assertNotEqual(h.guards[0].target,h.guards[1].target)
                self.assertEqual(h.guards[0].target,4) # Its death restores that next-night choice.
                self.assertEqual(tuple(g.target for g in h.guards),tuple(a.target for a in h.attacks))
            self.assertEqual(game,before)

    def test_public_corpse_condition_uses_each_hypothesis_previous_guard(self):
        game=self.fixture(two=False)
        rules,p=replay(game)
        # Next execution leaves three live players; wolf and guardian survive.
        game['history'].append({'target':4,'policy':game['policy'],'claims':game['claims'],'claim_policy':{}})
        rules,p=replay(game)
        prior=p.guard_state
        self.assertIsNotNone(prior)
        target=3
        board=condition_guard_observation(p.board,(target,),rules,state=prior)
        # For H=1/W=2, previous guard is 3 or dead4, each 1/2. Failure to
        # protect3 is 1 or 1/2, hence factor3/4; H=3 cannot self-guard3:1.
        weights={w[:-1]:w[-1] for w in board.worlds}
        original={w[:-1]:w[-1] for w in p.board.worlds}
        a=(2,0,0,1);b=(2,0,0,4)
        self.assertEqual(weights[a]/weights[b],original[a]/original[b]*F(3,4))

    def test_owner_table_conditions_same_law_and_unknown_previous_stays_pending(self):
        game=self.fixture();rules,p=replay(game);s=Strategy(**game['policy']);before=deepcopy(game)
        root=replay_root_secrets(game,p.board,rules,s,max_work=1000000)
        h=next(h for h in root.physical_law.hypotheses if h.roles[3]==1 and h.roles[0]==2)
        rows=[{'day':g.night,'target':g.target,'color':None} for g in h.guards]
        table=evaluate_private_table(p.board,'hunter',(1,),rows,rules,s,game_state=game,max_work=1000000)
        self.assertEqual([row['id'] for row in table['players'] if row['final'] is not None],[2])
        self.assertEqual(table['players'][1]['final']['village'],'1/3')
        self.assertFalse(table['players'][2]['legal'])
        with self.assertRaises(ValueError):evaluate_private_table(p.board,'hunter',(1,),
            [{'day':1,'target':3,'color':None},{'day':2,'target':3,'color':None}],rules,s,game_state=game)
        one=self.fixture(two=False);r,q=replay(one)
        missing=evaluate_private_table(q.board,'hunter',(1,),[],r,s,game_state=one,max_work=1000000)
        self.assertTrue(all(row['final'] is None for row in missing['players']))
        self.assertEqual(game,before)

    def test_rules_cache_and_cold_recalculation_keep_default_numbers(self):
        game=self.fixture();rules,p=replay(game);s=Strategy(**game['policy'])
        clear_public_cache();first=evaluate_public_game(game,p.board,rules,s,max_work=1000000)
        self.assertNotIsInstance(first,FuturePending)
        self.assertEqual(first.village_win,F(1,3))
        self.assertIs(first,evaluate_public_game({**game,'private_results':[{}]},p.board,rules,s,max_work=1000000))
        clear_public_cache();self.assertEqual(first,evaluate_public_game(game,p.board,rules,s,max_work=1000000))
        old=self.fixture(repeat=True);r,q=replay(old)
        self.assertNotEqual(public_history_key(game),public_history_key(old))
        self.assertEqual(evaluate_public_game(old,q.board,r,s,max_work=1000000).village_win,F(1,3))
        initial=evaluate_public_game({},initial_board(4,1,0,0,1),Rules(),s)
        self.assertEqual(initial.village_win,F(7,24))

    def test_dead_guardian_uses_existing_no_ability_flow_and_terminal_skips_choices(self):
        from werewolf.root_secret_flow import root_secret_value
        from werewolf.information_set_forecast import InformationSetForecast
        r=Rules(allow_repeat_guard=False);s=Strategy('random','random',fake_reports='random')
        b=replace_worlds(initial_board(5,1,0,0,1),((2,0,0,1,F(1)),))
        root=prepare_root_secrets(b,r)
        after=step_root_action(root,1,r,s,publish=False)[0][1]
        night=step_root_action(after,4,r,s,publish=False)[0][1]
        self.assertTrue(all(not h.guards for h in night.physical_law.hypotheses))
        self.assertEqual(root_secret_value(night,r,s),F(1,3))
        terminal=initial_board(2,1,0,0,1)
        self.assertEqual(InformationSetForecast(r,s).solve(terminal,None,(),None,None),0)

    def test_five_player_hand_value_and_old_rule_are_distinct(self):
        # Execute wolf:1/5; execute H:1/5 * 1/3; execute citizen:3/5.
        # Its four-player night is 23/72 under no-repeat, 35/108 under repeat.
        s=Strategy('random','random',fake_reports='random')
        b=initial_board(5,1,0,0,1)
        self.assertEqual(evaluate_public_game({},b,Rules(),s).village_win,F(83,180))
        value=evaluate_public_game({},b,Rules(allow_repeat_guard=False),s)
        self.assertEqual(value.village_win,F(11,24))
        self.assertEqual(set(dict(value.action_values).values()),{F(11,24)})


class NoRepeatGuardRouteTests(unittest.TestCase):
    def setUp(self):
        from app import create_app
        self.app=create_app({'TESTING':True,'SECRET_KEY':'no-repeat-tests',
                             'HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True})
        self.c=self.app.test_client()
        self.form={'citizens':'3','hunters':'1','wolves':'1','day':'random','night':'random',
                   'fake_reports':'random','disclosure_common':'none','allow_repeat_guard':'0'}

    def game(self,client=None):
        with (client or self.c).session_transaction() as session:return deepcopy(session['game'])

    def post(self,url,**extra):
        g=self.game()
        return self.c.post(url,data={'revision':str(g['revision']),'board_id':g['public_log']['board_id'],**extra})

    def execute(self,target):
        g=self.game()
        r=self.c.post('/advance',data={'revision':str(g['revision']),'target':str(target),'day':'random','night':'random'})
        self.assertEqual(r.status_code,303,r.get_data(as_text=True)[r.get_data(as_text=True).find('class="error"'):][:350])

    def gj(self):
        self.assertEqual(self.post('/dawn-report',mode='none').status_code,303)
        r=self.post('/dawn-advance')
        self.assertEqual(r.status_code,303,r.get_data(as_text=True)[r.get_data(as_text=True).find('class="error"'):][:350])

    def test_minimal_rule_control_default_and_false_save(self):
        from tests.test_setup import Controls
        top=self.c.get('/').get_data(as_text=True)
        self.assertEqual(Controls(top).values['repeat-guard'],'1')
        self.assertIn('name="allow_repeat_guard"',top)
        self.assertNotIn('なし（未対応）',top)
        self.assertEqual(self.c.post('/start',data=self.form).status_code,303)
        g=self.game();self.assertIs(g['rules']['allow_repeat_guard'],False)
        self.assertNotIn('allow_repeat_guard',g['policy'])
        main=self.c.get('/main')
        self.assertEqual(main.status_code,200)
        self.assertIn(b'data-fraction="11/24"',main.data)
        self.assertEqual(Controls(main.get_data(as_text=True)).values['view-repeat-guard'],'0')
        self.assertEqual(Controls(self.c.get('/').get_data(as_text=True)).values['repeat-guard'],'0')

    def test_saved_reentry_two_gj_private_back_and_corpse_edit(self):
        import json
        self.assertEqual(self.c.post('/start',data=self.form).status_code,303)
        self.execute(5);self.gj();self.execute(4);self.gj()
        saved=self.game();self.assertEqual(len(saved['history']),4)
        with self.c.session_transaction() as session:stored=deepcopy(dict(session))
        reopened=self.app.test_client()
        with reopened.session_transaction() as session:session.update(stored)
        r=reopened.get('/main');self.assertEqual(r.status_code,200)
        self.assertIn(b'data-fraction="1/3"',r.data)
        self.assertEqual(self.game(reopened)['history'],saved['history'])
        self.assertNotIn('guard_state',saved)
        self.assertEqual(self.c.post('/back',data={'revision':str(self.game()['revision'])}).status_code,303)
        night=self.game();self.assertEqual(len(night['history']),3)
        own={'role':'hunter','players':[1],'results':[{'day':1,'target':4,'color':None}]}
        response=self.post('/private-view',payload=json.dumps(own))
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual([x['id'] for x in response.json['players'] if x['final'] is not None],[2,3])
        self.assertEqual(self.game(),night)
        self.assertEqual(self.post('/dawn-report',mode='deaths',deaths='3').status_code,303)
        changed=self.post('/dawn-advance')
        self.assertEqual(changed.status_code,303,changed.data)
        self.assertEqual(self.game()['history'][-1]['deaths'],[3])
        self.assertNotEqual(public_history_key(saved),public_history_key(self.game()))
        self.assertEqual(self.c.get('/result').status_code,200)

    def test_invalid_rule_and_unsupported_max_do_not_replace_game(self):
        from werkzeug.datastructures import MultiDict
        self.assertEqual(self.c.post('/start',data=self.form).status_code,303)
        before=self.game()
        for changes in ({'allow_repeat_guard':'bad'},{'hunters':'2','citizens':'2'}):
            response=self.c.post('/start',data={**self.form,**changes})
            self.assertEqual(response.status_code,400,response.data)
            self.assertEqual(self.game(),before)
        duplicate=MultiDict(self.form);duplicate.add('allow_repeat_guard','1')
        self.assertEqual(self.c.post('/start',data=duplicate).status_code,400)
        self.assertEqual(self.game(),before)
        self.assertEqual(self.c.post('/advance',data={'revision':str(before['revision']),'target':'5','day':'max','night':'random'}).status_code,400)
        self.assertEqual(self.game(),before)

    def test_rule_works_with_existing_dawn_flow_when_preview_flags_are_off(self):
        from app import create_app
        from werewolf.dawn import FLOW
        c=create_app({'TESTING':True,'SECRET_KEY':'no-repeat-normal'}).test_client()
        self.assertEqual(c.post('/start',data=self.form).status_code,303)
        self.assertEqual(self.game(c)['board_flow'],FLOW)
        self.assertEqual(c.get('/main').status_code,200)

    def test_default_max_is_preserved_pending_and_each_phase_can_be_edited(self):
        response=self.c.post('/start',data={**self.form,'day':'max','night':'max'})
        self.assertEqual(response.status_code,303)
        g=self.game();self.assertEqual((g['policy']['day'],g['policy']['night']),('max','max'))
        main=self.c.get('/main');self.assertEqual(main.status_code,200)
        self.assertNotIn(b'data-fraction="11/24"',main.data)
        self.assertEqual(self.c.post('/strategy',data={'revision':str(g['revision']),'day':'random','night':'max'}).status_code,303)
        middle=self.game();self.assertEqual((middle['policy']['day'],middle['policy']['night']),('random','max'))
        self.assertEqual(self.c.post('/advance',data={'revision':str(middle['revision']),'target':'5','day':'random','night':'max'}).status_code,303)
        saved=self.game()
        self.assertEqual(saved['history'][-1]['target'],5)
        self.assertEqual(saved['history'][-1]['policy']['night'],'max')
        self.assertIs(saved['rules']['allow_repeat_guard'],False)
        self.assertEqual(self.c.post('/back',data={'revision':str(saved['revision'])}).status_code,303)
        restored=self.game()
        self.assertEqual((restored['policy']['day'],restored['policy']['night']),('random','max'))
        self.assertEqual(self.c.post('/strategy',data={'revision':str(restored['revision']),'day':'random','night':'random'}).status_code,303)
        self.assertIn(b'data-fraction="11/24"',self.c.get('/main').data)
