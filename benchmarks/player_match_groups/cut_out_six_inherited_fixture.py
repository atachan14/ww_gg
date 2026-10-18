"""Bounded six-player uniform two-night correctness, not speed measurement."""
import sys,time,json,subprocess,threading,os
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from .cut_out_candidate_context_fixture import zero_legacy


def scope_checks():
    from .cut_out_six_inherited import evaluate
    from .cut_out_two_nights import graph,spec
    from .cut_out_uniform_game import evaluate as old_evaluate
    from .cut_out_max_game import graph as four_graph
    from .cut_out_seven_minimal import graph as seven_graph
    from .cut_out_six_registry_fixture import setup
    from .cut_out_model_a import adapt_six_model_a
    from .partitioned_match_groups import UnsupportedPartition
    from werewolf.exact import Strategy,Rules
    from copy import copy
    source=graph()
    from .cut_out_saved_recipes import SavedCutOutGraph
    other=SavedCutOutGraph(adapt_six_model_a(replace(spec(),claims=('latent',)*6,reports=(),rules=Rules(initial_seer='none'))))
    other_refusal=evaluate(other)
    assert isinstance(other_refusal,UnsupportedPartition) and other_refusal.reason=='six_inherited_minimal_input_shape_unproved'
    bad=copy(source);bad.engine=copy(source.engine)
    bad.engine.baseline=replace(source.engine.baseline,spec=replace(spec(),strategy=Strategy()))
    assert isinstance(evaluate(bad),UnsupportedPartition)
    assert isinstance(adapt_six_model_a(replace(spec(),strategy=Strategy())),UnsupportedPartition)
    assert isinstance(evaluate(four_graph(4)),UnsupportedPartition)
    assert isinstance(evaluate(seven_graph()),UnsupportedPartition)
    base,registry=setup()
    refused=evaluate(registry)
    assert isinstance(refused,UnsupportedPartition) and refused.reason=='six_inherited_initial_saved_root_witness_required'
    return dict(six_max_refused=True,four_and_seven_refused=True,other_uniform_shapes_conservatively_refused=True,current_Board_registry_refused=refused.reason,
        classification='initial6 player-number guard was conservative; current registry has complete saved data but lacks an issued incremental current-source witness')


