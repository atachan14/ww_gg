import copy,unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import initial_board,Rules,Strategy,Progress,advance
from werewolf.dawn import observe
from werewolf.guard_history_prior import seed_history
from werewolf.public_prior import prepare_public_prior
from werewolf.model_a_public import public_forecast
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.night_knowledge import WolfAttack
from werewolf.private_adapter import evaluate_private_table
from tests.test_guard_forecast import prior


class GuardMaxHistoryTests(unittest.TestCase):
    rules=Rules(initial_seer='none');strategy=Strategy()

    def after_success(self):
        p=advance(Progress.initial(initial_board(5,1,0,0,1)),5,self.rules,self.strategy)
        return observe(p,{'deaths':[]},self.rules,self.strategy)

    def state(self,b):
        s,_=prepare_public_prior({},b,self.rules,track_live_seers=False)
        return seed_history(b,s)

    def test_first_five_player_result_matches_hand_calculation(self):
        b=initial_board(5,1,0,0,1)
        result=public_forecast(b,prior(b),(),self.rules,self.strategy)
        # First execution: 1/5 wins, 4/5 reaches the four-alive night.
        # Its success 1/6 continues at 13/48, failure 5/6 at 1/3.
        night=F(1,6)*F(13,48)+F(5,6)*F(1,3)
        self.assertEqual(night,F(31,96))
        self.assertEqual(result.village_win,F(1,5)+F(4,5)*night)
        self.assertEqual(result.village_win,F(11,24))

    def test_two_initial_wolves_keep_dead_teammate_in_owned_information_set(self):
        b=initial_board(5,2,0,0,1)
        result=public_forecast(b,prior(b),(),self.rules,self.strategy)
        self.assertEqual(result.village_win,F(23,180)) # 2/5 * 23/72.
        p=advance(Progress.initial(b),1,self.rules,self.strategy)
        p=observe(p,{'deaths':[]},self.rules,self.strategy)
        b=advance(p,5,self.rules,self.strategy).board;s=self.state(b)
        engine=InformationSetForecast(self.rules,self.strategy)
        self.assertEqual(engine.wolf_policy(b,s,(),3,(WolfAttack(1,3),)),((4,F(1)),))
        self.assertEqual(engine.wolf_policy(b,s,(),3,(WolfAttack(1,4),)),((3,F(1)),))

    def test_public_history_mixture_preserves_role_prior_and_all_alternatives(self):
        b=self.after_success().board;s=self.state(b);before=copy.deepcopy((b,s))
        self.assertEqual(s.public_roles,tuple(sorted(b.worlds)))
        self.assertEqual(len(s.hypotheses),2*len(b.worlds))
        for h in s.hypotheses:
            self.assertEqual(h.attacks[0].target,h.guards[0].target)
            self.assertFalse((h.roles[0]|h.roles[3])&(1<<(h.attacks[0].target-1)))
        result=public_forecast(b,s,(),self.rules,self.strategy)
        self.assertEqual(result.village_win,F(13,48))
        self.assertTrue(all(v==F(13,48) for _,v in result.action_values))
        self.assertTrue(all(v.village_win==F(1,4) and v.wolf_win==F(11,16) for _,v in result.by_dawn_values))
        self.assertEqual((b,s),before)

    def test_owned_histories_split_max_policy_and_cache_without_public_leak(self):
        b=advance(self.after_success(),4,self.rules,self.strategy).board;s=self.state(b)
        before=copy.deepcopy((b,s));engine=InformationSetForecast(self.rules,self.strategy)
        self.assertEqual(engine.wolf_policy(b,s,(),1,(WolfAttack(1,2),)),((3,F(1)),))
        self.assertEqual(engine.wolf_policy(b,s,(),1,(WolfAttack(1,3),)),((2,F(1)),))
        self.assertEqual(engine.wolf_policy(b,s,(),1,(WolfAttack(1,4),)),((2,F(1,2)),(3,F(1,2))))
        self.assertEqual(len(engine.policies),3)
        self.assertEqual(public_forecast(b,s,(),self.rules,self.strategy).village_win,F(1,36))
        self.assertEqual((b,s),before)

    def test_viewer_history_conditions_source_and_guard_actor_stays_private(self):
        b=advance(self.after_success(),4,self.rules,self.strategy).board
        before=copy.deepcopy(b)
        view=evaluate_private_table(b,'wolf',[1],[{'day':1,'target':2,'color':None}],self.rules,self.strategy)
        self.assertEqual(view['players'][1]['final']['village'],'1/12')
        self.assertEqual(view['players'][2]['final']['village'],'0')
        hunter=evaluate_private_table(b,'hunter',[1],[{'day':1,'target':2,'color':None}],self.rules,self.strategy)
        self.assertEqual(hunter['players'][1]['final']['village'],'0')
        self.assertEqual(hunter['players'][2]['final']['village'],'0')
        self.assertEqual(b,before)

    def test_historical_proof_is_required_not_inferred_from_later_symmetry(self):
        b=advance(self.after_success(),4,self.rules,self.strategy).board
        no_proof=replace(b,guard_prior_roster=None)
        s=self.state(no_proof)
        self.assertTrue(all(not h.attacks for h in s.hypotheses))
        result=public_forecast(no_proof,s,(),self.rules,self.strategy)
        self.assertEqual(result.reason,'guard_hidden_attack_max_unimplemented')

    def test_late_five_alive_cut_from_nine_players_preserves_full_roster(self):
        p=Progress.initial(initial_board(9,4,0,0,1));old=Strategy('random','random')
        for day,night in ((1,2),(3,4)):
            p=advance(p,day,self.rules,old)
            p=observe(p,{'deaths':[night]},self.rules,old)
        b=p.board
        self.assertEqual(b.alive,(5,6,7,8,9))
        self.assertEqual(sum(b.role_probability(i,'hunter') for i in b.alive),F(72,137))
        result=public_forecast(b,self.state(b),(),self.rules,self.strategy)
        self.assertEqual(result.village_win,F(268,2055))
        p=advance(p,5,self.rules,self.strategy)
        p=observe(p,{'deaths':[]},self.rules,self.strategy)
        self.assertEqual(p.board.guard_prior_roster,(3,(6,7,8,9)))
        p=advance(p,9,self.rules,self.strategy)
        view=evaluate_private_table(p.board,'hunter',[6],[{'day':1,'target':7,'color':None},
                  {'day':2,'target':7,'color':None},{'day':3,'target':7,'color':None}],self.rules,self.strategy)
        self.assertTrue(any(row['final'] is not None for row in view['players']))

    def test_guardian_can_be_deduced_by_wolves_without_public_identity(self):
        from werewolf.exact import condition_claims,ClaimPolicy
        from werewolf.guard_history_prior import hero_deducible
        b=condition_claims(initial_board(5,2,0,0,1),('latent','latent','latent','villager','villager'),ClaimPolicy())
        self.assertTrue(hero_deducible(b))
        self.assertEqual(b.role_probability(1,'hunter'),F(1,3))
        result=public_forecast(b,prior(b),(),self.rules,self.strategy)
        self.assertEqual(result.village_win,F(1,3))

    def test_private_guardian_deduction_keeps_scan_law_and_public_secrecy(self):
        from werewolf.exact import condition_claims,ClaimPolicy
        b=condition_claims(initial_board(5,1,1,1,1),('latent','latent','seer','medium','villager'),ClaimPolicy())
        p=advance(Progress.initial(b),5,self.rules,self.strategy);b=p.board
        game={'players':5,'rules':{'initial_seer':'none'},'seer_options':{'initial_rule':'none'},'seer_inputs':[],'public_log':{'version':2}}
        s,past=prepare_public_prior(game,b,self.rules)
        result=public_forecast(b,s,past,self.rules,self.strategy)
        self.assertEqual(result.village_win,F(11,18))
        engine=InformationSetForecast(self.rules,self.strategy)
        self.assertEqual(engine.wolf_policy(b,s,past,1),((3,F(1)),))
        self.assertEqual(b.role_probability(2,'hunter'),F(1,2))
