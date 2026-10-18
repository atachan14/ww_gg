"""Tiny-support seven comparisons; fresh process <=60s /1.5GB."""
import time,sys,subprocess,json,threading,os,hashlib
from pathlib import Path
from fractions import Fraction as F
from types import SimpleNamespace
from datetime import datetime,timezone
START=time.perf_counter()


def complete_table(graph,forecast,view):
    from werewolf.actor_information import condition_actor_state
    from werewolf.exact import replace_worlds,Values
    from werewolf.player_view import build_public_view,ViewScope,ResultFrame,private_api_rows
    root=graph.origin();law=root.public_state if view is None else condition_actor_state(root.public_state,view.accepts)
    board=replace_worlds(root.public,law.public_roles)
    rows=[{r:board.role_probability(p,r) for r in ('wolf','medium','seer','hunter','villager')} for p in range(1,8)]
    if view is not None:return private_api_rows(rows,targets=dict(forecast.action_values),final_values=dict(forecast.action_values),dawn_for=dict(forecast.by_dawn_values).get)
    roles=SimpleNamespace(probabilities=lambda p:rows[p-1]);primary=Values(forecast.village_win,1-forecast.village_win)
    table=build_public_view(graph.data,roles,board,ResultFrame(ViewScope.public(graph.data),'complete','seven-minimal'),
        state=graph.data.to_game(),event_history=board.history,alive=board.alive,
        action_values={p:Values(v,1-v) for p,v in forecast.action_values},by_dawn_values=dict(forecast.by_dawn_values),manual=True)
    return table,primary,graph.data.roles().progress.total_values(primary)


def independent_terminal_joint(case,state,*,private=False):
    # Known wolf2; actual seer identity has no effect on uniform deaths.
    # Hidden scans are generated on ORIGINAL targets before night deaths.
    from werewolf.seer_acquisition import Hypothesis,Acquisition,normalize
    from werewolf.night_knowledge import WolfAttack
    owners=(1,) if case=='public-disclosed' or private and case=='private-latent' else (1,3,4,5,6,7)
    entries=[]
    for owner in owners:
        variants=[((),F(1,len(owners)))];alive=set(range(1,8));attacks=[]
        for event in state.public.history:
            if event.phase=='night':
                attacks.append(WolfAttack(event.day,event.target))
                if owner in alive:
                    expanded=[]
                    for records,mass in variants:
                        legal=set(range(1,8))-{owner};visited={a.target for a in records}
                        choices=sorted(legal-visited or legal)
                        for target in choices:expanded.append((records+(Acquisition(event.day+1,owner,target,'black' if target==2 else 'white'),),mass/len(choices)))
                    variants=expanded
            alive.discard(event.target)
        for records,mass in variants:
            if all(Acquisition(r.acquired_day,r.player,r.target,r.color) in records for r in state.past):
                entries.append(Hypothesis((2,0,1<<(owner-1),0),records,mass,(),tuple(attacks)))
    return normalize(entries)


def independent_path_mass(state):
    mass=F(1);alive=7
    for event in state.public.history:
        mass/=alive if event.phase=='day' else alive-1
        alive-=1
    for report in state.past:
        assert report.player==1 and report.published_day==report.acquired_day and report.acquired_day in (2,3)
        mass/=6 if report.acquired_day==2 else 5
    return mass


def common_path_mass(request):
    from werewolf.board_future import ActionEvidence,PublicationEvidence,publication_key,evidence_reconstruction
    state=request.origin();mass=F(1)
    with evidence_reconstruction():
        for operation in request.history:
            if isinstance(operation,ActionEvidence):
                if state.public.phase=='day':mass/=len(state.public.alive)
                else:
                    attacks=state.public_state.hypotheses[0].attacks
                    mass*=dict(operation.engine.wolf_policy(state.public,state.public_state,state.past,2,attacks))[operation.target]
            elif isinstance(operation,PublicationEvidence):
                branches=operation.engine.push(state.public_state,state.private,operation.engine.morning(state.public,state.public_state,state.past))
                matches=[q for q,b,s,p,own in branches if publication_key(b,p)==operation.observation]
                assert len(matches)==1
                mass*=matches[0]
            state=operation(state)
    return mass


