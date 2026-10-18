"""Light current-source binding checks; no performance comparison or aggregate."""
from dataclasses import replace
from copy import copy
from pathlib import Path
import sys,time,json,subprocess,threading,os
from unittest.mock import patch
from .cut_out_six_source_bridge import issue,screen,read_action,require_bound,SourceWitness
from .cut_out_candidate_context_fixture import zero_legacy
from .cut_out_uniform_game import CutOutUniformEngine,OwnView
from .partitioned_match_groups import UnsupportedPartition
from werewolf.information_set_forecast import Pending


def require_ok(value):
    assert not isinstance(value,UnsupportedPartition),value
    return value


def guarded_screen(registry,witness,view=None):
    stack,mocks=zero_legacy()
    with stack,patch.object(CutOutUniformEngine,'legacy_large_groups',side_effect=AssertionError('old root grouping')) as root,patch.object(registry.engine,'start',side_effect=AssertionError('legacy current group ingestion')) as current,patch('benchmarks.player_match_groups.cut_out_model_a.adapt_six_model_a',side_effect=AssertionError('per-child initial-group rebuild')) as initial:
        result=require_ok(screen(registry,witness=witness,view=view))
        branch=require_ok(read_action(registry,witness=witness,target=5 if 5 in registry.read().public.alive else 4,view=view))
        assert root.call_count==current.call_count==initial.call_count==0 and all(m.call_count==0 for m in mocks)
    return result,branch


def compare_screen(registry,witness,view=None):
    from .cut_out_six_registry import current_screen,preview_action
    from werewolf.board_future import reconstruction_kernel_reuse,same_role_board
    from werewolf.calculation_budget import calculation_budget
    actual,(child,mass,request)=guarded_screen(registry,witness,view)
    old=current_screen(registry,view=view);reference=current_screen(registry,view=view,official_reference=True)
    for expected in (old,reference):
        assert actual.forecast==expected.forecast and actual.table==expected.table
        assert actual.public_joint==expected.public_joint and actual.own_belief==expected.own_belief and actual.physical_joint==expected.physical_joint
        assert actual.primary==expected.primary and actual.cumulative==expected.cumulative
    literal=5 if 5 in registry.read().public.alive else 4
    lazy=preview_action(registry,literal,view=view);expected=lazy.read()
    assert child.public_state==expected.public_state and child.private==expected.private and child.past==expected.past
    assert same_role_board(child.physical,expected.physical) and mass==lazy.mass()
    stack,mocks=zero_legacy()
    with stack,patch.object(CutOutUniformEngine,'legacy_large_groups',side_effect=AssertionError('cold old grouping')) as root,calculation_budget(1000000,max_seconds=25),reconstruction_kernel_reuse(False):
        cold=request.roles()
        assert cold.public_state==child.public_state and cold.private==child.private and cold.past==child.past
        assert same_role_board(cold.physical,child.physical)
    assert root.call_count==0 and all(m.call_count==0 for m in mocks)
    assert not actual.engine.capture_terminal and not actual.engine.terminal_records
    return actual


def audit_source():
    from .cut_out_six_registry_fixture import setup
    from .cut_out_day_night import moved_law,point_fix
    from werewolf.seer_acquisition import Acquisition
    registry=setup()[1];before=registry.read();stack,mocks=zero_legacy()
    with stack:witness=require_ok(issue(registry))
    assert all(m.call_count==0 for m in mocks)
    assert witness.source==before and before.public_state!=before.private
    swaps=0
    for context,branch in zip(witness.contexts,witness.replay_branches):
        if context.parent is not None:assert context.groups==point_fix(context.parent.groups,*context.new_fixed)
        for group in context.groups:
            for p in group[1:]:
                assert moved_law(branch.public_law,group[0],p,6)==branch.public_law
                assert moved_law(branch.physical_law,group[0],p,6)==branch.physical_law
                swaps+=1
    compare_screen(registry,witness)
    compare_screen(registry,witness,OwnView(1,'seer',(Acquisition(1,1,3,'white'),Acquisition(2,1,2,'white'))))
    assert registry.read()==before
    return dict(case='source',public_physical_separate=True,issued_replay_contexts=len(witness.contexts),both_carrier_swaps=swaps,
        complete_Table_joint_mass_old_two_modes_equal=True,public_and_own_cold_branch_equal=True,
        canonical_calls=0,CandidateRules_calls=0,initial_current_group_rebuild_calls=0)


def audit_edits():
    from .cut_out_six_registry_fixture import setup,event,withdraw
    registry=setup()[1];before=registry.data.inputs;original=registry.read();old=require_ok(issue(registry))
    report=event(registry,('seer',2,1))
    changed=registry.edited({'mode':'single','events':[dict(report,target=4,action='change',ref=report['id'])]})
    cancelled=withdraw(changed,(('seer',2,1),))
    restored=cancelled.edited({'mode':'single','events':[{'kind':'seer','player':1,'day':2,'target':2,'color':'white'}]})
    previous=None
    for current in (changed,cancelled,restored):
        assert isinstance(screen(current,witness=old),UnsupportedPartition)
        witness=require_ok(issue(current));assert witness is not old and witness.origin is not old.origin
        actual=compare_screen(current,witness)
        if previous is not None:
            assert previous.table.players[0].metric('action',current_frame=actual.table.players[0].frame).status=='stale'
        previous=actual
    assert restored.read()==original and registry.data.inputs==before and registry.read()==original
    require_bound(registry,old) # Immutable old snapshot remains valid ONLY for itself.
    assert isinstance(screen(restored,witness=old),UnsupportedPartition)
    return dict(case='edits',changed_cancel_redo_refreshed=3,old_witness_reuse_refused=True,
        old_snapshot_immutable=True,redo_equal_requires_new_origin=True,old_actor_frame_stale=True)


