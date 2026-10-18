import unittest
from dataclasses import replace
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_structural_publications_fixture import build
from benchmarks.player_match_groups.cut_out_structural_publications import produce,restore,Pending
from werewolf.morning_publications import public_report_branches,future_publications
from werewolf.seer_acquisition import normalize
from werewolf.exact import replace_worlds
from werewolf.actor_information import condition_actor_state
from werewolf.calculation_budget import calculation_budget


class SeparatePublicationTests(unittest.TestCase):
    def test_ordered_reporter_product_uses_only_target_symmetry_with_unequal_Q(self):
        with calculation_budget(4000000,max_seconds=30):
            cap=build(3,4);source=cap.source;e=cap.engine
            groups=((1,),(2,),(3,),(4,),(5,6,7))
            state=replace(source.public_state,hypotheses=normalize(tuple(
                replace(h,mass=h.mass*(2 if h.roles[2]==1 else 1)) for h in source.public_state.hypotheses)))
            board=replace_worlds(source.public,state.public_roles)
            patterns=produce(board,state,source.past,groups)
            rows=public_report_branches(board,source.past,restore(patterns,7))
            reference=public_report_branches(board,source.past,future_publications(state,source.past,board.alive,board.claims))
            key=lambda rows:{(b,p):(q,s) for q,b,s,p in rows}
            self.assertEqual(key(rows),key(reference))
            self.assertEqual(len(rows),64)
            self.assertLess(len(patterns),len(rows))
            self.assertTrue(all(p.reporter_factor==1 for p in patterns))
            self.assertTrue(any(p.multiplicity>1 for p in patterns))
            self.assertEqual(sum((h.mass for h in state.hypotheses if h.roles[2]==1),F()),F(2,3))
            private=condition_actor_state(state,lambda h:h.roles[0]==17 and h.acquisitions==next(h.acquisitions for h in state.hypotheses if h.roles[0]==17))
            own=lambda rows:{(b,p):(q,s,ps) for q,b,s,p,ps in rows}
            self.assertEqual(own(e.push(state,private,rows)),own(e.push(state,private,reference)))

    def test_false_target_symmetry_and_fake_configuration_still_refused(self):
        with calculation_budget(4000000,max_seconds=30):
            source=build(3,4).source
            with self.assertRaises(Pending):produce(source.public,source.public_state,source.past,((1,),(2,),(3,5),(4,),(6,7)))
            with self.assertRaises(Pending):produce(source.public,source.public_state,source.past,tuple((p,) for p in range(1,8)),fake_policy=('max',))

    def test_exact_saved_day3_stop_and_independent_initial_cold(self):
        from benchmarks.player_match_groups.cut_out_separate_publications_fixture import audit
        result=audit()
        self.assertEqual(result['status'],'verified')
        self.assertEqual((result['patterns'],result['named_vectors']),(16,16))
        self.assertEqual(result['independent_initial_origin_cold_reads'],49)
        self.assertEqual(result['variants']['scan']['zero_P'],12)