def audit(case):
    from .cut_out_seven_minimal import graph
    from .cut_out_uniform_game import evaluate,OwnView
    from .cut_out_two_nights import restore_terminals
    from .cut_out_day_night import moved_law,moved_board
    from .partitioned_match_groups import UnsupportedPartition
    from werewolf.board_future import same_role_board,SavedOrigin
    from unittest.mock import patch
    started=time.perf_counter();source=graph(latent=case!='public-disclosed');setup_seconds=time.perf_counter()-started
    view=OwnView(1,'seer') if case=='private-latent' else None
    original=source.data.inputs;root=source.origin()
    assert len(root.public_state.hypotheses)==(1 if case=='public-disclosed' else 6)
    with (patch('werewolf.exact_renaming.canonical_key',side_effect=AssertionError('old permutation search')),
          patch('werewolf.board_roles.prepare_evaluation',side_effect=AssertionError('child prior rebuild'))):
        actual=evaluate(source,view=view,capture_terminal=True)
        if isinstance(actual,UnsupportedPartition):raise RuntimeError('grouped scope/budget: '+actual.reason)
        forecast,grouped=actual
        expected=evaluate(source,view=view,official_reference=True,capture_terminal=True)
        if isinstance(expected,UnsupportedPartition):raise RuntimeError('official scope/budget: '+expected.reason)
        reference,full=expected
        assert forecast==reference
        start=time.perf_counter();small,small_restore=restore_terminals(grouped,max_publication_day=3)
        complete,full_restore=restore_terminals(full,max_publication_day=3);restore_seconds=time.perf_counter()-start
    assert complete_table(source,forecast,view)==complete_table(source,reference,view)
    # Independent uniform W1 recurrence: a known wolf label2 wins immediately;
    # any other first execution leaves a uniform five-player day after night.
    assert forecast.village_win==F(19,35)
    assert dict(forecast.action_values)=={p:F(1) if p==2 else F(7,15) for p in range(1,8)}
    assert all(v.village_win==int(p==2) and v.wolf_win==0 for p,v in forecast.by_dawn_values)
    checks=0
    for b,s,past,own,observer,physical,target in grouped.scalar_actions:
        for group in grouped.groups(b,past,own):
            for other in group[1:]:
                changed=moved_law(s,group[0],other,7);private=moved_law(own,group[0],other,7)
                assert changed==s and private==own
                assert same_role_board(moved_board(b,changed,group[0],other),b)
                assert same_role_board(moved_board(physical,private,group[0],other),physical)
                checks+=1
    unique={}
    for _,state,request in complete.values():
        identity=(state.public.history,state.past)
        assert identity not in unique
        unique[identity]=(independent_path_mass(state),state.public.winner)
    assert sum((q for q,w in unique.values()),F())==1
    assert sum((q for q,w in unique.values() if w=='village'),F())==F(19,35)
    if case!='public-disclosed':assert len(unique)==1+30+360+720
    third_day=two_nights=scan3=0
    for key,(q,state,request) in small.items():
        old_q,old,_=complete[key]
        assert q==old_q and state.public_state==old.public_state and state.private==old.private and state.past==old.past
        assert state.public_state.hypotheses==independent_terminal_joint(case,state)
        assert state.private.hypotheses==independent_terminal_joint(case,state,private=True)
        assert common_path_mass(request)==independent_path_mass(state)
        assert state.observer==old.observer and same_role_board(state.public,old.public) and same_role_board(state.physical,old.physical)
        assert type(request.origin) is SavedOrigin and request.origin is source.origin
        third_day+=state.public.day==3
        two_nights+=sum(e.phase=='night' for e in state.public.history)==2
        scan3+=any(a.day==3 for h in state.private.hypotheses for a in h.acquisitions)
    assert third_day and two_nights and scan3
    assert source.data.inputs==original and grouped.costs['saved_origins']==full.costs['saved_origins']==1
    return dict(case=case,initial_public_hypotheses=len(root.public_state.hypotheses),initial_private_hypotheses=1 if view else len(root.private.hypotheses),
        village_win=str(forecast.village_win),complete_table_joint_history_branch_mass_equal=True,independent_win_action_horizon_equal=True,independent_terminal_joint_equal=True,unconditional_labelled_terminal_mass_sum='1',unconditional_village_terminal_mass='19/35',
        setup_seconds=setup_seconds,grouped=dict(grouped.costs),full_labelled=dict(full.costs),grouped_terminal_restore=small_restore,full_terminal_restore=full_restore,
        all_label_restore_comparison_seconds=restore_seconds,third_day_terminals=third_day,two_night_terminals=two_nights,slot3_terminal_witnesses=scan3,
        group_swap_audits_in_tests_only=checks,worker_setup_eval_restore_verify_seconds=time.perf_counter()-started,
        private_table_semantics='conditional uniform execution table, not an ability/scan-choice intervention table' if view else 'public current complete display')


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    def watch():
        while True:
            if peak_bytes()>1_500_000_000:print('1.5GB limit exceeded',file=sys.stderr,flush=True);os._exit(137)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result=audit(case);result.update(peak_working_set_bytes=peak_bytes(),startup_and_work_seconds=time.perf_counter()-START)
    print(json.dumps(result),flush=True)


