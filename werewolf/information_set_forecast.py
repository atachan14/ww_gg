"""Model A: roster-informed wolf choices; compatibility-only public beliefs.

Physical branch mass and public decision beliefs are separate. Wolf policies
average unknown roles/acquisitions within a PUBLIC-prior roster group before
maximizing. Observer-only evidence never enters the policy cache or ranking.
"""
from dataclasses import replace
from fractions import Fraction as F
from functools import lru_cache
from math import comb
from .exact import (action_outcomes, legal_targets, replace_worlds, report_actions,
                    random_report_outcomes, BoardOutcome, winner_for)
from .seer_acquisition import Hypothesis, from_board, normalize
from .seer_future_uniform import TrueScanState, FuturePending, acquire_uniform
from .seer_future_forecast import project_private
from .morning_publications import future_publications, public_report_branches
from .phase_updates import night_observation_outcomes
from .action_flow import action_flow, FlowOutcome
from .calculation_budget import calculation_budget, tick, CalculationBudgetExceeded


class Pending(Exception):
    def __init__(self, reason): self.reason=reason


@lru_cache(None)
def exchangeable_value(n,w,phase,strategy):
    winner=winner_for(n,w)
    if winner:return F(winner=='village')
    if phase=='day':
        return F(w,n)*exchangeable_value(n-1,w-1,'night',strategy)+F(n-w,n)*exchangeable_value(n-1,w,'night',strategy)
    enemy=exchangeable_value(n-1,w,'day',strategy)
    if not strategy.include_self_bite:return enemy
    friend=exchangeable_value(n-1,w-1,'day',strategy)
    return min(friend,enemy) if strategy.night=='max' else F(w,n)*friend+F(n-w,n)*enemy


