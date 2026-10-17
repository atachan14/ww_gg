"""Count generated evidence-prefix replay; never use diagnostic wall as baseline."""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from board_b_benchmark import ROOT,worker

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tree',required=True);p.add_argument('--case',default='seven');p.add_argument('--output',required=True);p.add_argument('--version',default='improved');p.add_argument('--cases',default=str(ROOT/'benchmarks/board_b_cases.json'));a=p.parse_args()
 import sys
 tree=Path(a.tree).resolve();sys.path.insert(0,str(tree))
 from werewolf import board_future as flow
 counts={'reconstruct_calls':0,'completed_request_hits':0,'completed_prefix_hits':0,'actual_recipe_applications':0}
 original=flow.GeneratedBoard._reconstruct
 def reconstruct(request):
  counts['reconstruct_calls']+=1
  if getattr(request,'_completed',()):counts['completed_request_hits']+=1
  elif getattr(request,'_parent',None) is not None and request._parent._completed:counts['completed_prefix_hits']+=1
  return original(request)
 flow.GeneratedBoard._reconstruct=reconstruct
 if hasattr(flow.GeneratedBoard,'replay_operation'):
  original_operation=flow.GeneratedBoard.replay_operation
  def apply(operation,state):
   counts['actual_recipe_applications']+=1
   return original_operation(operation,state)
  flow.GeneratedBoard.replay_operation=staticmethod(apply)
 worker(SimpleNamespace(tree=str(tree),version=a.version,diagnostic='counts',case=a.case,cases=str(Path(a.cases).resolve()),iterations=1,experiment='none',output=str(Path(a.output).resolve())))
 result=json.loads(Path(a.output).read_text(encoding='utf-8'))
 if not hasattr(flow.GeneratedBoard,'replay_operation'):
  counts['actual_recipe_applications']=result['instrumentation']['input_elements']['GeneratedBoard._reconstruct']
 result['prefix_replay_counts']=counts
 result['prefix_replay_note']='Before path actual recipe count is the sum of every complete history loop; after path counts executed replay_operation calls. _reconstruct call count includes internal prefix materialization, not necessarily a full origin replay. Pending is censored, never compared as a completed improvement. Diagnostic wall time is not formal performance evidence.'
 Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'complete':result['rows'][0]['complete'],'pending':result['rows'][0]['pending'],'prefix':counts,'digest':result['rows'][0]['semantic_digest']}))
if __name__=='__main__':main()
