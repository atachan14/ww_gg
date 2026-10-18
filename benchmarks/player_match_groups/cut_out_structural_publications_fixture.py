"""42 bounded first-morning comparisons and representative Forecast cases."""
from dataclasses import replace
from fractions import Fraction as F
from time import perf_counter
from collections import Counter
from .cut_out_first_cycle_coverage import make_prefix,check,probe_legacy_aggregation
from .cut_out_structural_publications import StructuralPublicationKernel,produce,Pending
from .cut_out_live_medium_forecast import cold,issue_publication_receipt,certificate,evaluate
from werewolf.board_future import (ActionEvidence,PublicationEvidence,PublicReportEvidence,
    publication_key,kernel_snapshot,condition_recipe)
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.evaluation_branch import ContinuationInputs,physical_board
from werewolf.seer_acquisition import normalize
from werewolf.calculation_budget import calculation_budget


def build(executed,victim):
    prefix=make_prefix(executed,victim,kernel_class=StructuralPublicationKernel)
    prefix.engine.bind(prefix);return prefix


def variant(source,mode):
    if mode=='actual':return source
    seed=source.private.hypotheses[0]
    selected=tuple(h for h in source.private.hypotheses if h.roles==seed.roles and
        (mode=='roster' or h.acquisitions==seed.acquisitions))
    own=replace(source.private,hypotheses=normalize(selected))
    return replace(source,private=own,physical=physical_board(source.public,own,source.physical))


def condition_request(prefix,source):
    if source==prefix.source:return prefix.request
    recipe=condition_recipe(prefix.source,source)
    if recipe is None:raise Pending('publication_diagnostic_private_recipe_unproved')
    return prefix.request.child(recipe,None)


def audit(executed,victim):
    start=perf_counter();prefix=build(executed,victim);e=prefix.engine;source=prefix.source
    rebuilt=cold(prefix,prefix.request);assert rebuilt==source
    old=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False)
    old.retain_joint_guard_history=True
    actual=e.morning(source.public,source.public_state,source.past)
    reference=old.morning(rebuilt.public,rebuilt.public_state,rebuilt.past)
    key=lambda rows:{(b,p):(q,s) for q,b,s,p in rows}
    assert len(actual)==len(key(actual)) and key(actual)==key(reference)
    own=lambda rows:{(b,p):(q,s,private) for q,b,s,p,private in rows}
    variants={};cold_reads=0;physical_zero=0
    for mode in ('actual','roster','scan'):
        private_source=variant(source,mode)
        weighted=e.push(source.public_state,private_source.private,actual)
        expected=old.push(rebuilt.public_state,private_source.private,reference)
        assert own(weighted)==own(expected)
        variants[mode]=dict(positive_P=len(weighted),retained_Q=len(actual),zero_P=len(actual)-len(weighted))
        parent=condition_request(prefix,private_source)
        by_observation={publication_key(b,p):(q,b,s,p,private) for q,b,s,p,private in weighted}
        # ALL named actual continuations cold; diagnostic priors additionally
        # sample a supported event and a zero-P public event per history.
        if mode=='actual':selected=tuple(publication_key(b,p) for q,b,s,p in actual)
        else:
            first=next(iter(by_observation));zero=next((publication_key(b,p) for q,b,s,p in actual if publication_key(b,p) not in by_observation),None)
            selected=(first,) if zero is None else (first,zero)
        for observation in selected:
            if observation in by_observation:
                q,b,s,p,private=by_observation[observation]
                request=parent.child(PublicationEvidence(kernel_snapshot(e),observation),None)
                warm=request.roles();assert cold(prefix,request)==warm
                assert warm.public==b and warm.public_state==s and warm.past==p and warm.private==private
            else:
                request=parent.child(PublicReportEvidence(kernel_snapshot(e),observation),None)
                warm=request.roles();assert cold(prefix,request)==warm
                assert warm.private==warm.public_state
                physical_zero+=1
            cold_reads+=1
    counts=tuple(e.pattern_counts.values())
    reporters=len(tuple(p for p in source.public.alive if source.public.claims[p-1]=='seer'))
    return dict(status='verified',executed=executed,victim=victim,reporters=reporters,
        old_supported=probe_legacy_aggregation(prefix)[0] in ('joint-reports','single-reporter'),patterns=sum(n for n,k in counts),named_vectors=len(actual),
        medium_conditioned_laws=len(counts),complete_QP_and_legal_reports_equal=True,variants=variants,
        all_named_actual_cold_reads=variants['actual']['positive_P'],total_independent_cold_reads=cold_reads,
        diagnostic_zero_P_cold_reads=physical_zero,total_comparison_seconds=perf_counter()-start)


