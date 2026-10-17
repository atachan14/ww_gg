"""Sufficient scalar-continuation comparison contract for the guarded trial.

Player read views supply public relations only. Joint laws remain Board/state
owned immutable references. A certificate key, not carrier or PlayerData equality,
is the sufficient condition. No independent terminal solver runs here.
"""
from dataclasses import dataclass
from .exact_renaming import canonical_key


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


@dataclass(frozen=True)
class ComparisonCertificate:
    key: tuple
    mapping: tuple


@dataclass(frozen=True,eq=False)
class ComparisonContext:
    """One engine/request's fixed configuration and public relation snapshot.

    All referenced inputs are immutable. Edits/recalculation build a new context;
    no certificates or mutable PlayerData/BoardData runtime are globally cached.
    Rules/policies and relations are shared, never copied into individual players.
    """
    rules: object
    strategy: object
    relations: PublicRelations|None

    def certify(self,payload):
        """Exact full joint key, or no certificate (ordinary unique fallback).

        The carrier retains shared public/private/physical laws by reference.
        canonical_key includes complete history, configuration and observer
        scope, not just local player features. The guarded public trial excludes
        opaque/private observers even if a lower-level renamer supports one.
        """
        if payload.observer is not None:return None
        keyed=canonical_key(payload.public,payload.public_state,payload.past,
            payload.private,payload.observer,self.rules,self.strategy,
            physical=payload.physical,max_mappings=120,return_mapping=True)
        if keyed is None:return None
        key,mapping=keyed
        if self.relations is not None:key=(key,self.relations.signature(mapping))
        return ComparisonCertificate(key,mapping)
