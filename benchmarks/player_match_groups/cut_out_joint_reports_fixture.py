"""Bounded two-reporter distribution, small Forecast and independent cold checks."""
from dataclasses import replace
from fractions import Fraction as F
from time import perf_counter
from .cut_out_joint_reports import *
from .cut_out_live_medium_forecast import certificate,evaluate,cold,check
from .cut_out_joint_night_forecast import calculation_budget,physical_board
from werewolf.board_future import GeneratedBoard,publication_key,PublicationEvidence

CASES={
 'agree':((5,'black'),(5,'black')),
 'disagree':((5,'white'),(5,'black')),
 'different_target_color':((5,'white'),(6,'black')),
 'different_target_same_color':((5,'black'),(6,'black')),
 'peer_medium':((2,'black'),(3,'white')),
 'private_scan_supported':((6,'black'),(5,'white')),
}


def negatives():
    e,s,_=prepublication(executed=3);rejected=[]
    def refuse(name,call):
        try:call()
        except Pending as error:rejected.append(dict(case=name,reason=error.reason))
        else:raise AssertionError(name+' accepted')
    refuse('unproved_group_split',lambda:produce(s.public,s.public_state,s.past,((1,),(2,),(3,),(4,),(5,6,7))))
    entries=[]
    for roles in {h.roles for h in s.public_state.hypotheses}:
        selected=tuple(h for h in s.public_state.hypotheses if h.roles==roles)
        total=sum((h.mass for h in selected),F())
        biased=normalize(tuple(replace(h,mass=h.mass*(2 if any(a.day==2 and a.target==5 for a in h.acquisitions) else 1)) for h in selected))
        entries.extend(replace(h,mass=h.mass*total) for h in biased)
    changed=replace(s.public_state,hypotheses=normalize(tuple(entries)))
    marginal=lambda law:{r:sum(h.mass for h in law.hypotheses if h.roles==r) for r in {h.roles for h in law.hypotheses}}
    assert marginal(changed)==marginal(s.public_state)
    refuse('secret_scan_bias_same_role_marginals',lambda:produce(s.public,changed,s.past))
    refuse('unproved_backlog',lambda:produce(s.public,s.public_state,s.past[:1]))
    other=JointPublicationKernel(e.rules,replace(e.strategy,fake_seer_policy=('uniform',)),exact_renaming=False,retire_uninformative_scans=False)
    refuse('changed_configured_fake_law',lambda:other.generate_publications(s.public,s.public_state,s.past))
    old,wrong,_=prepublication(executed=1)
    refuse('wrong_prefix',lambda:produce(wrong.public,wrong.public_state,wrong.past))
    refuse('self_report',lambda:make_case(((1,'black'),(5,'white'))))
    receipt=make_case(CASES['agree'])
    refuse('copied_receipt',lambda:check(replace(receipt)))
    r=receipt.registry;data=r.data;r.data=data.updated(revision=data.to_game().get('revision',0)+1)
    try:refuse('stale_receipt',lambda:certificate(receipt))
    finally:r.data=data
    return dict(status='verified',rejected=rejected)


