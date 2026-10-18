"""One coordinated initial7 uniform comparison, strict bounded worker."""
from pathlib import Path
from fractions import Fraction as F
from unittest.mock import patch
import json,sys,time,os,threading,subprocess
from .cut_out_user_seven_source import *
from .cut_out_user_seven_source_fixture import ok
from .cut_out_candidate_context_fixture import zero_legacy
from .cut_out_max_fixture import complete_table


def audit():
    from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded
    from werewolf.board_future import same_role_board
    from .cut_out_two_nights import restore_terminals
    prepared=ok(prepare(comparison_game()[1]));r=ok(from_game(prepared.data.to_game(),prepared));w=ok(issue(r))
    row=dict(status='unverified',target='actual saved7 C3/M1/S1/W2/H0 public; only three policies max->random',
        initial_worlds=len(w.source.public.worlds),initial_hypotheses=len(w.source.private.hypotheses),paths={},
        forecast_equal=None,Table_joint_equal=None,branch_mass_comparisons=None,terminal_readbacks=None)
    stack,mocks=zero_legacy();engines={}
    with stack,patch.object(CutOutUniformEngine,'legacy_large_groups',side_effect=AssertionError('legacy root')) as legacy:
        for name,reference in (('inherited',False),('independent',True)):
            start=time.monotonic();result=evaluate_initial(r,witness=w,official_reference=reference,max_seconds=5)
            if isinstance(result,UnsupportedPartition):row['paths'][name]=dict(status='unverified',reason=result.reason,seconds=time.monotonic()-start)
            else:
                f,e=result;engines[name]=(f,e);row['paths'][name]=dict(status='complete',seconds=time.monotonic()-start,village_win=str(f.village_win))
            print(json.dumps(dict(progress=name,result=row['paths'][name])),flush=True)
        if len(engines)==2:
            actual,engine=engines['inherited'];reference,full=engines['independent']
            assert actual==reference;row['forecast_equal']=True
            assert complete_table(r,actual,None)==complete_table(r,reference,None);row['Table_joint_equal']=True
            try:
                with calculation_budget(300000,max_seconds=5):
                    old_branches={(b,s,own,observer,target):outcomes for b,s,own,observer,target,outcomes in full.branch_records}
                    count=0
                    for b,s,own,observer,target,outcomes in engine.branch_records:
                        assert old_branches[b,s,own,observer,target]==outcomes
                        assert sum((q for q,_ in outcomes),F())==1;count+=1
                    row['branch_mass_comparisons']=count
                    small,_=restore_terminals(engine,max_publication_day=4);large,_=restore_terminals(full,max_publication_day=4)
                    for key,(mass,state,request) in small.items():
                        old_mass,old,_=large[key]
                        assert mass==old_mass and state.public_state==old.public_state and state.private==old.private and state.past==old.past
                        assert same_role_board(state.public,old.public) and same_role_board(state.physical,old.physical)
                        assert request.origin is r.origin
                    assert count and small;row['terminal_readbacks']=len(small);row['status']='verified'
            except CalculationBudgetExceeded:row['comparison_reason']='readback_budget_exhausted'
        row.update(canonical_calls=sum(m.call_count for m in mocks[:2]),CandidateRules_calls=mocks[2].call_count,legacy_root_calls=legacy.call_count)
        assert all(m.call_count==0 for m in mocks) and legacy.call_count==0
    return row


def worker():
    from .cut_out_uniform_game_fixture import peak_bytes
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>30:os._exit(124)
            if peak_bytes()>1500000000:os._exit(137)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    result=audit();result.update(worker_seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker()
    try:
        p=subprocess.run([sys.executable,'-B','-m',__spec__.name,'worker'],capture_output=True,text=True,timeout=31)
        Path('.artifacts/user-seven-initial-comparison.log').write_text(p.stdout+p.stderr,encoding='utf-8')
        row=json.loads(p.stdout.splitlines()[-1]) if p.returncode==0 else dict(status='unverified',exit_code=p.returncode,error=p.stderr[-2000:])
    except subprocess.TimeoutExpired:row=dict(status='unverified',reason='worker_timeout')
    row.update(limits=dict(evaluation_seconds=5,worker_seconds=30,peak_working_set_bytes=1500000000),speed_measurement_executed=False)
    Path('benchmarks/player_match_groups/cut-out-user-seven-initial-results.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(row),flush=True)

if __name__=='__main__':main()