"""Request-local immutable player read views. No persistence, solver or UI hook.

Rows come from existing public/private adapters; this module never calculates or
conditions probability laws. Public declarations are indexed from existing log
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
    source=public.scope;scope=frame.scope
    if source.kind!='public'or scope.kind not in ('seer','wolf','hunter','medium')or not scope.owners or not scope.evidence_digest or(scope.runtime,scope.board_id,scope.revision,scope.input_digest)!=(source.runtime,source.board_id,source.revision,source.input_digest):raise ValueError('Matching Board and explicit personal frame required')
    if len(rows)!=len(public.players)or any(p>len(public.players)for p in scope.owners):raise ValueError('Complete player rows and valid owners required')
    players=[]
    for i,row in enumerate(rows,1):
        if set(row)!=_PRIVATE_FIELDS or row['id']!=i:raise ValueError('Existing private row schema required')
        base=public.by_id(i)
        players.append(PlayerData(i,freeze(row),frame,base.declarations,base.received_claims,base.current_co,base.name,base.alive))
    return PlayerBoardView(scope,tuple(players),public.public_index)