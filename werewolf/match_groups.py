"""Explicit opt-in public matching-group continuation, default disabled.

Sufficient scope: <=5 alive, no hunter, one true seer, configured fixed uniform
execution/bite/fake-medium instructions; standard scan/fake-seer selectors.
Group complete post-observation continuation inputs, not role marginals. Original
labelled histories are still generated; only recursive scalar evaluation stays
compressed. No new observation, strategy or multi-fake law is supplied.
"""
from math import comb
from fractions import Fraction as F
from time import perf_counter
from .information_set_forecast import InformationSetForecast,InformationSetActionPolicy
from .exact_renaming import state_signature,board_signature,record
from .matching_comparison import PublicRelations,ComparisonContext
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
        certificate=engine.comparison.certify(payload)
        engine.stats['proof_seconds']+=perf_counter()-start
        if certificate is None:
            fallback+=1;key=('unproved',fallback)
            ids=tuple(range(1,b.player_count+1))
        else:
            key,ids=certificate.key,certificate.mapping
        if key not in groups:groups[key]=[F(),payload,ids,[]]
        row=groups[key];row[0]+=probability
        if audit and certificate is not None:
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
        self.comparison=ComparisonContext(self.rules,self.strategy,relations)
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

def _dual_white_ledger_supported(board,state,past,rules,claimants,relations):
    """Uniform existing CO-group law: one true seer, one wolf, same white."""
    if board.player_count>6:return False
    from .seer_acquisition import Acquisition,SeerReport
    if (rules.initial_seer!='random_white'or state.initial_rule!='random_white'
        or len(past)!=2 or any(type(r)is not SeerReport for r in past)
        or state.tracked!=claimants or state.observed_prefix!=1
        or {r.player for r in past}!=set(claimants)
        or len({r.target for r in past})!=1):return False
    target=past[0].target
    if (target not in board.alive or target in claimants
        or board.role_probability(target,'wolf')!=0
        or any(r.acquired_day!=1 or r.published_day!=1 or r.color!='white'for r in past)
        or any(board.role_probability(p,'seer')!=F(1,2)or board.role_probability(p,'wolf')!=F(1,2)for p in claimants)):return False
    whites=tuple(r for r in relations.reports if r[0]=='seer')
    if (len(whites)!=2 or any(r[0]not in ('co','seer')for r in relations.reports)
        or {(r[1],r[2],r[4],r[5],r[6],r[7],r[8])for r in whites}
           !={(p,target,1,'white',0,1,'day')for p in claimants}):return False
    expected=2*comb(board.player_count-3,board.wolf_count-1)
    if len(state.hypotheses)!=expected:return False
    co_mask=sum(1<<(p-1)for p in claimants)
    for h in state.hypotheses:
        true=tuple(p for p in claimants if h.roles[2]==1<<(p-1))
        if len(true)!=1 or h.mass!=F(1,expected):return False
        actor=true[0]
        if (h.roles[0]&co_mask)!=(co_mask^(1<<(actor-1))):return False
        if h.acquisitions!=(Acquisition(1,actor,target,'white'),):return False
    return True


def _root_ledger_supported(board,state,past,rules,claimants,relations):
    """Empty ledger, one known-true white, or the narrow dual-white mixture."""
    from .seer_acquisition import Acquisition,SeerReport
    if any(h.guards or h.attacks for h in state.hypotheses):return False
    if len(claimants)==2:return _dual_white_ledger_supported(board,state,past,rules,claimants,relations)
    if rules.initial_seer=='none':
        return (state.initial_rule=='none'and not past
            and not any(h.acquisitions for h in state.hypotheses)
            and len(state.hypotheses)==comb(board.player_count-1,board.wolf_count))
    if (rules.initial_seer!='random_white'or state.initial_rule!='random_white'
        or len(claimants)!=1 or len(past)!=1 or type(past[0])is not SeerReport
        or state.tracked!=claimants or state.observed_prefix!=1):return False
    report=past[0];actor=claimants[0]
    if (report.player!=actor or report.acquired_day!=1 or report.published_day!=1
        or report.color!='white'or report.target not in board.alive
        or report.target==actor or board.role_probability(report.target,'wolf')!=0):return False
    whites=tuple(r for r in relations.reports if r[0]=='seer')
    if (len(whites)!=1 or any(r[0]not in ('co','seer')for r in relations.reports)
        or (whites[0][1],whites[0][2],whites[0][4],whites[0][5],whites[0][6],whites[0][7],whites[0][8])
           !=(actor,report.target,1,'white',0,1,'day')):return False
    acquisition=Acquisition(1,actor,report.target,'white')
    return (len(state.hypotheses)==comb(board.player_count-2,board.wolf_count)
        and all(h.acquisitions==(acquisition,)for h in state.hypotheses))


def make_engine(board,state,past,rules,strategy,*,enabled=False,view=None,audit=False,max_work=4000000):
    relations=PublicRelations.from_view(view)
    n=board.player_count;claimants=tuple(p for p in board.alive if board.claims[p-1]=='seer')
    supported=(enabled and relations is not None and relations.claims==board.claims and relations.alive==board.alive
        and (n,board.wolf_count)in((5,1),(6,1),(6,2),(7,1),(7,2)) and board.day==1 and board.phase=='day'
        and board.alive==tuple(range(1,n+1)) and not board.history
        and not board.initial_hunter_count and not board.initial_medium_count and board.initial_seer_count==1
        and len(claimants)in(1,2) and sum((board.role_probability(p,'seer')for p in claimants),F())==1
        and all(c in ('seer','latent')for c in board.claims)
        and not rules.allow_self_bite and not strategy.include_self_bite
        and state.rosters==(board.alive,)
        and _root_ledger_supported(board,state,past,rules,claimants,relations)
        and len({h.roles for h in state.hypotheses})==len(state.hypotheses)
        and state.public_roles==tuple(sorted(board.worlds))
        and strategy.day=='random'and strategy.night=='random'and strategy.fake_reports=='random'
        and tuple(strategy.seer_position)==('unvisited','uniform'))
    engine=MatchingForecast(rules,strategy,grouping=bool(supported),audit=audit and bool(supported),relations=relations,max_work=max_work)
    engine.stats['requested']=bool(enabled);engine.stats['active']=bool(supported)
    engine.stats['root_candidates']=relations.candidate_groups()if relations is not None else ()
    return engine