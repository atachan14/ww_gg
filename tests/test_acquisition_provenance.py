import unittest
from dataclasses import replace
from unittest.mock import patch
from benchmarks.player_match_groups.cut_out_first_cycle_coverage import base
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.evaluation_branch import ActionInputs,ContinuationInputs,physical_board
from werewolf.board_future import calculation_origin,remember,GeneratedBoard,kernel_snapshot
from werewolf.action_flow import resolve_action
from werewolf.actor_information import condition_actor_state
from werewolf.seer_future_uniform import TrueScanState,FuturePending,acquire_uniform


class AcquisitionProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry,cls.witness=base();root=cls.registry.origin()
        e=cls.engine(False)
        with calculation_origin(cls.registry.data):
            remember(e,cls.registry.root,root)
            payload=ActionInputs(root.public_state,root.past,root.private,None,root.physical)
            acquired,outcomes=resolve_action(root.public,payload,3,e.action_policy,terminal_payoffs=False)
            cls.source=e.action_policy.project(root.public,acquired,outcomes[0],3)

    @classmethod
    def engine(cls,enabled=True,**kwargs):
        b=cls.registry.engine.baseline
        return InformationSetForecast(b.rules,b.strategy,exact_renaming=False,retire_uninformative_scans=False,
            track_acquisition_provenance=enabled,**kwargs)

    def payload(self,*,parent=None,private=None,observer=None):
        s=self.source;private=s.private if private is None else private
        return ActionInputs(s.public_state,s.past,private,observer,physical_board(s.public,private,s.physical),provenance=parent)

    def test_default_off_optional_carrier_preserves_keys_and_tuple_contract(self):
        before=self.payload(parent=object());old=self.engine(False);tracked=self.engine()
        baseline=old.action_policy.acquire(self.source.public,before)
        after=tracked.action_policy.acquire(self.source.public,before)
        self.assertEqual(baseline,after);self.assertEqual(hash(baseline),hash(after))
        self.assertEqual(tuple(baseline),tuple(after));self.assertEqual(len(after),5)
        self.assertIsNone(baseline.provenance)
        self.assertTrue(tracked.acquisition_provenance.validates(after.provenance,self.source.public,before,after))
        self.assertIs(after.provenance.parent,before.provenance)
        self.assertEqual(replace(self.source,provenance=object()),self.source)
        self.assertEqual(len(self.source),5)

    def test_identity_validation_never_compares_hashes_laws_or_replays_parent(self):
        e=self.engine();before=self.payload();after=e.action_policy.acquire(self.source.public,before)
        with patch.object(TrueScanState,'__eq__',side_effect=AssertionError('law equality')),patch.object(TrueScanState,'__hash__',side_effect=AssertionError('law hashing')),patch.object(GeneratedBoard,'roles',side_effect=AssertionError('parent replay')):
            for i in range(100):self.assertTrue(e.acquisition_provenance.validates(after.provenance,self.source.public,before,after))

    def test_distinct_private_measure_is_generated_separately(self):
        own=condition_actor_state(self.source.private,lambda h:bool(h.roles[2]&1))
        before=self.payload(private=own);e=self.engine();after=e.action_policy.acquire(self.source.public,before)
        self.assertTrue(e.acquisition_provenance.validates(after.provenance,self.source.public,before,after))
        self.assertNotEqual(after.public_state.public_roles,after.private.public_roles)
        self.assertEqual(after.public_state.public_roles,before.public_state.public_roles)
        self.assertEqual(after.private.public_roles,before.private.public_roles)
        self.assertEqual(e.acquisition_provenance.stats['generation_records'],2)

    def test_substituted_or_copied_receipt_and_parent_are_rejected(self):
        e=self.engine();before=self.payload(parent=object());after=e.action_policy.acquire(self.source.public,before);r=after.provenance
        self.assertFalse(e.acquisition_provenance.validates(replace(r),self.source.public,before,replace(after,provenance=replace(r))))
        self.assertFalse(e.acquisition_provenance.validates(r,self.source.public,before,replace(after,private=replace(after.private))))
        self.assertFalse(e.acquisition_provenance.validates(r,self.source.public,replace(before,provenance=object()),after))
        self.assertFalse(self.engine().acquisition_provenance.validates(r,self.source.public,before,after))

    def test_observer_and_custom_generation_keep_ordinary_result_without_receipt(self):
        before=self.payload(observer=lambda h,state:True);e=self.engine()
        after=e.action_policy.acquire(self.source.public,before)
        self.assertIsNone(after.provenance)
        self.assertEqual(after,self.engine(False).action_policy.acquire(self.source.public,before))
        plain=self.payload();e=self.engine()
        e.acquire=lambda board,state:acquire_uniform(state,board.alive,position=e.strategy.seer_position)
        after=e.action_policy.acquire(self.source.public,plain)
        self.assertIsNone(after.provenance)
        self.assertEqual(e.acquisition_provenance.stats['unknown_generation_declines'],1)

    def test_unknown_and_equivalent_but_different_cache_inputs_are_unproved(self):
        before=self.payload();e=self.engine();old=self.engine(False)
        cached=old.acquire(self.source.public,before.public_state)
        e.acquired[self.source.public,before.public_state]=cached
        after=e.action_policy.acquire(self.source.public,before);self.assertIsNone(after.provenance)
        e=self.engine();first=e.action_policy.acquire(self.source.public,before)
        copied=replace(before,public_state=replace(before.public_state),private=replace(before.private))
        second=e.action_policy.acquire(self.source.public,copied)
        self.assertEqual(first,second);self.assertIsNone(second.provenance)
        self.assertTrue(e.acquisition_provenance.validates(first.provenance,self.source.public,before,first))

    def test_configuration_replacement_and_max_have_no_receipt(self):
        before=self.payload();e=self.engine();after=e.action_policy.acquire(self.source.public,before)
        e.strategy=replace(e.strategy)
        self.assertFalse(e.acquisition_provenance.validates(after.provenance,self.source.public,before,after))
        self.assertIsNone(e.action_policy.acquire(self.source.public,before).provenance)
        e=self.engine();e.strategy=replace(e.strategy,day='max',night='max',fake_reports='max')
        # Acquire the unchanged position kernel only; never evaluate a MAX score.
        self.assertIsNone(e.action_policy.acquire(self.source.public,before).provenance)

    def test_snapshot_and_uncertified_death_drop_provenance(self):
        before=self.payload();e=self.engine();after=e.action_policy.acquire(self.source.public,before)
        snapshot=kernel_snapshot(e);self.assertIsNone(snapshot.acquisition_provenance)
        self.assertIsNone(snapshot.action_policy.acquire(self.source.public,before).provenance)
        outcomes=e.action_policy.outcomes(self.source.public,after,4)
        child=e.action_policy._project_roles(self.source.public,after,outcomes[0],4)
        self.assertIsNone(child.provenance)

    def test_generation_failure_does_not_mint_or_change_error(self):
        before=self.payload();e=self.engine()
        with patch('werewolf.information_set_forecast.acquire_uniform',return_value=FuturePending('generation-budget')):
            with self.assertRaises(Pending) as error:e.action_policy.acquire(self.source.public,before)
        self.assertEqual(error.exception.reason,'generation-budget')
        self.assertEqual(e.acquisition_provenance.stats['generation_records'],0)
