"""One original wolf-information-group expectation per bounded checkpoint.

The frozen base.worker body (including its scalar e.act call) is unchanged.
Only its night_plan term list is selected down to one original complete group.
"""
import argparse,hashlib,json,subprocess,sys,time,inspect
from pathlib import Path
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from benchmarks.player_match_groups import checkpoint_audit as base


def adapter_version():return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
def fields(row):return {k:row.get(k)for k in ('engine','input','adapter','root','bite','index','mode','signature','weight','value','status')}

def context(n,w):
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.evaluation_projection import project_evaluation
    saved=base.CACHE/f'inputs/dual-{n}-{w}.json'
    if n==7 and w==2 and not saved.exists():
        blob=subprocess.run(['git','show','233cc35:benchmarks/player_match_groups/checkpoint-seven-input.json'],capture_output=True,check=True,encoding='utf-8').stdout
        base.write(saved,json.loads(blob))
    path,game=base.case_input(n,w);prepared=list(base.prepared_game(game));prepared[2],prepared[3]=project_evaluation(prepared[2],prepared[3],prepared[6])
    plans={};items={}
    for root in range(1,n+1):
        engine=InformationSetForecast(prepared[5],prepared[6]);_,plan=base.night_plan(prepared,engine,root);plans[str(root)]=plan
        counts={}
        for term in plan['terms']:
            bite=term['bite'];index=counts.get(bite,0);counts[bite]=index+1
            items[f'{root}:{bite}:{index}']=dict(root=root,bite=bite,index=index,signature=term['signature'],weight=term['weight'])
    return path,game,plans,items

def import_legacy(n,w,game,plans,items,version,adapter):
    """Verify exact frozen-code/input/plan provenance before importing values."""
    input_hash=base.digest(game);parts={'oracle':{},'audit':{}};imported_units=set();partial=0
    if n==7:
        blob=subprocess.run(['git','show','233cc35:benchmarks/player_match_groups/checkpoint-seven-assessment.json'],capture_output=True,check=True,encoding='utf-8').stdout
        old=json.loads(blob)
        if(old['engine'],old['input'])!=(version,input_hash):raise ValueError('Legacy engine/input mismatch')
        records=[]
        for r in old['records']:
            if r['status']!='complete':continue
            root,bite=map(int,r['unit'].split(':'));plan=plans[str(root)]
            row=dict(engine=version,input=input_hash,target=root,bite=bite,mode=r['mode'],status='complete',action=r['weighted_contribution'],dawn=plan['dawn'],root_branches=plan['root_branches'],plan=plan,completed_terms=r['completed_terms'])
            if base.digest(base.numeric(row))!=r['numeric_digest']:raise ValueError('Committed complete-unit checksum/plan mismatch')
            records.append((root,bite,r['mode'],r['completed_terms'],r['numeric_digest'],'legacy_complete'))
        for prefix in old['partial_verified_primitives']:
            root,bite=map(int,prefix['unit'].split(':'))
            for term in prefix['terms']:
                records.append((root,bite,'audit',[(term['index'],{k:term[k]for k in ('signature','weight','value')})],base.digest(prefix),'legacy_verified_prefix'))
        source=base.digest(old)
    else:
        identity=base.digest(dict(game=game,engine=version,contract='root-day-next-uniform-bite-v1'))
        old=base.read(base.CACHE/identity/'summary.json')
        if(old['engine'],old['input'])!=(version,input_hash):raise ValueError('Small legacy engine/input mismatch')
        records=[]
        for mode in ('oracle','audit'):
            for unit,row in old['parts'][mode].items():
                if row['status']!='complete':continue
                if base.digest(base.numeric(row))!=row['numeric_digest']:raise ValueError('Legacy checksum mismatch')
                root,bite=map(int,unit.split(':'))
                if row['plan']!=plans[str(root)]:raise ValueError('Legacy full joint/branch/conditioning plan mismatch')
                records.append((root,bite,mode,row['completed_terms'],row['numeric_digest'],'legacy_complete'))
        source=base.digest(old)
    for root,bite,mode,terms,checksum,kind in records:
        for index,value in (terms if kind=='legacy_verified_prefix'else enumerate(terms)):
            key=f'{root}:{bite}:{index}';item=items[key]
            if(value['signature'],value['weight'])!=(item['signature'],item['weight']):raise ValueError('Legacy primitive binding mismatch')
            row=dict(**item,mode=mode,engine=version,input=input_hash,adapter=adapter,status='complete',value=value['value'],source=kind,source_checksum=checksum)
            row['checksum']=base.digest(fields(row));parts[mode][key]=row
            if kind=='legacy_verified_prefix':partial+=1
            else:imported_units.add((root,bite,mode))
    paired_units={u[:2]for u in imported_units if(u[0],u[1],'oracle')in imported_units and(u[0],u[1],'audit')in imported_units}
    return parts,dict(source_checksum=source,complete_unit_pairs=len(paired_units),verified_prefix_terms=partial,oracle_terms=len(parts['oracle']),audit_terms=len(parts['audit']))

