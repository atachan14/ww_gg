"""Opt-in pre-vector aggregation after a surviving true medium's black report.

This is a morning producer checkpoint, not a Forecast or initial-seven solver.
Public generation only sees Q. Deferred named output is reweighted from the
complete physical/private law by the unchanged common observer flow.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F
from time import perf_counter
from .cut_out_seven_w2_mid import (initial_night, InformationSetForecast,
    physical_board, ActionEvidence, kernel_snapshot, outcome_key, choice_step,
    calculation_budget, Pending)
from .cut_out_joint_night_prototype import move_law, move_board
from werewolf.exact import random_report_outcomes
from werewolf.morning_publications import GeneratedPublication, public_report_branches
from werewolf.seer_future_uniform import true_reports
from werewolf.seer_acquisition import normalize


@dataclass(frozen=True)
class ReportOrbit:
    target_block: tuple
    color: str
    mass: F
    representative: GeneratedPublication


def prepublication():
    first=initial_night(1);r=first.registry;w=first.witness
    e=InformationSetForecast(r.engine.baseline.rules,r.engine.baseline.strategy,
        exact_renaming=False,retire_uninformative_scans=False)
    e.retain_joint_guard_history=True
    root=r.origin()
    outs=e.physical_children(physical_board(root.public,root.private,root.physical),1)
    request=r.root.child(ActionEvidence(kernel_snapshot(e),1,outcome_key(outs[0]),False),None)
    before=request.roles()
    op=choice_step(r,w,before,4,kernel_snapshot(e))
    return e,request.child(op,None).roles(),op.likelihood(before)


def single_truth_orbits(board,state,past,groups):
    """Partition acquisition patterns before constructing public report vectors.

    Receipt boundary: fixed true seer P2, one new scan, Day2, exact Q symmetry,
    and medium P3's observed black result for dead P1. No fake law is inferred.
    Every acquisition, attack and initial role mask remains in each branch.
    """
    if (board.player_count!=7 or board.day!=2 or board.initial_hunter_count or
        board.wolf_count!=1 or not any(r.reporter==3 and r.target==1 and r.color=='black' for r in board.reports)):
        raise Pending('live_medium_black1_single_true_seer_scope')
    if groups!=((1,),(2,),(3,),(4,),(5,6,7)):
        raise Pending('live_medium_group_receipt_unproved')
    if any(h.roles[2]!=2 for h in state.hypotheses):
        raise Pending('live_medium_fake_or_ambiguous_true_owner_not_implemented')
    if tuple(p for p in board.alive if board.claims[p-1]=='seer')!=(2,):
        raise Pending('live_medium_multiple_reporters_not_implemented')
    for p in (6,7):
        mapping=list(range(1,8));mapping[4],mapping[p-1]=p,5
        if (move_law(state,tuple(mapping))!=state or move_board(board,state,tuple(mapping))!=board or
            tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in past))!=past):
            raise Pending('live_medium_complete_history_Q_not_exchangeable')
    seen={(r.player,r.acquired_day) for r in past};patterns={}
    for h in state.hypotheses:
        scans=tuple(a for a in h.acquisitions if a.player==2 and (2,a.day) not in seen)
        if len(scans)!=1 or scans[0].day!=2:
            raise Pending('live_medium_one_unpublished_scan_required')
        a=scans[0];block=next(g for g in groups if a.target in g)
        # Only an acquisition pattern is keyed here. No complete named report
        # vectors are generated and subsequently canonicalized.
        patterns.setdefault((block,a.color),[]).append((h,a.target))
    result=[]
    for (block,color),entries in patterns.items():
        selected=tuple(h for h,target in entries if target==block[0])
        if not selected:raise Pending('live_medium_orbit_representative_missing')
        total=sum((h.mass for h,_ in entries),F())
        one=sum((h.mass for h in selected),F())
        if total!=one*len(block):raise Pending('live_medium_unequal_target_orbit_mass')
        reports=true_reports(selected[0],past,board.alive,board.claims,2)
        branch=GeneratedPublication(reports,one,replace(state,hypotheses=normalize(selected)))
        result.append(ReportOrbit(block,color,total,branch))
    if sum((o.mass for o in result),F())!=1:raise Pending('live_medium_incomplete_acquisition_patterns')
    return tuple(result)


def restore_reports(orbits):
    """Output-only label restoration; no report generator or solver is rerun."""
    for orbit in orbits:
        original=orbit.representative
        for target in orbit.target_block:
            mapping=list(range(1,8));a=orbit.target_block[0]
            mapping[a-1],mapping[target-1]=target,a
            reports=tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in original.reports))
            yield GeneratedPublication(reports,original.probability,move_law(original.state,tuple(mapping)))


def audit():
    start=perf_counter();e,source,chance=prepublication()
    old=e.morning(source.public,source.public_state,source.past)
    generated=[];counts={};black_orbits=None
    for outcome in random_report_outcomes(source.public):
        law=e.project(source.public_state,outcome.board)
        if any(r.color=='black' for r in outcome.board.reports):
            black_orbits=single_truth_orbits(outcome.board,law,source.past,((1,),(2,),(3,),(4,),(5,6,7)))
            rows=public_report_branches(outcome.board,source.past,restore_reports(black_orbits))
            counts['black_Q']=str(outcome.probability)
        else:
            # Explicit unchanged oracle fallback, not a claim of aggregation.
            rows=e.publications(outcome.board,law,source.past)
            try:single_truth_orbits(outcome.board,law,source.past,((1,),(2,),(3,),(4,),(5,6,7)))
            except Pending as error:counts['white_boundary']=error.reason
            else:raise AssertionError('white medium branch silently accepted')
        generated.extend((outcome.probability*q,b,s,p) for q,b,s,p in rows)
    keyed=lambda rows:{(b,p):(q,s) for q,b,s,p in rows}
    assert keyed(generated)==keyed(old)
    own=lambda rows:{(b,p):(q,s,private) for q,b,s,p,private in rows}
    pnew=e.push(source.public_state,source.private,tuple(generated))
    assert own(pnew)==own(e.push(source.public_state,source.private,old))
    blackP=sum((q for q,b,*_ in pnew if any(r.color=='black' for r in b.reports)),F())
    assert chance==F(9,40) and counts['black_Q']=='1/2' and blackP==F(4,9)
    # Legitimate Q-positive/P-zero public outcomes remain in Q. The common
    # physical transfer gives them zero mass, without uniform completion.
    restricted=replace(source.private,hypotheses=normalize(tuple(h for h in source.private.hypotheses if h.roles[0]==17)))
    restricted_rows=e.push(source.public_state,restricted,tuple(generated))
    assert own(restricted_rows)==own(e.push(source.public_state,restricted,old))
    zero=[(q,b,p) for q,b,_,p in generated if (b,p) not in {(c,t) for _,c,_,t,_ in restricted_rows}]
    assert zero and all(q>0 for q,_,_ in zero)
    assert any(any(r.target==1 and r.color=='black' for r in b.reports) and any(r.player==2 and r.target==5 and r.color=='white' and r.acquired_day==2 for r in p) for _,b,p in zero)
    outcome=next(o for o in random_report_outcomes(source.public) if any(r.color=='black' for r in o.board.reports))
    try:single_truth_orbits(outcome.board,replace(e.project(source.public_state,outcome.board),hypotheses=normalize(tuple(replace(h,mass=h.mass*(2 if h.roles[0]==17 else 1)) for h in e.project(source.public_state,outcome.board).hypotheses))),source.past,((1,),(2,),(3,),(4,),(5,6,7)))
    except Pending as error:counts['asymmetric_Q_boundary']=error.reason
    else:raise AssertionError('asymmetric secret joint support accepted')
    return dict(status='verified',prefix='execute1/bite4/medium3 black1',observed_team_choice=str(chance),
        medium_black_P=str(blackP),**counts,representative_vectors=len(black_orbits),
        restored_black_vectors=sum(len(o.target_block) for o in black_orbits),all_public_vectors=len(generated),
        complete_public_and_private_histories_equal=True,private_roster17_positive_Q_zero_P=len(zero),
        full_initial_search=False,Forecast_connected=False,total_comparison_seconds=perf_counter()-start)


def worker():
    import json,os,threading,time
    from .cut_out_uniform_game_fixture import peak_bytes
    start=perf_counter()
    def watch():
        while True:
            if perf_counter()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    with calculation_budget(4000000,max_seconds=30):result=audit()
    result['peak_working_set_bytes']=peak_bytes()
    print(json.dumps(result),flush=True)


if __name__=='__main__':worker()