def audit(case):
    from .cut_out_two_nights import spec,restore_terminals
    from .cut_out_model_a import adapt_six_model_a
    from .cut_out_saved_recipes import SavedCutOutGraph
    from .cut_out_six_inherited import evaluate,SixInheritedUniformEngine
    from .cut_out_uniform_game import evaluate as old_evaluate,OwnView,CutOutUniformEngine
    from .cut_out_max_fixture import complete_table
    from .cut_out_day_night import point_fix,moved_law,moved_board
    from .cut_out_inherited_groups_fixture import old_group_oracle
    from .partitioned_match_groups import UnsupportedPartition
    from werewolf.seer_acquisition import Acquisition,SeerReport
    from werewolf.board_future import same_role_board,reconstruction_kernel_reuse
    from werewolf.information_set_forecast import Pending
    from werewolf.calculation_budget import calculation_budget
    source_spec=spec();view=None
    if case=='own-seer':view=OwnView(1,'seer',(Acquisition(1,1,3,'white'),))
    elif case=='own-wolf':view=OwnView(2,'wolf')
    elif case=='medium':source_spec=replace(source_spec,mediums=1,claims=('seer','medium','medium','latent','latent','latent'),reports=(SeerReport(1,1,1,4,'white'),))
    source=SavedCutOutGraph(adapt_six_model_a(source_spec));root=source.origin()
    stack,mocks=zero_legacy()
    with stack,patch.object(CutOutUniformEngine,'legacy_large_groups',side_effect=AssertionError('initial group rebuild')) as rebuild,patch('werewolf.board_roles.prepare_evaluation',side_effect=AssertionError('child prior rebuild')) as prior:
        actual=evaluate(source,view=view,capture_terminal=True)
        if isinstance(actual,UnsupportedPartition):raise AssertionError(actual)
        forecast,engine=actual
        small,counts=restore_terminals(engine)
        assert counts['second_night_terminal_recipes'] and counts['killed_after_scan_witnesses'] and counts['corpse_scan_witnesses']
        assert rebuild.call_count==prior.call_count==0 and all(m.call_count==0 for m in mocks)
    # True cold replay may rebuild the saved INITIAL prior. It must not rebuild
    # descendant groups or invoke matching; the root input remains authoritative.
    request=next(request for q,c,request in small.values() if c.public.history[-1].phase=='night' and c.public.history[-1].day==2)
    warm=request.roles();cold_stack,cold_mocks=zero_legacy()
    with cold_stack,patch.object(CutOutUniformEngine,'legacy_large_groups',side_effect=AssertionError('cold root-group rebuild')) as cold_rebuild,calculation_budget(1000000,max_seconds=25),reconstruction_kernel_reuse(False):
        cold=request.roles()
        assert cold.public_state==warm.public_state and cold.private==warm.private and cold.past==warm.past
        assert same_role_board(cold.physical,warm.physical)
    assert cold_rebuild.call_count==0 and all(m.call_count==0 for m in cold_mocks)
    # Both old root/history-group evaluation and the all-labelled exact
    # reference are explicit comparison runs, outside actual-path guards.
    old_forecast,old=old_evaluate(source,view=view,capture_terminal=True)
    labelled_forecast,full=old_evaluate(source,view=view,capture_terminal=True,official_reference=True)
    assert old.inherited_groups is None
    assert forecast==old_forecast==labelled_forecast
    assert complete_table(source,forecast,view)==complete_table(source,old_forecast,view)==complete_table(source,labelled_forecast,view)
    scalar_checks=0;private_swaps=0
    root_groups=engine.inherited_groups.require(*root[:3]).groups
    for key,value in engine.scalar_actions.items():
        b,s,past,private,observer,physical,target=key
        assert value==old.act(b,s,past,target,private,observer,physical=physical)
        assert value==full.act(b,s,past,target,private,observer,physical=physical)
        actual_groups=engine.groups(b,past,private,observer,public_state=s)
        assert sorted(actual_groups)==sorted(old_group_oracle(root_groups,b,past,private,observer,view))
        for group in actual_groups:
            for other in group[1:]:
                assert moved_law(private,group[0],other,6)==private
                assert same_role_board(moved_board(physical,private,group[0],other),physical)
                private_swaps+=1
        scalar_checks+=1
    large,full_counts=restore_terminals(full)
    for key,(mass,state,request) in small.items():
        old_mass,expected,_=large[key]
        assert mass==old_mass and state.public_state==expected.public_state and state.private==expected.private
        assert state.past==expected.past and state.observer==expected.observer
        assert same_role_board(state.public,expected.public) and same_role_board(state.physical,expected.physical)
        assert request.origin is source.origin
    recursive=0;public_swaps=0
    for context in engine.inherited_groups.contexts.values():
        if context.parent is not None:
            assert context.groups==point_fix(context.parent.groups,*context.new_fixed)
            recursive+=1
        for group in context.groups:
            for other in group[1:]:
                assert moved_law(context.state,group[0],other,6)==context.state
                public_swaps+=1
    child=next(c for c in engine.inherited_groups.contexts.values() if c.depth>1)
    fresh=SixInheritedUniformEngine(source)
    try:fresh.inherited_groups.require(child.board,child.state,child.past)
    except Pending:pass
    else:raise AssertionError('missing child witness silently rebuilt')
    assert engine.costs['saved_origins']==1 and source.data.inputs==source.origin.board_data.inputs
    return dict(case=case,village_win=str(forecast.village_win),Table_forecast_joint_mass_equal_both_old_modes=True,
        scalar_and_old_group_checks=scalar_checks,recursive_contexts=recursive,
        inheritance_stats=dict(engine.inherited_groups.stats),private_law_swaps=private_swaps,public_law_swaps=public_swaps,
        second_night_terminal_counts=counts,all_labelled_reference_terminal_counts=full_counts,
        true_cold_second_night_replay_equal=True,missing_child_witness_refused=True,
        actual_canonical_calls=0,actual_CandidateRules_calls=0,actual_initial_group_rebuild_calls=0,actual_child_prior_rebuild_calls=0,
        default_six_route_unchanged=True,ordinary_UI_connected=False)


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>60 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result=scope_checks() if case=='scope' else audit(case)
    result.update(worker_seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    start=time.monotonic();rows=[];logs=[]
    for case in ('public','own-seer','own-wolf','medium','scope'):
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,270-(time.monotonic()-start)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+case,flush=True)
    for target in ('test_cut_out_six_inherited.py','test_cut_out_two_nights.py','test_cut_out_inherited_groups.py','test_cut_out_max_game.py'):
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture','pattern',target],capture_output=True,text=True,timeout=min(60,270-(time.monotonic()-start)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/six-inherited-focused-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,overall_seconds=time.monotonic()-start,scope='explicit6 uniform initial ModelA W1 S1 H0 M0/1, existing two-night cases',
        speed_measurement_executed=False,heavy_aggregate_executed=False,
        limits=dict(per_worker_seconds=60,overall_seconds=270,peak_working_set_bytes=1500000000))
    Path('benchmarks/player_match_groups/cut-out-six-inherited-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'])),flush=True)

if __name__=='__main__':main()
