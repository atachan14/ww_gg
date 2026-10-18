"""Finite latent day-max tests; no invented CO or private scan optimizer."""
import json,time,sys,subprocess,threading,os
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
from .cut_out_latent_max import graph,evaluate
from .cut_out_uniform_game import OwnView
from .cut_out_max_fixture import complete_table
from .partitioned_match_groups import UnsupportedPartition
from werewolf.seer_acquisition import Hypothesis,Acquisition,normalize


def independent_initial(n,mediums,initial):
    entries=[]
    for w in range(1,n+1):
        for s in range(1,n+1):
            if s==w:continue
            for group in combinations([p for p in range(1,n+1) if p not in (w,s)],mediums):
                targets=[p for p in range(1,n+1) if p not in (w,s)] if initial=='random_white' else [None]
                for t in targets:
                    roles=(1<<(w-1),sum(1<<(p-1) for p in group),1<<(s-1),0)
                    entries.append(Hypothesis(roles,() if t is None else (Acquisition(1,s,t,'white'),),F(1)))
    return normalize(entries)


def independent_terminal(initial,state,view=None,wolf_mask=None):
    from werewolf.night_knowledge import WolfAttack
    rows=[h for h in initial if (view is None or view.accepts(h)) and (wolf_mask is None or h.roles[0]==wolf_mask)]
    alive=set(range(1,state.public.player_count+1));history=state.public.history
    for i,event in enumerate(history):
        expanded=[]
        if event.phase=='night':
            for h in rows:
                if h.roles[0]&(1<<(event.target-1)):continue
                owner=next(p for p in range(1,state.public.player_count+1) if h.roles[2]&(1<<(p-1)))
                targets=sorted(set(range(1,state.public.player_count+1))-{owner})
                unvisited=[p for p in targets if p not in {a.target for a in h.acquisitions}]
                choices=(unvisited or targets) if owner in alive else [None]
                for target in choices:
                    records=h.acquisitions if target is None else h.acquisitions+(Acquisition(event.day+1,owner,target,'black' if h.roles[0]&(1<<(target-1)) else 'white'),)
                    expanded.append(Hypothesis(h.roles,records,h.mass/(len(alive)-1)/len(choices),(),h.attacks+(WolfAttack(event.day,event.target),)))
        else:
            expanded=[Hypothesis(h.roles,h.acquisitions,h.mass/len(alive),h.guards,h.attacks) for h in rows]
        alive.remove(event.target);rows=[]
        for h in expanded:
            wolf_alive=any(h.roles[0]&(1<<(p-1)) for p in alive)
            winner='village' if not wolf_alive else 'wolf' if len(alive)<=2 else None
            if winner==(state.public.winner if i==len(history)-1 else None):rows.append(h)
    return normalize(rows)


