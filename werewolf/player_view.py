"""Request-local immutable player read views. No persistence, solver or UI hook.

Rows use prepared role/forecast outputs or explicit compatibility adapters; this
module never calculates or conditions probability laws. Public declarations are indexed from existing log
projection. No view is attached to generated future Boards or global caches.
"""
from collections.abc import Mapping,Sequence
from dataclasses import dataclass,fields,is_dataclass,field
from fractions import Fraction
from hashlib import sha256
import json

@dataclass(frozen=True)
class ReadMap(Mapping):
    items_tuple: tuple
    def __iter__(self):return (k for k,v in self.items_tuple)
    def __len__(self):return len(self.items_tuple)
    def __getitem__(self,key):
        for k,v in self.items_tuple:
            if k==key:return v
        raise KeyError(key)

@dataclass(frozen=True)
class ReadList(Sequence):
    values: tuple
    def __getitem__(self,index):return self.values[index]
    def __len__(self):return len(self.values)


def freeze(value):
    if type(value)is dict:return ReadMap(tuple((k,freeze(v))for k,v in value.items()))
    if type(value)is list:return ReadList(tuple(freeze(v)for v in value))
    if type(value)is tuple:return tuple(freeze(v)for v in value)
    if value is None or type(value)in(str,int,bool,float,Fraction):return value
    if is_dataclass(value)and getattr(type(value),'__dataclass_params__').frozen:
        # Existing Values/HorizonValues/ManualPending are already immutable.
        if all(freeze(getattr(value,f.name))is getattr(value,f.name)for f in fields(value)):return value
    raise TypeError('Unsupported mutable row value')


def thaw(value):
    if isinstance(value,ReadMap):return {k:thaw(v)for k,v in value.items_tuple}
    if isinstance(value,ReadList):return [thaw(v)for v in value.values]
    if type(value)is tuple:return tuple(thaw(v)for v in value)
    return value

@dataclass(frozen=True)
class ViewScope:
    runtime: object=field(repr=False)
    board_id: object
    revision: int
    input_digest: str
    kind: str='public'
    owners: tuple=()
    evidence_digest: str=''
    @classmethod
    def public(cls,board_data):
        g=board_data.to_game()
        return cls(board_data.runtime,board_data.facts.board_id,g.get('revision',0),sha256(board_data.inputs.encode('utf8')).hexdigest())
    def personal(self,role,players,evidence):
        if self.kind!='public'or role not in ('seer','wolf','hunter','medium'):raise ValueError('Public source and explicit personal role required')
        players=tuple(players)
        if not players or len(set(players))!=len(players)or any(type(p)is not int or p<1 for p in players):raise ValueError('Distinct owner IDs required')
        text=json.dumps(evidence,sort_keys=True,separators=(',',':'),allow_nan=False)
        return ViewScope(self.runtime,self.board_id,self.revision,self.input_digest,role,players,sha256(text.encode('utf8')).hexdigest())

@dataclass(frozen=True)
class ResultFrame:
    scope: ViewScope
    stage: str
    request_id: str=''
    reason: str|None=None
    def __post_init__(self):
        if self.stage not in ('roles','complete','pending','invalid'):raise ValueError('Explicit existing calculation stage required')

@dataclass(frozen=True)
class MetricValue:
    status: str
    value: object=None
    reason: str|None=None

@dataclass(frozen=True)
class Declaration:
    event: ReadMap
    slot: int
    board_id: object
    batch_id: object
    mode: str|None
    order: tuple|None
    active: bool
    publication_day: int|None=None
    publication_phase: str|None=None
    @property
    def player(self):return self.event['player']
    @property
    def target(self):return self.event.get('target')
    @property
    def acquired_day(self):return self.event.get('day')
    @property
    def published_day(self):return self.publication_day
    @property
    def published_phase(self):return self.publication_phase

