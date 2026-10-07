"""v0.3 complete future and manual phase timings, without modifying v0.2 records."""
from pathlib import Path
from fractions import Fraction
from time import perf_counter
import json
import tracemalloc
from werewolf.exact import *

configs=[(9,2,2,0,'counter'),(9,2,2,2,'counter'),(9,2,2,3,'counter'),
         (9,2,2,4,'counter'),(9,3,2,4,'none'),(9,1,8,0,'counter'),(9,1,8,8,'counter')]
results=[]
for n,w,m,k,cco in configs:
 for include in (False,True):
  solve.cache_clear();symmetric_action.cache_clear()
  policy=Strategy(include_self_bite=include);rules=Rules(True)
  tracemalloc.start();start=perf_counter()
  board=condition_claims(initial_board(n,w,m),('medium',)*k+('latent',)*(n-k),ClaimPolicy(medium=cco))
  progress=Progress(board);phases=[];initial_value=None
  while not progress.finished:
   t=perf_counter();root=build_tree(progress.board,rules,policy);ev=evaluate_tree(root,policy)
   value=ev.board_value(root);candidates={i:ev.action_value(root,i) for i in legal_targets(progress.board,rules,policy)}
   if initial_value is None:initial_value=value.village_win
   # Exercise a long possible manual history. This is a test target, not an
   # automatic UI selection or an assignment of a true role.
   targets=list(candidates)
   target=next((i for i in targets if any(o.board.winner is None for o in action_outcomes(progress.board,i,rules,policy))),targets[0])
   phases.append({'day':progress.board.day,'phase':progress.board.phase,'alive':len(progress.board.alive),
                  'seconds':round(perf_counter()-t,6),'village':str(value.village_win),'manual_target':target})
   progress=advance(progress,target,rules,policy)
  seconds=perf_counter()-start;peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
  results.append({'players':n,'wolves':w,'mediums':m,'medium_claims':k,'cco':cco,'self_bite_included':include,
                  'complete_history_seconds':round(seconds,6),'peak_python_bytes':peak,'initial_village':str(initial_value),
                  'manual_history_cumulative_village':str(progress.total_values().village_win),'phases':phases,
                  'cache_states':solve.cache_info().currsize})
out=Path('docs/v0.3-benchmark.json');out.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print('conditions',len(results),'max_seconds',max(x['complete_history_seconds'] for x in results),
      'max_peak_bytes',max(x['peak_python_bytes'] for x in results))
