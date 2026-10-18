"""Finite recursive witness checks, with legacy matching forbidden globally."""
import json,sys,time,subprocess,threading,os
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
from .cut_out_candidate_context_fixture import zero_legacy
from .cut_out_day_night import point_fix,moved_law
from .cut_out_uniform_game import CutOutUniformEngine,OwnView
from .cut_out_inherited_groups import InheritedGroupRegistry


def old_group_oracle(root,b,past,private,observer,view):
    from werewolf.seer_intervention import SeerObserver
    fixed={e.target for e in b.history}
    fixed.update(x for r in past for x in (r.player,r.target))
    fixed.update(x for r in b.reports for x in (r.reporter,r.target))
    if view is not None:
        fixed.add(view.player)
        fixed.update(x for a in view.acquisitions for x in (a.player,a.target))
    masks={h.roles[0] for h in private.hypotheses}
    if len(masks)==1:fixed.update(p for p in range(1,b.player_count+1) if next(iter(masks))&(1<<(p-1)))
    if isinstance(observer,SeerObserver):
        fixed.update((observer.actor,observer.target))
        fixed.update(x for a in observer.acquisitions for x in (a.player,a.target))
    return point_fix(root,*sorted(fixed))


def boundary_checks():
    from dataclasses import replace
    from .cut_out_active_report_max import graph,ActiveReportMaxEngine
    from werewolf.information_set_forecast import Pending
    source=graph();engine=ActiveReportMaxEngine(source);root=source.origin();b,s,past=root[:3]
    changed=replace(b,claims=('latent',)*b.player_count)
    try:engine.record_group_publication(b,s,past,changed,s,past,'unconfigured-CO')
    except Pending as error:assert error.reason=='inherited_publication_or_CO_transition_unproved'
    else:raise AssertionError('unconfigured CO accepted')
    try:engine.inherited_groups.require(changed,s,past)
    except Pending:pass
    else:raise AssertionError('unknown source accepted')
    try:engine.groups(b,past,s,lambda h,s:True,public_state=s)
    except Pending as error:assert error.reason=='inherited_private_observer_unproved'
    else:raise AssertionError('unproved private evidence accepted')
    try:engine.groups(b,past,s,OwnView(3,'seer'),public_state=s)
    except Pending as error:assert error.reason=='inherited_private_observer_unproved'
    else:raise AssertionError('unbound own view accepted')
    return dict(unconfigured_CO_refused=True,missing_context_refused=True,unknown_private_observer_refused=True)


def audit(case):
    registries=[];requests=[];deferred=[]
    from . import cut_out_candidate_context_fixture as candidate_fixture
    candidate_oracle=candidate_fixture.compare_candidate_inputs
    def defer(source,engine):
        deferred.append((source,engine));return dict(deferred_explicit_oracle=True)
    old_init=InheritedGroupRegistry.__init__;old_groups=CutOutUniformEngine.inherited_value_groups
    def init(self,graph):
        old_init(self,graph);registries.append(self)
    def groups(self,b,past,private,observer,public_state):
        result=old_groups(self,b,past,private,observer,public_state)
        requests.append((self.inherited_groups,b,past,private,observer,self.view,result))
        return result
    stack,mocks=zero_legacy()
    with stack,ExitStack() as hooks:
        hooks.enter_context(patch.object(candidate_fixture,'compare_candidate_inputs',defer))
        hooks.enter_context(patch.object(InheritedGroupRegistry,'__init__',init))
        hooks.enter_context(patch.object(CutOutUniformEngine,'inherited_value_groups',groups))
        old_root=hooks.enter_context(patch.object(CutOutUniformEngine,'legacy_large_groups',side_effect=AssertionError('root rebuild in recursive child')))
        if case in ('active4','active5','basic5','white5'):
            from .cut_out_candidate_context_fixture import audit as existing
            result=existing(case)
        elif case=='seer5':
            from .cut_out_max_fixture import audit as existing
            result=existing(5,1,'max')
        elif case=='uniform4':
            sys.path.insert(0,str(Path('tests').resolve()))
            from test_cut_out_uniform_game import audit as existing
            from test_cut_out_model_a import cases
            forecast,grouped,full=existing(cases(4)['single'])
            result=dict(village_win=str(forecast.village_win),complete_table_joint_branch_mass_equal=True)
        else:raise ValueError(case)
        boundaries=boundary_checks()
        assert all(m.call_count==0 for m in mocks) and old_root.call_count==0
    # Independent correctness oracles run only AFTER the guarded actual flow.
    contexts=0;recursive=0;swaps=0;events={};max_depth=0
    for registry in registries:
        for context in registry.contexts.values():
            contexts+=1;max_depth=max(max_depth,context.depth)
            events[context.event]=events.get(context.event,0)+1
            if context.parent is not None:
                recursive+=1
                assert context.groups==point_fix(context.parent.groups,*context.new_fixed)
                assert context.depth==context.parent.depth+1
            for block in context.groups:
                for target in block[1:]:
                    assert moved_law(context.state,block[0],target,context.board.player_count)==context.state
                    swaps+=1
    for registry,b,past,private,observer,view,actual in requests:
        root=next(c for c in registry.contexts.values() if c.parent is None)
        expected=old_group_oracle(root.groups,b,past,private,observer,view)
        assert sorted(actual)==sorted(expected),(b.history,actual,expected)
    candidate_oracles=[candidate_oracle(source,engine) for source,engine in deferred]
    assert recursive and requests
    return dict(case=case,case_result=result,registry_count=len(registries),contexts=contexts,
        recursive_contexts=recursive,max_depth=max_depth,event_counts=events,
        full_public_law_invariance_swaps=swaps,private_groups_equal_old_root_oracle=len(requests),
        canonical_calls_all_recursive_children=0,legacy_candidate_constructors_all_children=0,
        legacy_root_rebuilds_all_children=0,boundaries=boundaries,candidate_oracles=candidate_oracles)


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
    for case in ('uniform4','seer5','active4','active5','basic5','white5'):
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-start)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+case,flush=True)
    for target in ('test_cut_out_inherited_groups.py','test_cut_out_max_game.py','test_cut_out_triple_max.py'):
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture','pattern',target],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-start)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/inherited-groups-focused-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,overall_seconds=time.monotonic()-start,aggregate_executed=False,
        timing_interpretation='finite correctness checkpoint only; no heavy speed measurement')
    Path('benchmarks/player_match_groups/cut-out-inherited-groups-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'])),flush=True)

if __name__=='__main__':main()