@dataclass(frozen=True)
class PublicIndex:
    events: tuple
    by_player: tuple
    received: tuple
    current_co: tuple
    @classmethod
    def from_board(cls,board_data):
        from .public_log import migrate,project
        from .public_log_changes import upgrade,declarations
        g=board_data.to_game();log=migrate(g);effective=project(g,log)
        publication_positions=effective.get('public_log',{}).get('report_publications',{})
        if log['version']==1:log=upgrade(log)
        active,known=declarations(log);active_ids={e['id']for slot,e in active.values()}
        metadata={}
        for bi,b in enumerate(log['batches']):
            for ei,e in enumerate(b['events']):metadata[e['id']]=(b.get('board_id'),b['id'],b['mode'],(bi,ei))
        n=board_data.game_data.players;events=[];by=[[]for _ in range(n)];received=[[]for _ in range(n)];co=effective['claims']
        for eid,(slot,e)in known.items():
            if slot>board_data.facts.slot:continue
            owner,bid,mode,order=metadata.get(eid,(None,None,None,None))
            is_active=eid in active_ids and(e['kind']!='co'or co[e['player']-1]==e['role'])
            position=None
            if e['kind']in('seer','medium'):
                token=f"{e['kind']}:{e['day']}:{e['player']}"+(f":{e['target']}"if e['kind']=='medium'else '')
                position=publication_positions.get(token)if is_active else None
            node=log.get('board_graph',{}).get('nodes',{}).get(owner,{})
            pubday=(position or node).get('published_day',(position or node).get('day'))
            pubphase=(position or node).get('published_phase',(position or node).get('phase'))
            d=Declaration(freeze(e),slot,owner,bid,mode,order,is_active,pubday,pubphase)
            events.append(d);by[d.player-1].append(d)
            if d.active and e['kind']in('seer','medium'):received[d.target-1].append(d)
        return cls(tuple(events),tuple(tuple(x)for x in by),tuple(tuple(x)for x in received),tuple(co))

@dataclass(frozen=True)
class PlayerData:
    id: int
    legacy: ReadMap=field(repr=False)
    frame: ResultFrame=field(repr=False)
    declarations: tuple=()
    received_claims: tuple=()
    current_co: str='latent'
    display_name: str=''
    alive: bool|None=None
    def __getitem__(self,key):return self.legacy[key]
    def get(self,key,default=None):return self.legacy.get(key,default)
    def __getattr__(self,key):
        try:return self.legacy[key]
        except KeyError:raise AttributeError(key)from None
    @property
    def name(self):return self.display_name
    @property
    def co(self):return self.current_co
    @property
    def co_history(self):return tuple(d for d in self.declarations if d.event['kind']=='co')
    @property
    def published_claims(self):return tuple(d for d in self.declarations if d.active and d.event['kind']in('seer','medium'))
    def to_legacy_row(self):return thaw(self.legacy)
    def metric(self,name,*,current_frame=None):
        if current_frame is not None and(self.frame.scope!=current_frame.scope or self.frame.request_id!=current_frame.request_id):return MetricValue('stale')
        if self.frame.stage=='invalid':return MetricValue('invalid',reason=self.frame.reason)
        value=self.legacy.get(name)
        # Roles may be complete while continuation is still pending. Do not
        # publish a retained old action value during a new roles/pending frame.
        continuation=name in ('action','by_dawn','dawn','final')
        if continuation and self.frame.stage in ('roles','pending'):return MetricValue('pending',reason=self.frame.reason)
        from .seer_manual import ManualPending
        from .seer_future_uniform import FuturePending
        def pending_reason(v):
            if isinstance(v,(ManualPending,FuturePending)):return v.reason
            children=v.values()if isinstance(v,ReadMap)else v if isinstance(v,(ReadList,tuple))else ()
            return next((reason for child in children if(reason:=pending_reason(child))is not None),None)
        reason=pending_reason(value)
        if reason is not None:return MetricValue('pending',reason=reason)
        if value is None:return MetricValue('missing')
        return MetricValue('complete',value)

@dataclass(frozen=True)
class PlayerBoardView:
    scope: ViewScope
    players: tuple
    public_index: PublicIndex
    def by_id(self,player):
        if type(player)is not int or not 1<=player<=len(self.players):raise KeyError(player)
        return self.players[player-1]

_PUBLIC_REQUIRED=frozenset(('id','name','claim','alive','status','legal','action','by_dawn','wolf_probability','village_probability','medium_probability','citizen_probability','extra_probabilities','medium_timeline','co_pending'))
_PUBLIC_ALLOWED=_PUBLIC_REQUIRED|{'seer_timeline','has_seer_evidence'}
_PRIVATE_FIELDS=frozenset(('id','probabilities','dawn','final','legal'))


def public_view(board_data,rows,frame):
    scope=ViewScope.public(board_data)
    if frame.scope!=scope:raise ValueError('Stale or personal frame cannot label public rows')
    index=PublicIndex.from_board(board_data);players=[]
    if len(rows)!=board_data.game_data.players:raise ValueError('Complete original player rows required')
    for i,row in enumerate(rows,1):
        if not _PUBLIC_REQUIRED<=row.keys()or row.keys()-_PUBLIC_ALLOWED or row['id']!=i:raise ValueError('Existing public row schema required; secret/private fields forbidden')
        if row['claim']!=index.current_co[i-1]:raise ValueError('Row CO differs from effective public declarations')
        players.append(PlayerData(i,freeze(row),frame,index.by_player[i-1],index.received[i-1],index.current_co[i-1],row['name'],row['alive']))
    return PlayerBoardView(scope,tuple(players),index)