def regressions(result,started):
    # Re-run the exact existing40 targets; do not rewrite their expectations.
    previous=json.loads(Path('benchmarks/player_match_groups/withdraw-standard-results.json').read_text(encoding='utf-8'))
    requests=[(c['kind'],c['target']) for c in previous['checks']]+[('pattern','test_cut_out_seven_minimal.py')]
    logs=[];checks=[]
    for kind,target in requests:
        remaining=300-(time.monotonic()-started)
        if remaining<=0:raise SystemExit('overall300s budget exhausted')
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture',kind,target],capture_output=True,text=True,timeout=min(30,remaining))
        logs.append(run.stdout+run.stderr)
        if run.returncode:print(logs[-1]);raise SystemExit(run.returncode)
        checks.append(dict(kind=kind,target=target,exit=run.returncode))
    Path('.artifacts/seven-minimal-regressions-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result['regression_tests']=42;result['existing40_targets_preserved']=True;result['regression_checks']=checks
    result['overall_wall_seconds']=time.monotonic()-started
    result['source_sha256']['tests/test_cut_out_seven_minimal.py']=hashlib.sha256(Path('tests/test_cut_out_seven_minimal.py').read_bytes()).hexdigest()
    result['source_sha256']['benchmarks/player_match_groups/cut_out_seven_minimal_fixture.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    Path('benchmarks/player_match_groups/cut-out-seven-minimal-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('42 regressions passed',flush=True)


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--regressions-only':
        result=json.loads(Path('benchmarks/player_match_groups/cut-out-seven-minimal-results.json').read_text(encoding='utf-8'))
        return regressions(result,time.monotonic())
    if len(sys.argv)>1:return worker(sys.argv[1])
    start=time.monotonic();rows=[]
    for case in ('public-disclosed','public-latent','private-latent'):
        remaining=300-(time.monotonic()-start)
        if remaining<=0:raise SystemExit('overall300s budget exhausted')
        stamp=time.perf_counter();run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,remaining))
        if run.returncode:print(case,run.stdout+run.stderr);raise SystemExit(run.returncode)
        row=json.loads(run.stdout);row['fresh_process_seconds']=time.perf_counter()-stamp;rows.append(row)
        print(case,round(row['fresh_process_seconds'],3),round(row['grouped']['total_seconds'],3),round(row['full_labelled']['total_seconds'],3),flush=True)
    paths=('benchmarks/player_match_groups/cut_out_model_a.py','benchmarks/player_match_groups/cut_out_seven_minimal.py','benchmarks/player_match_groups/cut_out_seven_minimal_fixture.py','benchmarks/player_match_groups/cut_out_two_nights.py')
    result=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),head_before_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),cases=rows,
        wall_seconds=time.monotonic()-start,per_process_limit_seconds=60,overall_limit_seconds=300,memory_limit_bytes=1_500_000_000,
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},normal_ui_connected=False,
        unsupported=['unrestricted seven-player initial support','seven initial random-white','seven input-correction registry','max','hunter','ability-choice private table'])
    Path('benchmarks/player_match_groups/cut-out-seven-minimal-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    regressions(result,start)

if __name__=='__main__':main()
