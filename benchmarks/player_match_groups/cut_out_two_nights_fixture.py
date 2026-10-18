"""Finite two-night joint-law and timing comparison, explicit six-player opt-in."""
import sys,time
WORKER_STARTED=time.perf_counter()
import json,subprocess,threading,os,hashlib
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    def watchdog():
        while True:
            if peak_bytes()>1_500_000_000:
                print('RSS/working-set limit 1.5GB exceeded',file=sys.stderr,flush=True);os._exit(137)
            time.sleep(.1)
    threading.Thread(target=watchdog,daemon=True).start()
    sys.path.insert(0,str(Path('tests').resolve()))
    from test_cut_out_uniform_game import table
    from .cut_out_two_nights import spec,restore_terminals
    from .cut_out_model_a import adapt_six_model_a,adapt_model_a
    from .cut_out_saved_recipes import SavedCutOutGraph
    from .cut_out_uniform_game import evaluate,OwnView
    from .cut_out_day_night import moved_law,moved_board
    from .partitioned_match_groups import UnsupportedPartition
    from werewolf.board_future import same_role_board
    from werewolf.seer_acquisition import Acquisition,SeerReport
    from unittest.mock import patch
    source=spec();view=None
    if case=='own-seer':view=OwnView(1,'seer',(Acquisition(1,1,3,'white'),))
    if case=='own-wolf':view=OwnView(2,'wolf')
    if case=='medium':source=replace(source,mediums=1,claims=('seer','medium','medium','latent','latent','latent'),reports=(SeerReport(1,1,1,4,'white'),))
    imports_seconds=time.perf_counter()-WORKER_STARTED
    assert isinstance(adapt_model_a(source),UnsupportedPartition) # default remains4/5
    start=time.perf_counter();adapter=adapt_six_model_a(source);adapter_seconds=time.perf_counter()-start
    start=time.perf_counter();graph=SavedCutOutGraph(adapter);saved_seconds=time.perf_counter()-start
    with (patch('werewolf.exact_renaming.canonical_key',side_effect=AssertionError('old full permutation')),
          patch('werewolf.board_roles.prepare_evaluation',side_effect=AssertionError('child initial-prior rebuild'))):
        start=time.perf_counter();actual=evaluate(graph,view=view,capture_terminal=True)
        if isinstance(actual,UnsupportedPartition):raise RuntimeError('grouped pending: '+actual.reason)
        result,grouped=actual;grouped_wall=time.perf_counter()-start
        start=time.perf_counter();expected=evaluate(graph,view=view,capture_terminal=True,official_reference=True)
        if isinstance(expected,UnsupportedPartition):raise RuntimeError('official pending: '+expected.reason)
        forecast,full=expected;full_wall=time.perf_counter()-start
        assert result==forecast
        start=time.perf_counter();a,grouped_restore=restore_terminals(grouped);b,full_restore=restore_terminals(full)
        restore_wall=time.perf_counter()-start
    start=time.perf_counter()
    assert table(graph,result,view)==table(graph,forecast,view)
    assert grouped_restore['second_night_terminal_recipes']>0
    assert grouped_restore['killed_after_scan_witnesses']>0
    assert grouped_restore['corpse_scan_witnesses']>0
    for key,(q,state,request) in a.items():
        old_q,old,_=b[key]
        assert q==old_q and state.public_state==old.public_state
        assert state.private==old.private and state.past==old.past and state.observer==old.observer
        assert same_role_board(state.public,old.public) and same_role_board(state.physical,old.physical)
        assert request.origin is graph.origin
    checks=0
    for board,law,past,own,observer,physical,target in grouped.scalar_actions:
        for group in grouped.groups(board,past,own):
            if len(group)<2:continue
            first=group[0]
            for other in group[1:]:
                changed=moved_law(law,first,other,6);private=moved_law(own,first,other,6)
                assert changed==law and private==own
                assert same_role_board(moved_board(board,changed,first,other),board)
                assert same_role_board(moved_board(physical,private,first,other),physical)
                checks+=1
    verification_seconds=time.perf_counter()-start
    row=dict(case=case,village_win=str(result.village_win),complete_table_action_dawn_win_equal=True,second_night_branch_mass_joint_equal=True,
        group_invariance_swaps_in_tests_only=checks,initial_adapter_seconds=adapter_seconds,saved_origin_gate_seconds=saved_seconds,
        import_startup_seconds=imports_seconds,grouped=dict(grouped.costs),official_labelled=dict(full.costs),
        grouped_evaluation_wall_seconds=grouped_wall,official_evaluation_wall_seconds=full_wall,
        grouped_terminal_restore=grouped_restore,all_individual_terminal_restore=full_restore,
        full_label_materialization_seconds=full_wall+full_restore['restore_seconds'],
        grouped_end_to_end_with_individual_full_label_pass_seconds=imports_seconds+adapter_seconds+saved_seconds+grouped_wall+full_wall+full_restore['restore_seconds'],
        verification_seconds=verification_seconds,worker_total_seconds=time.perf_counter()-WORKER_STARTED,process_peak_working_set_bytes=peak_bytes(),
        all_label_boundary='all individual terminal histories explicitly materialized by labelled common traversal; no optimized full-tree transport from representatives',
        memory_scope='combined grouped/reference engines, terminal recipes and verification, not isolated per-engine RSS')
    print(json.dumps(row),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    started=time.monotonic();rows=[]
    for case in ('public','public','public','own-seer','own-wolf','medium'):
        remaining=300-(time.monotonic()-started)
        if remaining<=0:raise SystemExit('300s overall budget exhausted')
        start=time.perf_counter()
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,remaining))
        if run.returncode:print(case,run.stdout+run.stderr);raise SystemExit(run.returncode)
        row=json.loads(run.stdout);row['repeat_index']=1+sum(r['case']==case for r in rows);row['process_end_to_end_seconds']=time.perf_counter()-start
        rows.append(row);print(case,round(row['process_end_to_end_seconds'],3),row['village_win'],row['grouped_terminal_restore']['second_night_terminal_recipes'],flush=True)
    paths=('benchmarks/player_match_groups/cut_out_two_nights.py','benchmarks/player_match_groups/cut_out_two_nights_fixture.py','benchmarks/player_match_groups/cut_out_uniform_game.py','benchmarks/player_match_groups/cut_out_model_a.py','tests/test_cut_out_two_nights.py')
    result=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),head_before_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),cases=rows,
        total_seconds=time.monotonic()-started,per_process_limit_seconds=60,overall_limit_seconds=300,rss_limit_bytes=1_500_000_000,
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        ordinary_or_public_changed=False,unsupported=['7 players','max','hunter','optimized complete-tree label transport','six-player SavedBinding.corrected/bind first-morning registry'])
    Path('benchmarks/player_match_groups/cut-out-two-nights-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
