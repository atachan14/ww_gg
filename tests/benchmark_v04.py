"""Run from repo: python -m tests.benchmark_v04 (or set PYTHONPATH)."""
import json,time,tracemalloc
from pathlib import Path
from werewolf.exact import *
from werewolf.reports import solve_reports,disclosure
cases=[
 (2,2,1,1,('medium',)+('latent',)*8,'equal',Strategy()),
 (2,2,1,1,('medium','medium')+('latent',)*7,'group',Strategy()),
 (2,2,1,1,('medium','medium','seer','hunter')+('latent',)*5,'group',Strategy(fake_reports='random')),
 (2,2,2,2,('medium','medium')+('latent',)*7,'equal',Strategy('random','random',False,'random')),
 (2,2,2,2,('medium','medium','medium')+('latent',)*6,'group',Strategy(include_self_bite=True)),
 (3,2,1,1,('medium','seer','hunter')+('latent',)*6,'group',Strategy(fake_reports='random')),
 (2,2,0,0,('medium',)*4+('latent',)*5,'group',Strategy(fake_reports='random')),
 (2,0,2,2,('seer','hunter')+('latent',)*7,'group',Strategy()),
 (1,8,0,0,('medium',)*9,'equal',Strategy()),
 (2,7,0,0,('medium',)*9,'group',Strategy(fake_reports='random')),
]
results=[]
for w,m,s,h,claims,model,strategy in cases:
 solve.cache_clear();symmetric_action.cache_clear();solve_reports.cache_clear();disclosure.cache_clear()
 tracemalloc.start();start=time.perf_counter();b=initial_board(9,w,m,s,h);initial_worlds=len(b.worlds)
 policy=ClaimPolicy(villager='none',medium='none',seer='none',hunter='none')
 b=group_initial_board(b,claims,policy) if model=='group' else condition_claims(b,claims,policy)
 p=Progress(b);phases=[]
 while not p.finished:
  b=p.board;root=build_tree(b,Rules(True),strategy);evaluation=evaluate_tree(root,strategy)
  values={i:evaluation.action_value(root,i) for i in legal_targets(b,Rules(True),strategy)}
  target=next((i for i in values if any(o.board.winner is None for o in action_outcomes(b,i,Rules(True),strategy))),next(iter(values)))
  phases.append({'day':b.day,'phase':b.phase,'alive':len(b.alive),'legal_targets':len(values),'worlds':len(b.worlds),'value':str(evaluation.board_value(root).village_win),'target':target})
  p=advance(p,target,Rules(True),strategy)
 elapsed=time.perf_counter()-start;current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
 entry={'roles':{'villager':9-w-m-s-h,'wolf':w,'medium':m,'seer':s,'hunter':h},'claims':claims,'model':model,'strategy':strategy.__dict__,'initial_worlds':initial_worlds,'seconds':elapsed,'python_peak_bytes':peak,'phases':phases,'final_cumulative':str(p.total_values().village_win),'solve_cache':str(solve_reports.cache_info()),'disclosure_cache':str(disclosure.cache_info())}
 results.append(entry);print(json.dumps({'done':len(results),'seconds':elapsed,'peak':peak,'phases':len(phases)}),flush=True)
Path('docs/v0.4-benchmark.json').write_text(json.dumps({'method':'Cold caches, tracemalloc Python allocation peak, all target values at each Board, full continuing manual history to terminal; future report subtrees exhaustively evaluated by exact memoized recursion','cases':results},ensure_ascii=False,indent=2),encoding='utf-8')