class InformationSetForecast:
    def __init__(self, rules, strategy, *, max_work=250000, trace=None):
        self.rules=rules;self.strategy=strategy;self.max_work=max_work;self.trace=trace
        self.values={};self.scores={};self.policies={};self.acquired={}
        self.action_policy=InformationSetActionPolicy(self)

    def exchangeable(self,b):
        # Exact reduction: no future information, and all live locations are
        # exchangeable in the PUBLIC wolf marginal. Public max ties are uniform.
        if b.initial_medium_count or any(b.claims[p-1]=='seer' for p in b.alive):return False
        masses={}
        for mask,q in b.belief:
            live=mask&b.alive_mask;masses[live]=masses.get(live,F())+q
        counts=b.wolf_count_distribution;n=len(b.alive)
        return len(masses)==sum(comb(n,w) for w in counts) and all(q==counts[m.bit_count()]/comb(n,m.bit_count()) for m,q in masses.items())

    def checked(self, value):
        if isinstance(value,FuturePending):raise Pending(value.reason)
        return value

    def project(self,state,board):
        return project_private(state,board,marginalize_private=False)

    def acquire(self,b,state):
        key=(b,state)
        if key not in self.acquired:
            self.acquired[key]=self.checked(acquire_uniform(state,b.alive,max_work=self.max_work,
                                                          position=self.strategy.seer_position))
        return self.acquired[key]

    def public_children(self,b,target):
        if b.phase=='day':return action_outcomes(b,target,self.rules,self.strategy)
        try:
            return night_observation_outcomes(b,target,self.rules,self.strategy)
        except ValueError:
            raise Pending('information_set_public_corpse_inconsistent')

    def publications(self,b,s,past):
        if self.strategy.disclosure_for('seer')=='none':return ((F(1),b,s,past),)
        branches=self.checked(future_publications(s,past,b.alive,b.claims,
                                                  fake_policy=self.strategy.fake_seer_policy))
        return public_report_branches(b,past,branches)

    def scalar(self,b,s,past):return self.solve(b,s,past,s,None)

    def morning(self,b,s,past):
        actions=report_actions(b) if self.strategy.disclosure_for('medium')=='all' else ()
        if not actions:return self.publications(b,s,past)
        if self.strategy.fake_reports=='random':outcomes=random_report_outcomes(b)
        else:
            scored=[]
            for action in actions:
                value=F()
                for o in action.outcomes:
                    st=self.project(s,o.board)
                    value+=o.probability*sum((q*self.scalar(child,ns,reports)
                        for q,child,ns,reports in self.publications(o.board,st,past)),F())
                scored.append((value,action))
            best=min(v for v,_ in scored);tied=tuple(a for v,a in scored if v==best)
            grouped={}
            for action in tied:
                for o in action.outcomes:
                    child,entries=grouped.setdefault(o.board.reports,(o.board,{}))
                    for w in o.board.worlds:entries[w[:-1]]=entries.get(w[:-1],F())+o.probability*w[-1]/len(tied)
            merged=[]
            for child,entries in grouped.values():
                mass=sum(entries.values(),F())
                merged.append(BoardOutcome(mass,replace_worlds(child,tuple((*w,q/mass) for w,q in sorted(entries.items())))))
            outcomes=tuple(merged)
        result=[]
        for o in outcomes:
            st=self.project(s,o.board)
            result.extend((o.probability*q,c,ns,reports) for q,c,ns,reports in self.publications(o.board,st,past))
        return tuple(result)

    def push(self,source,private,branches):
        public={(h.roles,h.acquisitions):h.mass for h in source.hypotheses}
        own={(h.roles,h.acquisitions):h.mass for h in private.hypotheses};result=[]
        for q,b,s,past in branches:
            entries=tuple(Hypothesis(h.roles,h.acquisitions,q*h.mass*own[(h.roles,h.acquisitions)]/public[(h.roles,h.acquisitions)])
                          for h in s.hypotheses if (h.roles,h.acquisitions) in own)
            mass=sum((h.mass for h in entries),F())
            if mass:result.append((mass,b,s,past,replace(s,hypotheses=normalize(entries))))
        if sum((q for q,*_ in result),F())!=1:raise Pending('information_set_report_likelihood_incomplete')
        return result

    def act(self,b,s,past,target,private,observer):
        tick(len(s.hypotheses)+len(private.hypotheses))
        private_board=replace_worlds(b,private.public_roles)
        if target not in legal_targets(private_board,self.rules,self.strategy):
            raise Pending('information_set_internal_illegal_action')
        return action_flow(b,(s,past,private,observer,private_board),target,self.action_policy)

    def wolf_policy(self,b,s,past,mask):
        key=(b,s,past,mask)
        if key in self.policies:return self.policies[key]
        # This conditional law starts from the PUBLIC joint prior, never the viewer.
        hs=tuple(h for h in s.hypotheses if h.roles[0]==mask)
        if not hs:raise Pending('information_set_roster_missing')
        group=replace(s,hypotheses=normalize(hs))
        targets=tuple(p for p in b.alive if self.strategy.include_self_bite or not mask&(1<<(p-1)))
        if self.strategy.night=='random':scores=();chosen=targets
        else:
            if self.exchangeable(b):
                w=(mask&b.alive_mask).bit_count();n=len(b.alive)
                scores=tuple((p,exchangeable_value(n-1,w-int(bool(mask&(1<<(p-1)))),'day',self.strategy)) for p in targets)
            else:scores=tuple((p,self.act(b,s,past,p,group,None)) for p in targets)
            best=min(v for _,v in scores);chosen=tuple(p for p,v in scores if v==best)
        if not chosen:raise Pending('information_set_no_legal_bite')
        result=tuple((p,F(1,len(chosen))) for p in chosen);self.policies[key]=result
        if self.trace is not None:
            self.trace.setdefault('wolf_policies',[]).append({'history':b.history,'mask':mask,'scores':scores,'policy':result})
        return result

    def day_scores(self,b,s,past):
        key=(b,s,past)
        if key not in self.scores:
            self.scores[key]=tuple((p,self.act(b,s,past,p,s,None)) for p in b.alive)
        return self.scores[key]

    def solve(self,b,s,past,private,observer):
        key=(b,s,past,private,observer is not None)
        if key in self.values:return self.values[key]
        tick(len(private.hypotheses))
        if b.winner is not None:return F(b.winner=='village')
        if self.exchangeable(b):
            value=sum((h.mass*exchangeable_value(len(b.alive),(h.roles[0]&b.alive_mask).bit_count(),b.phase,self.strategy)
                       for h in private.hypotheses),F())
            self.values[key]=value;return value
        if b.phase=='day':
            if self.strategy.day=='random':targets=b.alive
            else:
                scores=self.day_scores(b,s,past);best=max(v for _,v in scores)
                targets=tuple(p for p,v in scores if v==best)
            value=sum((self.act(b,s,past,p,private,observer) for p in targets),F())/len(targets)
        else:
            groups={}
            for h in private.hypotheses:groups.setdefault(h.roles[0],[]).append(h)
            value=F()
            for mask,hs in groups.items():
                mass=sum((h.mass for h in hs),F());group=replace(private,hypotheses=normalize(tuple(hs)))
                value+=mass*sum((q*self.act(b,s,past,p,group,observer)
                                for p,q in self.wolf_policy(b,s,past,mask)),F())
        self.values[key]=value
        return value


