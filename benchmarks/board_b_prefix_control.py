"""Serial three-way prefix diagnostic control under unchanged request budgets."""
import argparse,json,subprocess,sys,time,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'benchmarks'))
import board_b_benchmark as b
p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--tree');p.add_argument('--case');p.add_argument('--output');p.add_argument('--disable-prefix',action='store_true');a=p.parse_args()
if a.worker:
 from types import SimpleNamespace
 sys.path.insert(0,str(Path(a.tree).resolve()))
 if a.disable_prefix:
  from werewolf.board_future import GeneratedBoard
  GeneratedBoard.cacheable_evidence=lambda self:False
 b.worker(SimpleNamespace(tree=a.tree,case=a.case,version='improved',cases=str(root/'benchmarks/board_b_cases.json'),iterations=2,diagnostic='none',experiment='none',output=a.output))
else:
 out=root/'.artifacts/b-benchmark/prefix-three-way';out.mkdir(parents=True,exist_ok=True)
 trees=root/'.artifacts/b-benchmark/prefix-formal/snapshots'
 records=[]
 for rep in range(5):
  for case in ['seven','seven-observed'] if rep%2==0 else ['seven-observed','seven']:
   order=['before','prefix','disabled'] if rep%2==0 else ['disabled','prefix','before']
   for label in order:
    target=out/f'{rep:02d}-{case}-{label}.json'
    cmd=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--tree',str(trees/('new' if label=='before' else 'improved')),'--case',case,'--output',str(target)]
    if label=='disabled':cmd.append('--disable-prefix')
    before=b.system_cpu();began=time.perf_counter();subprocess.run(cmd,cwd=root,check=True,timeout=120);after=b.system_cpu()
    r=json.loads(target.read_text(encoding='utf-8'));r.update(repetition=rep,control=label,subprocess_wall_seconds=time.perf_counter()-began)
    busy=((after[1]-before[1])-(after[0]-before[0]))/1e7;total=(after[1]-before[1])/1e7
    r['estimated_background_cpu_percent']=100*max(0,busy-r['worker_cpu_total'])/total
    for row in r['rows']:row['high_background_load']=r['estimated_background_cpu_percent']>10
    target.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');records.append(r)
    print(json.dumps({'rep':rep,'case':case,'control':label,'cold':r['rows'][0]['seconds'],'cpu':r['rows'][0]['cpu_seconds'],'complete':r['rows'][0]['complete'],'background':r['estimated_background_cpu_percent']}),flush=True)
 groups={};digests={};mismatches=[]
 for r in records:
  for row in r['rows']:
   groups.setdefault(f"{r['case']}/{r['control']}/{row['cache']}",[]).append(row)
   if row['complete']:
    first=digests.setdefault(r['case'],row['semantic_digest'])
    if first!=row['semantic_digest']:mismatches.append([r['case'],r['control'],r['repetition']])
 result={'budget':b.BUDGET,'method':'Fresh serial processes; three-way alternating before/prefix/prefix-disabled; same current harness and fixed archived sources. Prefix-disabled changes only cacheable_evidence; retains existing step/kernel memoization. Five repetitions; two cases; cold and warm. All trials retained.','summaries':{k:b.summarize(v) for k,v in groups.items()},'digests':digests,'mismatches':mismatches,'records':records}
 (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 if mismatches:raise AssertionError(mismatches)
