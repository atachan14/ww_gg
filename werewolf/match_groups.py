"""Explicit opt-in public matching-group continuation, default disabled.

Sufficient scope: <=5 alive, no hunter, one true seer, configured fixed uniform
execution/bite/fake-medium instructions; standard scan/fake-seer selectors.
Group complete post-observation continuation inputs, not role marginals. Original
labelled histories are still generated; only recursive scalar evaluation stays
compressed. No new observation, strategy or multi-fake law is supplied.
"""
from dataclasses import dataclass
from math import comb
from fractions import Fraction as F
from time import perf_counter
from .information_set_forecast import InformationSetForecast,InformationSetActionPolicy
from .exact_renaming import canonical_key,state_signature,board_signature,record
from .evaluation_branch import physical_board
from .board_future import reconstruct_publication,publication_key


def signature(payload,ids):
    b,s,past,private,observer=payload
    n=b.player_count
    masks=tuple(sum(1<<(ids[p]-1)for p in range(n)if m>>p&1)for m in range(1<<n))
    if observer is not None:raise ValueError('opaque observer not proved')
    return (board_signature(b,ids,masks),state_signature(s,ids,masks),tuple(record(r,ids)for r in past),state_signature(private,ids,masks),board_signature(payload.physical,ids,masks))


def group_inputs(engine,weighted,*,audit=False):
    groups={};fallback=0
    for probability,payload in weighted:
        b,s,past,private,observer=payload
        start=perf_counter()
        keyed=None if observer is not None else canonical_key(b,s,past,private,observer,engine.rules,engine.strategy,physical=payload.physical,max_mappings=120,return_mapping=True)
        engine.stats['proof_seconds']+=perf_counter()-start
        if keyed is None:
            fallback+=1;key=('unproved',fallback)
            ids=tuple(range(1,b.player_count+1))
        else:
            key,ids=keyed
            if engine.relations is not None:key=(key,engine.relations.signature(ids))
        if key not in groups:groups[key]=[F(),payload,ids,[]]
        row=groups[key];row[0]+=probability
        if audit and keyed is not None:
            # Independent full transport equality, not scalar value equality.
            assert signature(payload,ids)==signature(row[1],row[2])
            from .exact import legal_targets,ROLES
            current=tuple(sorted((ids[t-1],tuple(b.role_probability(t,r)for r in ROLES))for t in range(1,b.player_count+1)))
            rb=row[1].public;rids=row[2]
            reference=tuple(sorted((rids[t-1],tuple(rb.role_probability(t,r)for r in ROLES))for t in range(1,rb.player_count+1)))
            assert current==reference
            assert sorted(ids[t-1]for t in legal_targets(b,engine.rules,engine.strategy))==sorted(rids[t-1]for t in legal_targets(rb,engine.rules,engine.strategy))
            row[3].append((probability,payload))
    engine.stats['unproved_branches']+=fallback
    engine.stats['raw_continuations']+=len(weighted)
    engine.stats['representative_continuations']+=len(groups)
    assert sum((p for p,x in weighted),F())==sum((r[0]for r in groups.values()),F())
    if audit:
        expected=F()
        for mass,representative,ids,members in groups.values():
            values=[engine.audit_oracle.solve(*child,physical=child.physical)for q,child in members]
            assert not values or all(v==values[0]for v in values)
            if values:expected+=mass*values[0]
            else:expected+=mass*engine.audit_oracle.solve(*representative,physical=representative.physical)
        engine.audits.append((sum((r[0]for r in groups.values()),F()),tuple((r[0],len(r[3]))for r in groups.values()),expected))
    return tuple((r[0],r[1])for r in groups.values())


class GroupPolicy(InformationSetActionPolicy):
    def morning_value(self,payload):
        e=self.engine;b,s,past,private,observer=payload
        if not e.supported(b,observer):return super().morning_value(payload)
        b,s,past,private,observer=e.continuation_context(b,s,past,private,observer)
        published=e.morning(b,s,past)
        if published==((F(1),b,s,past),):return super().morning_value(payload)
        branches=e.push(s,private,published)
        counts={}
        for q,c,ns,p,own in branches:
            k=publication_key(c,p);counts[k]=counts.get(k,0)+1
        weighted=[]
        for q,c,ns,p,own in branches:
            rebuilt=reconstruct_publication(e,payload,c,ns,p,own,physical_board(c,own,payload.physical),replay_unique=counts[publication_key(c,p)]==1)
            weighted.append((q,rebuilt))
        representatives=group_inputs(e,weighted,audit=e.audit)
        expected=e.audits[-1][-1]if e.audit else None
        value=sum((q*e.solve(*child,physical=child.physical)for q,child in representatives),F())
        if e.audit:assert value==expected
        return value


