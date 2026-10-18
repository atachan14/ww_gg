import unittest
from dataclasses import replace
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_publication_orbit_value import *
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import make_scope,audit,forecast,tables
from benchmarks.player_match_groups.cut_out_joint_night_prototype import move_law,move_board
from werewolf.board_future import calculation_origin,PublicationEvidence,publication_key,kernel_snapshot,reconstruct_publication,same_role_board,condition_recipe
from werewolf.evaluation_branch import physical_board
from werewolf.calculation_budget import calculation_budget
from werewolf.information_set_forecast import Pending


class PublicationOrbitValueTests(unittest.TestCase):
    def test_small_complete_recursive_value_and_all_named_tables_cold(self):
        with calculation_budget(4000000,max_seconds=30):r=audit('five')
        self.assertEqual(r['status'],'verified')
        self.assertEqual((r['value_only']['named_positive_P_solve_roots'],r['value_only']['representative_positive_P_solve_roots']),(9,6))
        self.assertEqual(r['value_only_named_restorations'],0)
        self.assertEqual(r['independent_saved_origin_cold_reads'],9)

    def test_same_role_marginal_and_physical_board_do_not_hide_asymmetric_secret(self):
        with calculation_budget(4000000,max_seconds=30):
            scope,cold=make_scope('asymmetric-scan');s=scope.source
            mapping=(1,2,3,4,5,7,6)
            self.assertEqual(move_law(s.public_state,mapping),s.public_state)
            self.assertEqual(move_law(s.private,mapping).public_roles,s.private.public_roles)
            self.assertTrue(same_role_board(move_board(s.physical,s.private,mapping),s.physical))
            self.assertNotEqual(move_law(s.private,mapping),s.private)
            with calculation_origin(scope.graph.data):plan=PublicationOrbitValue(scope)
            self.assertIn((6,7),plan.private_splits)
            self.assertEqual(plan.groups,tuple((p,) for p in range(1,8)))
            self.assertEqual(plan.representative_Boards,64)

    def test_Q_positive_P_zero_is_public_detail_only_without_invented_private_law(self):
        with calculation_budget(4000000,max_seconds=30):
            scope,cold=make_scope('asymmetric-scan')
            with calculation_origin(scope.graph.data):plan=PublicationOrbitValue(scope)
            positive={id(r.pattern) for r in plan.representatives}
            pattern=next(p for p in plan.patterns if id(p) not in positive)
            mapping=next(mappings(pattern,7))
            q,public,request=plan.public_labelled(pattern,mapping)
            self.assertGreater(q,0);self.assertEqual(public.private,public.public_state)
            self.assertEqual(cold(request),public)
            private=scope.request.child(PublicationEvidence(kernel_snapshot(plan.engine),publication_key(public.public,public.past)),None)
            with self.assertRaises(ValueError):private.roles()

    def test_observer_fixed_endpoints_and_unknown_observer_declined(self):
        with calculation_budget(4000000,max_seconds=30):
            scope,cold=make_scope('observer')
            with calculation_origin(scope.graph.data):plan=PublicationOrbitValue(scope)
            for row in plan.representatives:
                for mapping in mappings(row.pattern,7):self.assertEqual((mapping[1],mapping[5]),(2,6))
            with self.assertRaises(Pending):plan.labelled(plan.representatives[0],(2,1,3,4,5,6,7))
            scope,cold=make_scope('five');source=replace(scope.source,observer=lambda h,state:True)
            recipe=condition_recipe(scope.source,source);self.assertIsNotNone(recipe)
            request=scope.request.child(recipe,None)
            other=issue_scope(scope.graph,scope.builder,request,source)
            with self.assertRaises(Pending) as err:private_stabilizer(other)
            self.assertIn('observer_transport',err.exception.reason)

    def test_owner_revision_configuration_and_cloned_receipt_rejected(self):
        scope,cold=make_scope('five')
        with calculation_origin(scope.graph.data):plan=PublicationOrbitValue(scope)
        with self.assertRaises(Pending):check_scope(replace(scope))
        data=scope.graph.data;scope.graph.data=data.updated(revision=data.to_game().get('revision',0)+1)
        try:
            with self.assertRaises(Pending):plan.value()
        finally:scope.graph.data=data
        strategy=scope.builder.strategy;scope.builder.strategy=replace(strategy,night='max')
        try:
            with self.assertRaises(Pending):plan.value()
        finally:scope.builder.strategy=strategy

    def test_nontrivial_public_label_action_forecast_transport_on_two_requested_branches(self):
        # The full64-label aggregate baseline exceeded30s in its separate
        # worker. This is a distinct two-label inspection test, not its retry.
        with calculation_budget(4000000,max_seconds=30):
            scope,cold=make_scope('public');src=scope.source
            with calculation_origin(scope.graph.data):
                plan=PublicationOrbitValue(scope)
                row=next(r for r in plan.representatives if r.pattern.reporter_factor==2 and r.source.public.wolf_probability(1)!=r.source.public.wolf_probability(2))
                old=OrbitOracle(scope);remember(old,scope.request,src)
                branches=old.morning(src.public,src.public_state,src.past)
                own=old.push(src.public_state,src.private,branches)
                lookup={publication_key(b,p):(m,b,s,p,private) for m,b,s,p,private in own}
                selected=[]
                options=list(mappings(row.pattern,7));identity=options[0]
                flip=next(m for m in options if m[0]==2 and m[1]==1 and m[2:]==identity[2:])
                for mapping in (identity,flip):
                    q,p,child,result,request=plan.labelled(row,mapping)
                    mass,b,s,past,private=lookup[publication_key(child.public,child.past)]
                    expected=reconstruct_publication(old,src,b,s,past,private,physical_board(b,private,src.physical),replay_unique=True)
                    self.assertEqual(p,mass);self.assertEqual(result,forecast(old,expected))
                    self.assertEqual(tables(child,result),tables(expected,result));self.assertEqual(cold(request),child)
                    selected.append(result)
                self.assertEqual(len(selected),2)
                self.assertNotEqual(dict(selected[0].action_values)[1],dict(selected[1].action_values)[1])
                self.assertEqual(selected[0].village_win,selected[1].village_win)
