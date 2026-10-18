"""Bounded targeted regressions; saved-seven long requests are excluded."""
import os,sys,time,json,threading,unittest
from pathlib import Path
from .cut_out_uniform_game_fixture import peak_bytes
from werewolf.calculation_budget import calculation_budget


def run(group):
    start=time.monotonic();sys.path.insert(0,str(Path('tests').resolve()))
    def watch():
        while True:
            if time.monotonic()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    board=['two_actions_replay_the_entire_evidence_and_share_game_data','publication_and_actor_conditioning_match_previous_kernels','saved_terminal_board_stops_before_future_generation','actor_intervention_does_not_reuse_incompatible_actual_count_constraint','existing_kernel_reuse_matches_cold_full_evidence_reconstruction','complete_input_keys_preserve_structural_equality_and_secret_histories','reusing_canonical_initial_physical_board_preserves_full_law','count_sum_reuse_is_exact_and_caller_mutation_cannot_change_it']
    names={'new':['tests.test_compact_terminal','tests.test_action_flow','tests.test_cut_out_deferred_diagnostics'],
        'legacy':['tests.test_uniform_terminal_cut','tests.test_terminal_followup','tests.test_cut_out_saved_recipes'],
        'replay':['tests.test_board_future.GeneratedBoardTests.test_'+name for name in board]+['tests.test_cut_out_structural_publications','tests.test_cut_out_seven_publication']}[group]
    with calculation_budget(4000000,max_seconds=30):
        result=unittest.TextTestRunner(verbosity=1,stream=sys.stdout).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    row=dict(group=group,status='verified' if result.wasSuccessful() else 'failed',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes(),whole_initial7_search=False)
    Path('benchmarks/player_match_groups/compact-terminal-tests-'+group+'.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)
    raise SystemExit(not result.wasSuccessful())

if __name__=='__main__':run(sys.argv[1])
