"""Bounded public seven/W2 intermediate comparison. Never initial Forecast."""
from pathlib import Path
from fractions import Fraction as F
from unittest.mock import patch
import json,sys,time,os,threading,subprocess
from .cut_out_user_seven_source import *
from .cut_out_user_seven_source_fixture import ok,invariants
from .cut_out_candidate_context_fixture import zero_legacy
from .cut_out_max_fixture import complete_table


def audit(endgame=False):
    from werewolf.calculation_budget import calculation_budget
    from werewolf.board_future import same_role_board
    from .cut_out_two_nights import restore_terminals
    r=ok(synthetic_registry(endgame=endgame));w=ok(issue(r))
    stack,mocks=zero_legacy()
    with stack,patch.object(CutOutUniformEngine,'legacy_large_groups',side_effect=AssertionError('legacy root')) as legacy:
        actual=evaluate_intermediate(r,witness=w,max_seconds=5)
        if isinstance(actual,UnsupportedPartition):return dict(status='unverified',stage='inherited',reason=actual.reason)
        expected=evaluate_intermediate(r,witness=w,official_reference=True,max_seconds=5)
        if isinstance(expected,UnsupportedPartition):return dict(status='unverified',stage='independent',reason=expected.reason)
        result,engine=actual;reference,full=expected
        assert result==reference
        assert complete_table(r,result,None)==complete_table(r,reference,None)
        with calculation_budget(300000,max_seconds=5):
            old_branches={(b,s,own,observer,target):outcomes for b,s,own,observer,target,outcomes in full.branch_records}
            compared=0
            for b,s,own,observer,target,outcomes in engine.branch_records:
                assert old_branches[b,s,own,observer,target]==outcomes
                assert sum((q for q,_ in outcomes),F())==1
                compared+=1
            small,small_stats=restore_terminals(engine,max_publication_day=3)
            large,large_stats=restore_terminals(full,max_publication_day=3)
            for key,(mass,state,request) in small.items():
                old_mass,old,_=large[key]
                assert mass==old_mass and state.public_state==old.public_state and state.private==old.private and state.past==old.past
                assert same_role_board(state.public,old.public) and same_role_board(state.physical,old.physical)
                assert request.origin is r.origin
        assert all(m.call_count==0 for m in mocks) and legacy.call_count==0
    initial=ok(from_game(r.initial.data.to_game(),r.initial));iw=ok(issue(initial))
    assert isinstance(evaluate_intermediate(initial,witness=iw),UnsupportedPartition)
    assert isinstance(evaluate_intermediate(r,witness=w,view=OwnView(1,'wolf')),UnsupportedPartition)
    assert compared and small
    return dict(status='verified',alive=len(w.source.public.alive),village_win=str(result.village_win),
        actions={p:str(v) for p,v in result.action_values},complete_Table_joint_equal=True,branch_mass_comparisons=compared,
        terminal_readbacks=len(small),both_carrier_swaps=invariants(w),canonical_calls=0,CandidateRules_calls=0,legacy_root_calls=0,
        initial_seven_refused=True,private_entry_refused=True,group_stats=dict(engine.inherited_groups.stats))


def worker(endgame):
    from .cut_out_uniform_game_fixture import peak_bytes
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>15:os._exit(124)
            if peak_bytes()>1500000000:os._exit(137)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    result=audit(endgame);result.update(seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1]=='tiny')
    rows=[]
    for case in ('tiny','five'):
        try:
            p=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=16)
            row=json.loads(p.stdout) if p.returncode==0 else dict(status='unverified',exit_code=p.returncode,error=p.stderr[-2000:])
        except subprocess.TimeoutExpired:row=dict(status='unverified',reason='worker_timeout')
        row['case']=case;rows.append(row);print(json.dumps(row),flush=True)
    record=dict(cases=rows,initial_full_forecast_executed=False,speed_measurement_executed=False,
        limits=dict(evaluation_seconds=5,worker_seconds=15,peak_working_set_bytes=1500000000))
    Path('benchmarks/player_match_groups/cut-out-user-seven-intermediate-results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    if any(r['status']!='verified' for r in rows):sys.exit(1)

if __name__=='__main__':main()