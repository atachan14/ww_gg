"""All-medium six-player rescue comparison: per-run30s, stage180s,1.5GB."""
import time,json,threading,copy
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from werewolf.board_flow import BoardData
from werewolf.board_roles import prepare_evaluation
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.model_a_public import public_forecast
from werewolf.private_adapter import evaluate_private_table
from werewolf.actor_information import condition_actor_state
from werewolf.exact import Strategy,Values
from werewolf.player_view import build_public_view,ResultFrame,ViewScope
from werewolf.seer_future_uniform import FuturePending
from werewolf.calculation_budget import calculation_budget,cancellation_scope,CalculationCancelled
from benchmarks.board_b_benchmark import process_memory_peak
from .probe_plan_reachability import fixture
from .general_reuse import GeneralReuseForecast
from .planned_reuse import PlannedReuseForecast,OverCapReuseForecast
from .checkpoint_audit import encode

class MeteredMemo(dict):
 def __init__(self):super().__init__();self.lookups=0;self.hits=0
 def __contains__(self,key):
  self.lookups+=1;found=super().__contains__(key);self.hits+=int(found);return found

def memo_kinds(memo):
 result=Counter()
 for key in memo:
  raw=getattr(key,'values',key)
  if isinstance(raw,tuple)and raw:
   first=raw[0]
   kind=first if isinstance(first,str)else first[0]if isinstance(first,tuple)and first and isinstance(first[0],str)else'labelled'
  else:kind='other'
  result[kind]+=1
 return dict(result)

def main():
 started=time.perf_counter();done=threading.Event();cancel=threading.Event();rows=[];stops=[]
 def watch():
  while not done.wait(.05):
   p=process_memory_peak()
   if max(p['peak_working_set_bytes'],p['peak_process_commit_bytes'])>=1500000000:stops.append('memory_limit');cancel.set();return
   if time.perf_counter()-started>=180:stops.append('stage_limit');cancel.set();return
 threading.Thread(target=watch,daemon=True).start()
 out=Path('benchmarks/player_match_groups/medium-rescue-comparison.json')
 def save():out.write_text(json.dumps(dict(scope='actual6 medium5 wolf1 allmediumCO; no seer rollout; isolated comparison engines',per_run_seconds=30,stage_limit_seconds=180,memory_limit_bytes=1500000000,elapsed=time.perf_counter()-started,stop=stops,results=rows),indent=2)+'\n')
 try:
  app,c,g=fixture('medium');data=BoardData.from_game(g);roles=data.roles();b=roles.board;rules=roles.rules;strategy=Strategy(**g['policy']);kind,(s,past)=prepare_evaluation(g,b,rules,strategy,max_work=100000,max_seconds=10)
  assert kind=='prior';before=copy.deepcopy((g,b,s,past));reference=None
  for repeat in range(2):
   for mode in(('original','current','planned','selective')if repeat==0 else('selective','planned','current','original')):
    if cancel.is_set():raise CalculationCancelled()
    cold_start=time.perf_counter();cls={'original':InformationSetForecast,'current':GeneralReuseForecast,'planned':PlannedReuseForecast,'selective':OverCapReuseForecast}[mode]
    e=cls(rules,strategy,**({}if mode=='original'else dict(future_reuse=True,compact_keys=True,fast_parts=True)))
    e.values=MeteredMemo();e.action_values=MeteredMemo()
    for warmth in('cold','warm'):
     begin=cold_start if warmth=='cold'else time.perf_counter();old_reuse=dict(getattr(e,'reuse_stats',{}));old_plan=dict(getattr(e,'plan_stats',{}));old_selection=dict(getattr(e,'selection_stats',{}));old_memo=(e.values.lookups,e.values.hits,e.action_values.lookups,e.action_values.hits)
     with calculation_budget(2000000,max_seconds=30),cancellation_scope(cancel):
      with patch('werewolf.local_reuse.make_public_engine',lambda *a,**kw:e),patch('werewolf.local_reuse.make_view_engine',lambda *a,**kw:e):
       public=public_forecast(b,s,past,rules,strategy,max_seconds=30)
       assert not isinstance(public,FuturePending),public
       wolf=evaluate_private_table(b,'wolf',[1],[],rules,strategy,game_state=g,max_seconds=30)
      frame=ResultFrame(ViewScope.public(data),'complete')
      full=build_public_view(data,roles,b,frame,state=g,event_history=b.history,alive=b.alive,action_values={t:Values(v,1-v)for t,v in public.action_values},by_dawn_values=dict(public.by_dawn_values))
      own=condition_actor_state(s,lambda h:bool(h.roles[1]&1))
      # Internal conditional-payoff diagnostic; no new medium personal UI.
      medium=(e.solve(b,s,past,own,None),tuple((t,e.act(b,s,past,t,own,None))for t in b.alive))
      branches=tuple((t,e.public_children(b,t,s),e.physical_children(b,t))for t in b.alive)
      table=tuple(p.to_legacy_row()for p in full.players)
     result=(public,table,wolf,medium,branches)
     if reference is None:reference=result
     assert result==reference,(mode,warmth,'complete numerical mismatch')
     assert before==(g,b,s,past)
     assert all(sum(o.probability for o in pub)==1 and sum(o.probability for o in phys)==1 for t,pub,phys in branches)
     memo=dict(value_lookups=e.values.lookups-old_memo[0],value_hits=e.values.hits-old_memo[1],action_lookups=e.action_values.lookups-old_memo[2],action_hits=e.action_values.hits-old_memo[3])
     row=dict(mode=mode,repeat=repeat,warmth=warmth,seconds=time.perf_counter()-begin,complete_equal=True,output=encode(dict(forecast=public,table=table,wolf=wolf,medium_conditional=medium)),branch_masses=[(t,str(sum(o.probability for o in pub)),str(sum(o.probability for o in phys)))for t,pub,phys in branches],reuse={k:v-old_reuse.get(k,0)for k,v in getattr(e,'reuse_stats',{}).items()},plan={k:v-old_plan.get(k,0)for k,v in getattr(e,'plan_stats',{}).items()},selection={k:v-old_selection.get(k,0)for k,v in getattr(e,'selection_stats',{}).items()},memo=memo,value_key_kinds=memo_kinds(e.values),expansions=dict(e.expansions),memory=process_memory_peak())
     rows.append(row);save();print(json.dumps({k:row[k]for k in('mode','repeat','warmth','seconds','reuse','plan','memo','value_key_kinds')}),flush=True)
 except Exception as error:stops.append(type(error).__name__+':'+str(error));save();raise
 finally:done.set();save()
 print(json.dumps(dict(completed=len(rows),seconds=time.perf_counter()-started,memory=process_memory_peak())),flush=True)
if __name__=='__main__':main()