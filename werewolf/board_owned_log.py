"""Stable Board ownership and retained branches; no order-dependent likelihood."""
from copy import deepcopy
import json,hashlib

def signature(step):
    from dataclasses import asdict
    from .exact import Strategy,ClaimPolicy,VILLAGE_ROLES
    policy=asdict(Strategy(**step.get('policy',{})));cp=ClaimPolicy(**step.get('claim_policy',{}))
    claims={role:sorted(cp.conditions(role)) for role in VILLAGE_ROLES}
    return json.dumps({'target':step['target'],'policy':policy,'claim_policy':claims,'seer_options':step.get('seer_options'),'result_disclosure_model':step.get('result_disclosure_model')},sort_keys=True,separators=(',',':'))

def path(graph,board_id=None):
    result=[];seen=set();cursor=board_id or graph['current']
    while cursor is not None:
        if cursor in seen or cursor not in graph['nodes'] or not graph['nodes'][cursor].get('active',True):raise ValueError('Boardの親子関係が不正です。')
        seen.add(cursor);result.append(cursor);cursor=graph['nodes'][cursor]['parent']
    result.reverse()
    if not result or result[0]!=graph['root']:raise ValueError('Boardのrootが一致しません。')
    return result

def new_node(graph,parent,step,legacy_claims):
    number=graph['next_board'];graph['next_board']+=1;bid=f"{graph['game_id']}:board:{number}"
    slot=0 if parent is None else graph['nodes'][parent]['slot']+1
    branch=1 if parent is None else graph['nodes'][parent]['branch']
    if parent is not None and (graph['nodes'][parent]['children'] or graph['nodes'][parent].get('retired_children')):
        branch=graph['next_branch'];graph['next_branch']+=1
    graph['nodes'][bid]={'id':bid,'active':True,'generation':graph.get('generation',0),'parent':parent,'branch':branch,'slot':slot,'day':1+slot//2,'phase':'day' if slot%2==0 else 'night','edge':deepcopy(step),'children':[],'local_batches':[],'legacy_claims':list(legacy_claims),'legacy_seer':[],'legacy_medium':[],'revision':0,'input_revision':0 if parent is None else graph['nodes'][parent]['input_revision']}
    if parent is not None:graph['nodes'][parent]['children'].append(bid)
    return bid

def initialize(g,log):
    graph={'game_id':g.get('_owner_game_id') or hashlib.sha256(json.dumps({k:g.get(k) for k in ('players','wolves','seers','mediums','hunters','rules')},sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16],'nodes':{},'next_board':1,'next_branch':2}
    base=log['base_claims'];root=new_node(graph,None,None,base[0]);graph['root']=root;cursor=root;ids=[root]
    for i,step in enumerate(g['history']):
        cursor=new_node(graph,cursor,step,base[min(i+1,len(base)-1)]);ids.append(cursor)
    graph['current']=cursor
    for kind in ('seer','medium'):
        for r in log['base_'+kind]:
            slot=2*(r['day']-1)
            if slot>=len(ids):raise ValueError('旧保存の報告Boardが存在しません。')
            graph['nodes'][ids[slot]]['legacy_'+kind].append(deepcopy(r))
    for b in log['batches']:
        if type(b.get('slot'))is not int or not 0<=b['slot']<len(ids):raise ValueError('公開情報の所属Boardがありません。')
        b['board_id']=ids[b['slot']];graph['nodes'][b['board_id']]['local_batches'].append(deepcopy(b))
    log['board_graph']=graph
    return graph

def prepare(g,source):
    log=deepcopy(source);graph=log.get('board_graph') or initialize(g,log)
    old=path(graph);changed=[]
    buckets={bid:[] for bid in old}
    for batch in log['batches']:
        owner=batch.get('board_id')
        if owner is None:
            slot=batch['slot']
            if not 0<=slot<len(old):raise ValueError('公開情報の所属Boardがありません。')
            owner=old[slot];batch['board_id']=owner
        if owner not in buckets:raise ValueError('別枝の公開情報を混在できません。')
        if batch['slot']!=graph['nodes'][owner]['slot']:raise ValueError('Boardと公開位置が一致しません。')
        buckets[owner].append(deepcopy(batch))
    for i,bid in enumerate(old):
        node=graph['nodes'][bid];claims=log['base_claims'][min(i,len(log['base_claims'])-1)]
        legacy={kind:[deepcopy(r) for r in log['base_'+kind] if 2*(r['day']-1)==i] for kind in ('seer','medium')}
        if node['local_batches']!=buckets[bid] or node['legacy_claims']!=claims or any(node['legacy_'+k]!=v for k,v in legacy.items()):
            node['local_batches']=buckets[bid];node['legacy_claims']=list(claims)
            for k,v in legacy.items():node['legacy_'+k]=v
            node['revision']+=1;changed.append(bid)
    invalidated=set()
    def invalidate(bid):
        if bid in invalidated:return
        invalidated.add(bid);graph['nodes'][bid]['input_revision']+=1
        for child in graph['nodes'][bid]['children']:invalidate(child)
    for bid in changed:invalidate(bid)
    if changed:graph['invalidated']=sorted(invalidated)
    else:graph.setdefault('invalidated',[])
    cursor=graph['root'];selected=[cursor]
    for step in g['history']:
        candidates=[bid for bid in graph['nodes'][cursor]['children'] if signature(graph['nodes'][bid]['edge'])==signature(step)]
        if len(candidates)>1:raise ValueError('同じ遷移のBoardが重複しています。')
        cursor=candidates[0] if candidates else new_node(graph,cursor,step,graph['nodes'][cursor]['legacy_claims'])
        selected.append(cursor)
    graph['current']=cursor
    log['board_id']=cursor;log['branch_id']=graph['nodes'][cursor]['branch']
    log['batches']=[deepcopy(b) for bid in selected for b in graph['nodes'][bid]['local_batches']]
    log['base_claims']=[list(graph['nodes'][bid]['legacy_claims']) for bid in selected]
    for kind in ('seer','medium'):log['base_'+kind]=[deepcopy(r) for bid in selected for r in graph['nodes'][bid]['legacy_'+kind]]
    log['local_batches']=deepcopy(graph['nodes'][cursor]['local_batches'])
    node=graph['nodes'][cursor];parent=graph['nodes'].get(node['parent'])
    delta=[node['legacy_claims'][i] if parent is None or node['legacy_claims'][i]!=parent['legacy_claims'][i] else 'latent' for i in range(g['players'])]
    log['local_legacy']={'claims':delta,'seer':deepcopy(node['legacy_seer']),'medium':deepcopy(node['legacy_medium'])}
    log['has_local_legacy']=log['legacy'] and (any(c!='latent' for c in delta) or bool(node['legacy_seer'] or node['legacy_medium']))
    return log

def local_fingerprint(node):
    batches=[]
    for raw in node['local_batches']:
        b=deepcopy(raw);b['events']=sorted(b['events'],key=lambda e:e.get('id',''))
        batches.append(b)
    return json.dumps({'batches':batches,'claims':node['legacy_claims'],'seer':sorted(node['legacy_seer'],key=lambda r:(r['day'],r['reporter'])),'medium':sorted(node['legacy_medium'],key=lambda r:(r['day'],r['reporter'],r['target']))},sort_keys=True,separators=(',',':'))

def commit_owned_change(before,after):
    """Commit-only retirement; snapshots remain recoverable, never inherited."""
    result=deepcopy(after);old=before['public_log']['board_graph'];graph=result['public_log']['board_graph'];owner=old['current']
    changed=[bid for bid in old['nodes'] if bid in graph['nodes'] and local_fingerprint(old['nodes'][bid])!=local_fingerprint(graph['nodes'][bid])]
    if any(bid!=owner for bid in changed):raise ValueError('公開情報の訂正は所属するBoardで行ってください。')
    if not changed:
        for bid,node in old['nodes'].items():
            if bid in graph['nodes']:
                graph['nodes'][bid]['revision']=node['revision'];graph['nodes'][bid]['input_revision']=node['input_revision']
        return result
    generation=graph.get('generation',0)+1;graph['generation']=generation
    direct=list(old['nodes'][owner]['children']);descendants=[]
    def collect(bid):
        if bid in descendants:return
        descendants.append(bid)
        for child in old['nodes'][bid]['children']:collect(child)
    for child in direct:collect(child)
    ancestors=path(old,owner)
    protected={bid:deepcopy(old['nodes'][bid]) for bid in ancestors+descendants}
    graph.setdefault('archives',[]).append({'generation':generation,'owner':owner,'ancestor_path':ancestors,'retired_roots':direct,'nodes':protected,'settings':{k:deepcopy(before[k]) for k in ('players','wolves','seers','mediums','hunters','rules','model','policy','claim_policy') if k in before}})
    for bid in descendants:
        graph['nodes'][bid]['active']=False;graph['nodes'][bid]['retired_by']=owner;graph['nodes'][bid]['retired_generation']=generation
    node=graph['nodes'][owner];node['retired_children']=list(dict.fromkeys(node.get('retired_children',[])+direct));node['children']=[];node['content_generation']=generation
    return result

def check_item_owner(g,payload):
    bid=payload.get('replace',payload.get('delete'))
    if bid is not None:
        batch=next((b for b in g['public_log']['batches'] if b['id']==bid),None)
        if batch is None or batch['board_id']!=g['public_log']['board_id']:raise ValueError('公開情報の編集・削除は所属するBoardで行ってください。')
    if 'legacy' in payload or 'delete_legacy' in payload:
        action=payload.get('legacy',payload.get('delete_legacy'));key=action['key'];local=g['public_log']['local_legacy'][key['kind']]
        if not any(r['day']==key['day'] and r['reporter']==key['player'] and (key['kind']=='seer' or r['target']==key['target']) for r in local):raise ValueError('旧公開情報の訂正は所属するBoardで行ってください。')
