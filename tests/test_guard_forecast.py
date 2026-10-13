"""Reproducible small exact guard examples, independent hand-derived values."""
import copy,json,unittest
from dataclasses import replace
from fractions import Fraction as F
from app import create_app
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy,Progress,PublicEvent
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState,FuturePending
from werewolf.model_a_public import public_forecast
from werewolf.private_adapter import evaluate_private_table,private_slots
from werewolf.private_view import condition_private
from werewolf.dawn import observe,advance_step,OBSERVATION
from werewolf.guard_model import guard_choices


def known_hunter(n=3,phase='night'):
    b=initial_board(n,1,0,0,1)
    worlds=tuple(w for w in b.worlds if w[3]==1)
    mass=sum(w[-1] for w in worlds)
    return replace_worlds(b,tuple((*w[:-1],w[-1]/mass) for w in worlds),phase=phase)


def prior(b):
    return TrueScanState(from_board(b),(tuple(range(1,b.player_count+1)),),initial_rule='none',tracked=(),observed_prefix=1)


class GuardForecastTests(unittest.TestCase):
    rules=Rules(initial_seer='none')
    strategy=Strategy('max','random')

    def test_ordered_uniform_items_and_game_rule_are_separate(self):
        self.assertEqual(Strategy(guard_position=['uniform']).guard_position,('uniform',))
        for items in ((),('max',),('uniform','uniform')):
            with self.assertRaises(ValueError):Strategy(guard_position=items)
        self.assertEqual(guard_choices(known_hunter(),1,self.rules),((2,F(1,2)),(3,F(1,2))))

    def test_three_player_known_hunter_hand_calculated_values(self):
        b=known_hunter();s=prior(b);before=copy.deepcopy((b,s))
        result=public_forecast(b,s,(),self.rules,self.strategy)
        # Random bite: half hits H; the other half has 1/2 guard success.
        # A successful dawn then wins a public 1/2 execution: 1/2*1/2*1/2.
        self.assertEqual(result.village_win,F(1,8))
        self.assertEqual(dict(result.action_values),{1:F(0),2:F(1,4),3:F(1,4)})
        self.assertEqual(dict(result.by_dawn_values)[2].wolf_win,F(1,2))
        self.assertEqual((b,s),before)
        optimal=public_forecast(b,s,(),self.rules,Strategy())
        self.assertEqual(optimal.village_win,0) # Wolves can always attack H.

    def test_four_player_day_includes_guard_at_upcoming_dawn(self):
        b=known_hunter(4,'day')
        result=public_forecast(b,prior(b),(),self.rules,self.strategy)
        # Execute a non-H: 1/3 wins immediately, 2/3 continues to above 1/8.
        self.assertEqual(result.village_win,F(5,12))
        self.assertEqual(dict(result.action_values)[1],0)
        self.assertEqual(dict(result.by_dawn_values)[2].village_win,F(1,3))
        self.assertEqual(dict(result.by_dawn_values)[2].wolf_win,F(1,2))

    def test_fixed_guard_view_never_changes_public_wolf_policy(self):
        b=known_hunter();before=copy.deepcopy(b)
        result=evaluate_private_table(b,'hunter',[1],[],self.rules,self.strategy)
        for row in result['players'][1:]:
            self.assertEqual(row['final']['village'],'1/8')
            self.assertEqual(row['dawn']['wolf'],'3/4')
        self.assertIsNone(result['players'][0]['final'])
        optimal=evaluate_private_table(b,'hunter',[1],[],self.rules,Strategy())
        self.assertTrue(all(row['final']['village']=='0' for row in optimal['players'][1:]))
        self.assertEqual(b,before)

    def test_guard_history_is_private_and_missing_is_not_invented(self):
        b=replace(known_hunter(),day=2)
        before=copy.deepcopy(b)
        view=condition_private(b,'hunter',[1],[{'day':1,'target':2,'color':None}],rules=self.rules)
        self.assertEqual(view.board.wolf_probability(2),0)
        self.assertEqual(view.board.wolf_probability(3),1)
        self.assertEqual(view.guards[0].target,2)
        self.assertEqual(condition_private(b,'hunter',[1],[],rules=self.rules).board,b)
        self.assertEqual(private_slots(b,1,self.rules,role='hunter'),[{'day':1,'targets':[2,3]}])
        self.assertEqual(b,before)
        for result in ({'day':1,'target':1,'color':None},{'day':1,'target':2,'color':'white'},
                       {'day':2,'target':2,'color':None}):
            with self.assertRaises(ValueError):condition_private(b,'hunter',[1],[result],rules=self.rules)

    def test_no_death_public_observation_preserves_roles_and_replays(self):
        b=known_hunter();p=Progress.initial(b)
        after=observe(p,{'deaths':[]},self.rules,self.strategy)
        self.assertEqual(after.board.worlds,b.worlds)
        self.assertEqual((after.board.day,after.board.phase,after.board.history),(2,'day',()))
        step={'target':None,'deaths':[],'observation':OBSERVATION,'policy':{'night':'random'}}
        self.assertEqual(advance_step(p,step,self.rules),after)

    def test_secret_after_success_changes_view_values_without_public_change(self):
        b=replace(known_hunter(),day=2)
        before=public_forecast(b,TrueScanState(from_board(b),(b.alive,b.alive),initial_rule='none',tracked=(),observed_prefix=2),(),self.rules,self.strategy)
        result=evaluate_private_table(b,'hunter',[1],[{'day':1,'target':2,'color':None}],self.rules,self.strategy)
        self.assertEqual(result['players'][1]['final']['village'],'1/4')
        self.assertEqual(result['players'][2]['final']['village'],'0')
        self.assertEqual(b.wolf_probability(2),F(1,2))
        self.assertEqual(before.village_win,F(1,8))

    def test_past_guard_uses_original_roster_and_contradictory_corpse_fails(self):
        b=known_hunter(4)
        worlds=tuple(w for w in b.worlds if not w[0]&8)
        mass=sum(w[-1] for w in worlds)
        b=replace_worlds(b,tuple((*w[:-1],w[-1]/mass) for w in worlds),alive=(1,2,3),day=2,
                        history=(PublicEvent(2,'day',4),))
        record=[{'day':1,'target':4,'color':None}]
        self.assertEqual(condition_private(b,'hunter',[1],record,rules=self.rules).guards[0].target,4)
        with self.assertRaises(ValueError):
            condition_private(replace(b,history=(PublicEvent(1,'night',4),)),'hunter',[1],record,rules=self.rules)

    def test_uncertain_and_multiple_hunters_remain_explicit(self):
        for b,reason in ((initial_board(5,1,0,0,1),'guard_hidden_attack_history_unimplemented'),
                         (initial_board(5,1,0,0,2),'guard_multiple_hunters_unimplemented')):
            result=public_forecast(b,prior(b),(),self.rules,self.strategy)
            self.assertIsInstance(result,FuturePending);self.assertEqual(result.reason,reason)

    def test_scan_retirement_cannot_remove_live_guardian(self):
        from werewolf.information_set_forecast import InformationSetForecast
        b=initial_board(5,1,0,1,1)
        worlds=tuple(w for w in b.worlds if w[3]==1)
        mass=sum(w[-1] for w in worlds)
        b=replace_worlds(b,tuple((*w[:-1],w[-1]/mass) for w in worlds))
        s=prior(b);e=InformationSetForecast(self.rules,self.strategy)
        self.assertTrue(e.can_retire_scans(b,s,()))
        self.assertEqual(e.continuation_context(b,s,(),s,None),(b,s,(),s,None))
        from werewolf.evaluation_projection import project_evaluation
        self.assertEqual(project_evaluation(b,s,self.strategy),(b,s))


class GuardRouteTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SECRET_KEY':'guard','DAWN_BOARD_PREVIEW':True,'HYBRID_TABLE_PREVIEW':True})
        self.c=self.app.test_client()
        self.assertEqual(self.c.post('/start',data={'citizens':'3','hunters':'1','wolves':'1','day':'max','night':'random'}).status_code,303)

    def game(self):
        with self.c.session_transaction() as s:return copy.deepcopy(s['game'])

    def post(self,url,**extra):
        g=self.game()
        return self.c.post(url,data={'revision':str(g['revision']),'board_id':g['public_log']['board_id'],**extra})

    def test_public_no_death_private_input_switch_and_back(self):
        r=self.post('/public-log',operation='publish',payload=json.dumps({'mode':'simultaneous','events':[{'kind':'co','player':1,'role':'hunter'}]}))
        self.assertEqual(r.status_code,200,r.data)
        g=self.game()
        self.assertEqual(self.c.post('/advance',data={'revision':str(g['revision']),'target':'5','day':'max','night':'random'}).status_code,303)
        before=self.game();self.assertIn(b'name="guard_position"',self.c.get('/main').data)
        self.assertEqual(self.post('/dawn-report',mode='none').status_code,303)
        self.assertEqual(self.post('/dawn-advance').status_code,303)
        g=self.game();self.assertIsNone(g['history'][-1]['target']);self.assertEqual(g['history'][-1]['deaths'],[])
        self.assertEqual(self.c.get('/main').status_code,200)
        self.assertEqual(self.c.post('/back',data={'revision':str(g['revision'])}).status_code,303)
        old=self.game();self.assertEqual(old['history'],before['history'])
        # A real secret row is independent of the public form, cookie and log.
        r=self.post('/private-view',payload=json.dumps({'role':'hunter','players':[1],'results':[]}))
        self.assertEqual(r.status_code,200,r.data)
        self.assertTrue(any(row['final'] for row in r.json['players']))
        self.assertEqual(self.game(),old)
