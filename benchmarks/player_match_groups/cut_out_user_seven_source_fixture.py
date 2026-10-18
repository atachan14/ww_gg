"""Bounded7/W2 first-night and tiny endgame only; never full initial forecast."""
from dataclasses import replace
from copy import deepcopy,copy
from pathlib import Path
from fractions import Fraction as F
from unittest.mock import patch
import sys,time,json,subprocess,threading,os
from .cut_out_user_seven_source import *
from .cut_out_candidate_context_fixture import zero_legacy
from .cut_out_day_night import moved_law
from .cut_out_uniform_game import OwnView
from werewolf.seer_acquisition import Acquisition


def ok(value):
    assert not isinstance(value,UnsupportedPartition),value
    return value


def invariants(witness):
    swaps=0
    for context,branch in zip(witness.contexts,witness.replay_branches):
        if context.parent is not None:assert context.groups==point_fix(context.parent.groups,*context.new_fixed)
        for group in context.groups:
            for p in group[1:]:
                assert moved_law(branch.public_law,group[0],p,7)==branch.public_law
                assert moved_law(branch.physical_law,group[0],p,7)==branch.physical_law
                swaps+=1
    return swaps


def audit_prefix():
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.board_future import reconstruction_kernel_reuse
    r=ok(synthetic_registry());stack,mocks=zero_legacy()
    with stack,patch.object(InformationSetForecast,'solve',side_effect=AssertionError('no full solve')) as solve,patch.object(InformationSetForecast,'act',side_effect=AssertionError('no full action values')) as act,patch.object(CutOutUniformEngine,'legacy_large_groups',side_effect=AssertionError('old groups')) as old:
        w=ok(issue(r));assert (1,2) in w.contexts[-1].groups
        assert isinstance(evaluate_small(r,witness=w),UnsupportedPartition)
        child,mass,request=ok(read_action(r,witness=w,target=5))
        with calculation_budget(300000,max_seconds=10),reconstruction_kernel_reuse(False):cold=request.roles()
        assert cold==child and mass==1
        assert solve.call_count==act.call_count==old.call_count==0 and all(m.call_count==0 for m in mocks)
    assert any(b.public_law!=b.physical_law for b in w.replay_branches)
    assert r.engine.baseline.cast==SevenCast() and r.engine.baseline.wolves==2
    initial=ok(from_game(r.initial.data.to_game(),r.initial));iw=ok(issue(initial))
    assert iw.contexts[-1].groups==ROOT_GROUPS and isinstance(evaluate_small(initial,witness=iw),UnsupportedPartition)
    return dict(case='prefix',typed_cast=dict(players=7,wolves=2,mediums=1,seers=1,hunters=0),initial_worlds=len(iw.source.public.worlds),
        contexts=len(w.contexts),final_groups=w.contexts[-1].groups,both_carrier_swaps=invariants(w),
        Q_P_differ_in_saved_night=True,first_night_cold_child_equal=True,full_forecast_refused=True,
        canonical_calls=0,CandidateRules_calls=0,legacy_root_calls=0,solve_calls=0,act_value_calls=0)


def audit_endgame():
    from .cut_out_max_fixture import complete_table
    from werewolf.information_set_forecast import InformationSetForecast
    original=InformationSetForecast.solve
    def bounded(self,b,*args,**kwargs):
        assert b.winner or len(b.alive)<=3,'large forecast started'
        return original(self,b,*args,**kwargs)
    r=ok(synthetic_registry(endgame=True));w=ok(issue(r));stack,mocks=zero_legacy()
    with stack,patch.object(InformationSetForecast,'solve',bounded),patch.object(CutOutUniformEngine,'legacy_large_groups',side_effect=AssertionError('old groups')) as old:
        actual,engine=ok(evaluate_small(r,witness=w))
        assert actual.village_win==F(1,3) and dict(actual.action_values)=={1:F(1,2),2:F(1,2),3:F()}
        view=OwnView(1,'seer',(Acquisition(1,1,4,'white'),Acquisition(2,1,7,'white'),Acquisition(3,1,5,'black')))
        own,_=ok(evaluate_small(r,witness=w,view=view))
        assert own.village_win==F(1,3) and dict(own.action_values)=={1:F(),2:F(1),3:F()}
        terminal,q,request=ok(read_action(r,witness=w,target=3,winner='wolf'))
        assert q==1 and terminal.public.winner=='wolf'
        assert all(m.call_count==0 for m in mocks) and old.call_count==0
    reference,_=ok(evaluate_small(r,witness=w,official_reference=True))
    own_reference,_=ok(evaluate_small(r,witness=w,view=view,official_reference=True))
    assert actual==reference and own==own_reference
    assert complete_table(r,actual,None)==complete_table(r,reference,None)
    assert complete_table(r,own,view)==complete_table(r,own_reference,view)
    assert len(w.source.public.alive)==3 and all(h.roles[0].bit_count()==2 and len(h.attacks)==2 for h in w.source.private.hypotheses)
    return dict(case='endgame',alive=list(w.source.public.alive),village_win=str(actual.village_win),public_action_values={p:str(v) for p,v in actual.action_values},
        own_action_values={p:str(v) for p,v in own.action_values},Table_joint_mass_exact=True,
        final_groups=w.contexts[-1].groups,both_carrier_swaps=invariants(w),initial_two_wolf_roster_and_two_attacks_preserved=True,
        canonical_calls=0,CandidateRules_calls=0,legacy_root_calls=0)


def active_event(r,player,day):
    from werewolf.public_log_changes import declarations
    return declarations(r.data.to_game()['public_log'])[0]['seer',day,player][1]


