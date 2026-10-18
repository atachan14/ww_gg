"""Read-only synthesis of bounded regression evidence; not a new test run."""
import json,unittest,sys
from pathlib import Path

def main():
 sys.path.insert(0,str(Path('tests').resolve()))
 norm=lambda x:x.removeprefix('tests.')
 state={};current=None
 for line in Path('.artifacts/general-full-regression.log').read_text(encoding='utf-8').splitlines():
  if line.startswith('test_')and' ... 'in line:
   current=norm(line.split(' (',1)[1].split(') ... ',1)[0]);state[current]='unverified'
   if line.endswith(' ... ok'):state[current]='passed'
   elif line.endswith(' ... FAIL')or line.endswith(' ... ERROR'):state[current]='failed'
  elif line.strip()in('ok','FAIL','ERROR')and current:state[current]='passed'if line.strip()=='ok'else'failed'
 for file in('remaining-regression.json','regression-tail.json','long-regression.json'):
  for r in json.loads(Path('benchmarks/player_match_groups/'+file).read_text())['results']:state[norm(r['test'])]=r['status']
 final=json.loads(Path('benchmarks/player_match_groups/final-group-regression.json').read_text())
 if final['successful']:
  for name in final['test_ids']:state[norm(name)]='passed'
 def flatten(s):
  for t in s:
   if isinstance(t,unittest.TestSuite):yield from flatten(t)
   else:yield norm(t.id())
 ids=sorted(set(flatten(unittest.defaultTestLoader.discover('tests'))));counts={}
 for name in ids:counts[state.get(name,'not_run')]=counts.get(state.get(name,'not_run'),0)+1
 out=dict(current_unique_tests=len(ids),counts=counts,unresolved=[dict(test=n,status=state.get(n,'not_run'))for n in ids if state.get(n)!='passed'],method='Combined bounded full-discovery prefix, isolated remainder, cancellable tail, long-case followup, and final targeted rerun after hooks/expectation maintenance. Not a single uninterrupted final-HEAD full-suite run.',no_unresolved_assertion_failures=not any(state.get(n)=='failed'for n in ids))
 Path('benchmarks/player_match_groups/regression-summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
if __name__=='__main__':main()
