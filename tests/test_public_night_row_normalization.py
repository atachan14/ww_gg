"""Characterization only: the global proposal is not an enabled UI contract."""
import unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import initial_board,replace_worlds,action_outcomes,legal_targets,Rules,Strategy,value_for_action
from werewolf.seer_acquisition import from_board,normalize
from werewolf.seer_future_uniform import TrueScanState
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.model_a_public import horizon_for_action
from werewolf.model_a_public import public_forecast
from werewolf.by_dawn import action_by_dawn,HorizonValues


class PublicNightNormalizationTests(unittest.TestCase):
    rules=Rules(initial_seer='none')
    strategy=Strategy('random','random')

    def proposed(self,b,target):
        s=TrueScanState(from_board(b),(tuple(range(1,b.player_count+1)),),initial_rule='none',tracked=())
        kept=tuple(h for h in s.hypotheses if not h.roles[0]&(1<<(target-1)))
        own=replace(s,hypotheses=normalize(kept));e=InformationSetForecast(self.rules,self.strategy)
        return e,s,own

    def test_reachable_six_player_row_preserves_count_prior_only_in_old_law(self):
        b=action_outcomes(initial_board(6,2),6,self.rules,self.strategy)[0].board
        self.assertEqual(b.wolf_count_distribution,{1:F(1,3),2:F(2,3)})
        e,s,own=self.proposed(b,3)
        mass_by_count={w:sum((h.mass for h in s.hypotheses if not h.roles[0]&4 and
                              (h.roles[0]&b.alive_mask).bit_count()==w),F()) for w in (1,2)}
        self.assertEqual(mass_by_count,{1:F(4,15),2:F(6,15)})
        self.assertEqual(sum(mass_by_count.values()),F(2,3))
        old=action_outcomes(b,3,self.rules,self.strategy)
        old_weights={world[0]:o.probability*world[-1] for o in old for world in o.board.worlds}
        self.assertEqual({q for mask,q in old_weights.items() if mask&32},{F(1,12)})
        self.assertEqual({q for mask,q in old_weights.items() if not mask&32},{F(1,9)})
        self.assertEqual({h.mass for h in own.hypotheses},{F(1,10)})
        self.assertEqual(value_for_action(b,3,self.rules,self.strategy).village_win,F(1,12))
        self.assertEqual(e.act(b,s,(),3,own,None),F(1,10))
        self.assertEqual(action_by_dawn(b,3,self.rules,self.strategy),HorizonValues(F(0),F(2,3)))
        self.assertEqual(horizon_for_action(e,b,s,(),3,own),HorizonValues(F(0),F(3,5)))
        self.assertEqual(e.scalar(b,s,()),F(1,12))
        approved=public_forecast(b,s,(),self.rules,self.strategy)
        self.assertEqual(dict(approved.action_values)[3],F(1,12))
        self.assertEqual(dict(approved.by_dawn_values)[3],HorizonValues(F(0),F(2,3)))

    def test_old_row_is_absent_if_a_count_group_has_no_legal_assignment(self):
        seed=replace_worlds(initial_board(6,2),tuple((mask,0,0,0,F(1,4)) for mask in (33,36,3,10)))
        b=action_outcomes(seed,6,self.rules,self.strategy)[0].board
        self.assertNotIn(2,legal_targets(b,self.rules,self.strategy))
        e,s,own=self.proposed(b,2)
        self.assertEqual(e.act(b,s,(),2,own,None),F(1,4))
        self.assertNotIn(2,dict(public_forecast(b,s,(),self.rules,self.strategy).action_values))

    def test_single_count_conditioning_is_identical(self):
        b=replace(initial_board(5,1),phase='night');e,s,own=self.proposed(b,3)
        old=action_outcomes(b,3,self.rules,self.strategy)
        weights={world[0]:o.probability*world[-1] for o in old for world in o.board.worlds}
        self.assertEqual(weights,{h.roles[0]:h.mass for h in own.hypotheses})
        self.assertEqual(value_for_action(b,3,self.rules,self.strategy).village_win,F(1,4))
        self.assertEqual(e.act(b,s,(),3,own,None),F(1,4))
