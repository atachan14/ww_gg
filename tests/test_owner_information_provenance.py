import unittest
from dataclasses import replace
from unittest.mock import patch
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import owner_information_audit,make_role_filter_scope
from benchmarks.player_match_groups.cut_out_publication_orbit_value import seed_structural
from werewolf.actor_information import PersonalInformation,WolfInformation,condition_personal
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.action_flow import resolve_action
from werewolf.evaluation_branch import ActionInputs
from werewolf.board_future import calculation_origin,remember,GeneratedBoard
from werewolf.calculation_budget import calculation_budget
from werewolf.joint_value_sharing import independent_joint_values


class OwnerInformationProvenanceTests(unittest.TestCase):
    def root(self):
        scope=make_role_filter_scope();seed=seed_structural(scope);graph=scope.graph
        e=InformationSetForecast(graph.engine.baseline.rules,graph.engine.baseline.strategy,exact_renaming=False,
            retire_uninformative_scans=False,track_acquisition_provenance=True)
        e.retain_joint_guard_history=True
        token=e.acquisition_provenance._register_audited_root(seed.source.public,seed.source,seed.groups,(graph,graph.data),request=scope.request)
        source=replace(seed.source,provenance=token,board_data=scope.request)
        remember(e,scope.request,source)
        return graph,e,source

    def test_named_owner_wolf_results_and_cold_match(self):
        with calculation_budget(4000000,max_seconds=30),independent_joint_values():row=owner_information_audit()
        self.assertEqual(row['status'],'verified')
        self.assertEqual(row['counts']['cold_reads'],41)
        self.assertEqual(row['counts']['independent_Forecast_Table_checks'],8)
        self.assertEqual(row['counts']['independent_wolf_choice_mass_checks'],21)
        self.assertEqual(row['counts']['distinct_QP_information_weights'],15)
        self.assertEqual(row['proof_counts']['information_parent_replays_avoided'],11)
        self.assertEqual(row['proof_counts']['observed_acquisition_records'],17)
        self.assertEqual(row['proof_counts']['private_permutation_checks_avoided'],21)
        self.assertEqual(row['proof_counts']['uniform_wolf_solve_uses'],1)
        self.assertGreater(row['proof_counts']['report_ordinary_fallbacks'],0)
        self.assertFalse(row['full_initial7_search'])
        self.assertFalse(row['MAX_evaluated'])

    def test_only_owner_records_and_positive_support(self):
        graph,e,source=self.root()
        scan=next(a for h in source.private.hypotheses for a in h.acquisitions)
        with self.assertRaises(ValueError):PersonalInformation(scan.player,'seer',(replace(scan,player=2 if scan.player!=2 else 3),))
        with self.assertRaises(ValueError):PersonalInformation(scan.player,'medium',(scan,))
        with self.assertRaises(ValueError):condition_personal(source.private,PersonalInformation(1,'villager'))
        with self.assertRaises(ValueError):condition_personal(source.private,lambda h,s:True)
        with self.assertRaises(ValueError):e.wolf_choices(source)

    def test_unproved_callback_and_unknown_policy_cache_fall_back(self):
        graph,e,source=self.root()
        with calculation_origin(graph.data):
            payload=ActionInputs(source.public_state,source.past,source.private,None,source.physical,provenance=source.provenance)
            acquired,outcomes=resolve_action(source.public,payload,2,e.action_policy,terminal_payoffs=False)
            o=next(o for o in outcomes if o.board.winner is None)
            night=e.action_policy.project(source.public,acquired,o,2)
            bad=replace(night,observer=lambda h,s:True)
            plain=ActionInputs(bad.public_state,bad.past,bad.private,bad.observer,bad.physical,provenance=bad.provenance)
            self.assertIsNone(e.action_policy.acquire(bad.public,plain).provenance)
            # Publicly computed policy is identical under private restrictions;
            # externally replacing its cache row loses the generation stamp.
            rows=e.wolf_choices(night)
            mass,child,target,proof=rows[0]
            self.assertTrue(e.acquisition_provenance.validates_choice(proof,child))
            self.assertFalse(e.acquisition_provenance.validates_choice(replace(proof),child))
            self.assertFalse(e.acquisition_provenance.validates_choice(proof,replace(child,private=replace(child.private))))
            key=next(iter(e.policies));e.policies[key]=tuple(list(e.policies[key]))
            unknown=[p for m,c,t,p in e.wolf_choices(night) if c.private==child.private]
            self.assertTrue(unknown);self.assertTrue(all(p is None for p in unknown))


    def test_explicit_wolf_owner_view_keeps_Q_and_complete_private_histories(self):
        from benchmarks.player_match_groups.cut_out_compact_terminal_fixture import independent_cold
        from werewolf.actor_information import condition_actor_state
        graph,e,source=self.root()
        info=WolfInformation.from_hypothesis(source.private.hypotheses[0])
        with calculation_origin(graph.data),patch.object(GeneratedBoard,'roles',side_effect=AssertionError('owner replay')):
            mass,own=e.personal_view(source,info)
        expected=condition_actor_state(source.private,lambda h:h.roles[0]==info.initial_roster)
        self.assertIs(own.public_state,source.public_state)
        self.assertIs(own.public,source.public)
        self.assertEqual(own.private,expected)
        self.assertEqual(mass,sum(h.mass for h in source.private.hypotheses if h.roles[0]==info.initial_roster))
        self.assertIsNone(own.observer)
        self.assertEqual(own.provenance.public_mass,1)
        self.assertEqual(own.provenance.private_mass,mass)
        cold=independent_cold(graph,own.board_data)
        self.assertEqual((cold.public_state,cold.private,cold.past),(own.public_state,own.private,own.past))
