"""Finite checkpoint audit split by day intervention and next uniform bite.

Offline only. No partial unit becomes a completed action/forecast.
"""
import json,sys,time,subprocess
from pathlib import Path
from fractions import Fraction as F
from . import checkpoint_audit as base


numeric=base.numeric

def run(n,w,*,total_seconds=600,chunk_seconds=120,memory_bytes=1500000000):
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.evaluation_projection import project_evaluation
    case_path,game=base.case_input(n,w);prepared=list(base.prepared_game(game));prepared[2],prepared[3]=project_evaluation(prepared[2],prepared[3],prepared[6])
    version=base.engine_version();identity=base.digest(dict(game=game,engine=version,contract='root-day-next-uniform-bite-v1'))
    folder=base.CACHE/identity;meter=folder/'meter.json';summary_path=folder/'summary.json'
    charged=json.loads(meter.read_text())['consumed_seconds']if meter.exists()else 0
    started=time.perf_counter();parts={'oracle':{},'audit':{}};attempts=[];plans={}
    for root in range(1,n+1):
        e=InformationSetForecast(prepared[5],prepared[6])
        _,plan=base.night_plan(prepared,e,root);plans[str(root)]=plan
    def roots(mode):
        rows={}
        for root,plan in plans.items():
            bites=sorted({t['bite']for t in plan['terms']});required=[f'{root}:{b}'for b in bites]
            complete=all(k in parts[mode]and parts[mode][k]['status']=='complete'for k in required)
            value=(sum((F(d['weight'])*F(d['value'])for d in plan['direct']),F())+
                   sum((F(parts[mode][k]['action'])for k in required),F()))if complete else None
            rows[root]=dict(status='complete'if complete else 'pending',action=str(value)if complete else None,dawn=plan['dawn'],root_branches=plan['root_branches'])
        return rows
    def snapshot():
        summary=dict(identity=identity,engine=version,input=base.digest(game),limits=dict(total_seconds=total_seconds,chunk_seconds=chunk_seconds,memory_bytes=memory_bytes),consumed_seconds=charged+time.perf_counter()-started,plans=plans,parts=parts,attempts=attempts,verified_units=[])
        for key in parts['oracle'].keys()&parts['audit'].keys():
            a=parts['oracle'][key];b=parts['audit'][key]
            if a['status']=='complete'and b['status']=='complete':
                for field in ('action','dawn','root_branches','plan','completed_terms'):
                    if a[field]!=b[field]:raise AssertionError(f'Independent unit mismatch {key} {field}')
                summary['verified_units'].append(key)
        summary['verified_units'].sort();summary['root_parts']={mode:roots(mode)for mode in parts}
        for mode in parts:summary[mode]=base.aggregate(game,summary['root_parts'][mode])
        summary['verified_targets']=[int(t)for t in plans if summary['root_parts']['oracle'][t]['status']=='complete'and summary['root_parts']['audit'][t]['status']=='complete']
        summary['complete']=summary['oracle']['status']=='complete'and summary['audit']['status']=='complete'
        if summary['complete']and summary['oracle']!=summary['audit']:raise AssertionError('Full aggregate mismatch')
        base.write(summary_path,summary);base.write(meter,{'consumed_seconds':summary['consumed_seconds']})
        return summary
    stop=False
    for root,plan in plans.items():
        for bite in sorted({t['bite']for t in plan['terms']}):
            key=f'{root}:{bite}'
            for mode in ('oracle','audit'):
                output=folder/f'{mode}-{root}-{bite}.json'
                if output.exists():
                    row=base.read(output)
                    if(row.get('engine'),row.get('input'),row.get('target'),row.get('bite'),row.get('mode'))!=(version,base.digest(game),int(root),bite,mode):raise ValueError('Checkpoint provenance mismatch')
                    if row['status']=='complete'and row.get('numeric_digest')!=base.digest(numeric(row)):raise ValueError('Checkpoint numeric checksum mismatch')
                    parts[mode][key]=row;attempts.append(dict(unit=key,mode=mode,reused=True,status=row['status']));continue
                if mode=='audit'and parts['oracle'].get(key,{}).get('status')!='complete':continue
                remaining=total_seconds-(charged+time.perf_counter()-started)
                if remaining<=0:stop=True;break
                limit=min(chunk_seconds,remaining);worker_started=time.perf_counter()
                process=subprocess.Popen([sys.executable,str(Path(base.__file__).resolve()),'worker','--input',str(case_path),'--target',root,'--bite',str(bite),'--mode',mode,'--output',str(output),'--seconds',str(limit),'--memory',str(memory_bytes),'--engine',version],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                while process.poll()is None:
                    time.sleep(.1);used=time.perf_counter()-worker_started
                    row=base.read(output)if output.exists()else {}
                    peak=row.get('memory')or{}
                    over_memory=max(peak.get('peak_working_set_bytes',0),peak.get('peak_process_commit_bytes',0))>memory_bytes+50000000
                    if used>=limit or charged+time.perf_counter()-started>=total_seconds or over_memory:
                        process.kill();process.wait()
                        row=row or dict(target=int(root),bite=bite,mode=mode,engine=version,input=base.digest(game),action=None,dawn=None,root_branches=None)
                        # A fully computed record may survive process cleanup at
                        # deadline; incomplete computation always stays pending.
                        if row.get('status')!='complete'or over_memory:
                            row.update(status='pending',reason='memory_limit'if over_memory else 'time_limit',seconds=used)
                        base.write(output,row);break
                    base.write(meter,{'consumed_seconds':charged+time.perf_counter()-started})
                _,stderr=process.communicate();row=base.read(output)
                if base.engine_version()!=version:raise ValueError('Engine changed during trial')
                if row.get('plan')is not None and row['plan']!=plan:raise AssertionError('Joint/physical/actor policy plan changed in worker')
                if stderr:row['worker_log']=stderr
                if row['status']=='complete':row['numeric_digest']=base.digest(numeric(row))
                base.write(output,row);parts[mode][key]=row
                attempts.append(dict(unit=key,mode=mode,reused=False,status=row['status'],seconds=time.perf_counter()-worker_started))
                print(json.dumps(dict(unit=key,mode=mode,status=row['status'],reason=row.get('reason'),seconds=row.get('seconds'),memory=row.get('memory'))),flush=True)
                snapshot()
            if stop:break
        if stop:break
    return snapshot()

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--players',type=int,default=7);parser.add_argument('--wolves',type=int,default=2);parser.add_argument('--total',type=float,default=600);args=parser.parse_args()
    result=run(args.players,args.wolves,total_seconds=args.total)
    print(json.dumps({k:result[k]for k in ('identity','consumed_seconds','complete','verified_targets','verified_units')}),flush=True)