class InformationSetActionPolicy:
    """Public compatibility updates, separate physical weights and observer law."""
    acquire_terminal = True

    def __init__(self,engine):self.engine=engine

    def acquire(self,b,payload):
        s,past,private,observer,physical=payload;e=self.engine
        public=e.acquire(b,s);own=e.acquire(b,private)
        if observer is not None:
            kept=tuple(h for h in own.hypotheses if observer(h,own))
            if not kept:raise Pending('seer_view_scan_outside_public_support')
            own=replace(own,hypotheses=normalize(kept))
        return public,past,own,observer,physical

    def outcomes(self,b,payload,target):
        s,past,private,observer,physical=payload;e=self.engine
        public={o.board.winner:o.board for o in e.public_children(b,target)}
        return tuple(FlowOutcome(o.probability,o.board,public.get(o.board.winner))
                     for o in action_outcomes(physical,target,e.rules,e.strategy))

    def project(self,b,payload,outcome,target):
        s,past,private,observer,physical=payload;e=self.engine;child=outcome.context
        st=e.project(s,child);own=e.project(private,outcome.board)
        if e.trace is not None and b.phase=='night':
            e.trace.setdefault('public_updates',[]).append({'history':b.history,'target':target,
                'prior_counts':b.wolf_count_distribution,'child_counts':child.wolf_count_distribution})
        return child,st,past,own,observer

    def morning_value(self,payload):
        child,st,past,own,observer=payload;e=self.engine
        branches=e.push(st,own,e.morning(child,st,past))
        return sum((q*e.solve(c,ns,p,priv,observer) for q,c,ns,p,priv in branches),F())

    def day_value(self,payload):return self.engine.solve(*payload)


def information_forecast(b,s,past,rules,strategy,*,observer=None,mask=None,max_work=250000,max_seconds=20,trace=None):
    if s.public_roles!=tuple(sorted(b.worlds)):
        raise ValueError('Public acquisition prior must match public Board')
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            engine=InformationSetForecast(rules,strategy,max_work=max_work,trace=trace)
            hs=tuple(h for h in s.hypotheses if (observer(h,s) if observer is not None else h.roles[0]==mask))
            if not hs:raise ValueError('Inconsistent observer')
            private=replace(s,hypotheses=normalize(hs))
            if observer is not None:return engine.solve(b,s,past,private,observer)
            targets=tuple(p for p in b.alive if strategy.include_self_bite or not mask&(1<<(p-1)))
            return tuple((p,engine.act(b,s,past,p,private,None)) for p in targets)
    except CalculationBudgetExceeded:return FuturePending('information_set_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)
