"""Limited live-medium black publication -> Forecast and cold SavedOrigin.

A zero physical mass is an outcome receipt, not a normalized conditional law.
Its Q hypothetical remains evaluable through existing PublicReportEvidence.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from weakref import WeakKeyDictionary
from time import perf_counter
from .cut_out_live_medium_reports import prepublication,single_truth_orbits,restore_reports
from .cut_out_seven_w2_mid import SevenMidEngine,SevenMidReference,JointObservedChoice
from .cut_out_joint_night_forecast import (ForecastCertificate,ExperimentalGraph,
    InformationSetForecast,Pending,point_fix,require,remember,Forecast,horizon_for_action,
    calculation_budget,calculation_origin,physical_board,kernel_snapshot)
from .cut_out_joint_night_forecast import _issued
from werewolf.board_future import (PublicationEvidence,PublicReportEvidence,ConditionEvidence,
    ActionEvidence,publication_key,condition_recipe,GeneratedBoard,SavedOrigin,
    reconstruction_kernel_reuse)
from werewolf.seer_acquisition import normalize

GROUPS=((1,),(2,),(3,),(4,),(5,6,7))
_receipts=WeakKeyDictionary()


class StructuralPublicationKernel(InformationSetForecast):
    def generate_publications(self,b,s,past):
        if b.day==2 and len(b.history)==2 and any(r.reporter==3 and r.target==1 and r.color=='black' for r in b.reports):
            from werewolf.morning_publications import public_report_branches
            orbits=single_truth_orbits(b,s,past,GROUPS)
            return public_report_branches(b,past,restore_reports(orbits))
        return super().generate_publications(b,s,past)


@dataclass(frozen=True,eq=False)
class PublicationReceipt:
    registry:object
    witness:object
    before:object
    observation:tuple
    q:F
    p:F
    public_request:object
    physical_request:object
    public_source:object
    physical_source:object
    groups:tuple


def check(receipt):
    if type(receipt)is not PublicationReceipt or receipt not in _receipts:
        raise Pending('live_medium_publication_receipt_not_issued')
    r,data,revision,fields=_receipts[receipt]
    if r.data is not data or r.data.to_game().get('revision',0)!=revision or tuple(vars(receipt).values())!=fields:
        raise Pending('live_medium_publication_receipt_changed')
    from .cut_out_user_seven_source import require_bound
    require_bound(r,receipt.witness)
    return receipt


def make_case(target=5,color='white',*,restricted=False):
    if (target,color) not in ((1,'black'),(3,'white'),(5,'black'),(5,'white'),(6,'black'),(6,'white'),(7,'black'),(7,'white')):
        raise Pending('live_medium_black_single_scan_vector_scope')
    e,before,_,r,w,request=prepublication(receipt=True,kernel_class=StructuralPublicationKernel)
    if restricted:
        own=replace(before.private,hypotheses=normalize(tuple(h for h in before.private.hypotheses if h.roles[0]==17)))
        changed=replace(before,private=own,physical=physical_board(before.public,own,before.physical))
        recipe=condition_recipe(before,changed)
        if recipe is None:raise Pending('live_medium_private_roster_recipe_unproved')
        request=request.child(recipe,None);before=request.roles()
    rows=e.morning(before.public,before.public_state,before.past)
    physical=e.push(before.public_state,before.private,rows)
    wanted=lambda b,p:any(x.reporter==3 and x.target==1 and x.color=='black' for x in b.reports) and any(x.player==2 and x.acquired_day==2 and (x.target,x.color)==(target,color) for x in p)
    selected=[row for row in rows if wanted(row[1],row[3])]
    if len(selected)!=1:raise Pending('live_medium_public_vector_not_unique')
    q,b,s,past=selected[0];observation=publication_key(b,past)
    selectedP=[row for row in physical if wanted(row[1],row[3])]
    if len(selectedP)>1:raise Pending('live_medium_physical_vector_not_unique')
    p=selectedP[0][0] if selectedP else F()
    public_request=request.child(PublicReportEvidence(kernel_snapshot(e),observation),None)
    public_source=public_request.roles()
    physical_request=request.child(PublicationEvidence(kernel_snapshot(e),observation),None) if p else None
    physical_source=physical_request.roles() if p else None
    if not restricted and physical_source!=public_source:
        raise Pending('live_medium_public_Q_not_equal_actual_conditional_P')
    result=PublicationReceipt(r,w,before,observation,q,p,public_request,physical_request,
        public_source,physical_source,point_fix(GROUPS,target))
    _receipts[result]=(r,r.data,r.data.to_game().get('revision',0),tuple(vars(result).values()))
    return check(result)


def certificate(receipt,*,public=False):
    check(receipt)
    if not public and not receipt.p:
        raise Pending('live_medium_zero_physical_mass_has_no_conditional_P_law_use_public_receipt')
    r=receipt.registry;source=receipt.public_source if public else receipt.physical_source
    request=receipt.public_request if public else receipt.physical_request
    cap=ForecastCertificate(r,receipt.witness,source,request,receipt.groups,0,1,'seven-mid')
    _issued[cap]=(r,r.data,r.engine,r.origin,r.root,r.data.inputs,r.data.to_game().get('revision',0),
        source,request,receipt.groups,repr((r.engine.baseline.rules,r.engine.baseline.strategy)),1,'seven-mid')
    require(cap);return cap


def evaluate(cap,*,reference=False):
    from .cut_out_max_fixture import complete_table
    source=require(cap);graph=ExperimentalGraph(cap)
    engine=SevenMidReference(graph) if reference else SevenMidEngine(graph,cap=cap)
    engine.capture_terminal=True
    if not reference:engine.trusted_requests.add(cap.request)
    with calculation_origin(graph.data):
        remember(engine,cap.request,source)
        value=engine.solve(*source,physical=source.physical)
        actions=tuple((p,engine.act(*source[:3],p,source.private,None,physical=source.physical)) for p in source.public.alive)
        dawn=tuple((p,horizon_for_action(engine,source.public,source.public_state,source.past,p,source.private)) for p in source.public.alive)
        result=Forecast(value,actions,dawn)
        return result,engine,complete_table(graph,result,None)


def cold(cap,request):
    """New ordinary kernel + new SavedOrigin; aggregate generator not used."""
    from .cut_out_seven_w2_mid_fixture import RawObservedChoice
    fresh=InformationSetForecast(cap.registry.engine.baseline.rules,cap.registry.engine.baseline.strategy,
        exact_renaming=False,retire_uninformative_scans=False)
    fresh.retain_joint_guard_history=True
    origin=SavedOrigin(cap.registry.data,fresh.rules,fresh.strategy,project_public=False);ops=[]
    for op in request.history:
        if type(op) in (ActionEvidence,PublicationEvidence,PublicReportEvidence):ops.append(replace(op,engine=fresh))
        elif type(op)is ConditionEvidence:ops.append(replace(op))
        elif type(op)is JointObservedChoice:ops.append(RawObservedChoice(op,fresh))
        else:raise Pending('live_medium_cold_unknown_evidence')
    with reconstruction_kernel_reuse(False):result=GeneratedBoard(origin,tuple(ops)).roles()
    assert fresh.values=={} and origin is not request.origin
    return result


def audit(target,color,kind):
    from .cut_out_joint_two_nights_fixture import complete_joint_selection,path_mappings
    from .cut_out_joint_night_forecast_fixture import full_readback
    if kind not in ('public','physical','zero'):raise Pending('live_medium_measure_kind_unproved')
    start=perf_counter();restricted=kind!='public'
    receipt=make_case(target,color,restricted=restricted)
    cap=certificate(receipt,public=kind in ('public','zero'))
    assert cold(cap,cap.request)==cap.source
    rebuilt_before=cold(cap,GeneratedBoard(cap.request.origin,cap.request.history[:-1]))
    assert rebuilt_before==receipt.before
    ordinary=InformationSetForecast(cap.registry.engine.baseline.rules,cap.registry.engine.baseline.strategy,
        exact_renaming=False,retire_uninformative_scans=False)
    ordinary.retain_joint_guard_history=True
    old_rows=ordinary.morning(rebuilt_before.public,rebuilt_before.public_state,rebuilt_before.past)
    old_physical=ordinary.push(rebuilt_before.public_state,rebuilt_before.private,old_rows)
    assert sum((q for q,b,s,p in old_rows if publication_key(b,p)==receipt.observation),F())==receipt.q
    assert sum((q for q,b,s,p,own in old_physical if publication_key(b,p)==receipt.observation),F())==receipt.p
    a,e,table=evaluate(cap);b,old,old_table=evaluate(cap,reference=True)
    assert a==b and table==old_table
    selection=complete_joint_selection(cap,e,old)
    actual=full_readback(cap,e,max_seconds=30,mapping_fn=path_mappings)
    expected=full_readback(cap,old,max_seconds=30,mapping_fn=path_mappings)
    assert actual['branches']==expected['branches'] and actual['terminals']==expected['terminals']
    # Fully independent post-night morning readback, including live-medium and
    # seer results plus complete conditional secret histories.
    candidates=[(key,request) for key,request in e.board_sources.items()
        if len(request.history)>len(cap.request.history) and type(request.history[-1])is PublicationEvidence]
    if not candidates:raise Pending('live_medium_future_morning_cold_witness_missing')
    # Prefer the future morning with medium P3 alive, so its next execution
    # report and the true-seer scan are both covered by the cold reconstruction.
    candidates=[(key,request) for key,request in candidates if request.roles().public.day==3 and 3 in request.roles().public.alive]
    if not candidates:raise Pending('live_medium_surviving_future_medium_witness_missing')
    _,request=candidates[-1];warm=request.roles();assert cold(cap,request)==warm
    assert len(warm.public.history)==4 and any(r.reporter==3 for r in warm.public.reports)
    if kind=='zero':
        assert receipt.q>0 and receipt.p==0 and receipt.physical_request is None
        try:certificate(receipt)
        except Pending as error:zero_boundary=error.reason
        else:raise AssertionError('zero physical branch fabricated a law')
    else:zero_boundary=None
    return dict(status='verified',target=target,color=color,kind=kind,Q_mass=str(receipt.q),P_mass=str(receipt.p),
        forecast_measure='public_Q_hypothetical' if kind in ('public','zero') else 'conditional_physical_P',
        physical_weighted_contribution=str(receipt.p*a.village_win),
        village_win=str(a.village_win),action_values={p:str(v) for p,v in a.action_values},
        complete_Forecast_Table_equal=True,selection_contexts=selection[0],selection_pairs=selection[1],
        labelled_branches=len(actual['branches']),terminal_transitions=len(actual['terminals']),
        independent_cold_prefix_and_future=True,zero_boundary=zero_boundary,
        total_comparison_seconds=perf_counter()-start)


def worker(target,color,kind):
    import json,os,threading,time
    from .cut_out_uniform_game_fixture import peak_bytes
    start=perf_counter()
    def watch():
        while True:
            if perf_counter()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    with calculation_budget(4000000,max_seconds=30):row=audit(target,color,kind)
    row['peak_working_set_bytes']=peak_bytes()
    print(json.dumps(row),flush=True)

def run_all():
    import json,subprocess,sys
    from pathlib import Path
    cases=((1,'black'),(3,'white'),(5,'black'),(5,'white'),(6,'black'),(6,'white'),(7,'black'),(7,'white'))
    result=dict(scope='live-medium3-black1-only',status='running',rows=[])
    path=Path('benchmarks/player_match_groups/cut-out-live-medium-forecast-results.json')
    for restricted in (False,True):
        for target,color in cases:
            kind='public' if not restricted else ('zero' if (target,color) in ((5,'white'),(6,'black'),(7,'black')) else 'physical')
            try:
                output=subprocess.run([sys.executable,'-m',__spec__.name,str(target),color,kind],capture_output=True,text=True,timeout=121)
                if output.returncode:raise RuntimeError(output.stderr or output.stdout or 'worker stopped')
                row=json.loads(output.stdout)
            except (subprocess.TimeoutExpired,RuntimeError,json.JSONDecodeError) as error:
                row=dict(status='unverified',target=target,color=color,kind=kind,reason=str(error))
            result['rows'].append(row);path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(row),flush=True)
    result['status']='verified' if all(row['status']=='verified' for row in result['rows']) else 'unverified'
    if result['status']=='verified':
        public=result['rows'][:8];restricted=result['rows'][8:]
        assert sum(F(row['Q_mass']) for row in public)==F(1,2)
        assert sum(F(row['P_mass']) for row in public)==F(4,9)
        assert sum(F(row['Q_mass']) for row in restricted)==F(1,2)
        assert sum(F(row['P_mass']) for row in restricted)==1
        result['conditional_black_village_win']=str(sum(F(row['physical_weighted_contribution']) for row in public)/F(4,9))
        result['restricted_village_win']=str(sum(F(row['physical_weighted_contribution']) for row in restricted))
        result['retained_Q_positive_P_zero']=sum(row['kind']=='zero' for row in restricted)
        result['max_comparison_seconds']=max(row['total_comparison_seconds'] for row in result['rows'])
        result['max_peak_working_set_bytes']=max(row['peak_working_set_bytes'] for row in result['rows'])
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if result['status']!='verified':raise SystemExit(1)


if __name__=='__main__':
    import sys
    if len(sys.argv)==1:run_all()
    else:worker(int(sys.argv[1]),sys.argv[2],sys.argv[3])