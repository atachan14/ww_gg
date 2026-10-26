import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.exact import Board, PublicEvent, initial_board, winner_for

class BoardTerminalCacheTests(unittest.TestCase):
    def expected(self, board):
        outcomes={winner_for(len(board.alive), (mask & board.alive_mask).bit_count()) for mask,q in board.belief if q}
        return next(iter(outcomes)) if len(outcomes)==1 else None

    def test_exact_terminal_and_mixed_support(self):
        for alive,law in [((1,2,3),((1,F(1)),)), ((1,2),((1,F(1)),)), ((2,3),((1,F(1)),)), ((2,3),((1,F(1,3)),(2,F(2,3))))]:
            history=tuple(PublicEvent(1,'day',p) for p in range(1,4) if p not in alive)
            board=Board(3,alive,None,history=history,belief=law)
            self.assertEqual(board.winner,self.expected(board))
            with patch.object(Board,'wolf_count_distribution',property(lambda _: self.fail('cached winner rebuilt distribution'))):
                for _ in range(10):self.assertEqual(board.winner,self.expected(board))

    def test_children_and_different_beliefs_do_not_share(self):
        root=initial_board(3)
        dead=replace(root,alive=(2,3),history=(PublicEvent(1,'day',1),),wolf_count=None)
        village=replace(dead,belief=((1,F(1)),),role_belief=(),wolf_count=None)
        wolf=replace(dead,belief=((2,F(1)),),role_belief=(),wolf_count=None)
        self.assertIsNone(root.winner)
        self.assertEqual(village.winner,'village')
        self.assertEqual(wolf.winner,'wolf')
        self.assertIsNone(dead.winner)
        self.assertEqual(hash(village),hash(replace(village)))

    def test_mutable_compatibility_law_is_not_cached(self):
        law=[[1,F(1)]]
        board=Board(3,(2,3),None,history=(PublicEvent(1,'day',1),),belief=law)
        self.assertFalse(hasattr(board,'_wolf_counts_cache'))
        self.assertEqual(board.winner,'village')
        law[0][0]=2
        self.assertEqual(board.winner,'wolf')

    def test_legacy_derived_cache_is_still_readable(self):
        board=initial_board(3)
        object.__setattr__(board,'_wolf_counts_cache',board._wolf_counts_cache[:3])
        self.assertIsNone(board.winner)
