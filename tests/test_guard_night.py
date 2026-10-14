import unittest
from dataclasses import replace,asdict
from fractions import Fraction as F
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy
from werewolf.guard_effect import GuardIntent
from werewolf.guard_night import resolve_fixed_guard_night,guard_targets
from werewolf.setup import complete_rules,GameConfig


class GuardNightTests(unittest.TestCase):
    def board(self):
        b=initial_board(5,1,0,0,1)
        return replace_worlds(b,((4,0,0,1,F(1)),),phase='night')

    def test_game_rule_default_and_saved_rule(self):
        self.assertTrue(complete_rules({}).allow_repeat_guard)
        self.assertNotIn('allow_repeat_guard',asdict(Strategy()))
        for bad in (1,'true',None):
            with self.assertRaises(ValueError):Rules(allow_repeat_guard=bad)
        game=dict(players=5,wolves=1,hunters=1,rules=asdict(Rules(allow_repeat_guard=False)))
        self.assertFalse(GameConfig.from_game(game).draft().allow_repeat_guard)
        self.assertEqual(guard_targets(replace(self.board(),day=2),1,Rules(allow_repeat_guard=False),2),(3,4,5))

    def test_success_advances_no_death_and_no_private_notification(self):
        b=self.board();intent=GuardIntent(1,1,2)
        out,=resolve_fixed_guard_night(b,intent,2)
        self.assertEqual((out.board.day,out.board.phase,out.board.alive),(2,'day',b.alive))
        self.assertEqual(out.board.history,());self.assertIsNone(out.context)
        self.assertEqual(out.probability,1);self.assertEqual(b.day,1)

    def test_second_night_repeated_guard_and_guardian_attacked(self):
        b=resolve_fixed_guard_night(self.board(),GuardIntent(1,1,2),2)[0].board
        b=replace(b,phase='night')
        r=resolve_fixed_guard_night(b,GuardIntent(2,1,2),1)[0].board
        self.assertEqual(r.alive,(2,3,4,5));self.assertEqual(r.history[-1].day,2)
        self.assertEqual(r.history[-1].target,1)

    def test_success_precedes_terminal_preflight(self):
        # Build a complete three-player world instead of inconsistent history.
        b=replace_worlds(initial_board(3,1,0,0,1),((4,0,0,1,F(1)),),phase='night')
        saved=resolve_fixed_guard_night(b,GuardIntent(1,1,2),2)[0].board
        lost=resolve_fixed_guard_night(b,GuardIntent(1,1,2),1)[0].board
        self.assertIsNone(saved.winner);self.assertEqual(lost.winner,'wolf')

    def test_invalid_actions_and_uncertain_world_rejected(self):
        b=self.board()
        for intent,attack in ((GuardIntent(1,1,1),2),(GuardIntent(2,1,2),2),
                              (GuardIntent(1,2,4),2),(GuardIntent(1,1,2),3)):
            with self.subTest(intent=intent,attack=attack),self.assertRaises(ValueError):
                resolve_fixed_guard_night(b,intent,attack)
        with self.assertRaises(ValueError):
            resolve_fixed_guard_night(replace(initial_board(5,1,0,0,1),phase='night'),GuardIntent(1,1,2),2)
