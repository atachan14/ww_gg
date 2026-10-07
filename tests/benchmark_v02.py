"""Measure complete exact future evaluation and every phase to termination."""
from fractions import Fraction
from pathlib import Path
from time import perf_counter
import tracemalloc
import json
from werewolf.exact import *
from app import create_app

results=[]
for wolves in range(1,5):
 for included in (False,True):
  solve.cache_clear(); symmetric_action.cache_clear()
  policy=Strategy(include_self_bite=included); rules=Rules(True)
  tracemalloc.start(); started=perf_counter()
  progress=Progress(initial_board(9,wolves)); phases=[]
  while not progress.finished:
   t=perf_counter(); root=build_tree(progress.board,rules,policy)
   ev=evaluate_tree(root,policy)
   value=ev.board_value(root)
   actions=[ev.action_value(root,i) for i in progress.board.alive]
   phases.append({'day':progress.board.day,'phase':progress.board.phase,'alive':len(progress.board.alive),
                  'seconds':round(perf_counter()-t,6),'village':str(value.village_win)})
   progress=advance(progress,progress.board.alive[0],rules,policy)
  seconds=perf_counter()-started; peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
  results.append({'players':9,'wolves':wolves,'self_bite_included':included,'complete_history_seconds':round(seconds,6),
                  'peak_python_bytes':peak,'phases':phases,'final_village':str(progress.total_values().village_win),
                  'cached_public_states':solve.cache_info().currsize})
print(json.dumps(results,indent=2))
Path('docs/v0.2-benchmark.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