def audit(case,private='public'):
    from .cut_out_joint_two_nights_fixture import complete_joint_selection,path_mappings
    from .cut_out_joint_night_forecast_fixture import full_readback
    start=perf_counter();receipt=make_case(CASES[case],private=private)
    cap=certificate(receipt,public=receipt.p==0)
    assert cold(cap,cap.request)==cap.source
    before=cold(cap,GeneratedBoard(cap.request.origin,cap.request.history[:-1]));assert before==receipt.before
    ordinary=InformationSetForecast(cap.registry.engine.baseline.rules,cap.registry.engine.baseline.strategy,
        exact_renaming=False,retire_uninformative_scans=False);ordinary.retain_joint_guard_history=True
    rows=ordinary.morning(before.public,before.public_state,before.past)
    weighted=ordinary.push(before.public_state,before.private,rows)
    assert sum((q for q,b,s,p in rows if publication_key(b,p)==receipt.observation),F())==receipt.q
    assert sum((q for q,b,s,p,own in weighted if publication_key(b,p)==receipt.observation),F())==receipt.p
    a,e,table=evaluate(cap);expected,old,old_table=evaluate(cap,reference=True)
    assert a==expected and table==old_table
    selection=complete_joint_selection(cap,e,old)
    actual=full_readback(cap,e,max_seconds=30,mapping_fn=path_mappings)
    reference=full_readback(cap,old,max_seconds=30,mapping_fn=path_mappings)
    assert actual['branches']==reference['branches'] and actual['terminals']==reference['terminals']
    candidates=[request for request in e.board_sources.values() if len(request.history)>len(cap.request.history)
        and type(request.history[-1])is PublicationEvidence and request.roles().public.day==3
        and {1,2}<=set(request.roles().public.alive)]
    if not candidates:raise Pending('joint_report_both_reporters_future_cold_witness_missing')
    request=candidates[-1];warm=request.roles();assert cold(cap,request)==warm
    assert len(warm.public.history)==4
    assert {r.player for r in warm.past if r.acquired_day==3}=={1,2}
    if receipt.p==0:
        assert receipt.physical_request is None
        try:certificate(receipt)
        except Pending:pass
        else:raise AssertionError('zero-P conditional law fabricated')
    return dict(status='verified',case=case,private=private,Q_mass=str(receipt.q),P_mass=str(receipt.p),
        village_win=str(a.village_win),action_values={p:str(v) for p,v in a.action_values},
        forecast_measure='public_Q_hypothetical' if receipt.p==0 else 'conditional_P',physical_contribution=str(receipt.p*a.village_win),
        complete_Forecast_Table_joint_equal=True,selection_contexts=selection[0],selection_pairs=selection[1],
        labelled_branches=len(actual['branches']),terminal_transitions=len(actual['terminals']),
        independent_cold_prefix_and_two_reporter_future=True,total_comparison_seconds=perf_counter()-start)


def worker(case,private='public'):
    import os,time,json,threading
    from .cut_out_uniform_game_fixture import peak_bytes
    start=perf_counter()
    def watch():
        while True:
            if perf_counter()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    with calculation_budget(4000000,max_seconds=30):
        row=audit_distribution() if case=='distribution' else negatives() if case=='negative' else audit(case,private)
    row['peak_working_set_bytes']=peak_bytes();print(json.dumps(row),flush=True)


def run_all():
    import json,subprocess,sys
    from pathlib import Path
    cases=[('distribution','public'),('negative','public')]
    cases.extend((name,'public') for name in ('agree','disagree','different_target_color','different_target_same_color','peer_medium'))
    cases.extend((name,'roster17') for name in ('agree','disagree','different_target_color','different_target_same_color'))
    cases.extend((name,'private_scan5white') for name in ('private_scan_supported','different_target_color'))
    result=dict(status='running',scope='actual7-execute3-bite4-two-surviving-reporters',rows=[])
    path=Path('benchmarks/player_match_groups/cut-out-joint-reports-results.json')
    for case,private in cases:
        try:
            output=subprocess.run([sys.executable,'-m',__spec__.name,case,private],capture_output=True,text=True,timeout=121)
            if output.returncode:raise RuntimeError(output.stderr or output.stdout or 'worker stopped')
            row=json.loads(output.stdout)
        except (subprocess.TimeoutExpired,RuntimeError,json.JSONDecodeError) as error:
            row=dict(status='unverified',case=case,private=private,reason=str(error))
        result['rows'].append(row);path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(row),flush=True)
        if case in ('distribution','negative') and row['status']!='verified':break
    result['status']='verified' if all(row['status']=='verified' for row in result['rows']) else 'unverified'
    if result['status']=='verified':
        result['max_comparison_seconds']=max(row.get('total_comparison_seconds',0) for row in result['rows'])
        result['max_peak_working_set_bytes']=max(row['peak_working_set_bytes'] for row in result['rows'])
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if result['status']!='verified':raise SystemExit(1)


if __name__=='__main__':
    import sys
    if len(sys.argv)==1:run_all()
    else:worker(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else 'public')