"""Finite root-boundary counting, full labelled readback and independent cold."""
import sys,os,time,json,threading
from pathlib import Path
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
from .cut_out_publication_orbit_value import *
from .cut_out_publication_orbit_value import _scopes
from .cut_out_uniform_game_fixture import peak_bytes
from .cut_out_compact_terminal import CompactTerminalSmallEngine
from .cut_out_model_a import adapt_model_a
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_structural_publications_fixture import build,condition_request
from .cut_out_live_medium_forecast import cold as seven_cold
from .cut_out_compact_terminal_fixture import independent_cold
from .cut_out_deferred_alternating import fingerprint_rows
from werewolf.actor_information import condition_actor_state
from werewolf.board_future import ActionEvidence,outcome_key,calculation_origin
from werewolf.player_view import private_api_rows
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,budget_stop
from werewolf.joint_value_sharing import independent_joint_values


def make_scope(case):
    if case=='five':
        sys.path.insert(0,str(Path('tests').resolve()))
        from test_cut_out_model_a import cases
        graph=SavedCutOutGraph(adapt_model_a(cases()['same_reports']));e=CompactTerminalSmallEngine(graph)
        request=graph.root;source=graph.origin()
        for target in (3,4):
            out=next(o for o in e.physical_children(source.physical,target) if o.board.winner is None)
            request=request.child(ActionEvidence(kernel_snapshot(e),target,outcome_key(out),False),None);source=request.roles()
        return issue_scope(graph,e,request,source),lambda req:independent_cold(graph,req)
    prefix=build(3,4);source=prefix.source;request=prefix.request
    if case in ('roster','asymmetric-scan'):
        seed=next(h for h in source.private.hypotheses if h.roles[0]==17 and (case=='roster' or h.acquisitions[-1].target==6))
        private=condition_actor_state(source.private,lambda h:h.roles==seed.roles and (case=='roster' or h.acquisitions==seed.acquisitions))
        source=replace(source,private=private,physical=physical_board(source.public,private,source.physical));request=condition_request(prefix,source)
    if case=='observer':
        obs=SeerObserver(2,(),2,6)
        private=condition_actor_state(source.private,lambda h:obs(h,source.private))
        source=replace(source,private=private,observer=obs,physical=physical_board(source.public,private,source.physical));request=condition_request(prefix,source)
    return issue_scope(prefix.registry,prefix.engine,request,source),lambda req:seven_cold(prefix,req)


def forecast(engine,source):
    value=engine.solve(*source,physical=source.physical)
    actions=tuple((p,engine.act(*source[:3],p,source.private,source.observer,physical=source.physical)) for p in source.public.alive)
    dawn=tuple((p,horizon_for_action(engine,source.public,source.public_state,source.past,p,source.private,observer=source.observer)) for p in source.public.alive)
    return Forecast(value,actions,dawn)


def tables(source,result):
    role_names=('wolf','medium','seer','hunter','villager');rows=[]
    for board in (source.public,source.physical):
        roles=[{r:board.role_probability(p,r) for r in role_names} for p in range(1,board.player_count+1)]
        rows.append(private_api_rows(roles,targets=dict(result.action_values),final_values=dict(result.action_values),dawn_for=dict(result.by_dawn_values).get))
    return tuple(rows)


def audit(case):
    scope,cold=make_scope(case);src=scope.source
    with calculation_origin(scope.graph.data):
        before=time.perf_counter();baseline,old,public,weighted,children=named_value(scope);baseline_seconds=time.perf_counter()-before
        before=time.perf_counter();plan=PublicationOrbitValue(scope);value=plan.value();orbit_seconds=time.perf_counter()-before
        assert value==baseline
        assert plan.label_restorations==0 and plan.engine.audit['root_named_Boards']==0
        value_counts=dict(named_root_Boards=old.audit['root_named_Boards'],representative_root_Boards=plan.representative_Boards,
            named_positive_P_solve_roots=len(weighted),representative_positive_P_solve_roots=len(plan.representatives),
            named_solve_requests=old.audit['solve_requests'],orbit_solve_requests=plan.engine.audit['solve_requests'],
            named_actions=len(old.scalar_actions),orbit_actions=len(plan.engine.scalar_actions),named_value_states=len(old.values),orbit_value_states=len(plan.engine.values),
            named_future_Boards=old.audit['future_named_Boards'],orbit_future_Boards=plan.engine.audit['future_named_Boards'])
        by_label={publication_key(child.public,child.past):(mass,child) for mass,child in children}
        q_by_label={publication_key(b,past):q for q,b,s,past in public}
        restored={};reads=0;table_checks=0
        # Label Boards are first created here, only for requested Table/Tree
        # readback. No additional nonrepresentative solve occurs on plan.engine.
        start_solves=plan.engine.audit['solve_requests']
        for rep in plan.representatives:
            for mapping in mappings(rep.pattern,src.public.player_count):
                q,p_mass,child,result,request=plan.labelled(rep,mapping)
                key=publication_key(child.public,child.past);mass,expected=by_label[key]
                assert q==q_by_label[key] and p_mass==mass and child==expected
                assert key not in restored;restored[key]=child
                expected_forecast=forecast(old,expected)
                assert result==expected_forecast and tables(child,result)==tables(expected,expected_forecast);table_checks+=1
                rebuilt=cold(request);assert rebuilt==child;reads+=1
        assert len(restored)==len(weighted)
        # Forecast calls for representatives are lazy inspection work. The plan
        # never solves each transported label; cached representative forecasts
        # and exact target-index transport serve all labels.
        return dict(status='verified',case=case,village_win=str(value),public_groups=scope.groups,private_stabilizer=plan.groups,split_groups=plan.private_splits,
            q_patterns=len(plan.patterns),q_named_vectors=plan.named_Q_vectors,p_zero_patterns=plan.p_zero_patterns,
            value_only=value_counts,value_only_named_restorations=0,value_only_root_named_Boards=0,
            baseline_value_seconds=baseline_seconds,orbit_value_seconds=orbit_seconds,
            requested_label_restorations=plan.label_restorations,full_label_Forecast_QP_Table_checks=table_checks,independent_saved_origin_cold_reads=reads,
            full_QP_mass_and_forecast_equal=True,future_publication_backup='ordinary independent labelled recursion; prototype compresses ONE boundary only',
            full_initial7_search=False)


def worker(case):
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    try:
        with calculation_budget(4000000,max_seconds=30),independent_joint_values():row=audit(case)
    except CalculationBudgetExceeded:row=dict(status='unverified',case=case,reason='case_calculation_budget',budget_stop=budget_stop(),full_initial7_search=False)
    row.update(seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    Path('benchmarks/player_match_groups/publication-orbit-value-'+case+'-results.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)

if __name__=='__main__':worker(sys.argv[1] if len(sys.argv)>1 else 'five')
