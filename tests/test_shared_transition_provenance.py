import unittest
from dataclasses import replace
from unittest.mock import patch
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import shared_transition_audit,make_scope
from benchmarks.player_match_groups.cut_out_publication_orbit_value import with_audited_groups
from werewolf.acquisition_provenance import UniformAcquisitionCache
from werewolf.board_future import calculation_origin
from werewolf.calculation_budget import calculation_budget
from werewolf.joint_value_sharing import independent_joint_values


class SharedTransitionProvenanceTests(unittest.TestCase):
    def test_complete_common_chains_match_independent_histories_cold_forecast_tables(self):
        with calculation_budget(4000000,max_seconds=30),independent_joint_values():
            result=shared_transition_audit()
        self.assertEqual(result['status'],'verified')
        counts=result['counts'];proof=result['proof_counts']
        self.assertEqual(counts['complete_QP_history_physical_checks'],76)
        self.assertEqual(counts['cold_reads'],76)
        self.assertEqual(counts['independent_Forecast_Table_checks'],37)
        self.assertEqual(proof['death_group_receipts'],19)
        self.assertEqual(proof['report_group_receipts'],55)
        self.assertGreater(counts['public_only_death_rows'],0)
        self.assertGreater(counts['public_only_report_rows'],0)
        self.assertGreater(proof['public_semantic_hypothesis_visits'],0)
        self.assertGreater(proof['trusted_cache_equivalence_links'],0)
        private=result['cases'][-1]
        self.assertEqual(private['selected_first_report_Q'],'1/15')
        self.assertEqual(private['selected_first_report_P'],'1/5')
        self.assertFalse(result['whole_initial7_search'])
        self.assertFalse(result['MAX_evaluated'])

    def test_normal_cache_writes_strip_generated_ticket(self):
        cache=UniformAcquisitionCache();key=('canonical',);value=object();ticket=object()
        cache._store_generated(key,value,ticket)
        self.assertEqual(cache._lookup(key),(value,ticket))
        self.assertIs(cache[key],value)
        cache[key]=value
        self.assertEqual(cache._lookup(key),(value,None))
        cache._store_generated(key,value,ticket)
        cache.update({key:value})
        self.assertEqual(cache._lookup(key),(value,None))
        self.assertEqual(cache.copy(),{key:value})

    def test_active_foreign_game_and_copied_law_decline(self):
        scope,_=make_scope('five');cap=with_audited_groups(scope)
        source=cap.source;ledger=cap.group_ledger
        self.assertIsNotNone(ledger.groups_for(source.provenance,source.public,source))
        foreign=cap.graph.data.updated(revision=987654)
        with calculation_origin(foreign):
            self.assertIsNone(ledger.groups_for(source.provenance,source.public,source))
        self.assertIsNone(ledger.groups_for(source.provenance,source.public,replace(source,private=replace(source.private))))

    def test_custom_kernels_and_unknown_cached_morning_never_get_certificates(self):
        scope,_=make_scope('five');cap=with_audited_groups(scope)
        e=cap.builder;source=cap.source;ledger=cap.group_ledger
        self.assertTrue(ledger._canonical_death())
        self.assertTrue(ledger._reports_supported())
        with patch.object(e,'public_children',wraps=e.public_children):
            self.assertFalse(ledger._canonical_death())
        with patch.object(e,'generate_publications',wraps=e.generate_publications):
            self.assertFalse(ledger._reports_supported())
        # Equal numerical rows computed by another engine/cache are not a
        # canonical generated-operation stamp in this ledger.
        rows=((1,source.public,source.public_state,source.past),)
        self.assertEqual(ledger.public_only_reports(source,rows),())
        self.assertIsNone(ledger._mornings.get(id(rows)))
