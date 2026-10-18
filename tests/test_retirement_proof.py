import unittest
from dataclasses import replace
from benchmarks.player_match_groups.initial_white import initial_white_source
from benchmarks.player_match_groups.retirement_proof import RetirementProofForecast
from benchmarks.player_match_groups.retirement_probe import probe
from werewolf.action_flow import resolve_action
from werewolf.evaluation_branch import ActionInputs,physical_board


class RetirementProofTests(unittest.TestCase):
    def context(self):
        _,_,b,s,past,rules,strategy,_=initial_white_source(5,1,actors=(1,2))
        e=RetirementProofForecast(rules,strategy,retirement_proof=True)
        acquired,outcomes=resolve_action(b,ActionInputs(s,past,s,None,physical_board(b,s)),1,e.action_policy,terminal_payoffs=True)
        for outcome in outcomes:
            if outcome.board.winner is not None:continue
            payload=e.action_policy.project(b,acquired,outcome,1)
            if e.can_retire_scans(*payload[:3]):return e,tuple(payload)
        self.fail('Missing exposed fake witness')

    def test_retains_only_actual_observed_history(self):
        e,payload=self.context();result=e.continuation_context(*payload)
        self.assertEqual(result[0].initial_seer_count,0)
        self.assertEqual(result[2],payload[2]);self.assertTrue(result[2])
        self.assertTrue(e.can_retire_scans(*result[:3]))
        self.assertEqual(e.retirement_proof_hits,1)

    def test_unknown_initial_history_is_not_blessed(self):
        e,payload=self.context();b,s,_,own,obs=payload
        result=e.continuation_context(b,s,(),own,obs)
        self.assertEqual(result[0].initial_seer_count,1)
        self.assertEqual(e.retirement_proof_hits,0)

    def test_external_private_max_and_disabled_fall_back(self):
        for mode in ('disabled','private','max'):
            e,payload=self.context()
            if mode=='disabled':e.retirement_proof=False
            elif mode=='private':e.reuse_public_entry=False
            else:e.strategy=replace(e.strategy,day='max')
            result=e.continuation_context(*payload)
            self.assertEqual(result[2],())
            self.assertEqual(e.retirement_proof_hits,0)

    def test_diagnostic_role_independent_noise(self):
        row=probe()['rows'][0]
        self.assertEqual(row['generated_branches'],64)
        self.assertTrue(row['all_role_posteriors_unchanged'])
        self.assertEqual(row['total_probability'],'1')

    def test_completed_seven_matches_independent_count_reference(self):
        from benchmarks.player_match_groups.uniform_count_reference import validate
        result=validate()
        self.assertTrue(result['all_table_rows_equal'])
        self.assertEqual(result['value'],'8/35')
