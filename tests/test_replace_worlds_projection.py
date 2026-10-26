"""Independent legacy formula/full-state parity for complete-law replacement."""
import unittest
from dataclasses import replace,fields
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.exact import Board,PublicEvent,initial_board,replace_worlds


def legacy(board,worlds,**changes):
    projection={}
    for w,m,seer,hunter,q in worlds:
        projection[w,m]=projection.get((w,m),F(0))+q
    return replace(board,belief=(),role_belief=tuple((w,m,q) for (w,m),q in sorted(projection.items())),world_belief=tuple(worlds) if board.initial_seer_count or board.initial_hunter_count else (),**changes)


class CompleteLawProjectionTests(unittest.TestCase):
    def assert_state_equal(self,a,b):
        self.assertEqual(tuple(getattr(a,f.name) for f in fields(Board)),tuple(getattr(b,f.name) for f in fields(Board)))
        self.assertEqual(a.wolf_count_distribution,b.wolf_count_distribution)
        self.assertEqual(a.winner,b.winner)
        self.assertEqual(hash(a),hash(b))

    def test_full_laws_counts_and_unequal_masses_match_independent_formula(self):
        for n,w,m,s,h in [(4,1,0,1,0),(5,1,1,1,0),(5,1,0,1,1),(6,2,1,1,1),(5,2,0,0,1)]:
            root=initial_board(n,w,m,s,h)
            for subset in (root.worlds,root.worlds[:2]):
                total=sum(range(1,len(subset)+1))
                law=tuple((*row[:-1],F(i,total)) for i,row in enumerate(subset,1))
                for changes in ({'wolf_count':None},{'wolf_count':None,'day':2,'phase':'night'},
                                {'wolf_count':None,'alive':root.alive[:-1],'history':(PublicEvent(1,'day',n),),'phase':'night'}):
                    self.assert_state_equal(replace_worlds(root,law,**changes),legacy(root,law,**changes))

    def test_complete_path_passes_empty_discarded_projection_but_still_validates(self):
        root=initial_board(5,1,1,1)
        with patch('werewolf.exact.replace',wraps=replace) as construction:
            child=replace_worlds(root,root.worlds,wolf_count=None)
        self.assertEqual(construction.call_args.kwargs['role_belief'],())
        self.assert_state_equal(child,root)
        invalid=tuple((*r[:-1],r[-1]*2) for r in root.worlds)
        for law in (invalid,(root.worlds[0],root.worlds[0]),((1,1,4,0,F(1)),),((1,0,0,0,F(1)),)):
            with self.subTest(law=law[:2]):
                with self.assertRaises(ValueError):replace_worlds(root,law,wolf_count=None)
                with self.assertRaises(ValueError):legacy(root,law,wolf_count=None)

    def test_public_facts_and_live_count_constraints_remain_validated(self):
        root=initial_board(5,1,0,1)
        for changes in ({'alive':(1,2,3,4)}, {'claims':('seer',)}, {'wolf_count':0}, {'initial_seer_count':2}):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):replace_worlds(root,root.worlds,**changes)
                with self.assertRaises(ValueError):legacy(root,root.worlds,**changes)

    def test_ordinary_and_mutable_compatibility_stay_on_old_path(self):
        for root in (initial_board(5,1,1),initial_board(5,1,0,1)):
            for law in (root.worlds,list(root.worlds)):
                self.assert_state_equal(replace_worlds(root,law),legacy(root,law))

    def test_equal_visible_facts_do_not_merge_distinct_posteriors(self):
        root=initial_board(5,1,0,1)
        a=replace_worlds(root,(root.worlds[0][:-1]+(F(1),),),wolf_count=None)
        b=replace_worlds(root,(root.worlds[-1][:-1]+(F(1),),),wolf_count=None)
        self.assertEqual(a.alive,b.alive)
        self.assertNotEqual(a,b)
        self.assertNotEqual(a.worlds,b.worlds)
        self.assertNotEqual(a.wolf_probability(1),b.wolf_probability(1))