def personal_view(public,rows,frame):
    # A private API already owns validated public Board evidence; do not render
    # or calculate a public table just to construct personal read metadata.
    if isinstance(public,PlayerBoardView):
        source=public.scope;index=public.public_index
        metadata=tuple((p.name,p.alive)for p in public.players)
    else:
        from .board_flow import BoardData
        if not isinstance(public,BoardData):raise TypeError('Public Board source required')
        source=ViewScope.public(public);index=PublicIndex.from_board(public)
        metadata=tuple((f"Player {i}",i in public.facts.alive)for i in range(1,public.game_data.players+1))
    scope=frame.scope
    if source.kind!='public'or scope.kind not in ('seer','wolf','hunter','medium')or not scope.owners or not scope.evidence_digest or(scope.runtime,scope.board_id,scope.revision,scope.input_digest)!=(source.runtime,source.board_id,source.revision,source.input_digest):raise ValueError('Matching Board and explicit personal frame required')
    if len(rows)!=len(metadata)or any(p>len(metadata)for p in scope.owners):raise ValueError('Complete player rows and valid owners required')
    players=[]
    for i,row in enumerate(rows,1):
        if set(row)!=_PRIVATE_FIELDS or row['id']!=i:raise ValueError('Existing private row schema required')
        name,alive=metadata[i-1]
        players.append(PlayerData(i,freeze(row),frame,index.by_player[i-1],index.received[i-1],index.current_co[i-1],name,alive))
    return PlayerBoardView(scope,tuple(players),index)


def build_public_view(board_data,role_state,board,frame,*,state,event_history,alive,action_values,by_dawn_values,finished=False,manual=False,guard_scope_pending=False,probability_pending=None):
    """Build immutable UI rows directly; no temporary legacy row dict/list."""
    from .co_ui import medium_timeline
    from .seer_manual import timeline as seer_timeline
    scope=ViewScope.public(board_data)
    if frame.scope!=scope:raise ValueError('Stale or personal public frame')
    index=PublicIndex.from_board(board_data)
    deaths={e.target:f"D{e.day} "+("処刑"if e.phase=='day'else "襲撃")for e in event_history}
    players=[]
    for i in range(1,board_data.game_data.players+1):
        probabilities=role_state.probabilities(i);wolf=probabilities['wolf']
        claim=board.claims[i-1]
        if claim!=index.current_co[i-1]:raise ValueError('Row CO differs from effective public declarations')
        medium=medium_timeline(board,i,finished)
        extra=ReadMap(tuple((r,probability_pending if probability_pending is not None else probabilities[r])for r in ('seer','hunter')))
        values=(('medium_probability',probability_pending if probability_pending is not None else probabilities['medium']),
            ('citizen_probability',probability_pending if probability_pending is not None else probabilities['villager']),
            ('extra_probabilities',extra),('claim',claim),
            ('legal',i in action_values or(guard_scope_pending and not finished and board.phase=='day'and i in board.alive)),
            ('id',i),('name',f"Player {i}"),('status',deaths.get(i,"生存")),('alive',i in alive),
            ('wolf_probability',probability_pending if probability_pending is not None else wolf),
            ('village_probability',probability_pending if probability_pending is not None else 1-wolf),
            ('action',action_values.get(i)),('by_dawn',by_dawn_values.get(i)if i in action_values else None))
        if manual:
            timeline=seer_timeline(state,board,i,finished)
            values+=(('seer_timeline',freeze(timeline)),('has_seer_evidence',any(r['target']is not None or r['color']is not None for r in timeline)))
        values+=(('medium_timeline',freeze(medium)),('co_pending',claim=='medium'and any(r['editable']and not r['color']for r in medium)))
        players.append(PlayerData(i,ReadMap(values),frame,index.by_player[i-1],index.received[i-1],claim,f"Player {i}",i in alive))
    return PlayerBoardView(scope,tuple(players),index)


def private_api_rows(marginals,*,targets=(),final_values=None,dawn_for=None):
    """Single private-row formatter. The mutable JSON boundary is intentional."""
    final_values={}if final_values is None else final_values
    rows=[]
    for i,marginal in enumerate(marginals,1):
        probabilities={r:str(v)for r,v in marginal.items()}
        probabilities['citizen']=probabilities.pop('villager');probabilities['village']=str(1-marginal['wolf'])
        dawn=dawn_for(i)if dawn_for is not None else None
        rows.append({'id':i,'probabilities':probabilities,
            'dawn':{'village':str(dawn.village_win),'wolf':str(dawn.wolf_win)}if dawn else None,
            'final':{'village':str(final_values[i]),'wolf':str(1-final_values[i])}if i in final_values else None,
            'legal':i in targets})
    return rows
