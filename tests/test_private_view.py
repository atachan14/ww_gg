from fractions import Fraction as F
import unittest
from werewolf.exact import initial_board,Rules,Strategy,action_outcomes
from werewolf.private_view import condition_private

class PrivateViewTests(unittest.TestCase):
    def test_true_secret_filters_without_publication(self):
        public=initial_board(5,1,0,1,0)
        view=condition_private(public,'seer',(1,),({'day':1,'target':2,'color':'white'},),rules=Rules())
        self.assertEqual(view.board.role_probability(1,'seer'),1)
        self.assertEqual(view.board.wolf_probability(2),0)
        self.assertEqual(public.wolf_probability(2),F(1,5))
        self.assertEqual(view.board.claims,public.claims)
        self.assertEqual(view.board.reports,public.reports)
        self.assertEqual(len(view.acquisitions),1)

    def test_partial_input_is_unknown_not_white(self):
        public=initial_board(5,1,0,1,0)
        base=condition_private(public,'seer',(1,),rules=Rules())
        partial=condition_private(public,'seer',(1,),({'day':1,'target':2,'color':None},),rules=Rules())
        self.assertEqual(base.board,partial.board)
        self.assertEqual(partial.acquisitions,())

    def test_secret_black_rule_and_conflicts(self):
        board=initial_board(5,1,0,1,0)
        black=({'day':1,'target':2,'color':'black'},)
        with self.assertRaises(ValueError):condition_private(board,'seer',(1,),black,rules=Rules())
        true=condition_private(board,'seer',(1,),black,rules=Rules(initial_seer='normal'))
        self.assertEqual(true.board.wolf_probability(2),1)
        with self.assertRaises(ValueError):condition_private(board,'seer',(1,),({'day':1,'target':1,'color':'white'},),rules=Rules())

    def test_dead_wolf_roster_and_impossible_combo(self):
        initial=initial_board(7,2)
        night=next(o.board for o in action_outcomes(initial,1,Rules(),Strategy()) if o.board.winner is None)
        private=condition_private(night,'wolf',(1,2),rules=Rules())
        self.assertNotIn(1,private.board.alive)
        self.assertEqual(private.board.wolf_probability(1),1)
        self.assertEqual(private.board.wolf_probability(2),1)
        with self.assertRaises(ValueError):condition_private(night,'wolf',(2,),rules=Rules())
        with self.assertRaises(ValueError):condition_private(private.board,'wolf',(3,4),rules=Rules())

    def test_future_and_dead_scan_rejected(self):
        board=initial_board(7,1,0,1,0)
        night=next(o.board for o in action_outcomes(board,2,Rules(),Strategy()) if o.board.winner is None)
        morning=next(o.board for o in action_outcomes(night,3,Rules(),Strategy()) if o.board.winner is None)
        with self.assertRaises(ValueError):condition_private(morning,'seer',(1,),({'day':2,'target':2,'color':'white'},),rules=Rules())
        # A target dying that same night was still available when scanned.
        view=condition_private(morning,'seer',(1,),({'day':2,'target':3,'color':'white'},),rules=Rules())
        self.assertEqual(view.acquisitions[0].target,3)
        with self.assertRaises(ValueError):condition_private(morning,'seer',(1,),({'day':3,'target':4,'color':'white'},),rules=Rules())
