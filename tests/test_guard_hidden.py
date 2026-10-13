import copy,unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import initial_board,Rules,Strategy,PublicEvent,replace_worlds,Progress
from werewolf.model_a_public import public_forecast
from werewolf.seer_acquisition import from_board,normalize,Hypothesis
from werewolf.seer_future_uniform import TrueScanState
from werewolf.guard_model import GuardContext,condition_guard_observation
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.action_flow import resolve_action
from werewolf.dawn import observe
from werewolf.private_adapter import evaluate_private_table
from werewolf.private_view import condition_private
from tests.test_guard_forecast import prior


class HiddenGuardTests(unittest.TestCase):
    rules=Rules(initial_seer='none')
    strategy=Strategy('max','random')

    def board(self,n=3,phase='night'):return replace(initial_board(n,1,0,0,1),phase=phase)

    def test_hand_computed_three_player_night_and_four_player_day(self):
        for b,value in ((self.board(),F(1,12)),(self.board(4,'day'),F(7,24))):
            s=prior(b);before=(b,s)
            result=public_forecast(b,s,(),self.rules,self.strategy)
            self.assertEqual(result.village_win,value)
            self.assertEqual(set(dict(result.action_values).values()),{value})
            self.assertEqual((b,s),before)

    def test_private_hunter_cannot_give_public_village_its_identity(self):
        b=self.board();result=evaluate_private_table(b,'hunter',[1],[],self.rules,self.strategy)
        self.assertEqual(result['players'][1]['final']['village'],'1/12')
        self.assertNotEqual(result['players'][1]['final']['village'],'1/8')
        self.assertEqual(b.role_probability(1,'hunter'),F(1,3))

    def test_small_max_base_cases_have_no_future_secret_action_policy(self):
        for b,value in ((self.board(),F(1,12)),(self.board(4,'day'),F(7,24))):
            result=public_forecast(b,prior(b),(),self.rules,Strategy())
            self.assertEqual(result.village_win,value)
        view=evaluate_private_table(self.board(),'hunter',[1],[],self.rules,Strategy())
        self.assertEqual(view['players'][1]['final']['village'],'1/12')
        later=public_forecast(self.later(),TrueScanState(from_board(self.later()),((1,2,3,4),(1,2,3,4)),initial_rule='none',tracked=(),observed_prefix=2),(),self.rules,Strategy())
        self.assertEqual(later.reason,'guard_hidden_attack_max_unimplemented')

    def test_flow_records_both_owner_histories_without_public_target(self):
        b=self.board();s=prior(b);engine=InformationSetForecast(self.rules,self.strategy)
        # A fixed intervention excludes biting a wolf, preserving the role law.
        worlds=tuple(w for w in b.worlds if not w[0]&2);mass=sum(w[-1] for w in worlds)
        physical=replace_worlds(b,tuple((*w[:-1],w[-1]/mass) for w in worlds))
        own=engine.project(s,physical)
        acquired,outcomes=resolve_action(b,(s,(),own,None,physical),2,engine.action_policy)
        self.assertEqual(sum(o.probability for o in outcomes),1)
        success=next(o for o in outcomes if len(o.board.alive)==3)
        self.assertEqual(success.probability,F(1,4))
        self.assertIsInstance(success.context,GuardContext)
        self.assertEqual(success.context.public.worlds,b.worlds)
        self.assertTrue(all(h.attacks[-1].target==2 for h in success.context.private.hypotheses))
        self.assertTrue(all(h.guards[-1].target==2 for h in success.context.private.hypotheses))
        projected=engine.project(acquired[0],success.context.public)
        self.assertTrue(all(not h.attacks and not h.guards for h in projected.hypotheses))
        self.assertEqual(len({h.roles for h in success.context.private.hypotheses}),2)

    def test_public_corpse_uses_guard_failure_not_attack_policy_likelihood(self):
        b=self.board();observed=condition_guard_observation(b,(2,),self.rules)
        self.assertEqual(observed.wolf_probability(2),0)
        self.assertEqual(observed.role_probability(2,'hunter'),F(2,3))
        self.assertEqual(observed.role_probability(1,'hunter'),F(1,6))
        self.assertEqual(observed.role_probability(3,'hunter'),F(1,6))

    def test_no_death_eliminates_guardian_dead_before_night(self):
        from werewolf.exact import action_outcomes
        b=next(o.board for o in action_outcomes(initial_board(5,1,0,0,1),5,self.rules,self.strategy) if o.board.winner is None)
        self.assertGreater(b.role_probability(5,'hunter'),0)
        after=observe(Progress.initial(b),{'deaths':[]},self.rules,self.strategy).board
        self.assertEqual(after.role_probability(5,'hunter'),0)
        self.assertEqual((after.day,after.phase),(2,'day'))

    def later(self):
        b=replace(self.board(4),day=2)
        worlds=tuple(w for w in b.worlds if not w[0]&8);mass=sum(w[-1] for w in worlds)
        return replace_worlds(b,tuple((*w[:-1],w[-1]/mass) for w in worlds),alive=(1,2,3),history=(PublicEvent(2,'day',4),))

    def test_wolf_only_knows_own_successful_attack_and_can_edit_it(self):
        b=self.later();before=copy.deepcopy(b)
        result=evaluate_private_table(b,'wolf',[1],[{'day':1,'target':2,'color':None}],self.rules,self.strategy)
        self.assertEqual(result['players'][1]['probabilities']['hunter'],'0')
        self.assertEqual(result['players'][2]['probabilities']['hunter'],'1/2')
        self.assertEqual(result['players'][1]['final']['village'],'1/12')
        self.assertEqual(result['players'][2]['final']['village'],'0')
        alternate=evaluate_private_table(b,'wolf',[1],[{'day':1,'target':3,'color':None}],self.rules,self.strategy)
        self.assertEqual(alternate['players'][1]['final']['village'],'0')
        missing=evaluate_private_table(b,'wolf',[1],[],self.rules,self.strategy)
        self.assertTrue(all(p['final'] is None for p in missing['players']))
        self.assertIn('秘密襲撃先',missing['reason']);self.assertEqual(b,before)

    def test_invalid_private_attack_and_belief_projection_keep_records(self):
        b=self.later()
        for row in ({'day':1,'target':1,'color':None},{'day':1,'target':2,'color':'white'},
                    {'day':2,'target':2,'color':None}):
            with self.assertRaises(ValueError):condition_private(b,'wolf',[1],[row],rules=self.rules)
        from werewolf.night_knowledge import WolfAttack
        from werewolf.belief_projection import project_private
        s=TrueScanState(tuple(replace(h,attacks=(WolfAttack(1,2),)) for h in from_board(b)),((1,2,3,4),(1,2,3,4)),initial_rule='none',tracked=(),observed_prefix=2)
        projected=project_private(s,b)
        self.assertTrue(all(h.attacks==(WolfAttack(1,2),) for h in projected.hypotheses))
        self.assertEqual(sum(h.mass for h in normalize(projected.hypotheses)),1)

    def test_acquisition_and_report_transfer_preserve_all_personal_records(self):
        from werewolf.guard_effect import GuardIntent
        from werewolf.night_knowledge import WolfAttack
        from werewolf.seer_future_uniform import acquire_uniform
        from werewolf.information_weights import observer_report_weights
        roles=(4,0,0,1)
        source=TrueScanState((Hypothesis(roles,(),F(1)),),((1,2,3),(1,2,3)),initial_rule='none',tracked=(),observed_prefix=2)
        own=replace(source,hypotheses=tuple(Hypothesis(roles,(),F(1,2),(GuardIntent(1,1,t),),(WolfAttack(1,1),)) for t in (2,3)))
        generated=acquire_uniform(own,(1,2,3))
        self.assertEqual({h.guards for h in generated.hypotheses},{h.guards for h in own.hypotheses})
        branches=observer_report_weights(source,own,((F(1),None,source,()),),incomplete=lambda:ValueError())
        self.assertEqual(branches[0][0],1)
        self.assertEqual(branches[0][-1],own)
        self.assertEqual(len(normalize(own.hypotheses)),2)
        engine=InformationSetForecast(self.rules,self.strategy)
        self.assertEqual(engine.value_law(own),source)
        self.assertTrue(all(h.guards and h.attacks for h in own.hypotheses))
