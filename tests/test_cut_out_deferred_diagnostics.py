import unittest
from dataclasses import replace
from benchmarks.player_match_groups.cut_out_deferred_diagnostics_fixture import audit
from benchmarks.player_match_groups.cut_out_deferred_diagnostics import DeferredInitialEngine,DeferredSmallEngine
from benchmarks.player_match_groups.cut_out_separate_publications_fixture import reproduce
from benchmarks.player_match_groups.cut_out_initial_publications import InitialPublicationEngine
from werewolf.board_future import calculation_origin,remember
from werewolf.calculation_budget import calculation_budget


class DeferredDiagnosticTests(unittest.TestCase):
    def test_four_player_full_outputs_and_all_sources_cold(self):
        with calculation_budget(4000000,max_seconds=30):result=audit(4)
        self.assertEqual(result['status'],'verified')
        self.assertEqual(result['independent_cold_reads'],15)
        self.assertEqual(result['deferred_diagnostic_outcome_rows'],0)
        self.assertLess(result['new_retained_resolutions'],result['old_retained_resolutions'])

    def test_actual_seven_player_day3_checkpoint_without_initial_search(self):
        with calculation_budget(4000000,max_seconds=30):
            graph,seed,request,source,saved=reproduce()
            engines=[cls(graph,witness=seed.source_witness) for cls in (InitialPublicationEngine,DeferredInitialEngine)]
            outputs=[]
            for engine in engines:
                engine.inherited_groups=seed.inherited_groups;engine.capture_terminal=True
                with calculation_origin(graph.data):
                    remember(engine,request,source)
                    value=engine.solve(*source,physical=source.physical)
                    actions=tuple((p,engine.act(*source[:3],p,source.private,source.observer,physical=source.physical)) for p in source.public.alive)
                outputs.append((value,actions))
            self.assertEqual(outputs[0],outputs[1])
            eager,lazy=engines
            self.assertEqual(lazy.deferred_ledger.materialized,0)
            self.assertEqual(lazy.board_action_kernels,{})
            self.assertEqual(list(lazy.full_branch_records),eager.full_branch_records)
            rows=list(lazy.full_branch_records)
            # Deferred evidence owns the original configuration, even if the
            # live prototype is later configured for a different experiment.
            lazy.strategy=replace(lazy.strategy,night='max')
            self.assertEqual(list(lazy.full_branch_records),rows)
            self.assertGreater(lazy.board_action_kernels.terminal_not_retained,0)
