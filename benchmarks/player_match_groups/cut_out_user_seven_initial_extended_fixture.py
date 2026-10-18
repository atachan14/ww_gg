"""Explicitly coordinated initial7 correctness check: 60s/route, 150s worker."""
from pathlib import Path
from fractions import Fraction as F
from unittest.mock import patch
import json,sys,time,os,threading,subprocess,pickle,gc
from .cut_out_user_seven_source import *
from .cut_out_user_seven_source_fixture import ok
from .cut_out_candidate_context_fixture import zero_legacy
from .cut_out_max_fixture import complete_table
from .cut_out_uniform_game import _evaluate,OfficialLabelledEngine

BASE=Path(os.environ.get('WW_SEVEN_INITIAL_ARTIFACTS','.artifacts/user-seven-initial-60'))
CURRENT={}

def save(name,value):
    BASE.mkdir(exist_ok=True);p=BASE/(name+'.json');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)

def scale(e):
    return dict(value_cache=len(e.values),scalar_actions=len(e.scalar_actions),branch_records=len(e.branch_records),
        terminal_records=len(e.terminal_records),generated_boards=len(e.board_sources),costs=dict(e.costs),
        inherited_contexts=len(e.inherited_groups.contexts) if e.inherited_groups else 0)

def audit():
    from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,reset_diagnostics,budget_stop
    from werewolf.board_future import same_role_board
    from .cut_out_two_nights import restore_terminals
    prepared=ok(prepare(comparison_game()[1]));r=ok(from_game(prepared.data.to_game(),prepared));w=ok(issue(r));require_bound(r,w)
    row=dict(status='unverified',paths={},forecast_equal=None,Table_joint_equal=None,branch_mass_comparisons=None,terminal_readbacks=None)
    engines={};stack,mocks=zero_legacy()
    with stack,patch.object(CutOutUniformEngine,'legacy_large_groups',side_effect=AssertionError('legacy root')) as legacy:
        for name,reference in (('inherited',False),('independent',True)):
            start=time.monotonic();CURRENT.clear();CURRENT.update(name=name,status='running',mocks=mocks,legacy=legacy)
            save(name,dict(status='running'))
            def factory(graph,**kwargs):
                engine=OfficialLabelledEngine(graph,**kwargs) if reference else SevenInitialEngine(graph,witness=w,**kwargs)
                CURRENT['engine']=engine;return engine
            reset_diagnostics()
            try:result=_evaluate(r,official_reference=reference,max_seconds=60,capture_terminal=True,engine_class=factory)
            except CalculationBudgetExceeded:result=UnsupportedPartition('comparison evaluation budget exhausted')
            except Pending as error:result=UnsupportedPartition('common flow pending: '+error.reason)
            e=CURRENT.get('engine');part=dict(seconds=time.monotonic()-start,scale=scale(e) if e else {},budget_stop=budget_stop())
            if isinstance(result,UnsupportedPartition):part.update(status='unverified',reason=result.reason)
            else:
                f,e=result;table=complete_table(r,f,None)
                part.update(status='complete',village_win=str(f.village_win),actions={p:str(v) for p,v in f.action_values},Table_repr=repr(table))
                # Persist scalar/Table results even if later serialization fails.
                save(name,part)
                # Persist the complete route result BEFORE starting its peer.
                with (BASE/(name+'-complete.pickle')).open('wb') as handle:
                    pickle.dump(dict(forecast=f,table=table,branches=e.branch_records,terminals=e.terminal_records),handle,protocol=5)
                engines[name]=(f,e,table)
            part.update(canonical_calls=sum(m.call_count for m in mocks[:2]),CandidateRules_calls=mocks[2].call_count,legacy_root_calls=legacy.call_count)
            row['paths'][name]=part;save(name,part);save('checkpoint',row)
            CURRENT['status']='saved';print(json.dumps(dict(progress=name,result={k:v for k,v in part.items() if k!='Table_repr'})),flush=True)
            # An incomplete engine cannot participate in equality checks.
            # Drop its large graph before evaluating the other route.
            if isinstance(result,UnsupportedPartition):
                CURRENT.pop('engine',None);del e;gc.collect()
        if len(engines)==2:
            actual,e,table=engines['inherited'];reference,full,old_table=engines['independent']
            assert actual==reference;row['forecast_equal']=True
            assert table==old_table;row['Table_joint_equal']=True;save('checkpoint',row)
            try:
                with calculation_budget(1000000,max_seconds=20):
                    old={(b,s,p,o,t):outs for b,s,p,o,t,outs in full.branch_records};count=0
                    for b,s,p,o,t,outs in e.branch_records:
                        assert old[b,s,p,o,t]==outs and sum((q for q,_ in outs),F())==1;count+=1
                    row['branch_mass_comparisons']=count;save('checkpoint',row)
                    small,_=restore_terminals(e,max_publication_day=4);large,_=restore_terminals(full,max_publication_day=4)
                    for key,(mass,state,request) in small.items():
                        old_mass,old_state,_=large[key]
                        assert mass==old_mass and state.public_state==old_state.public_state and state.private==old_state.private and state.past==old_state.past
                        assert same_role_board(state.public,old_state.public) and same_role_board(state.physical,old_state.physical) and request.origin is r.origin
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
            reason='worker_timeout' if time.monotonic()-start>150 else 'memory_limit' if peak_bytes()>1500000000 else None
            if reason:
                save('watchdog',dict(status='unverified',reason=reason,current=CURRENT.get('name'),scale=scale(CURRENT['engine']) if 'engine'in CURRENT else {},seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes(),canonical_calls=sum(m.call_count for m in CURRENT.get('mocks',())[:2]),CandidateRules_calls=CURRENT['mocks'][2].call_count if 'mocks'in CURRENT else None,legacy_root_calls=CURRENT['legacy'].call_count if 'legacy'in CURRENT else None));os._exit(124 if reason=='worker_timeout' else 137)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    row=audit();row.update(worker_seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes());save('final',row);print(json.dumps(row),flush=True)

