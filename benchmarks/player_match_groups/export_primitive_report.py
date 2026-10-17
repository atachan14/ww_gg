"""Export saved primitive-window results; no continuation evaluation."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from benchmarks.player_match_groups import checkpoint_audit as base
from benchmarks.player_match_groups import primitive_checkpoint as primitive
_,game=base.case_input(7,2);core=base.engine_version();adapter=primitive.adapter_version()
identity=base.digest(dict(game=game,engine=core,adapter=adapter,contract='original-wolf-information-primitive-v1'))
folder=base.CACHE/identity;s=base.read(folder/'summary.json')
records=[]
for mode in ('oracle','audit'):
    for key,row in s['parts'][mode].items():
        assert row['checksum']==base.digest(primitive.fields(row))
        record=dict(key=key,**row)
        if row['source']=='primitive_worker':
            raw_path=folder/f'{mode}-{key.replace(":","-")}.json'
            if raw_path.exists():
                raw=base.read(raw_path);record['raw_stats']=raw.get('stats',{});record['raw_expansions']=raw.get('expansions',{})
        records.append(record)
counts={mode:sum(r['status']=='complete'for r in s['parts'][mode].values())for mode in ('oracle','audit')}
fresh=[r for r in records if r['source']=='primitive_worker']
peak=max((max((r.get('memory')or{}).get('peak_working_set_bytes',0),(r.get('memory')or{}).get('peak_process_commit_bytes',0))for r in fresh),default=0)
import statistics
mode_samples={mode:[r['seconds']for r in fresh if r['mode']==mode and r['status']=='complete']for mode in ('oracle','audit')}
timing={mode:dict(completed=len(samples),minimum=min(samples)if samples else None,median=statistics.median(samples)if samples else None,maximum=max(samples)if samples else None)for mode,samples in mode_samples.items()}
result=dict(identity=identity,engine=core,adapter=adapter,input=s['input'],cache_directory=str(folder),limits=s['limits'],consumed_seconds=s['consumed_seconds'],imports=s['imports'],planned_primitives=sum(len(p['terms'])for p in s['plans'].values()),complete_counts=counts,verified_primitives=s['verified_primitives'],verified_units=s['verified_units'],verified_targets=s['verified_targets'],complete=s['complete'],oracle=s['oracle'],audit=s['audit'],root_parts=s['root_parts'],peak_worker_bytes=peak,max_chunk_wall_seconds=max((a.get('seconds',0)for a in s['attempts']),default=0),timing=timing,remaining_counts={m:sum(len(p['terms'])for p in s['plans'].values())-counts[m]for m in counts},new_complete_values=sum(r['status']=='complete'for r in fresh),pending_new=[r for r in fresh if r['status']!='complete'],records=records)
base.write(ROOT/'benchmarks/player_match_groups/primitive-seven-assessment.json',result)
print(json.dumps({k:result[k]for k in ('identity','consumed_seconds','complete','planned_primitives','complete_counts','verified_targets','peak_worker_bytes','new_complete_values','max_chunk_wall_seconds')}),flush=True)
