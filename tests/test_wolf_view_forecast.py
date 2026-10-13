import copy
import unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import (initial_board, action_outcomes, Rules, Strategy, replace_worlds,
                            value_for_action, condition_claims, ClaimPolicy)
from werewolf.private_view import condition_private
from werewolf.wolf_view_forecast import wolf_forecast
from werewolf.seer_acquisition import Hypothesis, Acquisition, SeerReport
from werewolf.seer_future_uniform import TrueScanState, FuturePending


def night(n=5, wolves=1, target=5, **counts):
    return next(o.board for o in action_outcomes(initial_board(n, wolves, **counts), target, Rules(), Strategy())
                if o.board.winner is None)


class WolfConditionalForecastTests(unittest.TestCase):
    def test_symmetric_max_ties_are_uniform_for_every_roster_and_target(self):
        b = night()
        before = copy.deepcopy(b)
        for mask in (1, 2, 4, 8):
            with self.subTest(mask=mask):
                result = dict(wolf_forecast(b, mask, Rules(), Strategy()))
                self.assertEqual(set(result.values()), {F(1, 3)})
        self.assertEqual(b, before)

    def test_no_secret_leak_to_execution_even_when_naive_solver_would_win(self):
        b = night()
        private = condition_private(b, 'wolf', (3,), rules=Rules()).board
        self.assertEqual(value_for_action(private, 2, Rules(), Strategy()).village_win, 1)
        self.assertEqual(dict(wolf_forecast(b, 4, Rules(), Strategy()))[2], F(1,3))
        trace_a = {}; trace_b = {}
        wolf_forecast(b, 1, Rules(), Strategy(), trace=trace_a)
        wolf_forecast(b, 4, Rules(), Strategy(), trace=trace_b)
        def public_day_choices(trace):
            return {tuple(v['history']): v['targets'] for v in trace['choices'] if v['phase'] == 'day'}
        a, other = public_day_choices(trace_a), public_day_choices(trace_b)
        shared = set(a) & set(other)
        self.assertTrue(shared)
        self.assertTrue(all(a[k] == other[k] for k in shared))
        self.assertEqual(a[((1, 'day', 5), (1, 'night', 2))], (1,3,4))

    def test_random_day_averages_without_truth_optimization(self):
        b = night()
        for mask in (1, 2, 4, 8):
            with self.subTest(mask=mask):
                self.assertEqual(set(dict(wolf_forecast(b, mask, Rules(), Strategy('random', 'random'))).values()), {F(1, 3)})

    def test_uniform_private_values_recombine_to_existing_public_max_value(self):
        symmetric = night()
        asymmetric = replace_worlds(symmetric, ((2,0,0,0,F(1,2)), (4,0,0,0,F(1,4)), (8,0,0,0,F(1,4))))
        for b in (symmetric, asymmetric):
            conditional = {w[0]: dict(wolf_forecast(b,w[0],Rules(),Strategy())) for w in b.worlds}
            for target in b.alive:
                supported = [(w[0],w[-1]) for w in b.worlds if not w[0] & (1 << (target-1))]
                mass = sum((q for _,q in supported),F())
                combined = sum((q/mass*conditional[mask][target] for mask,q in supported),F())
                self.assertEqual(combined,value_for_action(b,target,Rules(),Strategy()).village_win)

    def test_random_continuation_matches_independent_actual_roster_enumeration(self):
        from functools import lru_cache
        @lru_cache(None)
        def brute(alive, phase, mask):
            count = sum(bool(mask & (1 << (p-1))) for p in alive)
            if count == 0: return F(1)
            if count >= len(alive) - count: return F(0)
            choices = alive if phase == 'day' else tuple(p for p in alive if not mask & (1 << (p-1)))
            return sum((brute(tuple(p for p in alive if p != t), 'night' if phase == 'day' else 'day', mask)
                        for t in choices), F()) / len(choices)
        b = night(7, 2, 7)
        for mask, literal in ((3, F(2,15)), (65, F(7,15))):
            with self.subTest(mask=mask):
                values = dict(wolf_forecast(b, mask, Rules(), Strategy('random','random')))
                for target, value in values.items():
                    self.assertEqual(value, brute(tuple(p for p in b.alive if p != target), 'day', mask))
                    self.assertEqual(value, literal)

    def test_player_relabeling_preserves_max_conditional_values(self):
        from itertools import permutations
        from werewolf.exact import PublicEvent
        b = night()
        # Asymmetric PUBLIC prior: wolf2 has double the mass of wolf3/4.
        # Permute the prior together with the player labels, not just the viewer.
        b = replace_worlds(b, ((2,0,0,0,F(1,2)), (4,0,0,0,F(1,4)), (8,0,0,0,F(1,4))))
        expected = dict(wolf_forecast(b, 4, Rules(), Strategy()))
        self.assertEqual(expected, {1:F(0), 2:F(1,2), 4:F(0)})
        for ids in permutations((1,2,3,4)):
            mapping = dict(zip((1,2,3,4,5), (*ids,5)))
            def relabel(mask):
                return sum(1 << (mapping[p]-1) for p in mapping if mask & (1 << (p-1)))
            worlds = tuple((*[relabel(mask) for mask in w[:-1]], w[-1]) for w in b.worlds)
            renamed = replace(replace_worlds(b,worlds),
                              alive=tuple(sorted(mapping[p] for p in b.alive)),
                              history=tuple(PublicEvent(e.day,e.phase,mapping[e.target]) for e in b.history))
            result = dict(wolf_forecast(renamed,relabel(4),Rules(),Strategy()))
            self.assertEqual(result,{mapping[p]:v for p,v in expected.items()})

    def test_dead_initial_teammates_and_self_bite_rules(self):
        b = night(7, 2, 1)
        result = wolf_forecast(b, 3, Rules(), Strategy('random', 'random'))
        self.assertNotIsInstance(result, FuturePending)
        self.assertEqual(set(dict(result)), {3, 4, 5, 6, 7})
        b = night()
        result = dict(wolf_forecast(b, 4, Rules(True), Strategy(include_self_bite=True)))
        self.assertEqual(result[3], 1)

    def test_budget_and_unsupported_prior_return_no_partial_values(self):
        self.assertIsInstance(wolf_forecast(night(), 4, Rules(), Strategy(), max_work=1), FuturePending)
        with self.assertRaises(ValueError): wolf_forecast(night(), 16, Rules(), Strategy())

    def test_existing_medium_random_and_max_instructions_remain_public(self):
        from werewolf.exact import Progress, advance
        worlds = ((2,4,0,0,F(1,2)),(4,2,0,0,F(1,2)))
        b = replace(replace_worlds(initial_board(5,1,1),worlds), claims=('latent','medium','medium','latent','latent'))
        b = advance(Progress.initial(b),4,Rules(),Strategy()).board
        for fake in ('random', 'max'):
            trace = {}
            result = wolf_forecast(b,2,Rules(),Strategy(fake_reports=fake),trace=trace)
            self.assertNotIsInstance(result,FuturePending)
            self.assertTrue(all(0 <= v <= 1 for _,v in result))
            self.assertTrue(trace['public_rankings'])

    def test_future_seer_signals_use_public_joint_ledger_and_public_policy(self):
        # Publicly known true seer1, uncertain wolf4/5; dead wolf2 retained.
        from werewolf.exact import Progress, advance
        from werewolf.seer_future_forecast import project_private
        worlds = ((10,0,1,0,F(1,2)),(18,0,1,0,F(1,2)))
        b = replace(replace_worlds(initial_board(5,2,0,1),worlds), claims=('seer','seer','latent','latent','latent'))
        s = TrueScanState(tuple(Hypothesis(r[:-1],(Acquisition(1,1,3,'white'),),r[-1]) for r in worlds), ((1,2,3,4,5),))
        b = advance(Progress.initial(b),2,Rules(),Strategy()).board
        s = project_private(s,b)
        before = copy.deepcopy((b,s))
        past=(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'black'))
        result=wolf_forecast(b,10,Rules(),Strategy(),scan_state=s,past=past,max_work=1000000)
        self.assertNotIsInstance(result,FuturePending)
        self.assertEqual(dict(result)[3],1)
        self.assertEqual(dict(result)[1],F(1,2))
        other=wolf_forecast(b,18,Rules(),Strategy(),scan_state=s,past=past,max_work=1000000)
        self.assertEqual(dict(other)[1],F(1,2))
        self.assertEqual(dict(other)[3],1)
        self.assertEqual((b,s),before)

    def test_multiple_fake_future_model_stays_pending_without_partial_table(self):
        seed = replace(replace_worlds(initial_board(7,2,0,1),((6,0,1,0,F(1)),)),
                       claims=('seer','seer','seer','latent','latent','latent','latent'))
        b = next(o.board for o in action_outcomes(seed,7,Rules(),Strategy()) if o.board.winner is None)
        s = TrueScanState((Hypothesis((6,0,1,0),(Acquisition(1,1,4,'white'),),F(1)),), ((1,2,3,4,5,6,7),))
        result = wolf_forecast(b,6,Rules(),Strategy(),scan_state=s)
        self.assertIsInstance(result,FuturePending)
        self.assertEqual(result.reason,'multiple_fake_report_correlation_unselected')
