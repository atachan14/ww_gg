"""Clock-independent prefix correctness audit; product defaults stay unchanged."""
import argparse,json,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from board_b_benchmark import ROOT,digest

def worker(a):
 sys.path.insert(0,str(Path(a.tree).resolve()))
 if a.version=='reference':
  from werewolf.board_future import GeneratedBoard
  GeneratedBoard.cacheable_evidence=lambda self:False
 if a.kind=='cache':
  import board_b_cache_audit as audit
  audit.BUDGET={**audit.BUDGET,'max_seconds':None}
  audit.worker(SimpleNamespace(tree=a.tree,cases=a.cases,version='new',sequence=a.sequence,output=a.output))
 else:
  import board_b_joint_audit as audit
  audit.BUDGET={**audit.BUDGET,'max_seconds':None}
  audit.worker(SimpleNamespace(tree=a.tree,cases=a.cases,version='new',output=a.output))

def run(a):
 output=Path(a.output).resolve();output.mkdir(parents=True,exist_ok=True)
 cases=json.loads((ROOT/'benchmarks/board_b_cache_cases.json').read_text(encoding='utf-8'))
 sequence=['base']
 for name in cases:
  if name!='base':sequence.extend([name,'base'])
 versions={};failures=[]
 for version,tree in [('before',a.before),('after',a.after),('reference',a.after)]:
  def invoke(kind,names,label):
   target=output/f'{version}-{label}.json'
   source=ROOT/'benchmarks'/('board_b_cache_cases.json' if kind=='cache' else 'board_b_cases.json')
   command=[sys.executable,'-B',str(Path(__file__).resolve()),'worker','--tree',str(Path(tree).resolve()),'--version',version,'--kind',kind,'--cases',str(source),'--output',str(target)]
   if names:command+=['--sequence',','.join(names)]
   subprocess.run(command,check=True)
   return json.loads(target.read_text(encoding='utf-8'))
  warm=invoke('cache',sequence,'mixed')
  fresh={name:invoke('cache',[name],'fresh-'+name)[0] for name in cases}
  joint=invoke('joint',None,'joint')
  for row in warm:
   if row['digest']!=fresh[row['case']]['digest']:failures.append([version,row['case'],'mixed-fresh'])
  versions[version]={'fresh':fresh,'warm':warm,'joint':joint}
 for name in cases:
  for version in ('after','reference'):
   if versions['before']['fresh'][name]['digest']!=versions[version]['fresh'][name]['digest']:failures.append([version,name,'before-fresh'])
 for name in versions['before']['joint']:
  for version in ('after','reference'):
   if versions['before']['joint'][name]['digest']!=versions[version]['joint'][name]['digest']:failures.append([version,name,'joint'])
 result={'before_revision':'899b453','cases':list(cases),'mixed_requests_per_version':len(sequence),'fresh_requests_per_version':len(cases),'versions':versions,'failures':failures,'budget':{'max_work':250000,'max_seconds':None},'note':'Correctness/count-only diagnostic. Product defaults and formal timing budgets remain unchanged. Reference disables only prefix reuse; pre-existing full-input step/kernel memoization remains. Unsupported/partial outputs are compared unchanged, not declared computed.'}
 (output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'cache_requests':3*(len(sequence)+len(cases)),'joint_cases':len(versions['before']['joint']),'failures':failures}),flush=True)
 if failures:raise AssertionError(failures)

def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
 q=s.add_parser('run');q.add_argument('--before',required=True);q.add_argument('--after',default=str(ROOT));q.add_argument('--output',required=True)
 q=s.add_parser('worker');q.add_argument('--tree',required=True);q.add_argument('--version',required=True);q.add_argument('--kind',required=True);q.add_argument('--cases',required=True);q.add_argument('--sequence');q.add_argument('--output',required=True)
 a=p.parse_args();worker(a) if a.command=='worker' else run(a)
if __name__=='__main__':main()
