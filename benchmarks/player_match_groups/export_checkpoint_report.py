"""Export already computed results only; never evaluates a continuation."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from benchmarks.player_match_groups import checkpoint_audit as base
from benchmarks.player_match_groups.deep_checkpoint import numeric
_,game=base.case_input(7,2);version=base.engine_version()
identity=base.digest(dict(game=game,engine=version,contract='root-day-next-uniform-bite-v1'))
folder=base.CACHE/identity;summary=base.read(folder/'summary.json')
assert summary['engine']==version and summary['input']==base.digest(game)
records=[]
for mode in ('oracle','audit'):
    for unit,row in summary['parts'][mode].items():
        if row['status']=='complete':assert row['numeric_digest']==base.digest(numeric(row))
        records.append(dict(unit=unit,mode=mode,status=row['status'],reason=row.get('reason'),seconds=row.get('seconds'),weighted_contribution=row.get('action'),completed_terms=row.get('completed_terms',[]),audited_batches=row.get('audited_batches',0),memory=row.get('memory'),numeric_digest=row.get('numeric_digest')))
partial_verified=[]
for unit in summary['parts']['oracle'].keys()&summary['parts']['audit'].keys():
    a=summary['parts']['oracle'][unit];b=summary['parts']['audit'][unit]
    if a['status']=='complete'and b['status']=='complete':continue
    prefix=[]
    for index,(left,right)in enumerate(zip(a.get('completed_terms',[]),b.get('completed_terms',[]))):
        assert left==right
        prefix.append(dict(index=index,**left))
    if prefix:partial_verified.append(dict(unit=unit,terms=prefix))
complete_oracle=sum(r['status']=='complete'for r in records if r['mode']=='oracle')
complete_audit=sum(r['status']=='complete'for r in records if r['mode']=='audit')
peak=max((max((r['memory']or{}).get('peak_working_set_bytes',0),(r['memory']or{}).get('peak_process_commit_bytes',0))for r in records),default=0)
report=dict(identity=identity,engine=version,input=summary['input'],cache_directory=str(folder),limits=summary['limits'],consumed_seconds=summary['consumed_seconds'],complete=summary['complete'],planned_units=sum(len({t['bite']for t in p['terms']})for p in summary['plans'].values()),complete_oracle_units=complete_oracle,complete_audit_units=complete_audit,verified_units=summary['verified_units'],verified_targets=summary['verified_targets'],root_parts=summary['root_parts'],oracle=summary['oracle'],audit=summary['audit'],peak_worker_bytes=peak,max_chunk_wall_seconds=max((a.get('seconds',0)for a in summary['attempts']),default=0),records=records,partial_verified_primitives=partial_verified)
base.write(ROOT/'benchmarks/player_match_groups/checkpoint-seven-assessment.json',report)
base.write(ROOT/'benchmarks/player_match_groups/checkpoint-seven-input.json',game)
print(json.dumps({k:report[k]for k in ('identity','consumed_seconds','complete','planned_units','complete_oracle_units','complete_audit_units','verified_targets','peak_worker_bytes','max_chunk_wall_seconds')}),flush=True)
