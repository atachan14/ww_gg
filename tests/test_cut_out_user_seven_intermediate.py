import unittest
from unittest.mock import patch
from benchmarks.player_match_groups.cut_out_user_seven_source import *
from benchmarks.player_match_groups.cut_out_user_seven_source_fixture import ok

class SevenIntermediateEntryTests(unittest.TestCase):
    def test_initial_dispatch_is_wired_without_solving(self):
        r=ok(synthetic_registry());root=ok(from_game(r.initial.data.to_game(),r.initial));w=ok(issue(root))
        with patch('benchmarks.player_match_groups.cut_out_user_seven_source.common_evaluate',return_value='dispatch-only') as dispatch:
            self.assertEqual(evaluate_initial(root,witness=w),'dispatch-only')
            kw=dispatch.call_args.kwargs
            self.assertEqual(kw['max_seconds'],5)
            self.assertIs(kw['engine_class'].func,SevenInitialEngine)
            self.assertEqual(kw['engine_class'].func.max_alive,7)
            self.assertEqual(evaluate_initial(root,witness=w,official_reference=True),'dispatch-only')
            self.assertIsNone(dispatch.call_args.kwargs['engine_class'])
            self.assertIsInstance(evaluate_intermediate(root,witness=w),UnsupportedPartition)
            self.assertIsInstance(evaluate_small(root,witness=w),UnsupportedPartition)
        with patch('benchmarks.player_match_groups.cut_out_user_seven_source.common_evaluate',side_effect=AssertionError('no dispatch')):
            self.assertIsInstance(evaluate_initial(root),UnsupportedPartition)
            self.assertIsInstance(evaluate_initial(r,witness=ok(issue(r))),UnsupportedPartition)

    def test_intermediate_small_reference_and_branch_readbacks_bounded(self):
        import subprocess,sys,json
        for case in ('tiny','five'):
            run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.cut_out_user_seven_intermediate_fixture',case],capture_output=True,text=True,timeout=16)
            self.assertEqual(run.returncode,0,run.stderr)
            result=json.loads(run.stdout)
            self.assertEqual(result['status'],'verified')
            self.assertTrue(result['complete_Table_joint_equal'])
