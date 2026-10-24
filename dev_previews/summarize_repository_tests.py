"""Reconcile bounded runs, including early start/finished-only unittest events."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('directories',nargs='+');p.add_argument('--output',default='.artifacts/repository-coverage.json');args=p.parse_args()
manifest=json.loads(Path('.artifacts/repository-test-manifest.json').read_text(encoding='utf-8'))
canonical=lambda id:'tests.'+id if id.startswith('test_') else id
all_ids=set(map(canonical,manifest['ids']));outcomes={};diagnostics=[];limits=[];modules=[]
for directory in args.directories:
 root=Path(directory);progress=root/'summary.json'
 if not progress.exists():progress=root/'progress.json'
 runs=json.loads(progress.read_text(encoding='utf-8'))['runs']
 for index,run in enumerate(runs):
  path=root/(str(index)+'.events.jsonl');events=[]
  for line in path.read_text(encoding='utf-8').splitlines():
   try:events.append(json.loads(line))
   except json.JSONDecodeError:pass
  active=None;status={};completed={};starts=[];finished=None
  for event in events:
   kind=event['event']
   if kind=='start':
    # unittest starts the next sequential case only after finishing the prior.
    if active is not None:completed[active]=status.get(active,'success')
    active=canonical(event['id']);starts.append(active)
   elif kind in ('failure','error','skip','expected_failure'):
    key=canonical(event['id']);status[key]={'skip':'skipped'}.get(kind,kind)
    if kind in ('failure','error','skip'):diagnostics.append(dict(directory=directory,module=run['module'],**event))
   elif kind=='end':completed[canonical(event['id'])]=event['status'];active=None
   elif kind=='finished':
    finished=event
    if active is not None:completed[active]=status.get(active,'success');active=None
  if finished and finished['run']!=len(starts):raise ValueError('Uncertain event count: '+str(path))
  for id,value in completed.items():
   if id in outcomes and outcomes[id]!=value:diagnostics.append(dict(event='inconsistent_repeat',id=id,before=outcomes[id],after=value))
   outcomes[id]=value
  if run['reason']:limits.append(dict(directory=directory,module=run['module'],reason=run['reason'],active=active,unattempted=[id for id in run['unattempted'] if id not in completed]))
  modules.append(dict(module=run['module'],kind=run['kind'],seconds=run['seconds'],returncode=run['returncode'],completed=len(completed),event_file=str(path)))
for limit in limits:
 if limit['active'] in outcomes:limit['later_outcome']=outcomes[limit['active']]
summary=dict(raw_discovered=len(manifest['ids']),canonical_unique=len(all_ids),completed=len(all_ids&outcomes.keys()),statuses={s:sum(id in all_ids and value==s for id,value in outcomes.items())for s in set(outcomes.values())},outcomes=outcomes,unattempted=sorted(all_ids-outcomes.keys()),diagnostics=diagnostics,limits=limits,modules=modules,loader_errors=manifest['loader_errors'])
Path(args.output).write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items()if k not in ('outcomes','unattempted','diagnostics','limits','modules','loader_errors')}));print(json.dumps(dict(limit_modules=len(limits),diagnostics=len(diagnostics),unattempted=len(summary['unattempted']))))
