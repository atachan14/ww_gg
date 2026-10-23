"""Full-game exact decisions for the fixed all-hidden/no-report belief owner.

Private scans never enter a public report or a wolf information set in this
admitted flow. Scalar evaluation may marginalize those records, retaining the
complete role law and every public/privately distinguished identity. The Tree
belief is never projected. This is relevance elimination, not a depth cutoff.
"""
from dataclasses import replace
from fractions import Fraction as F
from .anonymous_belief import Atom,Law,Belief,winner
from .anonymous_relations import Cell,Population
from .calculation_budget import tick

def projected(law):
    rows=[]
    for mass,atom in law.rows:
        pop=atom.population;refs=tuple(ref for name,ref in atom.pins);people=tuple(pop.people[ref] for ref in refs)
        pins=tuple((name,index) for index,(name,ref) in enumerate(atom.pins));cells={}
        for cell in pop.cells:cells[cell.group,cell.role,cell.alive]=cells.get((cell.group,cell.role,cell.alive),0)+cell.count
        for ref,person in enumerate(pop.people):
            if ref not in refs:cells[person.group,person.role,person.alive]=cells.get((person.group,person.role,person.alive),0)+1
        rows.append((mass,Atom(Population(tuple(Cell(g,r,n,alive) for (g,r,alive),n in sorted(cells.items()) if n),people),pins)))
    return Law.weighted(rows)[1]

def information(atom,groups):
    pop=atom.population
    return tuple(sum(p.group==g and p.role=='wolf' for p in pop.people)+sum(c.count for c in pop.cells if c.group==g and c.role=='wolf') for g in range(len(groups)))

def alive(b):
    dead={d.target for d in b.history};return tuple(p for group in b.groups for p in group if p not in dead)