def audit(n=5,mediums=1,initial='random_white',kind='public',medium_co=False,_terminal_night_max=False):
    from .cut_out_two_nights import restore_terminals
    from werewolf.board_future import same_role_board
    from werewolf.information_set_forecast import optimal_targets
    start=time.perf_counter()
    if _terminal_night_max:
        if n!=4 or medium_co:raise ValueError('terminal-night comparison is four-player all-latent only')
        from .cut_out_terminal_night_max import graph as build,evaluate as calculate
        source=build(mediums,initial)
    else:source=graph(n,mediums,initial,medium_co);calculate=evaluate
    root=source.origin()
    owner=2 if medium_co else 1
    view=None if kind=='public' else OwnView(owner,'seer',() if kind=='role' else (Acquisition(1,owner,3,'white'),))
    independent=independent_initial(n,mediums,initial)
    if medium_co:independent=normalize(h for h in independent if h.roles[1]==1)
    assert root.public_state.hypotheses==independent
    actual=calculate(source,view=view,capture_terminal=True);expected=calculate(source,view=view,official_reference=True,capture_terminal=True)
    if isinstance(actual,UnsupportedPartition) or isinstance(expected,UnsupportedPartition):raise AssertionError((actual,expected))
    forecast,engine=actual;reference,full=expected
    assert forecast==reference and complete_table(source,forecast,view)==complete_table(source,reference,view)
    value=(F(1,3) if n==4 else F(7,12)) if medium_co else F(1,4) if n==4 else F(7,15)
    assert forecast.village_win==value
    policy=optimal_targets(engine.day_scores(root.public,root.public_state,root.past),maximize=True)
    assert tuple(policy)==(root.public.alive[1:] if medium_co else root.public.alive)
    if view is None:
        assert dict(forecast.action_values)=={p:(F(0) if n==4 else F(1,3)) if medium_co and p==1 else value for p in root.public.alive}
    if kind=='white' and not medium_co:
        assert dict(forecast.action_values)=={p:(F(0) if n==4 else F(1,3)) if p in (1,3) else F(1,2) if n==4 else F(5,9) for p in root.public.alive}
        assert max(v for p,v in forecast.action_values)>value
    for key,v in engine.scalar_actions.items():
        b,s,past,own,observer,physical,target=key
        assert v==full.act(b,s,past,target,own,observer,physical=physical)
    small,_=restore_terminals(engine);large,_=restore_terminals(full)
    for key,(q,state,request) in small.items():
        old_q,old,_=large[key]
        assert q==old_q and state.public_state==old.public_state and state.private==old.private and state.past==old.past
        assert same_role_board(state.public,old.public) and same_role_board(state.physical,old.physical)
        assert request.origin is source.origin
        assert state.public_state.hypotheses==independent_terminal(independent,state)
        masks={h.roles[0] for h in key[1].private.hypotheses}
        mask=next(iter(masks)) if len(masks)==1 else None
        assert state.private.hypotheses==independent_terminal(independent,state,view if key[1].observer==view else None,mask)
    scan_targets=[];scan_private_contexts=scan_public_alternatives=scan_group_swaps=0
    if kind=='white':
        if _terminal_night_max:from .cut_out_terminal_night_max import scan_values
        else:from .cut_out_latent_max import scan_values
        from werewolf.player_view import private_api_rows
        scans,scan_engine=scan_values(source,view)
        labelled_scans,labelled_engine=scan_values(source,view,official_reference=True)
        assert scans==labelled_scans
        from werewolf.seer_intervention import SeerObserver
        from .cut_out_day_night import moved_law,moved_board
        for key in scan_engine.scalar_actions:
            b,s,past,own,observer,physical,target=key
            for group in scan_engine.groups(b,past,own,observer):
                for other in group[1:]:
                    assert moved_law(s,group[0],other,n)==s
                    assert moved_law(own,group[0],other,n)==own
                    assert same_role_board(moved_board(physical,own,group[0],other),physical)
                    scan_group_swaps+=1
        reference_branches=set(labelled_engine.branch_records)
        for record in scan_engine.branch_records:
            assert record in reference_branches
            assert sum((q for q,b in record[-1]),F())==1
        for context in scan_engine.projected:
            observer=context.observer
            if not isinstance(observer,SeerObserver):continue
            assert all(observer(h,context.private) for h in context.private.hypotheses)
            if len(context.private.rosters)>1 and owner in context.private.rosters[1]:
                scan_private_contexts+=1
                scan_public_alternatives+=any(h.roles[2]&(1<<(owner-1)) and any(a.player==owner and a.day==2 and a.target!=observer.target for a in h.acquisitions) for h in context.public_state.hypotheses)
        if n==5:assert scan_private_contexts and scan_public_alternatives
        assert all(request.origin is source.origin for request in scan_engine.board_sources.values())
        assert all(v==value for target,v in scans)
        scan_targets=[p for p,v in scans]
        assert scan_targets==[p for p in root.public.alive if p not in (owner,3)]
        from werewolf.actor_information import condition_actor_state
        from werewolf.exact import replace_worlds
        own_board=replace_worlds(root.public,condition_actor_state(root.public_state,view.accepts).public_roles)
        rows=[{r:own_board.role_probability(p,r) for r in ('wolf','medium','seer','hunter','villager')} for p in root.public.alive]
        assert private_api_rows(rows,targets=dict(scans),final_values=dict(scans))==private_api_rows(rows,targets=dict(labelled_scans),final_values=dict(labelled_scans))
    from werewolf.board_future import reconstruction_kernel_reuse
    with reconstruction_kernel_reuse(False):
        rebuilt=source.origin()
        assert rebuilt==root
    assert source.data.inputs==source.origin.board_data.inputs
    # A fixed latent scan policy cannot change public choices without a report.
    # Do not optimize it under the unrelated public day-max setting.
    owned=sum(1 for h in independent if view is not None and view.accepts(h))
    return dict(players=n,mediums=mediums,initial=initial,view=kind,medium_co=medium_co,initial_hypotheses=len(independent),own_initial_hypotheses=owned,
        village_win=str(value),public_policy=list(policy),complete_table_action_joint_physical_history_branch_equal=True,
        independently_generated_initial_and_terminal_joint_equal=True,terminal_readbacks=len(small),
        scalar_context_comparisons=len(engine.scalar_actions),own_scan_targets=scan_targets,private_intervention_contexts=scan_private_contexts,public_unforced_scan_contexts=scan_public_alternatives,own_scan_group_swap_audits=scan_group_swaps,grouped=dict(engine.costs),labelled=dict(full.costs),seconds=time.perf_counter()-start)


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    worker_started=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-worker_started>60:os._exit(124)
            if peak_bytes()>1_500_000_000:os._exit(137)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result=audit(*json.loads(case));result['peak_working_set_bytes']=peak_bytes();print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    started=time.monotonic();rows=[];logs=[]
    cases=[(4,0,'none','public'),(4,1,'random_white','white'),(5,0,'none','public'),(5,1,'random_white','public'),(5,1,'random_white','role'),(5,1,'random_white','white'),(5,1,'random_white','public',True),(5,1,'random_white','white',True)]
    for case in cases:
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,json.dumps(case)],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+str(case),flush=True)
    previous=json.loads(Path('benchmarks/player_match_groups/withdraw-standard-results.json').read_text(encoding='utf-8'))
    checks=[(c['kind'],c['target']) for c in previous['checks']]+[('pattern','test_cut_out_seven_minimal.py'),('pattern','test_cut_out_max_game.py'),('pattern','test_cut_out_latent_max.py')]
    for kind,target in checks:
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture',kind,target],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/latent-max-regressions-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,regression_checks=checks,existing44_preserved=True,regression_tests=47,overall_seconds=time.monotonic()-started)
    Path('benchmarks/player_match_groups/cut-out-latent-max-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'],checks=len(checks))),flush=True)

if __name__=='__main__':main()
