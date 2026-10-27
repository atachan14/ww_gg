import unittest
from dataclasses import replace
from fractions import Fraction as F
from itertools import permutations
from werewolf.exact import initial_board,replace_worlds,action_outcomes,Rules,Strategy,PublicEvent
from werewolf.seer_acquisition import from_board,Hypothesis
from werewolf.seer_future_uniform import TrueScanState
from werewolf.seer_future_forecast import project_private
from werewolf.information_set_forecast import InformationSetForecast,information_forecast


class ModelATests(unittest.TestCase):
    def fixture(self):
        seed=replace_worlds(initial_board(4,1,0,1),((2,0,1,0,F(1,2)),(1,0,4,0,F(1,2))))
        b=next(o.board for o in action_outcomes(seed,4,Rules(initial_seer='none'),Strategy()) if o.board.winner is None)
        s=project_private(TrueScanState(from_board(seed),((1,2,3,4),),initial_rule='none',tracked=()),b)
        return b,s

    def test_random_roster_kernel_and_max_tie_are_legal_and_uniform(self):
        b,s=self.fixture()
        for mode in ('random','max'):
            engine=InformationSetForecast(Rules(initial_seer='none'),Strategy('max',mode))
            self.assertEqual(engine.wolf_policy(b,s,(),2),((1,F(1,2)),(3,F(1,2))))
            self.assertEqual(engine.wolf_policy(b,s,(),1),((2,F(1,2)),(3,F(1,2))))

    def test_max_averages_hidden_roles_before_comparison(self):
        b=replace(initial_board(4,1,0,1),phase='night')
        b=replace_worlds(b,((2,0,1,0,F(1,2)),(2,0,4,0,F(1,2))))
        s=TrueScanState(from_board(b),((1,2,3,4),),initial_rule='none',tracked=())
        engine=InformationSetForecast(Rules(initial_seer='none'),Strategy())
        calls=[]
        # Isolate the information-set max with opposite hidden-state payoffs.
        # Per-world min would return0, while the information-set minimum is1/2.
        def payoff(b,state,past,target,private,observer):
            self.assertIsNone(observer);calls.append(tuple(private.hypotheses))
            return sum((h.mass*({1:{1:F(0),3:F(1),4:F(1)},4:{1:F(1),3:F(0),4:F(1)}}[h.roles[2]][target]) for h in private.hypotheses),F())
        engine.act=payoff
        self.assertEqual(engine.wolf_policy(b,s,(),2),((1,F(1,2)),(3,F(1,2))))
        self.assertTrue(all(len(hs)==2 for hs in calls))

    def test_actor_policy_is_player_permutation_invariant(self):
        b,s=self.fixture();base=InformationSetForecast(Rules(initial_seer='none'),Strategy()).wolf_policy(b,s,(),2)
        for ids in permutations((1,2,3)):
            mapping=dict(zip((1,2,3,4),(*ids,4)))
            def mask(m):return sum(1<<(mapping[p]-1) for p in mapping if m&(1<<(p-1)))
            hs=tuple(Hypothesis(tuple(mask(v) for v in h.roles),(),h.mass) for h in s.hypotheses)
            st=replace(s,hypotheses=hs)
            renamed=replace(replace_worlds(b,st.public_roles),history=tuple(PublicEvent(e.day,e.phase,mapping[e.target]) for e in b.history))
            actual=dict(InformationSetForecast(Rules(initial_seer='none'),Strategy()).wolf_policy(renamed,st,(),mask(2)))
            self.assertEqual(actual,{mapping[p]:q for p,q in base})

    def test_public_update_ignores_choice_likelihood(self):
        seed=replace_worlds(initial_board(7,2),((65,0,0,0,F(1,2)),(3,0,0,0,F(1,2))))
        b=next(o.board for o in action_outcomes(seed,7,Rules(),Strategy()) if o.board.winner is None)
        engine=InformationSetForecast(Rules(),Strategy('random','random'))
        child=engine.public_children(b,3)[0].board
        from werewolf.exact import Progress
        from werewolf.dawn import observe
        self.assertEqual(child,observe(Progress.initial(b),{'deaths':[3]},Rules(),Strategy('random','random')).board)
        self.assertEqual(child.wolf_count_distribution,{1:F(1,2),2:F(1,2)})
        self.assertNotEqual(child.wolf_count_distribution,{1:F(4,9),2:F(5,9)})

    def test_compatibility_update_reweights_illegal_rosters_without_policy_likelihood(self):
        seed=replace_worlds(initial_board(7,2),((65,0,0,0,F(1,2)),(3,0,0,0,F(1,2))))
        b=next(o.board for o in action_outcomes(seed,7,Rules(),Strategy()) if o.board.winner is None)
        child=InformationSetForecast(Rules(),Strategy()).public_children(b,2)[0].board
        self.assertEqual(child.wolf_count_distribution,{1:F(1)})

    def test_new_private_black_holder_does_not_change_wolf_information_policy(self):
        from tests.test_model_a_night_oracles import two_seer_attack_score
        seed=replace(replace_worlds(initial_board(7,2,0,2),((12,0,3,0,F(1,2)),(24,0,3,0,F(1,2)))),
                     claims=('seer','seer')+('latent',)*5)
        b=next(o.board for o in action_outcomes(seed,7,Rules(initial_seer='none'),Strategy()) if o.board.winner is None)
        s=project_private(TrueScanState(from_board(seed),((1,2,3,4,5,6,7),),initial_rule='none',tracked=(1,2)),b)
        for black_holder in (1,2):
            def actual_hidden(h,st):
                if h.roles[0]!=12:return False
                if len(st.rosters)<2:return True
                return all(any(a.day==2 and a.player==p and a.target==(3 if p==black_holder else 6)
                               for a in h.acquisitions) for p in (1,2))
            trace={}
            value=information_forecast(b,s,(),Rules(initial_seer='none'),Strategy(),observer=actual_hidden,
                                       trace=trace,max_work=2000000)
            self.assertEqual(value,F(3,4))
            root=next(x for x in trace['wolf_policies'] if x['history']==b.history and x['mask']==12)
            self.assertEqual(root['policy'],((1,F(1,2)),(2,F(1,2))))
            self.assertEqual(dict(root['scores'])[1],two_seer_attack_score(1))
            self.assertEqual(dict(root['scores'])[2],two_seer_attack_score(2))

    def test_self_bite_preference_and_dead_initial_teammate_are_respected(self):
        b,s=self.fixture()
        self.assertIn(2,dict(InformationSetForecast(Rules(True),Strategy('random','random',include_self_bite=True)).wolf_policy(b,s,(),2)))
        self.assertNotIn(2,dict(InformationSetForecast(Rules(True),Strategy('random','random')).wolf_policy(b,s,(),2)))
        seed=replace_worlds(initial_board(5,2),((3,0,0,0,F(1)),))
        b=next(o.board for o in action_outcomes(seed,1,Rules(),Strategy()) if o.board.winner is None)
        s=TrueScanState(from_board(b),((1,2,3,4,5),),initial_rule='none',tracked=())
        self.assertEqual(InformationSetForecast(Rules(),Strategy('random','random')).wolf_policy(b,s,(),3),
                         ((3,F(1,3)),(4,F(1,3)),(5,F(1,3))))

    def test_night_start_targets_preserve_explicit_model_difference(self):
        from tests.test_model_a_night_oracles import one_night_value
        from werewolf.seer_acquisition import Acquisition,SeerReport
        from werewolf.seer_future_forecast import forecast
        seed=replace(replace_worlds(initial_board(5,2,0,1),((9,0,2,0,F(1,2)),(17,0,2,0,F(1,2)))),
                     claims=('seer','seer','latent','latent','latent'))
        b=next(o.board for o in action_outcomes(seed,1,Rules(initial_seer='normal'),Strategy()) if o.board.winner is None)
        hs=tuple(Hypothesis(h.roles,(Acquisition(1,2,3,'white'),),h.mass) for h in from_board(seed))
        s=project_private(TrueScanState(hs,((1,2,3,4,5),),initial_rule='normal',tracked=(2,)),b)
        past=(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'white'))
        policy=Strategy('max','random');rules=Rules(initial_seer='normal')
        # bb3f5b6 supersedes corpse-target rules: executed1 is not a target.
        # The two evaluators intentionally have different attack measures.
        self.assertEqual(forecast(b,s,past,rules,policy).village_win,one_night_value(physical=False))
        self.assertEqual(InformationSetForecast(rules,policy).scalar(b,s,past),one_night_value(physical=True))
        self.assertEqual(F(5,6),F(1,3)*(F(1,2)+1+1))