class MatchingForecast(InformationSetForecast):
    def __init__(self,*args,grouping=False,audit=False,relations=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.grouping=grouping;self.audit=audit;self.public_entry=True;self.audits=[];self.relations=relations
        self.stats=dict(proof_seconds=0.,unproved_branches=0,raw_continuations=0,representative_continuations=0,solve_calls=0,act_calls=0,uncached_act_calls=0,generated_publication_branches=0,generated_acquisition_rows=0,generated_acquisition_states=0)
        self.action_policy=GroupPolicy(self)
        if audit:self.audit_oracle=MatchingForecast(*args,grouping=False,audit=False,**kwargs)
    def supported(self,b,observer=None):
        p=self.strategy
        return (self.grouping and self.public_entry and observer is None and self.trace is None
            and len(b.alive)<=5 and b.initial_hunter_count==0 and b.initial_seer_count==1
            and p.day=='random'and p.night=='random'and p.fake_reports=='random'
            and tuple(p.seer_position)==('unvisited','uniform')
            and tuple(p.fake_seer_policy)in (('uniform',),('noncontradictory','uniform')))
    def solve(self,*args,**kwargs):
        self.stats['solve_calls']+=1
        return super().solve(*args,**kwargs)
    def act(self,*args,**kwargs):
        self.stats['act_calls']+=1
        return super().act(*args,**kwargs)
    def uncached_act(self,*args,**kwargs):
        self.stats['uncached_act_calls']+=1
        return super().uncached_act(*args,**kwargs)
    def generate_publications(self,*args):
        result=super().generate_publications(*args)
        self.stats['generated_publication_branches']+=len(result)
        return result
    def acquire(self,b,s):
        miss=(b,s)not in self.acquired
        result=super().acquire(b,s)
        if miss:
            self.stats['generated_acquisition_rows']+=len(result.hypotheses)
            self.stats['generated_acquisition_states']+=1
        return result
    def evaluate(self,*args,**kwargs):
        # The external personal-table entry is outside this trial's proof.
        previous=self.public_entry;self.public_entry=False
        try:return super().evaluate(*args,**kwargs)
        finally:self.public_entry=previous


@dataclass(frozen=True)
class PublicRelations:
    claims: tuple
    alive: tuple
    reports: tuple
    @classmethod
    def from_view(cls,view):
        if view is None or view.scope.kind!='public':return None
        # Read the same derived incoming-claim index exposed by PlayerData.
        declarations=tuple(d for p in view.players for d in p.co_history if d.active)+tuple(d for p in view.players for d in p.received_claims)
        reports=tuple((d.event['kind'],d.player,d.target,d.event.get('role'),d.acquired_day,
            d.event.get('color'),d.slot,d.published_day,d.published_phase,d.mode,d.order)
            for d in declarations)
        return cls(tuple(p.co for p in view.players),tuple(p.id for p in view.players if p.alive),reports)
    def signature(self,ids):
        return (tuple(sorted((ids[p-1],c)for p,c in enumerate(self.claims,1))),
            tuple(sorted(ids[p-1]for p in self.alive)),
            tuple(sorted(((kind,ids[p-1],None if t is None else ids[t-1],role,day,color,slot,pubday,phase,mode,order)
                for kind,p,t,role,day,color,slot,pubday,phase,mode,order in self.reports),key=repr)))
    def candidate_groups(self):
        n=len(self.claims);identity=tuple(range(1,n+1));original=self.signature(identity);groups=[]
        for p in identity:
            for group in groups:
                q=group[0];ids=list(identity);ids[p-1],ids[q-1]=ids[q-1],ids[p-1]
                if self.signature(tuple(ids))==original:group.append(p);break
            else:groups.append([p])
        return tuple(tuple(g)for g in groups)


def make_engine(board,state,past,rules,strategy,*,enabled=False,view=None,audit=False,max_work=4000000):
    relations=PublicRelations.from_view(view)
    n=board.player_count;claimants=tuple(p for p in board.alive if board.claims[p-1]=='seer')
    supported=(enabled and relations is not None and relations.claims==board.claims and relations.alive==board.alive
        and (n,board.wolf_count)in((5,1),(6,1),(6,2),(7,1),(7,2)) and board.day==1 and board.phase=='day'
        and board.alive==tuple(range(1,n+1)) and not board.history and not past
        and not board.initial_hunter_count and not board.initial_medium_count and board.initial_seer_count==1
        and len(claimants)==1 and board.role_probability(claimants[0],'seer')==1
        and all(c in ('seer','latent')for c in board.claims)
        and rules.initial_seer=='none'and not rules.allow_self_bite and not strategy.include_self_bite
        and state.initial_rule=='none'and state.rosters==(board.alive,)
        and not any(h.acquisitions or h.guards or h.attacks for h in state.hypotheses)
        and len(state.hypotheses)==comb(n-1,board.wolf_count)
        and len({h.roles for h in state.hypotheses})==len(state.hypotheses)
        and all(h.mass==F(1,len(state.hypotheses))for h in state.hypotheses)
        and strategy.day=='random'and strategy.night=='random'and strategy.fake_reports=='random'
        and tuple(strategy.seer_position)==('unvisited','uniform'))
    engine=MatchingForecast(rules,strategy,grouping=bool(supported),audit=audit and bool(supported),relations=relations,max_work=max_work)
    engine.stats['requested']=bool(enabled);engine.stats['active']=bool(supported)
    engine.stats['root_candidates']=relations.candidate_groups()if relations is not None else ()
    return engine