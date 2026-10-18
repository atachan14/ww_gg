"""Local multi-day stop reproduction; never evaluates an initial value."""
import json
from pathlib import Path
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
from .cut_out_initial_publications import base,scope,InitialPublicationEngine,clean
from .cut_out_structural_publications import produce,restore
from .cut_out_live_medium_forecast import cold
from werewolf.board_future import (ActionEvidence,PublicationEvidence,PublicReportEvidence,
    kernel_snapshot,outcome_key,publication_key,condition_recipe,calculation_origin,remember)
from werewolf.evaluation_branch import physical_board
from werewolf.actor_information import condition_actor_state
from werewolf.seer_acquisition import SeerReport
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.calculation_budget import calculation_budget


def reproduce():
    saved=json.loads(Path('benchmarks/player_match_groups/initial-publications-new-trial.json').read_text())['first_refusal']
    graph,w=base();root=scope(graph,w);engine=InitialPublicationEngine(graph,witness=w)
    def forbidden(*args,**kwargs):raise AssertionError('local fixture must not solve/act')
    engine.solve=engine.act=forbidden
    request=graph.root;source=root
    def action(target):
        nonlocal request,source
        outcomes=engine.physical_children(source.physical,target)
        outcome=next(o for o in outcomes if o.board.winner is None)
        request=request.child(ActionEvidence(kernel_snapshot(engine),target,outcome_key(outcome),False),None)
        source=request.roles();remember(engine,request,source)
    with calculation_origin(graph.data):
        remember(engine,request,source)
        action(3)
        private=condition_actor_state(source.private,lambda h:h.roles[0]==17)
        selected=replace(source,private=private,physical=physical_board(source.public,private,source.physical))
        request=request.child(condition_recipe(source,selected),None);source=request.roles();remember(engine,request,source)
        action(4)
        desired=tuple(SeerReport(**r) for r in saved['past'])
        row=next(row for row in engine.morning(source.public,source.public_state,source.past) if row[3]==desired)
        request=request.child(PublicationEvidence(kernel_snapshot(engine),publication_key(row[1],row[3])),None);source=request.roles();remember(engine,request,source)
        action(5);action(6)
    assert clean(source.public)==saved['board']
    assert clean(source.public_state)==saved['public_state']
    assert clean(source.past)==saved['past']
    assert clean(source.private)==saved['before_morning']['private']
    return graph,engine,request,source,saved


def audit():
    from time import perf_counter
    start=perf_counter()
    with calculation_budget(4000000,max_seconds=30):
        graph,e,request,source,saved=reproduce()
        assert cold(SimpleNamespace(registry=graph),request)==source
        old=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False)
        old.retain_joint_guard_history=True
        groups=e.inherited_groups.require(source.public,source.public_state,source.past).groups
        assert groups==tuple(tuple(g) for g in saved['groups'])
        patterns=produce(source.public,source.public_state,source.past,groups,fake_policy=e.strategy.fake_seer_policy)
        actual=e.morning(source.public,source.public_state,source.past)
        reference=old.morning(source.public,source.public_state,source.past)
        key=lambda rows:{(b,p):(q,s) for q,b,s,p in rows}
        assert key(actual)==key(reference) and len(actual)==len(key(actual))
        variants={};reads=0
        for mode in ('actual','public','scan','biased'):
            private=source.public_state if mode=='public' else source.private
            if mode=='scan':private=condition_actor_state(private,lambda h:h.acquisitions==private.hypotheses[0].acquisitions)
            if mode=='biased':
                from werewolf.seer_acquisition import normalize
                private=replace(private,hypotheses=normalize(tuple(replace(h,mass=h.mass*(3 if h.acquisitions[-1].target==3 else 1)) for h in private.hypotheses)))
            view=replace(source,private=private,physical=physical_board(source.public,private,source.physical))
            recipe=condition_recipe(source,view)
            parent=request if view==source else (request.child(recipe,None) if recipe is not None else None)
            weighted=e.push(source.public_state,private,actual);expected=old.push(source.public_state,private,reference)
            own=lambda rows:{(b,p):(q,s,ps) for q,b,s,p,ps in rows}
            assert own(weighted)==own(expected)
            supported={publication_key(b,p) for q,b,s,p,ps in weighted}
            for q,b,s,p in actual if parent is not None else ():
                op=PublicationEvidence if publication_key(b,p) in supported else PublicReportEvidence
                child=parent.child(op(kernel_snapshot(e),publication_key(b,p)),None)
                assert cold(SimpleNamespace(registry=graph),child)==child.roles();reads+=1
            variants[mode]=dict(positive_P=len(weighted),zero_P=len(actual)-len(weighted),initial_origin_cold=parent is not None)
        assert all(p.reporter_factor==1 for p in patterns)
        return dict(status='verified',scope='local_day3_separate_reporter_product',history=clean(source.public.history),
            groups=groups,patterns=len(patterns),named_vectors=len(actual),variants=variants,
            initial_value_search=False,independent_initial_origin_cold_reads=reads+1,
            full_QP_legal_reports_equal=True,seconds=perf_counter()-start)


def worker():
    import os,time,threading
    from .cut_out_uniform_game_fixture import peak_bytes
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    result=audit();result['peak_working_set_bytes']=peak_bytes()
    Path('benchmarks/player_match_groups/separate-publications-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__':worker()
