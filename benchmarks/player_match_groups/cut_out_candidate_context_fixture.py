"""Small mechanism regressions; actual paths forbid the old matcher."""
import json,time,sys,subprocess,threading,os
from pathlib import Path
from fractions import Fraction as F
from unittest.mock import patch
# Import aliases before patching so the oracle is restored correctly afterward.
from werewolf.candidate_policy import CandidateRules as LegacyRules
from werewolf.actor_information import wolf_information_groups
from werewolf.policy_choice import uniform_policy


def zero_legacy():
    from contextlib import ExitStack
    stack=ExitStack()
    mocks=[stack.enter_context(patch(name,side_effect=AssertionError('legacy matching called: '+name))) for name in
        ('werewolf.exact_renaming.canonical_key','werewolf.candidate_policy.canonical_key','werewolf.candidate_policy.CandidateRules')]
    return stack,mocks


def compare_candidate_inputs(source,engine):
    from .cut_out_candidate_context import CutOutCandidateRules
    comparisons=0;contexts=0
    for context in engine.public_candidate_contexts.values():
        if not context.steps:continue
        b,s,past=context.board,context.state,context.past
        groups=wolf_information_groups(s)
        actual=CutOutCandidateRules(context,b,s,past,groups)
        old=LegacyRules(b,s,past,engine.rules,engine.strategy)
        assert actual.actions==old.actions
        pairs=list(actual.classes)
        for x in pairs:
            for y in pairs:assert (actual.classes[x]==actual.classes[y])==(old.classes[x]==old.classes[y])
        profiles=[tuple((i,uniform_policy(actions)) for i,actions in actual.actions.items()),
            tuple((i,((actions[0],F(1)),)) for i,actions in actual.actions.items())]
        for profile in profiles:
            for info,target in pairs:
                assert actual.candidate(profile,info,target)==old.candidate(profile,info,target)
                comparisons+=1
        assert actual.stats['law_permutation_checks']==actual.stats['law_rows_read_for_grouping']==0
        contexts+=1
    assert contexts
    return dict(public_contexts_compared=contexts,full_candidate_profiles_compared=comparisons,
        candidate_equivalence_matches_old=True,comparison_uses_explicit_old_oracle_only=True)


def boundary_and_fixed_points():
    from .cut_out_white_joint_max import graph,evaluate
    from .cut_out_no_read_night_max import WhiteJointNightMaxEngine,guarded_profile_probe
    from .cut_out_candidate_context import CutOutCandidateRules
    from .cut_out_uniform_game import OwnView
    from werewolf.seer_acquisition import Acquisition
    from werewolf.seer_intervention import SeerObserver
    from werewolf.actor_information import condition_actor_state
    from werewolf.information_set_forecast import Pending
    source=graph();stack,mocks=zero_legacy()
    with stack:
        # Compute only the public forecast, not a full aggregate fixture.
        forecast,engine=evaluate(source)
        context=next(c for c in engine.public_candidate_contexts.values() if c.steps and c.steps[0][1]==2)
        b,s,past=context.board,context.state,context.past
        view=OwnView(1,'seer',(Acquisition(1,1,3,'white'),))
        own=condition_actor_state(s,view.accepts)
        observer=SeerObserver(1,view.acquisitions,2,4)
        private_groups=engine.groups(b,past,own,observer)
        assert next(g for g in private_groups if 4 in g)==(4,)
        assert len(next(g for g in context.groups if 4 in g))==4
        fresh=WhiteJointNightMaxEngine(source)
        try:fresh.wolf_policy(b,s,past,1)
        except Pending as error:assert 'cut_out_candidate_context_required' in error.reason
        else:raise AssertionError('missing inherited context silently accepted')
        assert not fresh.no_read_certificates
        missing,diag=guarded_profile_probe(b,s,past,engine.rules,engine.strategy)
        assert missing.selected is None and missing.reason=='cut_out_candidate_context_required'
        assert diag['candidate_engines']==0
    assert all(m.call_count==0 for m in mocks)
    return dict(missing_context_refused=True,no_legacy_fallback=True,private_future_target_point_fixed=True,
        public_candidate_context_not_conditioned_on_other_private_target=True,legacy_match_calls=0)


def audit(case):
    from .cut_out_active_report_fixture import audit as reports
    from .cut_out_latent_max_fixture import audit as complete
    from .cut_out_no_read_night_max import graph as basic_graph,evaluate as basic_eval
    if case=='boundaries':return boundary_and_fixed_points()
    stack,mocks=zero_legacy()
    with stack:
        if case=='active4':result=reports(4,'random_white',True)
        elif case=='active5':result=reports(5,'random_white',True)
        elif case=='white5':result=complete(5,1,'random_white','white',_white_joint=True,_scan_interventions=False,_fake_reports='max')
        else:result=complete(5,0,'none','role',_no_read_night_max=True,_fake_reports='max')
        source=basic_graph(fake_reports='max');_,engine=basic_eval(source)
        for search,diagnostic in engine.no_read_diagnostics.values():
            assert diagnostic['grouping']=='inherited_block_pair_orbits'
            assert diagnostic['canonical_calls']==diagnostic['law_permutation_checks']==0
            assert diagnostic['complete_candidate_scores']==diagnostic['candidate_engines']==12
        for m in mocks:assert m.call_count==0
    # The old matcher is used only OUTSIDE the measured actual run as oracle.
    oracle=compare_candidate_inputs(source,engine)
    if case in ('active4','active5'):
        from .cut_out_active_report_max import graph as report_graph,evaluate as report_eval
        report_source=report_graph(int(case[-1]),'random_white')
        report_stack,report_mocks=zero_legacy()
        with report_stack:
            _,report_engine=report_eval(report_source)
        assert all(m.call_count==0 for m in report_mocks)
        oracle['active_report_contexts']=compare_candidate_inputs(report_source,report_engine)
    if case=='white5':
        from .cut_out_white_joint_max import graph as white_graph,evaluate as white_eval
        white_source=white_graph()
        white_stack,white_mocks=zero_legacy()
        with white_stack:
            _,white_engine=white_eval(white_source)
        assert all(m.call_count==0 for m in white_mocks)
        oracle['white_joint_contexts']=compare_candidate_inputs(white_source,white_engine)
    result.update(case=case,legacy_canonical_calls_actual=0,legacy_candidate_constructor_calls_actual=0,
        old_full_candidate_values_retained=True,candidate_oracle=oracle)
    return result


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>60 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result=audit(case);result.update(worker_seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    start=time.monotonic();rows=[];logs=[]
    for case in ('active4','active5','basic5','white5','boundaries'):
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-start)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+case,flush=True)
    # Focused regressions only. Do not run the62-case aggregate or fixture mains.
    targets=['test_cut_out_candidate_context.py','test_cut_out_max_game.py','test_cut_out_triple_max.py']
    for target in targets:
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture','pattern',target],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-start)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/candidate-context-focused-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,focused_patterns=targets,aggregate_executed=False,overall_seconds=time.monotonic()-start,
        timing_interpretation='correctness and zero-call instrumentation, not a speed comparison')
    Path('benchmarks/player_match_groups/cut-out-candidate-context-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'])),flush=True)

if __name__=='__main__':main()