def selected_worker(case_path,item,mode,output,seconds,memory,core,adapter):
    if base.engine_version()!=core or adapter_version()!=adapter:raise ValueError('Worker source changed')
    original=base.night_plan
    def select(prepared,engine,target):
        terms,metadata=original(prepared,engine,target)
        term=[t for t in terms if t['bite']==item['bite']][item['index']]
        if(term['signature'],str(term['weight']))!=(item['signature'],item['weight']):raise ValueError('Worker primitive plan changed')
        return [term],metadata
    base.night_plan=select
    # The exact old acquisition/projection/actor-conditioning/act implementation
    # executes unchanged; only the old loop's input collection has one member.
    try:return base.worker(case_path,item['root'],mode,output,seconds,memory,core,item['bite'])
    finally:base.night_plan=original

def convert(raw,item,mode,version,input_hash,adapter,plan):
    row=dict(**item,mode=mode,engine=version,input=input_hash,adapter=adapter,status='pending',value=None,reason=raw.get('reason'),seconds=raw.get('seconds'),memory=raw.get('memory'),audited_batches=raw.get('audited_batches',0),source='primitive_worker')
    if raw['status']=='complete':
        if raw.get('numeric_digest')!=base.digest(base.numeric(raw)):raise ValueError('Worker numeric checksum mismatch')
        if(raw['engine'],raw['input'],raw['target'],raw['bite'],raw['mode'])!=(version,input_hash,item['root'],item['bite'],mode):raise ValueError('Worker identity mismatch')
        if raw['plan']!=plan or len(raw['completed_terms'])!=1:raise ValueError('Worker plan/group partition changed')
        term=raw['completed_terms'][0]
        if(term['signature'],term['weight'])!=(item['signature'],item['weight']):raise ValueError('Worker conditioning changed')
        if F(raw['action'])!=F(term['weight'])*F(term['value']):raise ValueError('Worker coefficient changed')
        row.update(status='complete',value=term['value'])
    row['checksum']=base.digest(fields(row));return row

