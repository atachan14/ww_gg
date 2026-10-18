import unittest
from dataclasses import replace
from unittest.mock import patch
from benchmarks.player_match_groups.cut_out_first_cycle_coverage import base
from benchmarks.player_match_groups.cut_out_user_seven_source import ROOT_GROUPS
from benchmarks.player_match_groups.cut_out_joint_night_forecast_fixture import moved_source
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import make_scope,audit
from benchmarks.player_match_groups.cut_out_publication_orbit_value import with_audited_groups,check_scope
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.evaluation_branch import ActionInputs
from werewolf.board_future import calculation_origin,remember,GeneratedBoard,same_role_board
from werewolf.action_flow import resolve_action
from werewolf.seer_future_uniform import TrueScanState
from werewolf.calculation_budget import calculation_budget


class InheritedGroupConsumptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry,witness=base();root=cls.registry.origin()
        e=cls.engine(False)
        with calculation_origin(cls.registry.data):
            remember(e,cls.registry.root,root)
            payload=ActionInputs(root.public_state,root.past,root.private,None,root.physical)
            acquired,outcomes=resolve_action(root.public,payload,3,e.action_policy,terminal_payoffs=False)
            cls.source=e.action_policy.project(root.public,acquired,outcomes[0],3)

    @classmethod
    def engine(cls,enabled=True):
        b=cls.registry.engine.baseline
        return InformationSetForecast(b.rules,b.strategy,exact_renaming=False,
            retire_uninformative_scans=False,track_acquisition_provenance=enabled)

    def audited_frame(self):
        source=self.source
        # Complete root audit in the trusted test adapter, before registration.
        for group in ROOT_GROUPS:
            for player in group[1:]:
                mapping=list(range(1,8));mapping[group[0]-1],mapping[player-1]=player,group[0]
                moved=moved_source(source,tuple(mapping))
                self.assertTrue(same_role_board(moved.public,source.public))
                self.assertTrue(same_role_board(moved.physical,source.physical))
                self.assertEqual((moved.public_state,moved.private,moved.past),(source.public_state,source.private,source.past))
        e=self.engine();before=ActionInputs(source.public_state,source.past,source.private,None,source.physical)
        root=e.acquisition_provenance._register_audited_root(source.public,before,ROOT_GROUPS,(self.registry,self.registry.data))
        before=replace(before,provenance=root)
        after=e.action_policy.acquire(source.public,before)
        return e,before,after

    def test_acquisition_consumes_parent_groups_without_parent_walk_or_full_checks(self):
        e,before,after=self.audited_frame();ledger=e.acquisition_provenance
        with patch.object(TrueScanState,'__eq__',side_effect=AssertionError('full equality')),patch.object(TrueScanState,'__hash__',side_effect=AssertionError('full hashing')),patch.object(GeneratedBoard,'roles',side_effect=AssertionError('parent replay')),patch.object(ledger,'_roots',None):
            for i in range(100):
                self.assertTrue(ledger.validates(after.provenance,self.source.public,before,after))
                self.assertEqual(ledger.groups_for(after.provenance,self.source.public,after),ROOT_GROUPS)
        self.assertEqual(ledger.stats['inherited_groups'],1)

    def test_owner_revision_copy_and_changed_private_identity_are_rejected(self):
        e,before,after=self.audited_frame();ledger=e.acquisition_provenance;r=after.provenance
        self.assertIsNone(ledger.groups_for(replace(r),self.source.public,replace(after,provenance=replace(r))))
        self.assertIsNone(ledger.groups_for(r,self.source.public,replace(after,private=replace(after.private))))
        data=self.registry.data;self.registry.data=data.updated(revision=data.to_game().get('revision',0)+1)
        try:
            self.assertIsNone(ledger.groups_for(r,self.source.public,after))
            self.assertFalse(ledger.validates(r,self.source.public,before,after))
            self.assertIsNone(ledger.public_groups_for(r,self.source.public,after.public_state,after.past))
        finally:self.registry.data=data

    def test_existing_publication_entry_skips_checks_and_preserves_all_named_details(self):
        with calculation_budget(4000000,max_seconds=25):result=audit('five',inherited_groups=True)
        self.assertEqual(result['status'],'verified')
        self.assertEqual(result['full_label_Forecast_QP_Table_checks'],9)
        self.assertEqual(result['independent_saved_origin_cold_reads'],9)
        counts=result['inherited_group_counts']
        self.assertEqual(counts['private_permutation_checks_avoided'],3)
        self.assertEqual(counts['public_permutation_checks_avoided'],3)
        self.assertGreaterEqual(counts['scope_parent_replays_avoided'],3)
        self.assertGreater(counts['public_semantic_hypothesis_visits'],0)

    def test_unsupported_observer_keeps_ordinary_scope(self):
        scope,cold=make_scope('observer')
        self.assertIs(with_audited_groups(scope),scope)
        self.assertIsNone(scope.group_ledger)

    def test_fake_producer_proof_cannot_skip_normal_checks(self):
        from benchmarks.player_match_groups import cut_out_structural_publications as producer
        scope,cold=make_scope('five');source=scope.source
        class Fake:
            def public_groups_for(self,*args):raise AssertionError('untrusted callback')
        with patch.object(producer,'move_law',wraps=producer.move_law) as compared:
            producer.produce(source.public,source.public_state,source.past,scope.groups,_group_proof=(Fake(),None))
        self.assertGreater(compared.call_count,0)

    def test_fast_scope_remains_identity_bound_and_revision_guarded(self):
        scope,cold=make_scope('five');cap=with_audited_groups(scope)
        with patch.object(TrueScanState,'__eq__',side_effect=AssertionError('full equality')),patch.object(TrueScanState,'__hash__',side_effect=AssertionError('full hashing')),patch.object(GeneratedBoard,'roles',side_effect=AssertionError('parent replay')):
            for i in range(100):check_scope(cap)
        with self.assertRaises(Pending):check_scope(replace(cap))
        data=cap.graph.data;cap.graph.data=data.updated(revision=data.to_game().get('revision',0)+1)
        try:
            with self.assertRaises(Pending):check_scope(cap)
        finally:cap.graph.data=data
