"""Six-player opt-in boundary and terminal second-night evidence regression."""
from dataclasses import replace
import unittest
from benchmarks.player_match_groups.cut_out_two_nights import spec,graph,restore_terminals
from benchmarks.player_match_groups.cut_out_model_a import adapt_model_a,adapt_six_model_a
from benchmarks.player_match_groups.cut_out_uniform_game import evaluate
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition
from werewolf.exact import Strategy


class CutOutTwoNightTests(unittest.TestCase):
    def test_six_is_explicit_and_max_and_seven_remain_unsupported(self):
        source=spec()
        self.assertIsInstance(adapt_model_a(source),UnsupportedPartition)
        saved=graph();original=saved.data.inputs
        with self.assertRaisesRegex(ValueError,'six-player first-morning'):
            saved.bind(None)
        self.assertIsInstance(saved.corrected(source),UnsupportedPartition)
        self.assertEqual(saved.data.inputs,original)
        self.assertIsInstance(adapt_six_model_a(replace(source,seers=2)),UnsupportedPartition)
        self.assertIsInstance(adapt_six_model_a(replace(source,players=7,claims=source.claims+('latent',))),UnsupportedPartition)
        self.assertIsInstance(adapt_six_model_a(replace(source,strategy=Strategy())),UnsupportedPartition)

    def test_second_night_terminal_recipe_keeps_acquisition_and_both_attacks(self):
        source=graph();forecast,engine=evaluate(source,capture_terminal=True)
        rows,counts=restore_terminals(engine)
        self.assertEqual(str(forecast.village_win),'3/8')
        self.assertGreater(counts['second_night_terminal_recipes'],0)
        self.assertGreater(counts['killed_after_scan_witnesses'],0)
        self.assertGreater(counts['corpse_scan_witnesses'],0)
        self.assertEqual(engine.costs['saved_origins'],1)
        self.assertTrue(all(request.origin is source.origin for q,state,request in rows.values()))