def audit_edits():
    r=ok(synthetic_registry(endgame=True));before=r.data.inputs;w=ok(issue(r))
    e=active_event(r,1,3)
    changed=ok(r.edited({'mode':'single','events':[dict(e,color='white',action='change',ref=e['id'])]}));cw=ok(issue(changed))
    assert (1,2) not in cw.contexts[-1].groups and isinstance(evaluate_small(changed,witness=w),UnsupportedPartition)
    e=active_event(changed,2,3)
    assert isinstance(changed.edited({'mode':'single','events':[dict(e,action='withdraw',ref=e['id'])]}),UnsupportedPartition) # No possible true seer left.
    e=active_event(r,2,3)
    cancelled=ok(r.edited({'mode':'single','events':[dict(e,action='withdraw',ref=e['id'])]}));xw=ok(issue(cancelled))
    assert (1,2) not in xw.contexts[-1].groups
    e=active_event(cancelled,1,3)
    restored=ok(cancelled.edited({'mode':'simultaneous','events':[dict(e,color='black',action='change',ref=e['id']),dict(kind='seer',player=2,day=3,target=5,color='black')]}));rw=ok(issue(restored))
    assert restored.origin()==r.origin() and (1,2) in rw.contexts[-1].groups
    for registry,new in ((changed,cw),(cancelled,xw),(restored,rw)):
        assert isinstance(evaluate_small(registry,witness=w),UnsupportedPartition)
        actual,_=ok(evaluate_small(registry,witness=new));reference,_=ok(evaluate_small(registry,witness=new,official_reference=True));assert actual==reference
        invariants(new)
    # Same public payload from distinct origins remains conservatively split.
    e=active_event(r,1,3);separate=ok(r.edited({'mode':'single','events':[dict(e,action='change',ref=e['id'])]}));sw=ok(issue(separate))
    assert separate.origin()==r.origin() and (1,2) not in sw.contexts[-1].groups
    require_bound(r,w);assert r.data.inputs==before
    return dict(case='edits',one_sided_change_splits_pair=True,cancel_redo_reissues=True,same_batch_redo_preserves_pair=True,
        conflicting_withdrawal_zero_truth_refused=True,identical_info_distinct_origin_conservatively_split=True,old_witness_reuse_refused=True,old_snapshot_immutable=True)


def audit_rejections():
    r=ok(synthetic_registry());w=ok(issue(r));rejected=[]
    assert isinstance(evaluate_small(r),UnsupportedPartition);rejected.append('unbound')
    assert isinstance(evaluate_small(r,witness=replace(w)),UnsupportedPartition);rejected.append('unissued_copy')
    from werewolf.actor_information import condition_actor_state
    from werewolf.evaluation_branch import physical_board
    private=condition_actor_state(w.source.private,lambda h:bool(h.roles[0]&1))
    try:require_bound(r,w,source=replace(w.source,private=private,physical=physical_board(w.source.public,private,w.source.physical)))
    except Pending:pass
    else:raise AssertionError('private-only override accepted')
    rejected.append('private_only_substitute')
    from werewolf.exact import replace_worlds
    try:require_bound(r,w,source=replace(w.source,public_state=private,public=replace_worlds(w.source.public,private.public_roles)))
    except Pending:pass
    else:raise AssertionError('public-only override accepted')
    rejected.append('public_only_substitute')
    for value in (-1,True,1.0,'1',None,999):
        g=deepcopy(r.data.to_game());g['revision']=value
        assert isinstance(from_game(g,r.initial),UnsupportedPartition);rejected.append('revision_'+repr(value))
    for field,value in [('active',False),('input_revision',0)]:
        g=deepcopy(r.data.to_game());graph=g['public_log']['board_graph'];graph['nodes'][graph['current']][field]=value
        assert isinstance(from_game(g,r.initial),UnsupportedPartition);rejected.append('stale_owner_'+field)
    g=deepcopy(r.data.to_game());graph=g['public_log']['board_graph'];graph['nodes'][graph['current']]['edge']['target']=5
    assert isinstance(from_game(g,r.initial),UnsupportedPartition);rejected.append('owner_path')
    other=ok(from_game(r.data.to_game(),r.initial));assert isinstance(evaluate_small(other,witness=w),UnsupportedPartition);rejected.append('other_origin')
    g=deepcopy(r.data.to_game());g['policy']['day']='max';assert isinstance(from_game(g,r.initial),UnsupportedPartition);rejected.append('max')
    assert isinstance(r.edited({'mode':'single','events':[dict(kind='co',player=3,role='villager')]}),UnsupportedPartition);rejected.append('CO')
    return dict(case='rejections',rejected=rejected,one_sided_carrier_changes_refused=True)


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>30 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result={'prefix':audit_prefix,'endgame':audit_endgame,'edits':audit_edits,'rejections':audit_rejections}[case]()
    result.update(worker_seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes());print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    start=time.monotonic();rows=[];logs=[]
    for case in ('prefix','endgame','edits','rejections'):
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(30,90-(time.monotonic()-start)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+case,flush=True)
    for pattern in ('test_cut_out_user_seven_source.py','test_cut_out_user_seven_preparation.py','test_cut_out_six_source_bridge.py'):
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture','pattern',pattern],capture_output=True,text=True,timeout=min(30,90-(time.monotonic()-start)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/user-seven-source-light.log').write_text('\n'.join(logs),encoding='utf-8')
    record=dict(cases=rows,overall_seconds=time.monotonic()-start,initial_full_forecast_executed=False,initial_max_supported=False,speed_measurement_executed=False,
        scope='typed7/W2 uniform initial/first-night source; value evaluation only <=3 alive',limits=dict(worker_seconds=30,overall_seconds=90,peak_working_set_bytes=1500000000))
    Path('benchmarks/player_match_groups/cut-out-user-seven-source-results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=record['overall_seconds'])),flush=True)

if __name__=='__main__':main()
