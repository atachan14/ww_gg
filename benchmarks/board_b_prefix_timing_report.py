"""Compact report retaining every ordinary-budget trial and separate controls."""
import json,statistics,hashlib
from datetime import datetime,timezone,timedelta
from board_b_report import validate
from pathlib import Path
root=Path(__file__).resolve().parents[1]
files={'formal':root/'.artifacts/b-benchmark/prefix-formal/summary.json','three_way':root/'.artifacts/b-benchmark/prefix-three-way/summary.json'}
out={}
for label,path in files.items():
 if not path.exists():continue
 d=json.loads(path.read_text(encoding='utf-8'));verified=validate(d);groups={};starts=[];ends=[]
 for rec in d['records']:
  name=(f"{rec['repetition']:02d}-{rec['case']}-{rec['control']}.json" if 'control' in rec else f"{rec['repetition']:02d}-{rec['case']}-{rec['version']}-{rec['diagnostic']}-{rec['experiment']}.json")
  raw=path.parent/name
  if raw.exists():
   end=datetime.fromtimestamp(raw.stat().st_mtime,timezone.utc);ends.append(end);starts.append(end-timedelta(seconds=rec['subprocess_wall_seconds']))
 for record in d['records']:
  version=record.get('control',record['version'])
  for row in record['rows']:
   key=f"{record['case']}/{version}/{row['cache']}"
   groups.setdefault(key,[]).append((record,row))
 summaries={}
 for key,values in groups.items():
  complete=[row for _,row in values if row['complete']]
  def stats(xs):
   if not xs:return None
   q=statistics.quantiles(xs,n=4,method='inclusive') if len(xs)>1 else xs*3
   return {'median':statistics.median(xs),'iqr':q[2]-q[0],'raw':xs}
  summaries[key]={'requested':len(values),'completed':len(complete),'censored':len(values)-len(complete),'wall_seconds':stats([r['seconds'] for r in complete]),'cpu_seconds':stats([r['cpu_seconds'] for r in complete]),'low_background_wall_seconds':stats([row['seconds'] for rec,row in values if row['complete'] and not row['high_background_load']]),'background_percent':stats([rec['estimated_background_cpu_percent'] for rec,_ in values]),'whole_worker_peak_working_set_bytes':stats([rec['process_memory_peak']['peak_working_set_bytes'] for rec,_ in values]),'whole_worker_peak_commit_bytes':stats([rec['process_memory_peak']['peak_process_commit_bytes'] for rec,_ in values]),'pending_reasons':[r['pending'] for _,r in values if not r['complete']]}
 out[label]={'verified_complete_results_against_fixed_exact_values':verified,'observation_window_utc':{'approx_start':min(starts).isoformat(),'approx_end':max(ends).isoformat(),'method':'Raw record mtime minus subprocess elapsed; approximate interval, not event log.'},'source':str(path.relative_to(root)),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'versions':d.get('versions',{'before':'899b45316249b8c3ed5fdacbcada039b693dc95e','prefix':'45d0df353c38d85aa50ff8369887fccf5c5a6039','disabled':'45d0df353c38d85aa50ff8369887fccf5c5a6039 + diagnostic-only prefix disable'}),'budget':d['budget'],'method':d['method'],'mismatches':d['mismatches'],'semantic_digests':d.get('completed_semantic_digests',d.get('digests')),'summaries':summaries}
out['interpretation']={'decision':'No demonstrated CPU or wall-time benefit from prefix addition. Do not adopt it as a performance fix. Keep the 899b453 ownership fix and existing exact step/kernel reuse as the safe alternative. Current prefix implementation remains in local history for reproducibility; no rollback is claimed.','memory_scope':'Native whole-worker peak includes startup, semantic output and both cold/warm requests, not isolated per-request allocations.','load_scope':'Every trial retained; background >10% flagged separately. Short cases can be dominated by startup/background estimation; no causal attribution from one sample.','prior_failure':'Previous ordinary 681-test run had one real HTTP 20-second budget failure; successful current isolated timings cannot erase that result.','semantic_scope':'No relaxed budgets or expected values. Complete result digests compared exactly; Pending censored separately.'}
phase=root/'.artifacts/b-benchmark/prefix-phase-diagnostic'
out['phase_diagnostics']={}
for q in phase.glob('*.json'):
 r=json.loads(q.read_text(encoding='utf-8'));row=r['rows'][0]
 assert row['complete'] and row['semantic_digest']==out['formal']['semantic_digests']['seven-observed']
 out['phase_diagnostics'][q.stem]={'complete':row['complete'],'semantic_digest':row['semantic_digest'],'phases':r['phases'],'gc':r['gc'],'method':r['method']}
(root/'benchmarks/results/board_b_prefix_timing.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({label:len(data['summaries']) for label,data in out.items() if 'summaries' in data}))
