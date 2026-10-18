"""Small seven-player known-medium trial; no factory admission assumed."""
import time,json,threading
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy,action_outcomes
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.belief_projection import project_private
from werewolf.information_set_forecast import InformationSetForecast
from benchmarks.player_match_groups.general_reuse import GeneralReuseForecast
from werewolf.calculation_budget import calculation_budget,cancellation_scope
from benchmarks.board_b_benchmark import process_memory_peak

def fixture(deaths=(7,6)):
 b=replace(initial_board(7,1,1,1),claims=('seer','latent','latent','latent','medium','latent','latent'))
 b=replace_worlds(b,tuple((w,16,1,0,F(1,3))for w in(2,4,8)))
 s=TrueScanState(from_board(b),(b.alive,),initial_rule='none');rules=Rules(initial_seer='none');strategy=Strategy('random','random')
 for target in deaths:
  b=next(o.board for o in action_outcomes(b,target,rules,strategy)if o.board.winner is None);s=project_private(s,b)
 return b,s,rules,strategy

def run():
 rows=[];cancel=threading.Event();done=threading.Event()
 def watch():
  while not done.wait(.1):
   p=process_memory_peak()
   if max(p['peak_working_set_bytes'],p['peak_process_commit_bytes'])>=1500000000:cancel.set()
 threading.Thread(target=watch,daemon=True).start()
 try:
  for deaths in((7,6),(6,7)):
   b,s,rules,strategy=fixture(deaths);reference=None
   for repeat in range(2):
    for enabled in((False,True)if repeat==0 else(True,False)):
     e=GeneralReuseForecast(rules,strategy,future_reuse=True,compact_keys=True,fast_parts=True)if enabled else InformationSetForecast(rules,strategy)
     started=time.perf_counter()
     with calculation_budget(2000000,max_seconds=30),cancellation_scope(cancel):
      value=e.scalar(b,s,());table=tuple((t,e.act(b,s,(),t,s,None))for t in b.alive)
      branches=tuple((t,e.public_children(b,t))for t in b.alive)
     result=value,table,branches
     if reference is None:reference=result
     assert result==reference
     row=dict(deaths=deaths,repeat=repeat,enabled=enabled,seconds=time.perf_counter()-started,value=str(value),table=[(t,str(v))for t,v in table],branch_mass=[(t,str(sum(o.probability for o in bs)))for t,bs in branches],stats=getattr(e,'reuse_stats',None),memory=process_memory_peak())
     rows.append(row);print(json.dumps(row),flush=True)
     Path('benchmarks/player_match_groups/late-seven-medium-trial.json').write_text(json.dumps(rows,indent=2)+'\n')
 finally:done.set()
if __name__=='__main__':run()