def audit_rejections():
    from .cut_out_six_registry_fixture import setup,withdraw
    from .cut_out_six_registry import SixInputRegistry
    from werewolf.board_future import SavedOrigin,GeneratedBoard
    registry=setup()[1];witness=require_ok(issue(registry));rejected=[]
    assert isinstance(screen(registry),UnsupportedPartition);rejected.append('unbound')
    assert isinstance(screen(registry,witness=replace(witness)),UnsupportedPartition);rejected.append('unissued_copy')
    forged=replace(witness.source,private=witness.source.public_state,physical=witness.source.public)
    try:require_bound(registry,witness,source=forged)
    except Pending as error:assert error.reason=='source_bridge_complete_source_mismatch'
    else:raise AssertionError('Q-only substitute accepted')
    rejected.append('P_or_physical_substitution')
    for value in (-1,True,1.0,'1',None,99):
        altered=copy(registry);altered.data=registry.data.updated(revision=value)
        altered.origin=SavedOrigin(altered.data,registry.base.rules,registry.base.strategy,project_public=False)
        altered.root=GeneratedBoard(altered.origin)
        answer=issue(altered);assert isinstance(answer,UnsupportedPartition) and answer.reason=='source_bridge_invalid_revision',answer
        rejected.append('revision_'+repr(value))
    altered=copy(registry);altered.data=registry.data.updated(model='individual')
    altered.origin=SavedOrigin(altered.data,registry.base.rules,registry.base.strategy,project_public=False);altered.root=GeneratedBoard(altered.origin)
    answer=issue(altered);assert isinstance(answer,UnsupportedPartition) and answer.reason=='source_bridge_model_unproved'
    rejected.append('other_public_model')
    from copy import deepcopy
    log=deepcopy(registry.data.to_game()['public_log']);log['board_graph']['nodes'][log['board_graph']['current']]['edge']['target']=4
    altered=copy(registry);altered.data=registry.data.updated(public_log=log)
    altered.origin=SavedOrigin(altered.data,registry.base.rules,registry.base.strategy,project_public=False);altered.root=GeneratedBoard(altered.origin)
    answer=issue(altered);assert isinstance(answer,UnsupportedPartition) and answer.reason=='source_bridge_owner_path_mismatch'
    rejected.append('owner_path_mismatch')
    # Same valid input and revision but a different owner/origin cannot borrow it.
    twin=SixInputRegistry(registry.base,registry.data)
    assert twin.read()==registry.read() and isinstance(screen(twin,witness=witness),UnsupportedPartition)
    rejected.append('same_content_other_origin')
    changed_CO=withdraw(registry,(('co',1),('seer',1,1),('seer',2,1)))
    assert isinstance(issue(changed_CO),UnsupportedPartition);rejected.append('CO_withdrawal')
    return dict(case='rejections',rejected=rejected)


def audit_medium():
    from .cut_out_two_nights import spec
    from .cut_out_six_registry import SixInputRegistry
    from werewolf.exact import MediumReport
    from werewolf.seer_acquisition import SeerReport
    base=replace(spec(),mediums=1,claims=('seer','medium','medium','latent','latent','latent'),reports=(SeerReport(1,1,1,4,'white'),))
    registry=SixInputRegistry.create(base,(5,6),(SeerReport(2,2,1,5,'white'),),(MediumReport(2,2,5,'white'),MediumReport(2,3,5,'white')))
    witness=require_ok(issue(registry));compare_screen(registry,witness)
    return dict(case='medium',both_saved_medium_reports_preserved=True,old_Table_joint_equal=True)


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>60 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result={'source':audit_source,'edits':audit_edits,'rejections':audit_rejections,'medium':audit_medium}[case]()
    result.update(worker_seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    start=time.monotonic();rows=[];logs=[]
    for case in ('source','edits','rejections','medium'):
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,120-(time.monotonic()-start)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+case,flush=True)
    checks=[('pattern','test_cut_out_six_source_bridge.py'),('named','tests.test_root_secret_replay.RootReplayTests.test_observed_uniform_bite_likelihood_changes_physical_mass_only'),('named','tests.test_root_secret_replay.RootReplayTests.test_report_edit_cancel_and_cache_rebuild_use_initial_joint_law'),('pattern','test_cut_out_six_inherited.py'),('named','tests.test_root_secret_replay.RootReplayTests.test_positive_public_truth_with_impossible_repeated_scan_is_pending')]
    for kind,target in checks:
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture',kind,target],capture_output=True,text=True,timeout=min(60,120-(time.monotonic()-start)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/six-source-bridge-light.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,light_regression_requests=checks,overall_seconds=time.monotonic()-start,
        heavy_comparison_executed=False,speed_measurement_executed=False,ordinary_UI_connected=False,
        limits=dict(per_worker_seconds=60,overall_seconds=120,peak_working_set_bytes=1500000000))
    Path('benchmarks/player_match_groups/cut-out-six-source-bridge-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'])),flush=True)

if __name__=='__main__':main()
