"""Append-only declaration changes. Event order is recorded, not a new likelihood."""
from copy import deepcopy

def identity(e):
    return ('co',e['player']) if e['kind']=='co' else ('seer',e['day'],e['player']) if e['kind']=='seer' else ('medium',e['day'],e['player'],e['target'])

def upgrade(log):
    out=deepcopy(log);out['version']=2
    for b in out['batches']:
        for i,e in enumerate(b['events']):e.setdefault('id',f"b{b['id']}:e{i}");e.setdefault('action','assert')
    return out

def declarations(log):
    active={};known={};records=[]
    previous={}
    for slot,claims in enumerate(log['base_claims']):
        for player,role in enumerate(claims,1):
            if role!='latent' and previous.get(player)!=role:
                e={'kind':'co','player':player,'role':role,'id':f'legacy:co:{slot}:{player}','action':'assert'};records.append((slot,e))
            previous[player]=role
    for name,kind in (('base_seer','seer'),('base_medium','medium')):
        for i,r in enumerate(log[name]):records.append((2*(r['day']-1),{'kind':kind,'player':r['reporter'],'day':r['day'],'target':r['target'],'color':r['color'],'id':f"legacy:{kind}:{r['day']}:{r['reporter']}"+(f":{r['target']}" if kind=='medium' else ''),'action':'assert'}))
    for b in log['batches']:
        for e in b['events']:records.append((b['slot'],e))
    for slot,e in records:
        eid=e['id'];key=identity(e);action=e.get('action','assert')
        if eid in known:raise ValueError('宣言IDが重複しています。')
        if action in ('withdraw','change'):
            ref=e.get('ref');old=known.get(ref)
            if old is None or identity(old[1])!=key or active.get(key,(None,None))[1] is None or active[key][1]['id']!=ref:raise ValueError('後続変更の参照が一致しません。先のLogItemを確認してください。')
            active.pop(key)
        elif action!='assert':raise ValueError('宣言操作を確認してください。')
        known[eid]=(slot,e)
        if action!='withdraw':active[key]=(slot,e)
    return active,known

