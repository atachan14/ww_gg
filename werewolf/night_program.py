"""Shared exact night joint measure and role-ordered prefix states.

Policies are committed from night-start Q/actor information. Stage partitions
are viewer P, never new public evidence or input to a later actor's policy.
Equivalent target branches require one full source automorphism transporting
all named outcome laws and remaining stage paths. Named recipes are retained.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from itertools import permutations,product
from .night_abilities import AbilityStep,recorded_steps,ROLE_ORDER
from .exact_renaming import renamed_source_signature as signature
from .actor_information import wolf_information_groups,condition_actor_state
from .evaluation_branch import ContinuationInputs,ActionInputs,physical_board
from .action_flow import resolve_action
from .board_future import outcome_key
from .joint_action_kernel import report_signature
from .group_partition import _fix
from .calculation_budget import tick

@dataclass(frozen=True)
class NightLeaf:
    mass:F
    counter:F
    source:object
    steps:tuple
    information:object
    owner_index:int
    target:int
    outcome_index:int
    death_key:object
    report:object
    wolves:tuple
    scans:tuple
    groups:tuple

@dataclass(frozen=True)
class StageBranch:
    probability:F
    policy_probability:F
    counter_probability:F
    mass:F
    step:AbilityStep
    targets:tuple
    state:object
    images:tuple

class NightStage:
    def __init__(self,program,leaves,prefix=()):
        self.program=program;self.leaves=tuple(leaves);self.prefix=prefix;self._branches=None;self._outcomes=None
        self.mass=sum((r.mass for r in leaves),F());self.counter=sum((r.counter for r in leaves),F())
        self.public=program.source.public_state
    @property
    def physical_atoms(self):
        # Integrate future actions/results; these coordinates are latent, not
        # actor observations. Original Q is kept in self.public unchanged.
        from .seer_acquisition import normalize
        total=self.mass or self.counter
        return normalize(tuple(replace(h,mass=h.mass*(r.mass if self.mass else r.counter)/total)
            for r in self.leaves if (r.mass if self.mass else r.counter)
            for h in r.source.private.hypotheses))

    @property
    def terminal(self):return all(len(r.steps)==len(self.prefix) for r in self.leaves)
    def actor_information(self,actor):
        return tuple((h.roles,tuple(a for a in h.acquisitions if a.player==actor),h.mass) for h in self.public.hypotheses)
    def branches(self):
        if self._branches is not None:return self._branches
        buckets={};index=len(self.prefix)
        for leaf in self.leaves:
            if index<len(leaf.steps):buckets.setdefault(leaf.steps[index],[]).append(leaf)
        groups=[]
        ordered=sorted(buckets.items(),key=lambda pair:(pair[0].kind,pair[0].actor or 0,pair[0].actors,{'white':0,'black':1}.get(pair[0].value,pair[0].value)))
        for step,leaves in ordered:
            if self.program.method=='role-staged-exact-v1':
                groups.append([step,leaves,[(step,tuple(leaves),self.program.identity)]]);continue
            found=False
            for group in groups:
                for mapping in self.program.automorphisms:
                    if (self.program.moved_steps(self.prefix,mapping)!=self.prefix or
                        self.program.moved_steps((step,),mapping)!=(group[0],)):continue
                    if self.program.measure(leaves,mapping)!=self.program.measure(group[1],self.program.identity):continue
                    group[2].append((step,tuple(leaves),mapping));found=True;break
                if found:break
            if not found:groups.append([step,leaves,[(step,tuple(leaves),self.program.identity)]])
        branches=[]
        for step,leaves,images in groups:
            mass=sum((r.mass for _,rows,_ in images for r in rows),F());counter=sum((r.counter for _,rows,_ in images for r in rows),F())
            # A target group lists images fixing the canonical actor. Actor
            # transports are retained separately, never interpreted as a set
            # cross product between possible actors and possible targets.
            targets=tuple(sorted({s.value for s,rows,m in images if s.actor==step.actor and s.actors==step.actors})) if step.kind.endswith('_target') else ()
            branches.append(StageBranch(mass/self.mass if self.mass else counter/self.counter,
                mass/self.mass if self.mass else F(),counter/self.counter,mass,step,targets,
                NightStage(self.program,leaves,(*self.prefix,step)),tuple(images)))
        self._branches=tuple(branches);return self._branches
    def outcomes(self):
        if self._outcomes is not None:return self._outcomes
        groups=[];identity=self.program.identity
        if self.program.method=='role-staged-exact-v1':
            buckets={}
            for leaf in self.leaves:buckets.setdefault(leaf.source,[]).append(leaf)
            self._outcomes=tuple((sum(r.mass for r in rows),sum(r.counter for r in rows),rows[0],tuple((r,identity) for r in rows)) for rows in buckets.values())
            return self._outcomes
        for leaf in self.leaves:
            found=False
            for group in groups:
                first=group[0]
                for mapping in self.program.automorphisms:
                    if (self.program.moved_steps(self.prefix,mapping)!=self.prefix or
                        leaf.mass!=first.mass or leaf.counter!=first.counter):continue
                    left,right=self.program.leaf_signature(leaf,mapping),self.program.leaf_signature(first,identity)
                    if left is not None and right is not None and left==right:
                        group[1].append((leaf,mapping));found=True;break
                if found:break
            if not found:groups.append([leaf,[(leaf,identity)]])
        self._outcomes=tuple((sum((r.mass for r,m in images),F()),sum((r.counter for r,m in images),F()),leaf,tuple(images)) for leaf,images in groups)
        return self._outcomes
    def value(self,engine):
        if self.terminal:
            total=self.mass or self.counter
            return sum(((mass if self.mass else counter)/total*self.program.continuation(engine,leaf) for mass,counter,leaf,images in self.outcomes()),F())
        return sum((b.probability*b.state.value(engine) for b in self.branches() if (b.policy_probability if self.mass else b.probability)),F())

class NightProgram:
    def __init__(self,engine,source,groups,leaves):
        self.method='role-staged-exact-v1' if source.public.initial_medium_count or source.public.initial_hunter_count else 'verified-named'
        self.source=source;self.leaves=tuple(leaves);self.groups=groups;self.identity=tuple(range(1,source.public.player_count+1));self.values={};self.signatures={};self.measures={}
        if self.method=='role-staged-exact-v1':
            self.automorphisms=(self.identity,);self.root=NightStage(self,self.leaves);return
        original=signature(source,self.identity);parts=tuple(groups)+tuple((p,) for p in self.identity if not any(p in g for g in groups))
        maps=[]
        if original is not None:
            for orders in product(*(permutations(g) for g in parts)):
                m=dict((a,b) for g,order in zip(parts,orders) for a,b in zip(g,order));mapping=tuple(m[p] for p in self.identity)
                if signature(source,mapping)==original:maps.append(mapping)
        self.automorphisms=tuple(maps) or (self.identity,)
        self.root=NightStage(self,self.leaves)
    def moved_steps(self,steps,mapping):
        return tuple(replace(s,actor=None if s.actor is None else mapping[s.actor-1],
            value=mapping[s.value-1] if s.kind.endswith('_target') else s.value,
            visible_to=tuple(mapping[p-1] for p in s.visible_to),actors=tuple(sorted(mapping[p-1] for p in s.actors))) for s in steps)
    def leaf_signature(self,leaf,mapping):
        key=(id(leaf.source),mapping)
        if key not in self.signatures:self.signatures[key]=signature(leaf.source,mapping)
        return self.signatures[key]
    def measure(self,leaves,mapping):
        key=(tuple(id(r) for r in leaves),mapping)
        if key in self.measures:return self.measures[key]
        result={}
        for r in leaves:
            tick();state=(id(r.source),mapping)
            if state not in self.signatures:self.signatures[state]=signature(r.source,mapping)
            key_state=self.signatures[state]
            if key_state is None:return ('unsupported',id(leaves),mapping)
            k=(key_state,self.moved_steps(r.steps,mapping));old=result.get(k,(F(),F()));result[k]=(old[0]+r.mass,old[1]+r.counter)
        self.measures[key]=result;return result
    def continuation(self,engine,leaf):
        s=leaf.source;key=s if self.method=='role-staged-exact-v1' else signature(s,self.identity) or ('named',s)
        if key not in self.values:
            with engine.group_scope(leaf.groups):self.values[key]=engine.solve(*s,physical=s.physical)
        return self.values[key]


def supported(engine,source):
    b=source.public
    return (b.phase=='night' and not b.winner and b.initial_hunter_count<=1
        and source.observer is None and source.public_state.tracked is None and source.private.tracked is None
        and getattr(engine,'retain_joint_guard_history',False) and hasattr(engine,'group_scope')
        and engine.acquisition_provenance is None and engine.trace is None
        and all(engine.strategy.disclosure_for(r)=='all' for r in ('seer','medium')))


def compile_night(engine,source,groups):
    if not supported(engine,source):return None
    if not hasattr(engine,'night_programs'):engine.night_programs={}
    key=(source,tuple(groups))
    if key in engine.night_programs:return engine.night_programs[key]
    b=source.public;leaves=[];offset=0
    # Commit every wolf information-set policy BEFORE any result partition.
    owners=[]
    for info,mass,law in wolf_information_groups(source.private):
        with engine.actor_scope(info):policy=dict(engine.wolf_policy(b,source.public_state,source.past,info.initial_roster,info.attacks))
        owners.append((info,mass,law,policy,offset));offset+=len(policy)
    for info,owner_mass,law,policy,owner_index in owners:
        wolves=tuple(p for p in b.alive if info.initial_roster&(1<<(p-1)))
        initial_wolves=tuple(p for p in range(1,b.player_count+1) if info.initial_roster&(1<<(p-1)))
        legal=tuple(p for p in b.alive if engine.strategy.include_self_bite or p not in wolves)
        payload=ActionInputs(source.public_state,source.past,law,None,physical_board(b,law,source.physical))
        for target in legal:
            with engine.group_scope(_fix(groups,(*initial_wolves,target))):
                acquired,deaths=resolve_action(b,payload,target,engine.action_policy,terminal_payoffs=False)
                for index,death in enumerate(deaths):
                    child=engine.action_policy.project(b,acquired,death,target)
                    reports=engine.report_children(child) if child.public.winner is None else ()
                    for report_mass,after,report in (tuple((p,c,report_signature(c)) for q,p,c in reports) if reports else ((F(1),child,None),)):
                        events={}
                        for h in after.private.hypotheses:
                            steps=recorded_steps(h,b.day+1)
                            if b.initial_medium_count:
                                execution=next((e.target for e in reversed(b.history) if e.phase=='day'),None)
                                if execution is not None:
                                    medium=tuple(AbilityStep('medium_result',p,(execution,'black' if h.roles[0]&(1<<(execution-1)) else 'white'),(p,)) for p in b.alive if h.roles[1]&(1<<(p-1)))
                                    steps=(*medium,*steps)
                            if not steps or steps[-1].kind!='wolf_target':steps=(*steps,AbilityStep('wolf_target',None,target,()))
                            steps=tuple(replace(step,actors=wolves) if step.kind=='wolf_target' else step for step in steps)
                            if b.initial_medium_count or b.initial_hunter_count:
                                dead=tuple(p for p in b.alive if p not in child.public.alive)
                                if len(dead)>1:raise engine.pending('staged_multiple_deaths_unimplemented')
                                steps=(*steps,AbilityStep('death_notice',None,dead[0] if dead else None))
                                if any(claim in ('seer','medium') for claim in b.claims):
                                    from .tree_public_updates import publication_label
                                    steps=(*steps,AbilityStep('publication',None,publication_label(child,after)))
                            scans=tuple(sorted((a.player,a.target) for a in h.acquisitions if a.day==b.day+1))
                            events.setdefault((steps,scans),[]).append(h)
                        for (steps,scans),hypotheses in events.items():
                            event_mass=sum((h.mass for h in hypotheses),F());own=condition_actor_state(after.private,lambda h:h in hypotheses)
                            final=replace(after,private=own,physical=physical_board(after.public,own,after.physical),board_data=None,provenance=None)
                            chance=owner_mass*death.probability*report_mass*event_mass
                            positions=(*initial_wolves,target,*(p for pair in scans for p in pair))
                            leaves.append(NightLeaf(chance*policy.get(target,F()),chance/F(len(legal)),final,steps,info,owner_index,target,index,outcome_key(death),report,initial_wolves,scans,_fix(groups,positions)))
    result=NightProgram(engine,source,groups,leaves);engine.night_programs[key]=result;return result
