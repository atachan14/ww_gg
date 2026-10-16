import unittest
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import initial_board,replace_worlds,action_outcomes,Rules,Strategy
from werewolf.wolf_view_forecast import wolf_forecast
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState,FuturePending
from werewolf.seer_future_forecast import project_private
from tests.test_seer_view_forecast import fixture as seer_fixture

class WolfTargetChoiceTests(unittest.TestCase):
    def night_fixture(self):
        seed=replace_worlds(initial_board(7,1),tuple((m,0,0,0,q) for m,q in
            zip((2,4,8,16,32),(F(2,5),F(3,10),F(1,10),F(1,10),F(1,10)))))
        return next(o.board for o in action_outcomes(seed,7,Rules(),Strategy()) if not o.board.winner)

    def test_night_filters_owned_wolf_before_min_and_preserves_all_ties(self):
        b=self.night_fixture();before=deepcopy(b);trace={}
        value=wolf_forecast(b,4,Rules(),Strategy(),trace=trace)
        self.assertEqual(value,tuple((t,F(1)) for t in (1,2,4,5,6)))
        history=((1,'day',7),(1,'night',1),(2,'day',2))
        ranked=next(x['values'] for x in trace['public_rankings'] if x['history']==history)
        self.assertEqual(dict(ranked)[3],F(1,3))
        self.assertTrue(all(v==F(3,5) for p,v in ranked if p!=3))
        chosen=next(x['targets'] for x in trace['choices'] if x['history']==history)
        self.assertEqual(chosen,(4,5,6))
        self.assertEqual(b,before)

    def test_random_legal_candidates_are_not_replaced_by_public_max_selection(self):
        b=self.night_fixture();history=((1,'day',7),(1,'night',4),(2,'day',2));choices={}
        for night in ('max','random'):
            trace={};wolf_forecast(b,4,Rules(),Strategy('max',night),trace=trace)
            choices[night]=next(x['targets'] for x in trace['choices'] if x['history']==history)
        self.assertEqual(choices,{'max':(1,),'random':(1,5,6)})

    def test_observer_private_payoffs_keep_public_ranking_and_complete_values(self):
        b,s=seer_fixture();before=deepcopy((b,s));rankings=[]
        for target,expected in ((2,F(67,80)),(3,F(121,140))):
            def observer(h,state,target=target):
                return len(state.rosters)<2 or any(a.player==1 and a.day==2 and a.target==target
                                                   for a in h.acquisitions)
            trace={}
            value=wolf_forecast(b,None,Rules(initial_seer='none'),Strategy('max','random'),
                               scan_state=s,observer=observer,trace=trace)
            self.assertEqual(value,expected)
            # Later observations can publish different scan targets/results.
            # Equal death history alone does not identify the same public Board.
            root_history=tuple((e.day,e.phase,e.target) for e in b.history)
            root=tuple(x['values'] for x in trace['public_rankings']
                       if x['history']==root_history and x['phase']==b.phase)
            self.assertEqual(len(root),1);rankings.append(root)
        self.assertEqual(rankings[0],rankings[1])
        self.assertEqual((b,s),before)

    def test_observer_illegal_public_instruction_stays_pending_without_reselection(self):
        worlds=((12,0,1,0,F(1,4)),(68,0,1,0,F(1,4)),
                (9,0,2,0,F(1,4)),(65,0,2,0,F(1,4)))
        seed=replace(replace_worlds(initial_board(7,2,0,1),worlds),claims=('seer',)+('latent',)*6)
        b=next(o.board for o in action_outcomes(seed,7,Rules(initial_seer='none'),Strategy())
               if not o.board.winner)
        s=project_private(TrueScanState(from_board(seed),(tuple(range(1,8)),),
                                       initial_rule='none',tracked=(1,)),b)
        before=deepcopy((b,s))
        result=wolf_forecast(b,None,Rules(initial_seer='none'),Strategy('max','random'),
            scan_state=s,observer=lambda h,state:bool(h.roles[2]&1),max_work=1000000)
        self.assertIsInstance(result,FuturePending)
        self.assertEqual(result.reason,'seer_view_public_instruction_private_illegal')
        self.assertEqual((b,s),before)
