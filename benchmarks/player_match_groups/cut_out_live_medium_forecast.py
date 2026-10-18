"""Limited live-medium single publication -> Forecast and cold SavedOrigin.

A zero physical mass is an outcome receipt, not a normalized conditional law.
Its Q hypothetical remains evaluable through existing PublicReportEvidence.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from weakref import WeakKeyDictionary
from time import perf_counter
from .cut_out_live_medium_reports import prepublication,single_report_orbits,restore_reports
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
        if b.day==2 and len(b.history)==2 and any(r.reporter==3 and r.target==1 and r.color in ('black','white') for r in b.reports):
            from werewolf.morning_publications import public_report_branches
            orbits=single_report_orbits(b,s,past,GROUPS,fake_policy=self.strategy.fake_seer_policy)
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


def make_case(target=5,color='white',*,restricted=False,medium='black',roster=None):
    if medium not in ('black','white'):raise Pending('live_medium_result_scope')
    if type(target)is not int or not 1<=target<=7 or color not in ('black','white'):
        raise Pending('live_medium_single_report_input_scope')
    if roster is not None and not restricted:raise Pending('live_medium_private_roster_requires_condition')
    e,before,_,r,w,request=prepublication(receipt=True,kernel_class=StructuralPublicationKernel)
    if restricted:
        roster=(17 if medium=='black' else 18) if roster is None else roster
        if roster not in (17,18):raise Pending('live_medium_private_roster_scope')
        own=replace(before.private,hypotheses=normalize(tuple(h for h in before.private.hypotheses if h.roles[0]==roster)))
        changed=replace(before,private=own,physical=physical_board(before.public,own,before.physical))
        recipe=condition_recipe(before,changed)
        if recipe is None:raise Pending('live_medium_private_roster_recipe_unproved')
        request=request.child(recipe,None);before=request.roles()
    rows=e.morning(before.public,before.public_state,before.past)
    wanted=lambda b,p:any(x.reporter==3 and x.target==1 and x.color==medium for x in b.reports) and any(x.player==2 and x.acquired_day==2 and (x.target,x.color)==(target,color) for x in p)
    selected=[row for row in rows if wanted(row[1],row[3])]
    if not selected:raise Pending('live_medium_public_vector_support_zero')
    if len(selected)>1:raise Pending('live_medium_public_vector_not_unique')
    q,b,s,past=selected[0];observation=publication_key(b,past)
    return issue_publication_receipt(r,w,before,request,e,observation,point_fix(GROUPS,target),require_equal=not restricted)


def issue_publication_receipt(r,w,before,request,e,observation,groups,*,require_equal=False):
    """Shared Q/P publication receipt; physical zero never creates a fake law."""
    rows=e.morning(before.public,before.public_state,before.past)
    selected=[row for row in rows if publication_key(row[1],row[3])==observation]
    if len(selected)!=1:raise Pending('publication_public_observation_not_unique')
    q=selected[0][0]
    physical=e.push(before.public_state,before.private,rows)
    selectedP=[row for row in physical if publication_key(row[1],row[3])==observation]
    if len(selectedP)>1:raise Pending('live_medium_physical_vector_not_unique')
    p=selectedP[0][0] if selectedP else F()
    public_request=request.child(PublicReportEvidence(kernel_snapshot(e),observation),None)
    public_source=public_request.roles()
    physical_request=request.child(PublicationEvidence(kernel_snapshot(e),observation),None) if p else None
    physical_source=physical_request.roles() if p else None
    if require_equal and physical_source!=public_source:
        raise Pending('live_medium_public_Q_not_equal_actual_conditional_P')
    result=PublicationReceipt(r,w,before,observation,q,p,public_request,physical_request,
        public_source,physical_source,groups)
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


def audit(target,color,kind,medium='black'):
    from .cut_out_joint_two_nights_fixture import complete_joint_selection,path_mappings
    from .cut_out_joint_night_forecast_fixture import full_readback
    if kind not in ('public','physical','zero'):raise Pending('live_medium_measure_kind_unproved')
    start=perf_counter();restricted=kind!='public'
    receipt=make_case(target,color,restricted=restricted,medium=medium,roster=17 if medium=='white' and kind=='zero' else None)
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
    with_reporter=[row for row in candidates if 2 in row[1].roles().public.alive]
    _,request=(with_reporter or candidates)[-1];warm=request.roles();assert cold(cap,request)==warm
    assert len(warm.public.history)==4 and any(r.reporter==3 for r in warm.public.reports)
    parity=None
    if medium=='white':
        def root_outcomes(target):
            return next(outcomes for board,payload,t,outcomes in e.full_branch_records
                if board==cap.source.public and payload.private==cap.source.private and t==target)
        assert cap.source.public.wolf_count==2
        assert all(o.board.winner=='wolf' for o in root_outcomes(3))
        assert all(o.board.winner is None and o.board.wolf_count==1 for o in root_outcomes(2))
        parity='execute known citizen -> immediate W2 parity; execute wolf2 -> W1 continuation'
    if kind=='zero':
        assert receipt.q>0 and receipt.p==0 and receipt.physical_request is None
        try:certificate(receipt)
        except Pending as error:zero_boundary=error.reason
        else:raise AssertionError('zero physical branch fabricated a law')
    else:zero_boundary=None
    return dict(status='verified',medium=medium,target=target,color=color,kind=kind,Q_mass=str(receipt.q),P_mass=str(receipt.p),
        forecast_measure='public_Q_hypothetical' if kind in ('public','zero') else 'conditional_physical_P',
        physical_weighted_contribution=str(receipt.p*a.village_win),
        village_win=str(a.village_win),action_values={p:str(v) for p,v in a.action_values},
        complete_Forecast_Table_equal=True,selection_contexts=selection[0],selection_pairs=selection[1],
        labelled_branches=len(actual['branches']),terminal_transitions=len(actual['terminals']),
        independent_cold_prefix_and_future=True,zero_boundary=zero_boundary,parity_check=parity,
        total_comparison_seconds=perf_counter()-start)


def worker(target,color,kind,medium='black'):
    import json,os,threading,time
    from .cut_out_uniform_game_fixture import peak_bytes
    start=perf_counter()
    def watch():
        while True:
            if perf_counter()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    with calculation_budget(4000000,max_seconds=30):row=audit(target,color,kind,medium)
    row['peak_working_set_bytes']=peak_bytes()
    print(json.dumps(row),flush=True)

def run_all(medium='black'):
    import json,subprocess,sys
    from pathlib import Path
    cases=((1,'black'),(3,'white'),(5,'black'),(5,'white'),(6,'black'),(6,'white'),(7,'black'),(7,'white')) if medium=='black' else tuple((t,c) for t in (1,3,5,6,7) for c in ('white','black'))
    result=dict(scope='live-medium3-'+medium+'1-only',status='running',rows=[])
    suffix='' if medium=='black' else '-white'
    path=Path('benchmarks/player_match_groups/cut-out-live-medium'+suffix+'-forecast-results.json')
    modes=('public','physical') if medium=='black' else ('public','physical','zero')
    for mode in modes:
        for target,color in cases:
            kind='zero' if medium=='black' and mode=='physical' and (target,color) in ((5,'white'),(6,'black'),(7,'black')) else mode
            try:
                output=subprocess.run([sys.executable,'-m',__spec__.name,str(target),color,kind,medium],capture_output=True,text=True,timeout=121)
                if output.returncode:raise RuntimeError(output.stderr or output.stdout or 'worker stopped')
                row=json.loads(output.stdout)
            except (subprocess.TimeoutExpired,RuntimeError,json.JSONDecodeError) as error:
                row=dict(status='unverified',target=target,color=color,kind=kind,reason=str(error))
            result['rows'].append(row);path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(row),flush=True)
    result['status']='verified' if all(row['status']=='verified' for row in result['rows']) else 'unverified'
    if result['status']=='verified':
        n=len(cases);public=result['rows'][:n];restricted=result['rows'][n:2*n]
        pmass=F(4,9) if medium=='black' else F(5,9)
        for rows,expectedP in ((public,pmass),(restricted,F(1))):
            assert sum(F(row['Q_mass']) for row in rows)==F(1,2)
            assert sum(F(row['P_mass']) for row in rows)==expectedP
        result['conditional_'+medium+'_village_win']=str(sum(F(row['physical_weighted_contribution']) for row in public)/pmass)
        result['restricted_village_win']=str(sum(F(row['physical_weighted_contribution']) for row in restricted))
        result['retained_Q_positive_P_zero']=sum(row['kind']=='zero' for row in result['rows'][n:])
        if medium=='white':
            assert sum(F(row['Q_mass']) for row in result['rows'][2*n:])==F(1,2)
            assert all(F(row['P_mass'])==0 for row in result['rows'][2*n:])
        result['max_comparison_seconds']=max(row['total_comparison_seconds'] for row in result['rows'])
        result['max_peak_working_set_bytes']=max(row['peak_working_set_bytes'] for row in result['rows'])
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if result['status']!='verified':raise SystemExit(1)


if __name__=='__main__':
    import sys
    if len(sys.argv)==1:run_all()
    elif sys.argv[1]=='--white':run_all('white')
    else:worker(int(sys.argv[1]),sys.argv[2],sys.argv[3],sys.argv[4] if len(sys.argv)>4 else 'black')