def run(n,w,total_seconds=600,*,verify_fresh=False):
    started=time.perf_counter()
    case_path,game,plans,items=context(n,w);version=base.engine_version();adapter=adapter_version();input_hash=base.digest(game)
    identity=base.digest(dict(game=game,engine=version,adapter=adapter,contract='original-wolf-information-primitive-v1'))
    folder=base.CACHE/identity;meter=folder/'meter.json';charged=base.read(meter)['consumed_seconds']if meter.exists()else 0
    parts,imports=import_legacy(n,w,game,plans,items,version,adapter);attempts=[]
    # Small-case acceptance recomputes ONE nontrivial original group in each
    # mode, comparing with the imported exact value; all other old work stays.
    reference={}
    if verify_fresh:
        candidates=[k for k in items if parts['oracle'].get(k,{}).get('value')not in(None,'0')and items[k]['root']>=3]
        key=candidates[-1]
        for mode in parts:reference[mode]=parts[mode].pop(key)
    def snapshot():
        result=dict(identity=identity,engine=version,adapter=adapter,input=input_hash,limits=dict(total_seconds=total_seconds,chunk_seconds=120,memory_bytes=1500000000),consumed_seconds=charged+time.perf_counter()-started,imports=imports,attempts=attempts,parts=parts,plans=plans,verified_primitives=[])
        roots={mode:{}for mode in parts};unit_pairs=[]
        for key in parts['oracle'].keys()&parts['audit'].keys():
            a,b=parts['oracle'][key],parts['audit'][key]
            if a['status']=='complete'and b['status']=='complete':
                if(a['signature'],a['weight'],a['value'])!=(b['signature'],b['weight'],b['value']):raise AssertionError('Independent primitive mismatch '+key)
                result['verified_primitives'].append(key)
        for root,plan in plans.items():
            for mode in parts:
                keys=[k for k in items if str(items[k]['root'])==root]
                complete=all(parts[mode].get(k,{}).get('status')=='complete'for k in keys)
                value=(sum((F(d['weight'])*F(d['value'])for d in plan['direct']),F())+sum((F(items[k]['weight'])*F(parts[mode][k]['value'])for k in keys),F()))if complete else None
                roots[mode][root]=dict(status='complete'if complete else 'pending',action=str(value)if complete else None,dawn=plan['dawn'],root_branches=plan['root_branches'])
            for bite in {t['bite']for t in plan['terms']}:
                keys=[k for k in items if items[k]['root']==int(root)and items[k]['bite']==bite]
                if all(k in result['verified_primitives']for k in keys):unit_pairs.append(f'{root}:{bite}')
        result['root_parts']=roots;result['verified_units']=sorted(unit_pairs);result['verified_targets']=[int(r)for r in plans if all(roots[m][r]['status']=='complete'for m in parts)]
        for mode in parts:result[mode]=base.aggregate(game,roots[mode])
        result['complete']=result['oracle']['status']=='complete'and result['audit']['status']=='complete'
        if result['complete']and result['oracle']!=result['audit']:raise AssertionError('Full aggregate mismatch')
        base.write(folder/'summary.json',result);base.write(meter,dict(consumed_seconds=result['consumed_seconds']));return result
    for key,item in items.items():
        for mode in ('oracle','audit'):
            if key in parts[mode]:continue
            output=folder/f'{mode}-{key.replace(":","-")}.json';record=output.with_suffix('.primitive.json')
            if record.exists():
                row=base.read(record)
                if row.get('checksum')!=base.digest(fields(row))or(row['engine'],row['input'],row['adapter'])!=(version,input_hash,adapter):raise ValueError('Saved primitive provenance mismatch')
                parts[mode][key]=row;attempts.append(dict(key=key,mode=mode,reused=True,status=row['status']));continue
            if mode=='audit'and parts['oracle'].get(key,{}).get('status')!='complete':continue
            remaining=total_seconds-(charged+time.perf_counter()-started)
            if remaining<=0:return snapshot()
            limit=min(120,remaining);begin=time.perf_counter()
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'worker','--input',str(case_path),'--item',json.dumps(item),'--mode',mode,'--output',str(output),'--seconds',str(limit),'--engine',version,'--adapter',adapter],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            while process.poll()is None:
                time.sleep(.1);used=time.perf_counter()-begin
                raw=base.read(output)if output.exists()else {}
                peak=raw.get('memory')or{};over=max(peak.get('peak_working_set_bytes',0),peak.get('peak_process_commit_bytes',0))>1550000000
                if used>=limit or charged+time.perf_counter()-started>=total_seconds or over:
                    process.kill();process.wait();raw=raw or dict(status='pending',action=None,completed_terms=[])
                    if raw.get('status')!='complete'or over:raw.update(status='pending',reason='memory_limit'if over else 'time_limit',seconds=used)
                    base.write(output,raw);break
                base.write(meter,dict(consumed_seconds=charged+time.perf_counter()-started))
            _,stderr=process.communicate();raw=base.read(output)
            if base.engine_version()!=version or adapter_version()!=adapter:raise ValueError('Source changed during trial')
            row=convert(raw,item,mode,version,input_hash,adapter,plans[str(item['root'])]);base.write(record,row)
            if mode in reference and reference[mode]['signature']==item['signature']:
                if(row['status'],row['value'])!=('complete',reference[mode]['value']):raise AssertionError('Fresh primitive differs from original whole-unit loop')
            parts[mode][key]=row;attempts.append(dict(key=key,mode=mode,reused=False,status=row['status'],seconds=time.perf_counter()-begin))
            print(json.dumps(dict(key=key,mode=mode,status=row['status'],reason=row.get('reason'),seconds=row.get('seconds'),memory=row.get('memory'))),flush=True);snapshot()
    return snapshot()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','worker']);parser.add_argument('--players',type=int,default=7);parser.add_argument('--wolves',type=int,default=2);parser.add_argument('--total',type=float,default=600);parser.add_argument('--input',type=Path);parser.add_argument('--item');parser.add_argument('--mode');parser.add_argument('--output',type=Path);parser.add_argument('--seconds',type=float);parser.add_argument('--engine');parser.add_argument('--adapter');args=parser.parse_args()
    if args.action=='worker':selected_worker(args.input,json.loads(args.item),args.mode,args.output,args.seconds,1500000000,args.engine,args.adapter)
    else:
        r=run(args.players,args.wolves,args.total);print(json.dumps({k:r[k]for k in ('identity','consumed_seconds','complete','verified_targets','verified_units','imports')}),flush=True)
