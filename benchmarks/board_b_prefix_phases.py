"""Separate inclusive phase / GC diagnostic; never a normal timing baseline."""
import argparse,json,sys,time,gc
from pathlib import Path
from types import SimpleNamespace
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'benchmarks'))
import board_b_benchmark as b
p=argparse.ArgumentParser();p.add_argument('--tree',required=True);p.add_argument('--label',required=True);p.add_argument('--disable-prefix',action='store_true');a=p.parse_args()
sys.path.insert(0,str(Path(a.tree).resolve()))
from werewolf import board_future as flow
if a.disable_prefix:flow.GeneratedBoard.cacheable_evidence=lambda self:False
b.BUDGET={**b.BUDGET,'max_seconds':None}
phases={};gcdata={};gcstart={}
def callback(phase,info):
 g=info['generation']
 if phase=='start':gcstart[g]=time.perf_counter()
 else:
  d=gcdata.setdefault(str(g),{'calls':0,'seconds':0,'collected':0});d['calls']+=1;d['seconds']+=time.perf_counter()-gcstart[g];d['collected']+=info['collected']
gc.callbacks.append(callback)
def wrap(obj,name):
 old=getattr(obj,name)
 def call(*args,**kwargs):
  began=time.perf_counter()
  try:return old(*args,**kwargs)
  finally:
   d=phases.setdefault(name,{'calls':0,'inclusive_seconds':0});d['calls']+=1;d['inclusive_seconds']+=time.perf_counter()-began
 setattr(obj,name,call)
for name in ['evidence_key','kernel_snapshot','source_key','condition_recipe']:wrap(flow,name)
wrap(flow.GeneratedBoard,'_reconstruct')
out=root/'.artifacts/b-benchmark/prefix-phase-diagnostic';out.mkdir(parents=True,exist_ok=True);target=out/f'{a.label}.json'
b.worker(SimpleNamespace(tree=a.tree,case='seven-observed',version='improved',cases=str(root/'benchmarks/board_b_cases.json'),iterations=1,diagnostic='none',experiment='none',output=str(target)))
r=json.loads(target.read_text(encoding='utf-8'));r.update(phases=phases,gc=gcdata,method='Separate instrumented diagnostic with wall deadline disabled, max_work unchanged; inclusive phase times overlap and cannot be added; not a formal baseline.')
target.write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({'label':a.label,'complete':r['rows'][0]['complete'],'phases':phases,'gc':gcdata}))
