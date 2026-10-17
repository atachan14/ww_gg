"""Report hash/physical follow-up trials without treating Pending as completion."""
import json,statistics,hashlib
from pathlib import Path
from board_b_benchmark import ROOT
from board_b_report import validate

def stats(v):
 if not v:return None
 q=statistics.quantiles(v,n=4,method='inclusive') if len(v)>1 else v*3
 return {'median':statistics.median(v),'iqr':q[2]-q[0],'raw':v}

def summarize(records,label_name):
 groups={}
 for r in records:
  for row in r['rows']:groups.setdefault(f"{r['case']}/{r[label_name]}/{row['cache']}",[]).append((r,row))
 return {key:{'requested':len(v),'completed':sum(row['complete'] for _,row in v),'censored':sum(not row['complete'] for _,row in v),'wall':stats([row['seconds'] for _,row in v if row['complete']]),'cpu':stats([row['cpu_seconds'] for _,row in v if row['complete']]),'whole_worker_peak_bytes':stats([r['process_memory_peak']['peak_working_set_bytes'] for r,_ in v]),'whole_worker_peak_commit_bytes':stats([r['process_memory_peak']['peak_process_commit_bytes'] for r,_ in v]),'background_percent':stats([r.get('estimated_background_cpu_percent',r.get('background_cpu_percent')) for r,_ in v]),'quiet_wall':stats([row['seconds'] for r,row in v if row['complete'] and r.get('estimated_background_cpu_percent',r.get('background_cpu_percent'))<=10]),'pending':[row['pending'] for _,row in v if not row['complete']]} for key,v in groups.items()}

def main():
 out={}
 p=ROOT/'.artifacts/b-benchmark/verified-hash-repeat/summary.json';d=json.loads(p.read_text(encoding='utf-8'));assert not d['failures'];out['whole_board_hash']={'decision':'rejected: negligible time difference and increased memory','summaries':summarize(d['records'],'label'),'failures':d['failures'],'source':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 for label,folder in [('prehashed_role_fields','prehashed-role-formal'),('single_lookup','single-lookup-formal')]:
  p=ROOT/f'.artifacts/b-benchmark/{folder}/summary.json'
  if not p.exists():continue
  d=json.loads(p.read_text(encoding='utf-8'));checked=validate(d)
  for r in d['records']:
   for row in r['rows']:
    if r['case']=='nine-seer-none':
     value=row['semantic']['result'];assert row['complete'] and value['village_win']=={'fraction':'503/1620'} and len(value['action_values'])==9 and len(value['by_dawn_values'])==9
  out[label]={'decision':'rejected: small time reduction, higher memory; nine-player CPU unchanged' if label=='prehashed_role_fields' else 'pending: formal timing and full regression/HTTP required before adoption','versions':d['versions'],'budget':d['budget'],'exact_complete_results_checked':checked,'mismatches':d['mismatches'],'semantic_digests':d['completed_semantic_digests'],'summaries':summarize(d['records'],'version'),'source':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 out['single_probes']={}
 for name in ['physical-projection-probe','physical-projection-baseline-probe','hypothesis-hash-probe','hypothesis-hash-baseline-probe','verified-hash-nine-probe']:
  p=ROOT/f'.artifacts/b-benchmark/{name}.json';d=json.loads(p.read_text(encoding='utf-8'));out['single_probes'][name]={'rows':[{k:row[k] for k in ['cache','seconds','cpu_seconds','complete','pending','semantic_digest']} for row in d['rows']],'memory':d['process_memory_peak'],'scope':'Single normal-budget probe; never formal performance evidence.'}
 out['scope']={'baseline':'f3a12bdb150f0a6edde520314b561a1778ecac3c','normal_budget':{'max_work':250000,'max_seconds':20},'nine_player':'CO-group seer-none only, no future seer acquisition; not an all-abilities standard nine-player village. Equal-model Pending retained separately.','native_memory':'Whole-worker high-water mark including startup and cold/warm results, not per-request allocation totals.','no_edit_probes':'The first single-lookup edit script failed before writing. Both probes are named invalid-no-edit and excluded.'}
 validation=ROOT/'benchmarks/results/hash_physical_trials_20261017_validation.json'
 if validation.exists():
  out['validation']=json.loads(validation.read_text(encoding='utf-8'))
  out['single_lookup']['decision']=out['validation']['decision']
 (ROOT/'benchmarks/results/hash_physical_trials_20261017.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v.get('exact_complete_results_checked') for k,v in out.items() if 'summaries' in v}))
if __name__=='__main__':main()