def pick_receipt(executed,victim,mode='actual',medium=None):
    prefix=build(executed,victim);e=prefix.engine;source=variant(prefix.source,mode)
    parent=condition_request(prefix,source)
    rows=e.morning(source.public,source.public_state,source.past)
    # Prefer a medium result retaining an ambiguous true owner if possible;
    # selection is an explicit experiment observation, not an action policy.
    if medium is not None:rows=tuple(r for r in rows if any(report.color==medium for report in r[1].reports))
    if not rows:raise Pending('publication_observation_selection_has_no_support')
    row=next((r for r in rows if len(r[2].hypotheses)>1),rows[0])
    q,b,s,p=row;groups=e.publication_groups.require(b,s,p).groups
    return issue_publication_receipt(prefix.registry,prefix.witness,source,parent,e,publication_key(b,p),groups)


def forecast(executed,victim,mode='actual',medium=None):
    from .cut_out_joint_two_nights_fixture import complete_joint_selection,path_mappings
    from .cut_out_joint_night_forecast_fixture import full_readback
    start=perf_counter();receipt=pick_receipt(executed,victim,mode,medium);cap=certificate(receipt,public=receipt.p==0)
    assert cold(cap,cap.request)==cap.source
    actual,e,table=evaluate(cap);reference,old,ref_table=evaluate(cap,reference=True)
    assert actual==reference and table==ref_table
    selection=complete_joint_selection(cap,e,old)
    a=full_readback(cap,e,max_seconds=30,mapping_fn=path_mappings)
    b=full_readback(cap,old,max_seconds=30,mapping_fn=path_mappings)
    assert a['branches']==b['branches'] and a['terminals']==b['terminals']
    return dict(status='verified',executed=executed,victim=victim,mode=mode,medium=medium,Q_mass=str(receipt.q),P_mass=str(receipt.p),
        village_win=str(actual.village_win),full_Forecast_Table_joint_branches_equal=True,
        labelled_branches=len(a['branches']),terminal_transitions=len(a['terminals']),selection_pairs=selection[1],
        independent_cold=True,total_comparison_seconds=perf_counter()-start)


def worker(kind,executed,victim,mode='actual',medium=None):
    import os,time,json,threading
    from .cut_out_uniform_game_fixture import peak_bytes
    start=perf_counter()
    def watch():
        while True:
            if perf_counter()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    with calculation_budget(4000000,max_seconds=30):row=forecast(executed,victim,mode,medium) if kind=='forecast' else audit(executed,victim)
    row['peak_working_set_bytes']=peak_bytes();print(json.dumps(row),flush=True)


def run_all():
    import json,sys,subprocess
    from pathlib import Path
    result=dict(status='running',scope='actual-first-cycle-general-publication-patterns',distributions=[],forecasts=[])
    path=Path('benchmarks/player_match_groups/cut-out-structural-publications-results.json')
    cases=[('distribution',d,v,'actual',None) for d in range(1,8) for v in range(1,8) if d!=v]
    cases.extend(('forecast',d,v,mode,medium) for d,v,mode,medium in (
        (1,3,'actual',None),(2,4,'actual',None),(5,1,'actual',None),
        (5,4,'actual','black'),(5,6,'actual','white'),(4,3,'actual',None)))
    for kind,executed,victim,mode,medium in cases:
        try:
            output=subprocess.run([sys.executable,'-m',__spec__.name,kind,str(executed),str(victim),mode,medium or 'none'],capture_output=True,text=True,timeout=121)
            if output.returncode:raise RuntimeError(output.stderr or output.stdout or 'worker stopped')
            row=json.loads(output.stdout)
        except (subprocess.TimeoutExpired,RuntimeError,json.JSONDecodeError) as error:
            row=dict(status='unverified',executed=executed,victim=victim,reason=str(error))
        result['forecasts' if kind=='forecast' else 'distributions'].append(row)
        path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(kind=kind,**row)),flush=True)
    entries=result['distributions']+result['forecasts']
    result['status']='verified' if all(row['status']=='verified' for row in entries) else 'unverified'
    if result['status']=='verified':
        rows=result['distributions']
        assert len(rows)==42 and sum(r['named_vectors'] for r in rows)==1452
        result.update(nonvacuous_supported=sum(r['reporters']>0 for r in rows),vacuous_no_report=sum(r['reporters']==0 for r in rows),previous_nonvacuous_supported=sum(r['old_supported'] for r in rows),
            pending_first_morning=0,total_patterns=sum(r['patterns'] for r in rows),total_named_vectors=sum(r['named_vectors'] for r in rows),
            all_named_actual_cold_reads=sum(r['all_named_actual_cold_reads'] for r in rows),
            total_independent_cold_reads=sum(r['total_independent_cold_reads'] for r in rows),
            max_distribution_seconds=max(r['total_comparison_seconds'] for r in rows),
            max_forecast_seconds=max(r['total_comparison_seconds'] for r in result['forecasts']),
            max_peak_working_set_bytes=max(r['peak_working_set_bytes'] for r in entries),
            automatic_initial_solver_fast_dispatch=False,full_initial_search=False)
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if result['status']!='verified':raise SystemExit(1)


if __name__=='__main__':
    import sys
    if len(sys.argv)==1:run_all()
    else:worker(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4] if len(sys.argv)>4 else 'actual',sys.argv[5] if len(sys.argv)>5 and sys.argv[5]!='none' else None)