def main():
    global BASE
    if len(sys.argv)>1:return worker()
    BASE=Path(str(BASE)+'-'+str(time.time_ns()))
    os.environ['WW_SEVEN_INITIAL_ARTIFACTS']=str(BASE)
    try:
        p=subprocess.run([sys.executable,'-B','-m',__spec__.name,'worker'],capture_output=True,text=True,timeout=151)
        BASE.mkdir(exist_ok=True);(BASE/'worker.log').write_text(p.stdout+p.stderr)
        row=json.loads((BASE/'final.json').read_text()) if p.returncode==0 else dict(status='unverified',exit_code=p.returncode,error=p.stderr[-3000:])
    except subprocess.TimeoutExpired:row=dict(status='unverified',reason='outer_worker_timeout')
    row['saved_paths']={name:json.loads((BASE/(name+'.json')).read_text()) for name in ('inherited','independent') if (BASE/(name+'.json')).exists()}
    if (BASE/'watchdog.json').exists():
        row['watchdog']=json.loads((BASE/'watchdog.json').read_text())
        name=row['watchdog'].get('current')
        if name and row['saved_paths'].get(name,{}).get('status')=='running':
            row['saved_paths'][name]=dict(row['watchdog'],note='worker-wide limit; not standalone route memory')
    row.update(forecast_equal=row.get('forecast_equal'),Table_joint_equal=row.get('Table_joint_equal'),branch_mass_comparisons=row.get('branch_mass_comparisons'),terminal_readbacks=row.get('terminal_readbacks'))
    row.update(limits=dict(evaluation_seconds=60,worker_seconds=150,peak_working_set_bytes=1500000000,readback_seconds=20),speed_measurement_executed=False,
        remaining_cost='Board constructor two full-history validation passes; unchanged',tested_parent='2b55a5675452854edd2a1fa88a79bb36bce96b93')
    Path('benchmarks/player_match_groups/cut-out-user-seven-initial-60-results.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)

if __name__=='__main__':main()