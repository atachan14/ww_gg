"""Finite quiet-window numerical/performance comparison, small original fixtures."""
import time,json,threading,copy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from collections import Counter
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.model_a_public import public_forecast
from werewolf.seer_view_forecast import seer_forecast
from werewolf.seer_future_uniform import FuturePending
from werewolf.exact import Values,legal_targets
from werewolf.player_view import build_public_view,ResultFrame
from werewolf.calculation_budget import calculation_budget,cancellation_scope,CalculationCancelled,CalculationBudgetExceeded
from benchmarks.board_b_benchmark import process_memory_peak
from .extension_cases import fixture,prepare_game
from .general_reuse import GeneralReuseForecast
from .planned_reuse import PlannedReuseForecast
from .checkpoint_audit import encode

OUT=Path('benchmarks/player_match_groups/bounded-plan-comparison.json')

def main():
 stage=time.perf_counter();done=threading.Event();cancel=threading.Event();rows=[];stop=[]
 def guard():
  while not done.wait(.05):
   peak=process_memory_peak()
   if max(peak['peak_working_set_bytes'],peak['peak_process_commit_bytes'])>=1500000000:stop.append('memory_limit');cancel.set();return
   if time.perf_counter()-stage>=300:stop.append('stage_time_limit');cancel.set();return
 threading.Thread(target=guard,daemon=True).start()
 def save():
  OUT.write_text(json.dumps(dict(scope='small5/6 original fixtures; no app factory changes',per_run_seconds=30,stage_seconds_limit=300,memory_limit_bytes=1500000000,elapsed=time.perf_counter()-stage,stop=stop,results=rows),indent=2)+'\n')
 try:
  for name,options in(('five-uniform',{}),('six-uniform',dict(n=6,wolves=2)),('five-different-reports',dict(mediums=1))):
   c,g=fixture(**options)
   if name=='five-different-reports':
    # Different white recipients retain real asymmetric public evidence.
    payload={'claims':g['claims'],'seers':[{'day':1,'reporter':1,'target':4,'color':'white'},{'day':1,'reporter':2,'target':5,'color':'white'}],'mediums':[]}
    assert c.post('/table-publish',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps(payload)}).status_code==200
    from .extension_cases import game_of
    g=game_of(c)
   data,roles,b,s,past,rules,strategy,view=prepare_game(g);before=copy.deepcopy((g,b,s,past));reference=None
   for repeat in range(2):
    modes=('original','current','planned')if repeat==0 else('planned','current','original')
    for mode in modes:
     cls={'original':InformationSetForecast,'current':GeneralReuseForecast,'planned':PlannedReuseForecast}[mode]
     e=cls(rules,strategy,**({}if mode=='original'else dict(future_reuse=True,compact_keys=True,fast_parts=True)))
     for warmth in('cold','warm'):
      started=time.perf_counter();before_stats=dict(getattr(e,'reuse_stats',{}));before_plan=dict(getattr(e,'plan_stats',{}))
      with calculation_budget(2000000,max_seconds=30),cancellation_scope(cancel):
       with patch('werewolf.local_reuse.make_public_engine',lambda *a,**kw:e),patch('werewolf.local_reuse.make_view_engine',lambda *a,**kw:e):
        forecast=public_forecast(b,s,past,rules,strategy,max_seconds=30)
        if isinstance(forecast,FuturePending):raise RuntimeError('incomplete public '+forecast.reason)
        own=next(tuple(a for a in h.acquisitions if a.player==1)for h in s.hypotheses if h.roles[2]&1)
        seer=seer_forecast(b,1,own,rules,strategy,scan_state=s,past=past,max_seconds=30)
        if isinstance(seer,FuturePending):raise RuntimeError('incomplete seer '+seer.reason)
        wolf=next(h.roles[0]for h in s.hypotheses)
        private=e.evaluate(b,s,past,mask=wolf)
       full=build_public_view(data,roles,b,ResultFrame(view.scope,'complete'),state=g,event_history=b.history,alive=b.alive,action_values={t:Values(v,1-v)for t,v in forecast.action_values},by_dawn_values=dict(forecast.by_dawn_values))
       table=tuple(p.to_legacy_row()for p in full.players)
       branches=tuple((t,e.public_children(b,t,s),e.physical_children(b,t))for t in legal_targets(b,rules,strategy))
      result=(forecast,table,seer,private,branches)
      if reference is None:reference=result
      assert result==reference,(name,mode,warmth,'complete output mismatch')
      assert (g,b,s,past)==before
      assert all(sum(o.probability for o in public)==1 and sum(o.probability for o in physical)==1 for t,public,physical in branches)
      stats={k:v-before_stats.get(k,0)for k,v in getattr(e,'reuse_stats',{}).items()}
      plan={k:v-before_plan.get(k,0)for k,v in getattr(e,'plan_stats',{}).items()}
      row=dict(case=name,mode=mode,repeat=repeat,warmth=warmth,seconds=time.perf_counter()-started,exact_all_results=True,output=encode(dict(forecast=forecast,table=table,seer=seer,wolf=private)),branch_masses=[(t,str(sum(o.probability for o in public)),str(sum(o.probability for o in physical)))for t,public,physical in branches],reuse=stats,plan=plan,memory=process_memory_peak())
      rows.append(row);save();print(json.dumps({k:row[k]for k in('case','mode','repeat','warmth','seconds','reuse','plan')}),flush=True)
 except (CalculationCancelled,CalculationBudgetExceeded,Pending,RuntimeError,AssertionError)as error:
  stop.append(type(error).__name__+':'+str(error));save();raise
 finally:done.set();save()
 print(json.dumps(dict(complete=True,rows=len(rows),seconds=time.perf_counter()-stage,memory=process_memory_peak())),flush=True)
if __name__=='__main__':main()