"""First-cycle coverage and owned observed-corpse mixture, no value recursion."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from weakref import WeakKeyDictionary
from collections import Counter
from time import perf_counter
from .cut_out_user_seven_uniform_preparation import prepare,comparison_game
from .cut_out_user_seven_source import from_game,issue,require_bound,ROOT_GROUPS
from .cut_out_seven_w2_mid import JointObservedChoice,_choices,_check_choice
from .cut_out_joint_night_forecast import (InformationSetForecast,Pending,physical_board,
    ActionEvidence,kernel_snapshot,outcome_key,point_fix,calculation_budget)
from .cut_out_live_medium_forecast import cold
from werewolf.actor_information import wolf_information_groups

_issued=WeakKeyDictionary()


@dataclass(frozen=True,eq=False)
class FirstCycle:
    registry:object
    witness:object
    engine:object
    request:object
    source:object
    before:object
    groups:tuple
    choice:object
    physical_mass:F


def base():
    initial=prepare(comparison_game()[1])
    if not hasattr(initial,'source'):raise Pending('first_cycle_initial_descriptor')
    r=from_game(initial.data.to_game(),initial)
    if not hasattr(r,'origin'):raise Pending('first_cycle_initial_registry')
    w=issue(r)
    if not hasattr(w,'source'):raise Pending('first_cycle_initial_witness')
    return r,w


def observed_choice(r,w,source,request,target,e):
    """A team-policy likelihood followed by the existing observation kernel.

    A chosen-target intervention must not preserve count classes incompatible
    with an observed corpse. Public children use the shared compatibility-only
    corpse law; P is first weighted by configured team choice and filtered.
    """
    require_bound(r,w)
    if (request.origin is not r.origin or len(request.history)!=1 or type(request.history[0])is not ActionEvidence
        or request.roles()!=source or source.public.day!=1 or source.public.phase!='night'
        or len(source.public.history)!=1 or len(source.public.alive)!=6 or source.observer is not None):
        raise Pending('first_cycle_owned_day_event_required')
    if e.rules!=r.engine.baseline.rules or e.strategy!=r.engine.baseline.strategy:
        raise Pending('first_cycle_exact_configured_policy_required')
    if (e.strategy.day,e.strategy.night,e.strategy.fake_reports)!=('random',)*3 or e.strategy.include_self_bite or source.public.initial_hunter_count:
        raise Pending('first_cycle_uniform_H0_no_self_bite_required')
    if type(target)is not int or target not in source.public.alive:
        raise Pending('first_cycle_target_must_be_alive')
    chance=sum((h.mass/F(len(source.public.alive)-(h.roles[0]&source.public.alive_mask).bit_count())
        for h in source.private.hypotheses if not h.roles[0]&(1<<(target-1))),F())
    if not chance:raise Pending('first_cycle_zero_physical_choice_no_conditional_P')
    outs=e.public_children(source.public,target,source.public_state)
    if len(outs)!=1 or outs[0].board.winner:raise Pending('first_cycle_single_observed_corpse_required')
    op=JointObservedChoice(e,source,target,outcome_key(outs[0]))
    _choices[op]=(r,w,r.data,r.data.to_game().get('revision',0),source,target,op.observation,repr((e.rules,e.strategy)))
    _check_choice(op);return op


def make_prefix(executed,victim,*,kernel_class=InformationSetForecast):
    if type(executed)is not int or not 1<=executed<=7:raise Pending('first_cycle_living_execution_required')
    r,w=base();e=kernel_class(r.engine.baseline.rules,r.engine.baseline.strategy,
        exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
    def no_value(*args,**kwargs):raise AssertionError('first cycle census must not solve/act')
    e.solve=e.act=no_value
    root=r.origin();out=e.physical_children(physical_board(root.public,root.private,root.physical),executed)
    if len(out)!=1 or out[0].board.winner:raise Pending('first_cycle_single_day_event_required')
    request=r.root.child(ActionEvidence(kernel_snapshot(e),executed,outcome_key(out[0]),False),None)
    before=request.roles();op=observed_choice(r,w,before,request,victim,kernel_snapshot(e))
    chance=op.likelihood(before);request=request.child(op,None);source=request.roles()
    receipt=FirstCycle(r,w,e,request,source,before,point_fix(w.contexts[-1].groups,executed,victim),op,F(1,7)*chance)
    _issued[receipt]=(r,r.data,r.data.to_game().get('revision',0),tuple(vars(receipt).values()))
    check(receipt);return receipt


def check(receipt):
    if type(receipt)is not FirstCycle or receipt not in _issued:raise Pending('first_cycle_issued_receipt_required')
    r,data,rev,fields=_issued[receipt]
    if r.data is not data or r.data.to_game().get('revision',0)!=rev or tuple(vars(receipt).values())!=fields:
        raise Pending('first_cycle_owner_revision_changed')
    require_bound(r,receipt.witness);_check_choice(receipt.choice)
    if receipt.engine.rules!=r.engine.baseline.rules or receipt.engine.strategy!=r.engine.baseline.strategy:
        raise Pending('first_cycle_owner_policy_changed')
    return receipt


def classification(executed,victim):
    if {executed,victim}=={1,2}:return 'legitimate_exclusion','no surviving seer reporter; common medium-only flow'
    if (executed,victim)==(3,4):return 'supported','two-surviving-reporters-all64'
    if (executed,victim)==(1,4):return 'supported','single-reporter-both-medium-results-all18'
    if (executed,victim)==(1,3):return 'structure_unproved','old-specific-vector-only; no complete morning selector'
    return 'structure_unproved',('unknown-corpse-team-mixture' if victim not in (3,4) else 'other-owned-history/no structural report selector')


def probe_legacy_aggregation(cap):
    """Run existing producer guards, not a hand-maintained coverage whitelist."""
    from .cut_out_joint_reports import produce,restore
    from .cut_out_live_medium_reports import single_report_orbits,restore_reports
    from werewolf.exact import random_report_outcomes
    from werewolf.morning_publications import public_report_branches
    source=check(cap).source;refusals=[]
    living=tuple(p for p in source.public.alive if source.public.claims[p-1]=='seer')
    if not living:return 'no-seer-opportunity',(),()
    try:
        rows=public_report_branches(source.public,source.past,restore(produce(source.public,source.public_state,source.past,cap.groups)))
        return 'joint-reports',rows,()
    except Pending as error:refusals.append(error.reason)
    outcomes=random_report_outcomes(source.public)
    if outcomes:
        try:
            rows=[]
            for outcome in outcomes:
                state=cap.engine.project(source.public_state,outcome.board)
                patterns=single_report_orbits(outcome.board,state,source.past,cap.groups,
                    fake_policy=cap.engine.strategy.fake_seer_policy)
                rows.extend((outcome.probability*q,b,s,p) for q,b,s,p in
                    public_report_branches(outcome.board,source.past,restore_reports(patterns)))
            return 'single-reporter',tuple(rows),tuple(refusals)
        except Pending as error:refusals.append(error.reason)
    else:refusals.append('no-supported-single-reporter-medium-observation')
    return 'unproved',(),tuple(refusals)

def probe_aggregation(cap):
    """Current generic route, based on the issued context rather than labels."""
    from .cut_out_structural_publications import StructuralPublicationKernel
    source=check(cap).source
    engine=StructuralPublicationKernel(cap.engine.rules,cap.engine.strategy,exact_renaming=False,retire_uninformative_scans=False)
    engine.retain_joint_guard_history=True
    def no_value(*args,**kwargs):raise AssertionError('publication probe must not solve/act')
    engine.solve=engine.act=no_value
    try:
        engine.bind(cap)
        rows=engine.morning(source.public,source.public_state,source.past)
    except Pending as error:return 'unproved',(),(error.reason,)
    living=tuple(p for p in source.public.alive if source.public.claims[p-1]=='seer')
    return ('generic-structural-publication' if living else 'no-seer-opportunity'),rows,()

def census():
    import gc
    from .cut_out_joint_night_prototype import move_law,move_board
    from werewolf.board_future import same_role_board
    start=perf_counter();rows=[];micros=0;illegal=0;physical_total=F();unknown_mass=F()
    group_of=lambda p:next(i for i,g in enumerate(ROOT_GROUPS) if p in g)
    classes=Counter()
    for executed in range(1,8):
        for victim in range(1,8):
            if victim==executed:continue
            cap=make_prefix(executed,victim);source=check(cap).source
            assert cold(cap,cap.request)==source
            # Validate the event-derived stabilizer, never discover a group by
            # permutation search or rebuild one from a posterior's marginals.
            for group in cap.groups:
                for target in group[1:]:
                    mapping=list(range(1,8));mapping[group[0]-1],mapping[target-1]=target,group[0];mapping=tuple(mapping)
                    for law,board in ((source.public_state,source.public),(source.private,source.physical)):
                        assert move_law(law,mapping)==law
                        assert same_role_board(move_board(board,law,mapping),board)
            # Independent literal per-information policy: count every legal
            # choice and its exact BEFORE-observation physical mass.
            raw=F();legal_count=0
            e=InformationSetForecast(cap.registry.engine.baseline.rules,cap.registry.engine.baseline.strategy,
                exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
            for info,mass,own in wolf_information_groups(cap.before.private):
                policy=dict(e.wolf_policy(cap.before.public,cap.before.public_state,cap.before.past,info.initial_roster,info.attacks))
                if victim in policy:raw+=mass*policy[victim];legal_count+=1
                else:illegal+=1
            assert raw==cap.choice.likelihood(cap.before)
            micros+=legal_count;physical_total+=cap.physical_mass
            if victim not in (3,4):unknown_mass+=cap.physical_mass
            # Common unaggregated morning is an ORACLE/fallback, not counted as
            # structural report aggregation. Compare against the independent
            # cold prefix, all Q/P weights and complete conditional histories.
            rebuilt=cold(cap,cap.request)
            old=e.morning(rebuilt.public,rebuilt.public_state,rebuilt.past)
            actual=cap.engine.morning(source.public,source.public_state,source.past)
            assert old==actual
            assert e.push(rebuilt.public_state,rebuilt.private,old)==cap.engine.push(source.public_state,source.private,actual)
            legacy_status,legacy_reason=classification(executed,victim)
            legacy_route,_,legacy_refusals=probe_legacy_aggregation(cap)
            assert (legacy_route in ('joint-reports','single-reporter'))==(legacy_status=='supported')
            route,aggregated,refusals=probe_aggregation(cap)
            status='supported' if route=='generic-structural-publication' else 'legitimate_exclusion' if route=='no-seer-opportunity' else 'structure_unproved'
            reason='derived certified reporter/target patterns' if status=='supported' else legacy_reason
            assert (route=='no-seer-opportunity')==(status=='legitimate_exclusion')
            if route=='no-seer-opportunity':assert len(actual)==1
            if aggregated:
                keyed=lambda branches:{(b,p):(q,law) for q,b,law,p in branches}
                assert keyed(aggregated)==keyed(actual)
                own=lambda branches:{(b,p):(q,law,private) for q,b,law,p,private in branches}
                assert own(cap.engine.push(source.public_state,source.private,aggregated))==own(e.push(rebuilt.public_state,rebuilt.private,old))
            classes[group_of(executed),group_of(victim)]+=1
            qcounts=Counter();pcounts=Counter()
            for h in source.public_state.hypotheses:qcounts[(h.roles[0]&source.public.alive_mask).bit_count()]+=h.mass
            for h in source.private.hypotheses:pcounts[(h.roles[0]&source.public.alive_mask).bit_count()]+=h.mass
            rows.append(dict(executed=executed,victim=victim,structure_class=[group_of(executed),group_of(victim)],
                status=status,reason_before=legacy_reason,report_reason_after=(reason if status!='structure_unproved' else 'complete structural publication recipe not issued for this event'),night_micro_legal=legal_count,physical_path_mass=str(cap.physical_mass),
                unknown_corpse=victim not in (3,4),old_night_roster_action_scope=executed in (1,3),
                direct_full_report_aggregation=status=='supported',legacy_direct_full_report_aggregation=legacy_status=='supported',legacy_alpha_possible_not_auto=(executed,victim)==(2,4),
                generalized_observed_transition=True,observed_transition_status_after='supported',common_morning_Q_vectors=len(actual),
                producer_guard_route=route,producer_guard_refusals=refusals,legacy_producer_guard_route=legacy_route,legacy_producer_refusals=legacy_refusals,
                Q_live_counts={k:str(v) for k,v in qcounts.items()},P_live_counts={k:str(v) for k,v in pcounts.items()},
                cold_full_source_equal=True,event_derived_groups_full_QP_verified=True,complete_common_morning_equal=True))
            del cap,source,e,rebuilt,old,actual;gc.collect()
    assert len(rows)==42 and len(classes)==14 and micros==180 and illegal==72
    assert physical_total==1 and unknown_mass==F(3,5)
    covered=[r for r in rows if r['direct_full_report_aggregation']]
    return dict(status='verified',rows=rows,structure_classes={str(k):v for k,v in classes.items()},
        legal_labelled_histories=42,invalid_repeat_death_histories=7,legal_information_action_branches=micros,
        illegal_wolf_self_bite_branches=illegal,unknown_corpse_histories=30,unknown_corpse_physical_mass=str(unknown_mass),
        report_aggregation_classification={status:sum(row['status']==status for row in rows) for status in ('supported','structure_unproved','legitimate_exclusion')},
        full_report_aggregation_before=2,full_report_aggregation_after=len(covered),legacy_report_coverage_physical_mass='19/280',full_report_coverage_physical_mass=str(sum((F(r['physical_path_mass']) for r in covered),F())),
        observed_mixture_certificate_before=3,observed_mixture_certificate_after=42,
        old_observed_mixture_physical_mass='1/10',new_observed_mixture_physical_mass='1',
        no_seer_report_mass=str(sum((F(r['physical_path_mass']) for r in rows if r['status']=='legitimate_exclusion'),F())),
        automatic_initial_solver_fast_dispatch=False,full_initial_search=False,total_comparison_seconds=perf_counter()-start)


def worker():
    import os,time,json,threading
    from .cut_out_uniform_game_fixture import peak_bytes
    start=perf_counter()
    def watch():
        while True:
            if perf_counter()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    with calculation_budget(4000000,max_seconds=30):row=census()
    row['peak_working_set_bytes']=peak_bytes();print(json.dumps(row),flush=True)


if __name__=='__main__':
    import sys
    sys.modules[__spec__.name]=sys.modules[__name__]
    worker()