class Evaluator:
    def __init__(self,day='random',night='random',win_cutoff=False):
        if day not in ('random','max') or night not in ('random','max'):raise ValueError('Existing random/MAX choices required')
        self.win_cutoff=win_cutoff and day=='max';self.cutoff_hits=0
        self.day=day;self.night=night;self.values={};self.policies={};self.scores={};self.transitions={};self.reductions={}
    def scalar(self,b):
        living=set(alive(b));groups=[]
        for group in b.groups:
            groups.extend((p,) for p in group if p not in living)
            residual=tuple(p for p in group if p in living)
            if residual:groups.append(residual)
        b=b.refine(tuple(groups))
        return replace(b,q=projected(b.q),p=projected(b.p))
    def value(self,b):
        b=self.scalar(b)
        if b in self.values:return self.values[b]
        from .win_certificate import certify_anonymous
        if certify_anonymous(b,self.win_cutoff) is not None:
            self.cutoff_hits+=1;self.values[b]=F(1);self.reductions[b]='guaranteed-win-certificate';return F(1)
        tick();terminal={winner(a.population) for m,a in b.p.rows}
        if len(terminal)==1 and None not in terminal:result=F(next(iter(terminal))=='village')
        elif None not in terminal or len(terminal)>1:raise ValueError('Separate observed terminal states before evaluation')
        elif b.phase=='day':
            scores=self.day_scores(b);best=max(v for group,v in scores)
            selected=[(group,v) for group,v in scores if self.day=='random' or v==best];total=sum(len(g) for g,v in selected)
            result=sum((F(len(g),total)*self.force_day(b,g[0]) for g,v in selected),F())
        else:
            result=sum((mass*self.value(child) for mass,observation,child in self.night_children(b)),F())
        self.values[b]=result;self.reductions[b]='terminal' if None not in terminal else 'evaluated-anonymous-'+b.phase;return result
    def day_scores(self,b):
        key=(b.groups,b.q,b.day,b.history)
        if key not in self.scores:
            public=replace(b,p=b.q);living=set(alive(b))
            groups=tuple(tuple(p for p in group if p in living) for group in b.groups)
            self.scores[key]=tuple((g,self.force_day(public,g[0])) for g in groups if g)
        return self.scores[key]
    def day_children(self,b,target):
        key=('day',b,target)
        if key not in self.transitions:self.transitions[key]=b.execute(target)
        return self.transitions[key]
    def night_children(self,b,target=None):
        key=('night',b,target)
        if key not in self.transitions:
            flow=self.night_flow(b) if target is None else self.forced_night_flow(b,target)
            self.transitions[key]=tuple((pair[0],obs,pair[1]) for obs in flow.observations() if (pair:=self.positive(flow,obs)) is not None)
        return self.transitions[key]
    def force_day(self,b,target):return sum((mass*self.value(child) for mass,result,child in self.day_children(b,target)),F())
    def actor(self,b,info):
        partitions=[];wolves=set()
        for group,count in zip(b.groups,info):
            owned=group[:count];rest=group[count:];wolves.update(owned)
            if owned:partitions.append(owned)
            if rest:partitions.append(rest)
        actor=replace(b,p=b.q).refine(tuple(partitions))
        expected=tuple(len(g) if set(g)<=wolves else 0 for g in actor.groups)
        law=actor.p.condition(lambda atom:information(atom,actor.groups)==expected)[1]
        return replace(actor,p=law),wolves
    def wolf_policy(self,b,info):
        key=(b.groups,b.q,b.day,b.history,info)
        if key in self.policies:return self.policies[key]
        living=set(alive(b));eligible=[sum(p in living for p in group)-count if all(p in living for p in group) else sum(p in living for p in group) for group,count in zip(b.groups,info)]
        # Public groups are refined at death, so all members share life status.
        if self.night=='random':result={g:F(1,sum(eligible)) for g,n in enumerate(eligible) if n}
        else:
            actor,wolves=self.actor(b,info);scores=[]
            for index,group in enumerate(b.groups):
                targets=tuple(p for p in group if p in living and p not in wolves)
                if targets:scores.append((index,len(targets),self.force_night(actor,targets[0])))
            best=min(v for g,n,v in scores);total=sum(n for g,n,v in scores if v==best)
            result={g:F(1,total) if v==best else F() for g,n,v in scores}
        self.policies[key]=result;return result
    def night_flow(self,b,*,acquire=False):
        def factory(atom):
            policy=self.wolf_policy(b,information(atom,b.groups))
            return lambda choice,bindings:policy.get(choice.population.people[choice.target].group,F())
        return b.night(factory,acquire=acquire)
    def forced_night_flow(self,b,target,*,acquire=False):
        groups=[]
        for group in b.groups:
            if target in group and len(group)>1:groups.extend(((target,),tuple(p for p in group if p!=target)))
            else:groups.append(group)
        b=b.refine(tuple(groups))
        def identify(law):return Law.weighted((mass*q,child) for mass,atom in law.rows for q,child,ref in atom.pin(target,b.groups))[1]
        b=replace(b,q=identify(b.q),p=identify(b.p))
        totals={};legal={}
        def count(atom):
            pop=atom.population
            return sum(p.alive and p.role=='wolf' for p in pop.people)+sum(c.count for c in pop.cells if c.alive and c.role=='wolf')
        for mass,atom in b.p.rows:
            w=count(atom);totals[w]=totals.get(w,F())+mass
            if atom.population.people[dict(atom.pins)[target]].role!='wolf':legal[w]=legal.get(w,F())+mass
        if set(totals)!=set(legal):raise ValueError('Target cannot be legally bitten in every count hypothesis')
        law=Law.weighted((mass*totals[count(atom)]/legal[count(atom)],atom) for mass,atom in b.p.rows if atom.population.people[dict(atom.pins)[target]].role!='wolf')[1]
        b=replace(b,p=law)
        def factory(atom):
            ref=dict(atom.pins)[target]
            return lambda choice,bindings:F(choice.target==ref)
        return b.night(factory,acquire=acquire)
    def force_night(self,b,target):
        return sum((mass*self.value(child) for mass,obs,child in self.night_children(b,target)),F())
    def horizon(self,b,target):
        from .by_dawn import HorizonValues
        v=w=F()
        if b.phase=='night':
            rows=self.forced_night_flow(self.scalar(b),target).rows
            return HorizonValues(sum((r.mass for r in rows if r.observation[1]=='village'),F()),sum((r.mass for r in rows if r.observation[1]=='wolf'),F()))
        for mass,result,child in self.scalar(b).execute(target):
            if result:v+=mass*F(result=='village');w+=mass*F(result=='wolf')
            else:
                rows=self.night_flow(self.scalar(child)).rows
                v+=mass*sum((r.mass for r in rows if r.observation[1]=='village'),F())
                w+=mass*sum((r.mass for r in rows if r.observation[1]=='wolf'),F())
        return HorizonValues(v,w)
    def forecast(self,b):
        from .forecast_result import Forecast
        b=self.scalar(b)
        if all(winner(atom.population) is not None for mass,atom in b.p.rows):return Forecast(self.value(b),())
        actions=[];horizons=[]
        for group in b.groups:
            targets=tuple(p for p in group if p in alive(b))
            if not targets:continue
            target=targets[0]
            try:value=self.force_day(b,target) if b.phase=='day' else self.force_night(b,target)
            except ValueError as error:
                if str(error)!='Target cannot be legally bitten in every count hypothesis':raise
                continue
            horizon=self.horizon(b,target)
            actions.extend((p,value) for p in targets);horizons.extend((p,horizon) for p in targets)
        return Forecast(self.value(b),tuple(sorted(actions)),tuple(sorted(horizons)))
    @staticmethod
    def positive(flow,obs):
        try:return flow.branch(obs)
        except ValueError as error:
            if str(error)!='Anonymous observation has zero support':raise
            return None


def initial_forecast(data):
    """Opt-in initial fixed-hidden public value; unsupported semantics return None.

    Named BoardTable preparation/Current compatibility remain separate callers.
    This entry does not reconstruct roles or create a named initial prior.
    """
    game=data.to_game();g=data.game_data
    if (g.mediums or g.hunters or g.rules.allow_self_bite or game.get('history') or game.get('seer_inputs') or game.get('reports')
        or any(c!='latent' for c in game.get('claims',())) or game.get('model')!='group'
        or game.get('seer_mode')!='information-fixed-v1' or game.get('seer_options',{}).get('likelihood')!='compatibility'
        or game.get('seer_options',{}).get('initial_rule')!='random_white'):
        return None
    from .exact import Strategy
    policy=Strategy(**game['policy'])
    if policy.include_self_bite or (policy.day,policy.night,policy.fake_reports) not in (('random',)*3,('max',)*3) or any(policy.disclosure_for(role)!='all' for role in ('seer','medium')):return None
    key=('anonymous-public-no-report-v1',data.inputs)
    hit,value=data.runtime.get(key)
    if hit:return value
    owner=Belief.initial((tuple(range(1,g.players+1)),),dict(wolf=g.wolves,seer=g.seers,villager=g.players-g.wolves-g.seers),g.rules.initial_seer)
    result=Evaluator(policy.day,policy.night,policy.win_cutoff).forecast(owner)
    data.runtime.put(key,result);return result
