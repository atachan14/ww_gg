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
    def test_minimal_four_default_oracle_unchanged_and_optin_full_unknown_law(self):
        spec,original,changed=minimal_four()
        record,branch=examine(spec,changed)
        self.assertEqual(record['default_result'],'full_disclosure_truth_not_conditioned')
        self.assertEqual(record['wolf_rates'],{'1':'3/5','3':'1/5','4':'1/5'})
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
        self.assertEqual(record['default_result'],'full_disclosure_truth_not_conditioned')
        expected=independent_unknown_history(changed.data.roles().board,night=True)
        self.assertEqual(branch.public_law.hypotheses,expected)
        self.assertEqual(branch.physical_law.hypotheses,expected)
        self.assertEqual(len(expected),116)
        self.assertEqual(original.data.inputs,inputs)
