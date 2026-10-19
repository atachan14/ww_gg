import unittest
from dataclasses import replace
from unittest.mock import patch
import test_owner_information_provenance as owner_tests
from werewolf.evaluation_branch import ActionInputs
from werewolf.action_flow import resolve_action
from werewolf.board_future import calculation_origin


class ProvenanceBoundaryCostsTests(unittest.TestCase):
    def test_death_checks_owner_once_but_external_consumers_recheck(self):
        graph,e,source=owner_tests.OwnerInformationProvenanceTests().root()
        ledger=e.acquisition_provenance
        payload=ActionInputs(source.public_state,source.past,source.private,None,source.physical,provenance=source.provenance)
        with calculation_origin(graph.data):
            acquired,outcomes=resolve_action(source.public,payload,2,e.action_policy,terminal_payoffs=False)
            outcome=next(o for o in outcomes if o.board.winner is None)
            with patch.object(ledger,'_owner_current',wraps=ledger._owner_current) as checked:
                child=e.action_policy.project(source.public,acquired,outcome,2)
                self.assertEqual(checked.call_count,1)
                self.assertIsNotNone(ledger.groups_for(child.provenance,child.public,child))
                self.assertEqual(checked.call_count,2)
                self.assertIsNotNone(ledger.groups_for(child.provenance,child.public,child))
                self.assertEqual(checked.call_count,3)
            data=graph.data;graph.data=data.updated(revision=424242)
            try:self.assertIsNone(ledger.groups_for(child.provenance,child.public,child))
            finally:graph.data=data
            self.assertIsNone(ledger.groups_for(child.provenance,child.public,replace(child,private=replace(child.private))))

    def test_one_shot_generation_stamps_release_after_consumption(self):
        from werewolf.actor_information import PersonalInformation
        graph,e,source=owner_tests.OwnerInformationProvenanceTests().root()
        with calculation_origin(graph.data):
            mass,child=e.personal_view(source,PersonalInformation(1,'seer'))
            self.assertIsNotNone(child.provenance)
            self.assertEqual(e.acquisition_provenance._information_outputs,{})
            from werewolf.information_set_forecast import Pending
            with self.assertRaises(Pending):e.morning(source.public,source.public_state,source.past)
            self.assertEqual(e.acquisition_provenance._morning_components,{})


    def test_weak_indices_release_dead_entries_and_keep_replacement(self):
        import gc
        from weakref import ref
        graph,e,source=owner_tests.OwnerInformationProvenanceTests().root()
        ledger=e.acquisition_provenance
        token=source.provenance;old=ref(token)
        groups=ledger.groups_for(token,source.public,source)
        replacement=ledger._register_audited_root(source.public,source,groups,(graph,graph.data),request=source.board_data)
        key=next(k for k,v in ledger._frames.items() if v() is replacement)
        source=replace(source,provenance=replacement);token=None;gc.collect()
        self.assertIsNone(old())
        self.assertIs(ledger._frames[key](),replacement)
        payload=ActionInputs(source.public_state,source.past,source.private,None,source.physical,provenance=replacement)
        outcomes=e.action_policy.outcomes(source.public,payload,2)
        outcome=outcomes[0];outcome_key=id(outcome);weak=ref(outcome)
        self.assertIn(outcome_key,ledger._deaths)
        outcomes=None;outcome=None;gc.collect()
        self.assertIsNone(weak())
        self.assertNotIn(outcome_key,ledger._deaths)
