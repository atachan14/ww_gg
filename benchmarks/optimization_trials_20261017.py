"""Retain ordinary-budget optimization trials separately from diagnostics."""
import json,statistics,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from board_b_benchmark import ROOT
from board_b_report import validate

def stats(values):
 if not values:return None
 q=statistics.quantiles(values,n=4,method='inclusive') if len(values)>1 else values*3
 return {'median':statistics.median(values),'iqr':q[2]-q[0],'raw':values}

def main():
 reference=json.loads((ROOT/'.artifacts/b-benchmark/prefix-formal/summary.json').read_text(encoding='utf-8'))
 result={}
 for name,folder in [('prefix_removal','prefix-removal-formal'),('complete_role_validation','role-validation-formal')]:
  path=ROOT/f'.artifacts/b-benchmark/{folder}/summary.json'
  if not path.exists():continue
  data=json.loads(path.read_text(encoding='utf-8'));verified=validate(data,reference);groups={};starts=[];ends=[]
  for rec in data['records']:
   raw=path.parent/f"{rec['repetition']:02d}-{rec['case']}-{rec['version']}-{rec['diagnostic']}-{rec['experiment']}.json"
   end=datetime.fromtimestamp(raw.stat().st_mtime,timezone.utc);ends.append(end);starts.append(end-timedelta(seconds=rec['subprocess_wall_seconds']))
   for row in rec['rows']:groups.setdefault(f"{rec['case']}/{rec['version']}/{row['cache']}",[]).append((rec,row))
  summaries={}
  for key,values in groups.items():
   done=[row for _,row in values if row['complete']]
   summaries[key]={'requested':len(values),'complete':len(done),'censored':len(values)-len(done),'wall_seconds':stats([r['seconds'] for r in done]),'cpu_seconds':stats([r['cpu_seconds'] for r in done]),'quiet_wall_seconds':stats([row['seconds'] for rec,row in values if row['complete'] and not row['high_background_load']]),'background_percent':stats([r['estimated_background_cpu_percent'] for r,_ in values]),'whole_worker_peak_working_set_bytes':stats([r['process_memory_peak']['peak_working_set_bytes'] for r,_ in values]),'whole_worker_peak_commit_bytes':stats([r['process_memory_peak']['peak_process_commit_bytes'] for r,_ in values]),'pending_reasons':[row['pending'] for _,row in values if not row['complete']]}
  result[name]={'versions':data['versions'],'budget':data['budget'],'method':data['method'],'exact_complete_results_checked':verified,'semantic_digests':data['completed_semantic_digests'],'mismatches':data['mismatches'],'source':str(path.relative_to(ROOT)),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'approx_observation_window_utc':[min(starts).isoformat(),max(ends).isoformat()],'window_method':'Raw worker file mtime minus subprocess wall, approximate interval.','summaries':summaries}
 probes={}
 for name in ['cached','uncached']:
  p=ROOT/f'.artifacts/b-benchmark/role-validation-{name}-probe.json'
  if p.exists():
   d=json.loads(p.read_text(encoding='utf-8'));probes[name]={'rows':[{k:v for k,v in row.items() if k!='semantic'} for row in d['rows']],'cache_info':d['complete_role_cache_info'],'memory':d['process_memory_peak'],'scope':'Single normal-budget diagnostic control, not an interleaved formal baseline.'}
 result['single_probe_controls']=probes
 p=ROOT/'.artifacts/b-benchmark/role-validation-profile.json'
 if p.exists():
  d=json.loads(p.read_text(encoding='utf-8'));assert d['rows'][0]['complete'] and d['rows'][0]['semantic_digest']==reference['completed_semantic_digests']['seven-observed'];result['separate_profile']={'complete':d['rows'][0]['complete'],'semantic_digest':d['rows'][0]['semantic_digest'],'cache_info':d['complete_role_cache_info'],'top_self_functions':d['profile']['functions'][:12],'scope':'Instrumented diagnostic with max_seconds=None; never a normal timing improvement claim.'}
 for label,folder in [('cache_audit','role-validation-cache-audit'),('joint_audit','role-validation-joint-audit')]:
  path=ROOT/f'.artifacts/b-benchmark/{folder}/summary.json'
  if not path.exists():continue
  d=json.loads(path.read_text(encoding='utf-8'));assert not d['failures']
  if label=='cache_audit':
   result[label]={'cases':d['cases'],'input_immutability_checked':d['input_immutability_checked'],'evaluations':sum(len(v['fresh'])+len(v['warm']) for v in d['versions'].values()),'failures':d['failures'],'pending_preserved':{name:{k:r['pending'] for k,r in v['fresh'].items() if r['pending']} for name,v in d['versions'].items()}}
  else:result[label]={'cases':d['cases'],'evaluations':sum(len(v) for v in d['versions'].values()),'failures':d['failures']}
  result[label].update(source=str(path.relative_to(ROOT)),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 result['interpretation']={'prefix_removal':'Adopt for approximately 2 MiB lower native whole-worker peak and simpler ownership; CPU/wall benefit not established. Preserve edit memo init=False and existing exact step/kernel reuse.','complete_role_validation':'Adoption requires formal timings, exact semantic checks, full regression and HTTP validation. Only immutable complete role input values are shared; no symmetry grouping or secret-history projection is introduced.','scope':'No budget or expected value relaxation. All trials retained; background >10% flagged, never silently dropped. Whole-worker native high-water marks include startup and cold+warm output.'}
 validation=ROOT/'benchmarks/results/optimization_trials_20261017_validation.json'
 if validation.exists():
  result['final_validation']=json.loads(validation.read_text(encoding='utf-8'))
  result['interpretation']['complete_role_validation']=result['final_validation']['adoption']['complete_role_validation']
 (ROOT/'benchmarks/results/optimization_trials_20261017.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v.get('exact_complete_results_checked') for k,v in result.items() if 'summaries' in v}))
if __name__=='__main__':main()
