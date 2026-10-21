"""Presentation records: saved input revisions versus generated public events.

Saved revisions have no likelihood or calculation identity. Arrival states retain
actual pre-publication Q/P; their outgoing updates use the existing report law.
"""
from copy import deepcopy
from fractions import Fraction as F
from dataclasses import asdict

def event_label(events):
    from .exact import ROLE_LABELS
    role_names={**ROLE_LABELS,'seer':'占い師','medium':'霊能','hunter':'狩人'}
    rows={}
    for event in events:
        actor=event['player'];parts=rows.setdefault(actor,[])
        if event['kind']=='co':text=role_names[event['role']]+'CO'
        else:text=str(event['target'])+('白' if event['color']=='white' else '黒')
        if event.get('action')=='withdraw':text+='撤回'
        parts.append(text)
    return ' / '.join(str(actor)+' '+ '・'.join(parts) for actor,parts in rows.items())

def state_summary(board,private,identity,game_data,role_order,*,value=None,record_kind='arrival',past=()):
    from .physical_selection import counts
    from .calculation_tree import composition_label
    totals={}
    if private is not None:
        for h in private.hypotheses:
            key=counts(h,board.alive);totals[key]=totals.get(key,F())+h.mass
    else:
        alive=sum(1<<(p-1) for p in board.alive)
        for *masks,q in board.worlds:
            row=tuple((mask&alive).bit_count() for mask in masks);key=(*row,len(board.alive)-sum(row));totals[key]=totals.get(key,F())+q
    return dict(node=identity,snapshot_only=True,record_kind=record_kind,public_current=False,day=board.day,phase=board.phase,column_day=board.day,column_phase=board.phase,
        alive=list(board.alive),winner=board.winner,public_claims=list(board.claims),public_reports=[asdict(r) for r in board.reports],public_seer_reports=[asdict(r) for r in past],
        village_win=None if value is None else str(value),actions=[],native_mode=True,
        players=[dict(player=p,wolf_probability=str(board.role_probability(p,'wolf')),seer_probability=str(board.role_probability(p,'seer'))) for p in range(1,board.player_count+1)],
        distribution=[dict(id=str(i),label=composition_label(key,game_data,role_order),probability=str(q),children=[]) for i,(key,q) in enumerate(sorted(totals.items()))])

def input_timeline(data,role_order):
    from .public_log import migrate
    from .board_flow import BoardData
    g=data.to_game()
    if g.get('history'):return None
    log=migrate(g);batches=deepcopy(log['batches']);legacy=[]
    for player,role in enumerate(log['base_claims'][0],1):
        if role!='latent':legacy.append(dict(kind='co',player=player,role=role))
    for key,kind in (('base_seer','seer'),('base_medium','medium')):
        legacy.extend(dict(kind=kind,player=r['reporter'],day=r['day'],target=r['target'],color=r['color']) for r in log[key])
    if not legacy and not batches:return None
    snapshots=[]
    # Legacy inputs lack internal timing: keep them together, never invent order.
    groups=([legacy] if legacy else [])+[batch['events'] for batch in batches]
    def capture(events,prefix):
        changed=deepcopy(g);changed.pop('public_log',None);changed['claims']=['latent']*g['players'];changed['seer_inputs']=[];changed['reports']=[]
        active={}
        for event in events:
            key=(event['kind'],event['player']) if event['kind']=='co' else (event['kind'],event['day'],event['player'],event.get('target') if event['kind']=='medium' else None)
            if event.get('action')=='withdraw':active.pop(key,None)
            else:active[key]=event
        for event in active.values():
            if event['kind']=='co':changed['claims'][event['player']-1]=event['role']
            else:changed['seer_inputs' if event['kind']=='seer' else 'reports'].append(dict(day=event['day'],reporter=event['player'],target=event['target'],color=event['color']))
        board=BoardData.from_game(changed).roles().board
        result=state_summary(board,None,'input:'+str(prefix),data.game_data,role_order,record_kind='input_snapshot')
        result['public_seer_reports']=deepcopy(changed['seer_inputs']);return result
    events=[];before=capture(events,0)
    for index,group in enumerate(groups):
        events.extend(group);snapshots.append(dict(label=event_label(group),state=capture(events,index+1),probability=None))
    return dict(before=before,updates=snapshots,kind='recorded_inputs')

def publication_label(before,after):
    events=[dict(kind='seer',player=r.player,day=r.acquired_day,target=r.target,color=r.color) for r in after.past if r not in before.past]
    events.extend(dict(kind='medium',player=r.reporter,day=r.day,target=r.target,color=r.color) for r in after.public.reports if r not in before.public.reports)
    events.extend(dict(kind='co',player=p,role=claim) for p,claim in enumerate(after.public.claims,1) if claim!=before.public.claims[p-1])
    return event_label(events) or '更新なし'
