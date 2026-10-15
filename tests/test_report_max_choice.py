import unittest
from copy import deepcopy
from fractions import Fraction as F
from werewolf.exact import (initial_board,replace_worlds,PublicEvent,Rules,Strategy,
    report_actions,random_report_outcomes,condition_claims,ClaimPolicy,action_outcomes)
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.wolf_view_forecast import wolf_forecast

class ReportMaxChoiceTests(unittest.TestCase):
    def fixture(self):
        b=replace_worlds(initial_board(8,2,1),((129,2,0,0,F(1,2)),(3,4,0,0,F(1,2))),
            alive=(1,2,3,4,5,6),wolf_count=None,day=2,
            claims=('latent','medium')+('latent',)*6,
            history=(PublicEvent(1,'day',8),PublicEvent(1,'night',7)),
            medium_opportunities=((2,2,8),))
        s=TrueScanState(from_board(b),(tuple(range(1,9)),tuple(range(1,7))),
                        initial_rule='none',tracked=())
        return b,s,InformationSetForecast(Rules(),Strategy(fake_reports='max',disclosure_common='all'))

    def test_all_ties_keep_original_instruction_mass_and_merge_public_vectors(self):
        b,s,e=self.fixture();before=deepcopy((b,s));e.scalar=lambda *args:F(1,2)
        branches=e.morning(b,s,());actual=tuple((q,child) for q,child,*_ in branches)
        self.assertEqual(actual,tuple((o.probability,o.board) for o in random_report_outcomes(b)))
        black=next((q,c,st) for q,c,st,p in branches if c.reports[-1].color=='black')
        self.assertEqual(black[0],F(3,4))
        self.assertEqual(black[1].wolf_count_distribution,{1:F(2,3),2:F(1,3)})
        self.assertEqual(black[2].public_roles,tuple(sorted(black[1].worlds)))
        self.assertEqual(sum(q for q,*_ in branches),1)
        self.assertEqual((b,s),before)

    def test_unique_min_uses_whole_instruction_expectation_before_selection(self):
        b,s,e=self.fixture();e.scalar=lambda child,*args:F(child.reports[-1].color=='black')
        branches=e.morning(b,s,())
        expected=next(a for a in report_actions(b) if a.fake_colors==((2,'white'),))
        self.assertEqual(tuple((q,c) for q,c,*_ in branches),
                         tuple((o.probability,o.board) for o in expected.outcomes))

    def test_incomplete_report_evaluation_is_not_selected_or_cached(self):
        b,s,e=self.fixture();calls=[]
        def incomplete(*args):
            calls.append(args)
            if len(calls)==2:raise Pending('unfinished-report')
            return F()
        e.scalar=incomplete
        with self.assertRaises(Pending) as failure:e.morning(b,s,())
        self.assertEqual(failure.exception.reason,'unfinished-report')
        self.assertFalse(e.mornings)

    def test_legacy_wolf_owner_keeps_public_report_ranking_and_all_rows(self):
        b=condition_claims(initial_board(5,1,1),('medium','medium','latent','latent','latent'),
                           ClaimPolicy(medium='none'))
        b=next(o.board for o in action_outcomes(b,5,Rules(),Strategy()) if not o.board.winner)
        before=deepcopy(b)
        for mode,other in (('max',F(1,2)),('random',F(3,4))):
            strategy=Strategy('max','max',fake_reports=mode)
            self.assertEqual(wolf_forecast(b,1,Rules(),strategy),((2,F(1)),(3,other),(4,other)))
            self.assertEqual(wolf_forecast(b,2,Rules(),strategy),((1,F(1)),(3,other),(4,other)))
        self.assertEqual(b,before)