def project_changes(g,log):
    from .board_owned_log import prepare
    log=prepare(g,log)
    out=deepcopy(g);active,known=declarations(log)
    def claims_at(slot):
        result=['latent']*g['players']
        for key,(origin,e) in active.items():
            if key[0]=='co' and origin<=slot:result[e['player']-1]=e['role']
        return result
    for i,step in enumerate(out['history']):step['claims']=claims_at(i)
    out['claims']=claims_at(len(out['history']))
    seers=[];mediums=[]
    for key,(_,e) in active.items():
        if key[0] in ('seer','medium'):
            row={'day':e['day'],'reporter':e['player'],'target':e['target'],'color':e['color']}
            (seers if key[0]=='seer' else mediums).append(row)
    out['seer_inputs']=sorted(seers,key=lambda r:(r['day'],r['reporter']))
    out['reports']=sorted(mediums,key=lambda r:(r['day'],r['reporter'],r['target']))
    from .board_owned_log import path
    board_path=path(log['board_graph'])
    publications={}
    for key,(origin,e) in active.items():
        if key[0] not in ('seer','medium'):continue
        token=f"{key[0]}:{e['day']}:{e['player']}"+(f":{e['target']}" if key[0]=='medium' else '')
        publications[token]={'slot':origin,'board_id':board_path[origin],'published_day':1+origin//2,'published_phase':'day' if origin%2==0 else 'night'}
        if origin<len(out['history']):out['history'][origin]['claims'][e['player']-1]=key[0]
    log['report_publications']=publications
    for i,step in enumerate(out['history']):
        if 'reports' in step:step['reports']=[r for r in out['reports'] if publications[f"medium:{r['day']}:{r['reporter']}:{r['target']}"]['slot']<=i]
    # This ledger records declaration provenance, NEVER asserts that fake claims
    # were actual private acquisitions. Withdrawal does not erase provenance.
    ledger=[{'source':eid,'day':e['day'],'player':e['player'],'target':e['target'],'color':e['color'],'action':e.get('action','assert')} for eid,(_,e) in known.items() if e['kind']=='seer']
    changed={ (e['day'],e['player']) for _,e in known.values() if e['kind']=='seer' and e.get('action') in ('withdraw','change') }
    log=deepcopy(log);log['acquisition_provenance']=ledger;log['retired_input_reports']=[{'day':day,'player':p} for day,p in sorted(changed)]
    out['public_log']=log;out.pop('public_draft',None)
    return out

def transaction_changes(g,board,payload,finished=False):
    from .public_log import migrate
    log=upgrade(migrate(g))
    if 'legacy' in payload or 'delete_legacy' in payload:
        from .public_log import transaction
        legacy=deepcopy(log);legacy['version']=1;legacy['batches']=[]
        changed=transaction({**g,'public_log':legacy},board,payload,finished)
        for key in ('base_claims','base_seer','base_medium'):log[key]=changed['public_log'][key]
        return project_changes(g,log)
    if 'delete' in payload:
        bid=payload['delete'];old=next((b for b in log['batches'] if b['id']==bid),None)
        if old is None:raise ValueError('削除対象がありません。')
        log['batches'].remove(old);return project_changes(g,log)
    replacing=payload.get('replace')
    old=next((b for b in log['batches'] if b['id']==replacing),None) if replacing is not None else None
    if replacing is not None and old is None:raise ValueError('訂正対象がありません。')
    events=payload.get('events')
    if payload.get('mode') not in ('single','simultaneous') or not isinstance(events,list) or not 1<=len(events)<=128:raise ValueError('公開内容を確認してください。')
    if finished and old is None:raise ValueError('終局後の新規公開はできません。')
    slot=old['slot'] if old else len(g['history']);bid=old['id'] if old else log['next_id'];day=1+slot//2
    alive=set(range(1,g['players']+1));scan=set(alive)
    for i,s in enumerate(g['history'][:slot]):
        alive.discard(s['target'])
        if i<2*(day-1)-1:scan.discard(s['target'])
    normalized=[];seen=set()
    active,_=declarations(log)
    if not old:
        expanded=[]
        supplied={identity(e) for e in events}
        for raw in events:
            if raw.get('kind')=='co' and raw.get('action','assert')=='assert' and ('co',raw.get('player')) in active:
                previous=active['co',raw['player']][1]
                if previous['role']==raw.get('role'):continue
                raw={**raw,'action':'change','ref':previous['id']}
                for key,(_,e) in active.items():
                    if key[0] in ('seer','medium') and e['player']==raw['player'] and previous['role']==key[0] and raw['role']!=key[0] and key not in supplied:expanded.append({**e,'action':'withdraw','ref':e['id']})
            expanded.append(raw)
        events=expanded
        if not events:raise ValueError('変更がありません。')
    for i,raw in enumerate(events):
        e=deepcopy(raw);action=e.get('action','assert');kind=e.get('kind');player=e.get('player')
        if kind not in ('co','seer','medium') or type(player)is not int or player not in range(1,g['players']+1) or action not in ('assert','withdraw','change'):raise ValueError('宣言を確認してください。')
        if action!='withdraw' and player not in alive:raise ValueError('新しい申告者は生存者にしてください。')
        if kind=='co':
            if e.get('role') not in ('villager','seer','medium','hunter','wolf'):raise ValueError('COを確認してください。')
        else:
            if type(e.get('day'))is not int or not 1<=e['day']<=day or e.get('target') not in range(1,g['players']+1) or e.get('color') not in ('white','black'):raise ValueError('対象と色を入力してください。')
            acquired_alive=set(range(1,g['players']+1))
            if e['day']>1:
                for step in g['history'][:2*e['day']-3]:acquired_alive.discard(step['target'])
            if kind=='seer' and (e['target']==player or player not in acquired_alive):raise ValueError('取得時点の対象を確認してください。')
            if kind=='medium' and (e['day']<2 or len(g['history'])<2*e['day']-3 or e['target']!=g['history'][2*e['day']-4]['target']):raise ValueError('霊能の取得日と処刑対象を確認してください。')
        key=identity(e)
        if key in seen:raise ValueError('同じ宣言が重複しています。')
        seen.add(key)
        if old:
            prior=next((x for x in old['events'] if identity(x)==key),None)
            if prior is None:raise ValueError('訂正では宣言の種類・本人・取得日を変更できません。')
            e['id']=prior['id'];e['action']=prior.get('action','assert')
            if 'ref' in prior:e['ref']=prior['ref']
        else:e['id']=f'b{bid}:e{i}';e['action']=action
        if not old and action=='assert' and key in active:raise ValueError('既存宣言は変更または訂正してください。')
        normalized.append(e)
    if old:old['events']=normalized;old['mode']=payload['mode']
    else:log['batches'].append({'id':bid,'slot':slot,'day':day,'phase':'day' if slot%2==0 else 'night','mode':payload['mode'],'events':normalized});log['next_id']+=1
    return project_changes(g,log)
