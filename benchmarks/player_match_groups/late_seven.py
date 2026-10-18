"""Bounded late-seven complete-table comparisons against corrected ordinary flow."""
import time,json,sys,threading
from fractions import Fraction as F
from dataclasses import replace
from pathlib import Path
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy,action_outcomes
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.belief_projection import project_private
from werewolf.information_set_forecast import InformationSetForecast
from benchmarks.player_match_groups.general_reuse import GeneralReuseForecast
from werewolf.calculation_budget import calculation_budget,cancellation_scope
from benchmarks.board_b_benchmark import process_memory_peak

def fixture(asymmetric=False):
 weights=(F(2,5),F(3,10),F(1,5),F(1,10))if asymmetric else(F(1,4),)*4
 b=replace(initial_board(7,1,0,1),claims=('seer',)+('latent',)*6)
 b=replace_worlds(b,tuple((w,0,1,0,q)for w,q in zip((2,4,8,16),weights)))
 s=TrueScanState(from_board(b),(b.alive,),initial_rule='none')
 rules=Rules(initial_seer='none');strategy=Strategy('random','random')
 for target in(7,6):
  b=next(o.board for o in action_outcomes(b,target,rules,strategy)if o.board.winner is None)
  s=project_private(s,b)
 return b,s,rules,strategy

def run():
 rows=[];cancel=threading.Event();done=threading.Event()
 def watch():
  while not done.wait(.1):
   p=process_memory_peak()
   if max(p['peak_working_set_bytes'],p['peak_process_commit_bytes'])>=1500000000:cancel.set()
 threading.Thread(target=watch,daemon=True).start()
 try:
  for asymmetric in(False,True):
   b,s,rules,strategy=fixture(asymmetric);reference=None
   for repeat in range(3):
    for enabled in ((False,True)if repeat%2==0 else(True,False)):
     e=GeneralReuseForecast(rules,strategy,future_reuse=True,compact_keys=True,fast_parts=True)if enabled else InformationSetForecast(rules,strategy)
     started=time.perf_counter()
     with calculation_budget(2000000,max_seconds=30),cancellation_scope(cancel):
      value=e.scalar(b,s,())
      table=tuple((t,e.act(b,s,(),t,s,None))for t in b.alive)
      branches=tuple((t,tuple((o.probability,o.board)for o in e.public_children(b,t)))for t in b.alive)
     output=(value,table,branches)
     if reference is None:reference=output
     assert output==reference
     row=dict(asymmetric=asymmetric,repeat=repeat,enabled=enabled,seconds=time.perf_counter()-started,value=str(value),table=[(t,str(v))for t,v in table],branch_mass=[(t,str(sum(q for q,_ in outcomes)))for t,outcomes in branches],stats=getattr(e,'reuse_stats',None),memory=process_memory_peak())
     rows.append(row);print(json.dumps(row),flush=True)
     Path('benchmarks/player_match_groups/late-seven-trial.json').write_text(json.dumps(rows,indent=2)+'\n')
 finally:done.set()
if __name__=='__main__':run()