"""Isolated alternating terminal-compact comparisons on finite solved cases."""
import time
START=time.perf_counter()
import os,sys,json,threading,subprocess,statistics
from pathlib import Path
from datetime import datetime,timezone


def worker(case,mode,repeat):
    from .cut_out_uniform_game_fixture import peak_bytes
    def watch():
        while True:
            if time.perf_counter()-START>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    from .cut_out_deferred_diagnostics import DeferredSmallEngine,DeferredDiagnostics,DeferredPolicy
    from .cut_out_compact_terminal import CompactTerminalSmallEngine,TerminalPolicy
    from .cut_out_seven_w2_mid import make_mid,SevenMidEngine
    from .cut_out_joint_night_forecast import ExperimentalGraph
    from .cut_out_two_nights import graph as six_graph
    from .cut_out_compact_terminal_fixture import independent_cold,terminal_table
    from .cut_out_live_medium_forecast import cold as mid_cold
    from .cut_out_deferred_alternating import fingerprint_rows
    from .cut_out_max_fixture import complete_table
    from .cut_out_uniform_game import evaluate
    from .cut_out_initial_publications import clean
    from werewolf.information_set_forecast import InformationSetActionPolicy
    from werewolf.board_future import calculation_origin,remember,source_key
    from werewolf.evaluation_branch import ActionInputs
    from werewolf.forecast_result import Forecast
    from werewolf.model_a_public import horizon_for_action
    from werewolf.exact import action_world_groups
    from werewolf.terminal_outcome import terminal_death_outcomes,TerminalOutcome
    from werewolf.calculation_budget import calculation_budget
    from types import SimpleNamespace
    class MidPolicy(DeferredPolicy):
        def project(self,b,payload,outcome,target):
            result=super().project(b,payload,outcome,target)
            if not getattr(self.engine,'_board_evidence_snapshot',False):
                request=self.engine.board_sources[source_key(result.public,ActionInputs(result.public_state,result.past,result.private,result.observer,result.physical),self.engine)]
                self.engine.trusted_requests.add(request)
            return result
    class MidCompactPolicy(TerminalPolicy,MidPolicy):pass
    class MidOff(DeferredDiagnostics,SevenMidEngine):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self.action_policy=MidPolicy(self)
    class MidOn(MidOff):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self.terminal_compact_actions=0;self.action_policy=MidCompactPolicy(self)
    imported=time.perf_counter()
    with calculation_budget(4000000,max_seconds=30):
        cap=make_mid('agree') if case=='seven-mid' else None
        graph=ExperimentalGraph(cap) if cap is not None else six_graph()
        source=graph.origin();prepared=time.perf_counter()
        if cap is None:
            forecast,engine=evaluate(graph,engine_class=CompactTerminalSmallEngine if mode=='on' else DeferredSmallEngine,capture_terminal=True)
        else:
            engine=(MidOn if mode=='on' else MidOff)(graph,cap=cap);engine.capture_terminal=True;engine.trusted_requests.add(cap.request)
            with calculation_origin(graph.data):
                remember(engine,cap.request,source)
                value=engine.solve(*source,physical=source.physical)
                actions=tuple((p,engine.act(*source[:3],p,source.private,None,physical=source.physical)) for p in source.public.alive)
                dawn=tuple((p,horizon_for_action(engine,source.public,source.public_state,source.past,p,source.private)) for p in source.public.alive)
            forecast=Forecast(value,actions,dawn)
        evaluated=time.perf_counter();table=complete_table(graph,forecast,None);formatted=time.perf_counter()
        assert engine.deferred_ledger.materialized==0
        requests=list({id(r):r for r in engine.board_sources.values()}.values())
        requests.sort(key=lambda r:(len(r.history),repr(r.facts),repr(tuple((type(op).__name__,getattr(op,'target',None),getattr(op,'observation',None)) for op in r.history))))
        cold_rows=[]
        for i in sorted({0,len(requests)//2,len(requests)-1}):
            req=requests[i];warm=req.roles()
            rebuilt=mid_cold(SimpleNamespace(registry=graph.cap.registry),req) if cap is not None else independent_cold(graph,req)
            assert rebuilt==warm;cold_rows.append((warm.public,warm.public_state,warm.private,warm.past,warm.physical))
        cold_done=time.perf_counter();result_peak=peak_bytes()
        # Both modes select the same first three all-terminal action payloads.
        selected=[]
        for b,payload,target,terminal in engine.deferred_ledger.inputs:
            if terminal and None not in action_world_groups(payload.physical,target,engine.rules,engine.strategy)[1]:selected.append((b,payload,target))
            if len(selected)==3:break
        display_rows=[]
        for b,payload,target in selected:
            rows=terminal_death_outcomes(b,payload,target,engine) if mode=='on' else InformationSetActionPolicy.outcomes(engine.action_policy,b,payload,target)
            assert rows is not None;display_rows.append(rows)
        summaries_ready=time.perf_counter();summary_peak=peak_bytes()
        def display():
            rows=[]
            for outcomes in display_rows:
                for out in outcomes:
                    full=out.materialize() if isinstance(out,TerminalOutcome) else out
                    rows.append((full.probability,full.board,full.context,terminal_table(full.board),terminal_table(full.context) if full.context is not None else None))
            return fingerprint_rows(rows)
        display_first=display();display_opened=time.perf_counter();display_peak=peak_bytes()
        display_second=display();display_reopened=time.perf_counter();assert display_first==display_second
        diagnostic=lambda:{name:fingerprint_rows(getattr(engine,name)) for name in ('full_branch_records','terminal_records','branch_records')}
        first=diagnostic();opened=time.perf_counter();diag_peak=peak_bytes()
        second=diagnostic();reopened=time.perf_counter();assert first==second
        signatures=dict(source=fingerprint_rows([(source.public,source.public_state,source.private,source.past)]),forecast=fingerprint_rows([forecast]),Table=fingerprint_rows([table]),cold=fingerprint_rows(cold_rows),terminal_display=display_first,diagnostics=first)
        assert cap is None or str(forecast.village_win)=='2/15'
    phases=dict(imports=imported-START,preprocessing=prepared-imported,Forecast=evaluated-prepared,Table=formatted-evaluated,cold=cold_done-formatted,
        terminal_summary_preparation=summaries_ready-cold_done,terminal_display_first=display_opened-summaries_ready,terminal_display_repeat=display_reopened-display_opened,
        diagnostic_first=opened-display_reopened,diagnostic_repeat=reopened-opened)
    row=dict(status='verified',case=case,mode=mode,repeat=repeat,signatures=signatures,phases=phases,
        result_Table_cold_seconds=cold_done-START,all_outputs_first_and_repeated_seconds=reopened-START,
        peak_through_result_cold_bytes=result_peak,peak_after_terminal_summary_bytes=summary_peak,peak_after_terminal_display_bytes=display_peak,peak_after_first_diagnostic_bytes=diag_peak,peak_after_all_outputs_bytes=peak_bytes(),
        values=len(engine.values),actions=len(engine.scalar_actions),sources=len(engine.board_sources),compact_actions=getattr(engine,'terminal_compact_actions',0),full_initial7_search=False,worker_seconds=time.perf_counter()-START)
    print('RESULT_JSON '+json.dumps(row),flush=True)


def run():
    path=Path('benchmarks/player_match_groups/compact-terminal-alternating-results.json')
    result=dict(status='running',recorded_utc=datetime.now(timezone.utc).isoformat(),tested_head='dd79ac0',cases=['six','seven-mid'],order='off/on,on/off,off/on,on/off;one engine per worker',runs=[],limits=dict(calculation_seconds=30,worker_seconds=120,bytes=1500000000),
        short_initial_gate='full outputs equal; Forecast median at least5% lower and lower in>=3/4 paired rounds in BOTH cases; result+cold and all-output time and peak medians no more than5% higher')
    def save():path.write_text(json.dumps(result,indent=2)+'\n')
    save()
    for case in result['cases']:
        for repeat in range(1,5):
            for mode in (('off','on') if repeat%2 else ('on','off')):
                begin=time.perf_counter();proc=subprocess.run([sys.executable,'-B','-m',__spec__.name,case,mode,str(repeat)],capture_output=True,text=True,timeout=120)
                if proc.returncode:
                    result.update(status='unverified',failure=dict(case=case,mode=mode,repeat=repeat,stderr=proc.stderr,stdout=proc.stdout));save();raise RuntimeError(result['failure'])
                row=json.loads(next(line[12:] for line in proc.stdout.splitlines() if line.startswith('RESULT_JSON ')));row['process_wall_seconds']=time.perf_counter()-begin;result['runs'].append(row);save()
                print(json.dumps({key:row[key] for key in ('case','mode','repeat','result_Table_cold_seconds','all_outputs_first_and_repeated_seconds','peak_through_result_cold_bytes')}),flush=True)
    summary={};gates={}
    for case in result['cases']:
        rows=[r for r in result['runs'] if r['case']==case];assert all(r['signatures']==rows[0]['signatures'] for r in rows)
        summary[case]={mode:{key:statistics.median(r[key] for r in rows if r['mode']==mode) for key in ('result_Table_cold_seconds','all_outputs_first_and_repeated_seconds','peak_through_result_cold_bytes','peak_after_all_outputs_bytes')}|{'phases':{phase:statistics.median(r['phases'][phase] for r in rows if r['mode']==mode) for phase in rows[0]['phases']}} for mode in ('off','on')}
        s=summary[case];wins=sum(next(r for r in rows if r['repeat']==i and r['mode']=='on')['phases']['Forecast']<next(r for r in rows if r['repeat']==i and r['mode']=='off')['phases']['Forecast'] for i in range(1,5))
        gates[case]=dict(paired_Forecast_wins=wins,stable=s['on']['phases']['Forecast']<=.95*s['off']['phases']['Forecast'] and wins>=3 and all(s['on'][k]<=1.05*s['off'][k] for k in ('result_Table_cold_seconds','all_outputs_first_and_repeated_seconds','peak_through_result_cold_bytes','peak_after_all_outputs_bytes')))
    result.update(status='verified',summary=summary,short_initial_gate_results=gates,short_initial_eligible=all(g['stable'] for g in gates.values()),all_mode_repeat_contents_equal=True)
    save();print('SHORT_INITIAL_ELIGIBLE '+str(result['short_initial_eligible']),flush=True)

if __name__=='__main__':
    if len(sys.argv)>1:worker(sys.argv[1],sys.argv[2],int(sys.argv[3]))
    else:run()
