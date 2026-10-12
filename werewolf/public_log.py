"""Ordered public batches; order is recorded, never used as likelihood."""
from copy import deepcopy

VERSION=1

def migrate(g):
    if 'public_log' in g:return deepcopy(g['public_log'])
    return {'version':VERSION,'legacy':bool(g['history'] or any(x!='latent' for x in g.get('claims',['latent']*g['players'])) or g.get('seer_inputs') or g.get('reports')),
            'base_claims':[deepcopy(s.get('claims',['latent']*g['players'])) for s in g['history']]+[deepcopy(g.get('claims',['latent']*g['players']))],
            'base_seer':deepcopy(g.get('seer_inputs',[])), 'base_medium':deepcopy(g.get('reports',[])), 'batches':[], 'next_id':1}

def project(g,log):
    if log.get('version')!=VERSION:raise ValueError('SystemLogの保存形式が未対応です。')
    result=deepcopy(g)
    def claims_at(slot):
        claims=list(log['base_claims'][min(slot,len(log['base_claims'])-1)])
        for b in log['batches']:
            if b['slot']<=slot:
                for e in b['events']:
                    if e['kind']=='co':claims[e['player']-1]=e['role']
        return claims
    for i,step in enumerate(result['history']):step['claims']=claims_at(i)
    result['claims']=claims_at(len(result['history']))
    seers={(r['day'],r['reporter']):deepcopy(r) for r in log['base_seer']}
    mediums={(r['day'],r['reporter'],r['target']):deepcopy(r) for r in log['base_medium']}
    for b in log['batches']:
        for e in b['events']:
            if e['kind']=='seer':
                seers[e['day'],e['player']]={'day':e['day'],'reporter':e['player'],'target':e['target'],'color':e['color']}
            if e['kind']=='medium':
                mediums[e['day'],e['player'],e['target']]={'day':e['day'],'reporter':e['player'],'target':e['target'],'color':e['color']}
    if result.get('seer_mode'):result['seer_inputs']=[seers[k] for k in sorted(seers)]
    if mediums or 'reports' in result:result['reports']=[mediums[k] for k in sorted(mediums)]
    for i,step in enumerate(result['history']):
        if 'reports' in step:step['reports']=[r for r in result.get('reports',[]) if r['day']<=1+i//2]
    result['public_log']=log
    result.pop('public_draft',None)
    return result

def transaction(g,board,payload,finished=False):
    log=migrate(g)
    if not isinstance(payload,dict) or set(payload)-{'mode','events','replace','delete','legacy','delete_legacy'}:raise ValueError('公開バッチの形式を確認してください。')
    if 'legacy' in payload or 'delete_legacy' in payload:
        if len(payload)!=1:raise ValueError('旧データ訂正の形式を確認してください。')
        editing='legacy' in payload
        action=payload['legacy' if editing else 'delete_legacy']
        if not isinstance(action,dict) or set(action)!=({'key','event'} if editing else {'key'}):raise ValueError('旧データの対象を確認してください。')
        key=action['key']
        if not isinstance(key,dict) or set(key)!={'kind','player','day','target'} or type(key['player']) is not int or type(key['day']) is not int or key.get('kind') not in ('seer','medium'):raise ValueError('旧保存の結果だけを訂正できます。')
        entries=log['base_seer' if key['kind']=='seer' else 'base_medium']
        old=next((r for r in entries if r['day']==key.get('day') and r['reporter']==key.get('player') and (key['kind']=='seer' or r['target']==key.get('target'))),None)
        if old is None:raise ValueError('旧保存の結果がありません。')
        if editing:
            e=action['event']
            if not isinstance(e,dict) or set(e)!={'kind','player','day','target','color'} or any(e[k]!=key[k] for k in ('kind','player','day')) or type(e['target']) is not int or e['target'] not in range(1,g['players']+1) or e['color'] not in ('white','black'):raise ValueError('旧結果の取得日・発言者を維持して対象と白黒を訂正してください。')
            old.update(target=e['target'],color=e['color'])
        else:entries.remove(old)
        return project(g,log)
    if 'delete' in payload:
        if set(payload)!={'delete'}:raise ValueError('削除と公開を同時に指定できません。')
        if type(payload['delete']) is not int:raise ValueError('削除対象を確認してください。')
        batch=next((b for b in log['batches'] if b['id']==payload['delete']),None)
        if batch is None:raise ValueError('削除対象がありません。')
        log['batches'].remove(batch)
        return project(g,log)
    events=payload.get('events');mode=payload.get('mode')
    if mode not in ('single','simultaneous') or not isinstance(events,list) or not 1<=len(events)<=27 or mode=='single' and len(events)!=1:raise ValueError('一件公開または同時公開バッチを選び、全行を完成させてください。')
    replacing=payload.get('replace')
    previous=next((b for b in log['batches'] if b['id']==replacing),None) if replacing is not None else None
    if replacing is not None and (type(replacing) is not int or previous is None):raise ValueError('訂正対象がありません。')
    slot=previous['slot'] if previous else len(g['history'])
    day=1+slot//2;phase='day' if slot%2==0 else 'night'
    if not previous and (finished or board.winner or len(g['history'])!=slot):raise ValueError('終局後の新規公開はできません。')
    alive=set(range(1,g['players']+1));scan=set(alive)
    for i,s in enumerate(g['history'][:slot]):
        alive.discard(s['target'])
        if i<2*(day-1)-1:scan.discard(s['target'])
    seen=set()
    for e in events:
        if not isinstance(e,dict) or e.get('kind') not in ('co','seer','medium') or type(e.get('player')) is not int or e['player'] not in alive:raise ValueError('公開時点で生存している発言者を指定してください。')
        if e['kind']=='co':
            if set(e)!={'kind','player','role'} or e['role'] not in ('villager','seer','medium','hunter','wolf'):raise ValueError('CO撤回は未対応です。訂正または依存する結果を含む削除を使ってください。')
            key=('co',e['player'])
        else:
            if set(e)!={'kind','player','day','target','color'} or type(e['day']) is not int or e['day']!=day or phase!='day':raise ValueError('取得日と公開日は同じ昼のみ対応しています。遅延公開は未対応です。')
            if type(e['target']) is not int or e['target'] not in range(1,g['players']+1) or e['color'] not in ('white','black'):raise ValueError('対象と白黒の両方を指定してください。')
            if e['kind']=='seer':
                if not g.get('seer_mode') or e['target']==e['player'] or e['target'] not in scan:raise ValueError('占いの取得時点で生存する別プレイヤーを指定してください。')
                key=('seer',e['day'],e['player'])
            else:key=('medium',e['day'],e['player'],e['target'])
        if key in seen:raise ValueError('同時バッチ内で同じCO・結果が重複しています。')
        seen.add(key)
    if not previous:
        for b in log['batches']:
            for old in b['events']:
                key=('co',old['player']) if old['kind']=='co' else (old['kind'],old['day'],old['player']) if old['kind']=='seer' else ('medium',old['day'],old['player'],old['target'])
                if key in seen and old['kind']!='co':raise ValueError('公開済みの結果です。該当バッチの訂正を使ってください。')
    if previous:
        previous['events']=deepcopy(events);previous['mode']=mode
    else:
        log['batches'].append({'id':log['next_id'],'slot':slot,'day':day,'phase':phase,'mode':mode,'events':deepcopy(events)})
        log['next_id']+=1
    return project(g,log)

def trim(g):
    if 'public_log' not in g:return g
    log=deepcopy(g['public_log']);slot=len(g['history'])
    log['batches']=[b for b in log['batches'] if b['slot']<=slot]
    log['base_claims']=log['base_claims'][:slot+1]
    day=1+slot//2
    log['base_seer']=[r for r in log['base_seer'] if r['day']<=day]
    log['base_medium']=[r for r in log['base_medium'] if r['day']<=day]
    return project(g,log)

def validate_draft(payload):
    if not isinstance(payload,dict):raise ValueError('下書きの形式を確認してください。')
    if set(payload)=={'legacy'}:
        action=payload['legacy']
        if not isinstance(action,dict) or set(action)!={'key','event'} or not isinstance(action['key'],dict) or not isinstance(action['event'],dict):raise ValueError('旧結果の下書きを確認してください。')
        return
    if set(payload)-{'mode','events','replace'} or payload.get('mode') not in ('single','simultaneous') or not isinstance(payload.get('events'),list) or len(payload['events'])>27 or any(not isinstance(e,dict) or set(e)-{'kind','player','role','day','target','color'} for e in payload['events']):raise ValueError('下書きの形式を確認してください。')
    if 'replace' in payload and type(payload['replace']) is not int:raise ValueError('訂正対象を確認してください。')
