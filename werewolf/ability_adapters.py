"""Established role semantics over common anonymous binders and memory slots."""
from dataclasses import dataclass,replace
from .anonymous_abilities import Memory,Effect,slots
from .anonymous_relations import Step,Scan

class Personal:
    def actors(self,pop):return tuple(ref for ref,p in enumerate(pop.people) if p.alive and p.role in self.roles)

@dataclass(frozen=True)
class Divination(Personal):
    key:str='seer'
    roles:tuple=('seer',)
    def choices(self,pop,actor,context):
        seen={s.target for s in pop.scans if s.actor==actor} if not context.initial_white else set()
        return slots(pop,lambda p,ref:p.alive and ref!=actor and ref not in seen and (not context.initial_white or p.role!='wolf'))
    def apply(self,path,actor,choice,context):
        pop=path.population;target=choice.target;color='black' if pop.people[target].role=='wolf' else 'white'
        memory=Memory('divination',context.acquisition_day,actor,(target,),color,(actor,))
        pop=replace(pop,scans=(*pop.scans,Scan(context.acquisition_day,actor,target,color)),memories=(*pop.memories,memory))
        return replace(path,population=pop,steps=(*path.steps,Step('seer_target',actor,target),Step('seer_result',actor,color)))

@dataclass(frozen=True)
class Medium(Personal):
    key:str='medium'
    roles:tuple=('medium',)
    observation_only:bool=True
    def observe(self,path,actor,context):
        if context.execution is None:return path
        pop=path.population;color='black' if pop.people[context.execution].role=='wolf' else 'white'
        record=Memory('medium',context.acquisition_day,actor,(context.execution,),color,(actor,))
        return replace(path,population=replace(pop,memories=(*pop.memories,record)),steps=(*path.steps,Step('medium_result',actor,(context.execution,color))))

@dataclass(frozen=True)
class Guard(Personal):
    key:str='guard'
    roles:tuple=('hunter',)
    def choices(self,pop,actor,context):
        previous=next((m.participants[0] for m in reversed(pop.memories) if m.kind=='guard' and m.actor==actor and m.day==context.day-1),None)
        if context.day>1 and not context.allow_repeat_guard and previous is None:raise ValueError('Previous guard history required by no-repeat rule')
        return slots(pop,lambda p,ref:p.alive and ref!=actor and (context.allow_repeat_guard or ref!=previous))
    def apply(self,path,actor,choice,context):
        pop=path.population;target=choice.target
        record=Memory('guard',context.day,actor,(target,),None,(actor,))
        return replace(path,population=replace(pop,memories=(*pop.memories,record),effects=(*pop.effects,Effect('protect',(target,),context.day))),steps=(*path.steps,Step('guard_target',actor,target)))

@dataclass(frozen=True)
class WolfAttack:
    key:str='attack'
    roles:tuple=()
    def actors(self,pop):return (None,)
    def choices(self,pop,actor,context):return slots(pop,lambda p,ref:p.alive and (context.include_self_bite or p.role!='wolf'))
    def apply(self,path,actor,choice,context):
        pop=path.population;target=choice.target
        record=Memory('attack',context.day,None,(target,),None,tuple(ref for ref,p in enumerate(pop.people) if p.role=='wolf'))
        return replace(path,population=replace(pop,attacks=(*pop.attacks,(context.day,target)),memories=(*pop.memories,record),effects=(*pop.effects,Effect('attack',(target,),context.day))),steps=(*path.steps,Step('wolf_target',None,target,pop.wolves())))
