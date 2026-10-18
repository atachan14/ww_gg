"""Independent joint enumeration for the opt-in report-existence proof."""
import unittest
from dataclasses import replace
from fractions import Fraction as F
from benchmarks.player_match_groups.withdraw_prefix_diagnostic import minimal_four,examine
from benchmarks.player_match_groups.cut_out_six_registry_fixture import setup,withdraw
from werewolf.seer_acquisition import Acquisition,Hypothesis,normalize
from werewolf.night_knowledge import WolfAttack


def independent_unknown_history(board,night=False):
    entries=[];n=board.player_count;first=tuple(range(1,n+1))
    roster=tuple(p for p in first if p!=2)
    for world in board.worlds:
        masks=world[:-1];owner=masks[2].bit_length()
        choices=tuple(p for p in first if p!=owner and not masks[0]&(1<<(p-1)))
        for target in choices:
            initial=Acquisition(1,owner,target,'white')
            later=tuple(p for p in first if p!=owner and p!=target) if night and owner in roster else (None,)
            for follow in later:
                records=(initial,) if follow is None else (initial,Acquisition(2,owner,follow,'black' if masks[0]&(1<<(follow-1)) else 'white'))
                entries.append(Hypothesis(masks,records,world[-1]/len(choices)/len(later),(),(WolfAttack(1,3),) if night else ()))
    return normalize(entries)


class WithdrawPrefixDiagnosticTests(unittest.TestCase):
    def test_minimal_four_standard_matches_independent_law_and_explicit_legacy_still_pending(self):
        spec,original,changed=minimal_four()
        record,branch=examine(spec,changed)
        self.assertEqual(record['legacy_result'],'full_disclosure_truth_not_conditioned')
        self.assertEqual(record['default_result'],'completed')
        self.assertEqual(record['wolf_rates'],{'1':'3/5','3':'1/5','4':'1/5'})
        worlds=tuple(sorted([(1,0,1<<(p-1),0,F(1,5)) for p in (2,3,4)]+[(1<<(p-1),0,1,0,F(1,5)) for p in (3,4)]))
        self.assertEqual(tuple(sorted(changed.roles().board.worlds)),worlds)
        expected=independent_unknown_history(changed.roles().board)
        self.assertEqual(branch.public_law.hypotheses,expected)
        self.assertEqual(branch.physical_law.hypotheses,expected)
        self.assertEqual(record['truth1_initial_targets'],[2,3,4])
        self.assertEqual(branch.past,())
        self.assertEqual(original.to_game()['seer_inputs'][0]['target'],3)

    def test_missing_historical_report_is_not_manufactured_or_rescued(self):
        spec,original,changed=minimal_four(report=False)
        record,branch=examine(spec,changed)
        self.assertEqual(record['default_result'],'completed')
        self.assertEqual(branch.public.wolf_probability(1),1)
        self.assertFalse(any(h.roles[2]&1 for h in branch.public_law.hypotheses))
        self.assertEqual(branch.public_law.hypotheses,independent_unknown_history(changed.roles().board))

    def test_six_two_saved_actions_preserve_old_role_oracle_and_both_secret_slots(self):
        base,original=setup();inputs=original.data.inputs
        changed=withdraw(original,(('co',1),('seer',1,1),('seer',2,1)))
        record,branch=examine(base,changed.data)
        self.assertEqual(record['legacy_result'],'full_disclosure_truth_not_conditioned')
        self.assertEqual(record['default_result'],'completed')
        worlds=tuple(sorted([(1,0,1<<(p-1),0,F(1,8)) for p in range(2,7)]+[(1<<(p-1),0,1,0,F(1,8)) for p in (4,5,6)]))
        self.assertEqual(tuple(sorted(changed.data.roles().board.worlds)),worlds)
        expected=independent_unknown_history(changed.data.roles().board,night=True)
        self.assertEqual(branch.public_law.hypotheses,expected)
        self.assertEqual(branch.physical_law.hypotheses,expected)
        self.assertEqual(len(expected),116)
        self.assertEqual(original.data.inputs,inputs)

    def test_standard_role_state_forecast_cache_and_cold_rebuild_match_uniform_formula(self):
        from werewolf.board_flow import BoardData
        spec,original,data=minimal_four()
        state=data.roles();forecast=state.forecast(max_work=1000000,max_seconds=20)
        self.assertEqual(forecast.village_win,0) # Three alive, night, W1: wolf wins.
        self.assertIs(forecast,state.forecast(max_work=1000000,max_seconds=20))
        self.assertEqual(forecast,BoardData.from_game(data.to_game()).roles().forecast(max_work=1000000,max_seconds=20))
        base,original=setup();changed=withdraw(original,(('co',1),('seer',1,1),('seer',2,1)))
        forecast=changed.data.roles().forecast(max_work=1000000,max_seconds=20)
        self.assertEqual(forecast.village_win,F(1,4)) # Four alive, one uniform execution then lethal night.
        self.assertEqual(dict(forecast.action_values),{1:F(5,8),4:F(1,8),5:F(1,8),6:F(1,8)})

    def test_private_entry_uses_only_explicit_own_scan_and_does_not_restore_retired_public_value(self):
        from werewolf.board_roles import prepare_private
        from werewolf.seer_future_uniform import FuturePending
        spec,original,data=minimal_four();public=data.roles().board
        before=data.inputs;worlds=public.worlds
        old_content=prepare_private(public,'seer',(1,),[dict(day=1,target=3,color='white')],spec.rules,spec.strategy,game_state=data.to_game())
        different=prepare_private(public,'seer',(1,),[dict(day=1,target=2,color='white')],spec.rules,spec.strategy,game_state=data.to_game())
        self.assertNotIsInstance(old_content.actor,FuturePending)
        self.assertNotIsInstance(different.actor,FuturePending)
        self.assertEqual(old_content.role_board.wolf_probability(4),1)
        self.assertEqual(different.role_board.wolf_probability(3),F(1,2))
        self.assertEqual(different.role_board.wolf_probability(4),F(1,2))
        self.assertTrue(all(any(a.player==1 and a.target==2 for a in h.acquisitions) for h in different.actor.physical_law.hypotheses))
        self.assertEqual(public.worlds,worlds)
        self.assertEqual(data.inputs,before)
        self.assertEqual(data.to_game()['seer_inputs'],[])
