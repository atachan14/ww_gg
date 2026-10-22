"""Explicit legacy/Current boundary. Never used to generate anonymous beliefs.

This module expands names only for existing named scalar/MAX consumers. The
belief owner and public posterior kernels do not call back into a named solver.
"""
from dataclasses import replace
from itertools import combinations,permutations
from fractions import Fraction as F
from math import factorial
from .anonymous_relations import Person
from .seer_acquisition import Acquisition,Hypothesis,normalize,public_worlds
from .night_knowledge import WolfAttack
from .calculation_budget import tick

def assignments(atom,groups):
    pop=atom.population;fixed={ref:name for name,ref in atom.pins}
    def group_rows(index,names,roles):
        if index==len(groups):yield names,roles;return
        group=groups[index];available=tuple(p for p in group if p not in fixed.values())
        refs=tuple(ref for ref,p in enumerate(pop.people) if p.group==index and ref not in fixed)
        for selected in permutations(available,len(refs)):
            chosen={**names,**dict(zip(refs,selected))};remaining=tuple(p for p in available if p not in selected)
            cells=tuple((i,c) for i,c in enumerate(pop.cells) if c.group==index and c.count)
            def cells_rows(at,left,current):
                if at==len(cells):
                    if left:raise ValueError('Anonymous cell capacity mismatch')
                    yield current;return
                cell_index,cell=cells[at]
                for subset in combinations(left,cell.count):
                    yield from cells_rows(at+1,tuple(p for p in left if p not in subset),{**current,**{p:cell.role for p in subset}})
            for cell_roles in cells_rows(0,remaining,roles):yield from group_rows(index+1,chosen,cell_roles)
    yield from group_rows(0,fixed,{})

def hypothesis(pop,names,cell_roles,mass=F(1)):
    roles={**cell_roles,**{names[i]:p.role for i,p in enumerate(pop.people)}}
    masks=tuple(sum(1<<(p-1) for p,r in roles.items() if r==role) for role in ('wolf','medium','seer','hunter'))
    acquired=tuple(sorted(Acquisition(a.day,names[a.actor],names[a.target],a.color) for a in pop.scans))
    bitten=tuple(WolfAttack(day,names[ref]) for day,ref in pop.attacks)
    from .guard_effect import GuardIntent
    guards=tuple(GuardIntent(m.day,names[m.actor],names[m.participants[0]]) for m in pop.memories if m.kind=='guard')
    return Hypothesis(masks,acquired,mass,guards,bitten)

def expand(law,groups):
    rows=[]
    for mass,atom in law.rows:
        count=1
        for index,group in enumerate(groups):
            free=len(group)-sum(name in group for name,ref in atom.pins)
            count*=factorial(free)
            for cell in atom.population.cells:
                if cell.group==index:count//=factorial(cell.count)
        for names,cell_roles in assignments(atom,groups):
            tick();rows.append(hypothesis(atom.population,names,cell_roles,mass/count))
    return normalize(tuple(rows))

def representative(atom,groups):
    from .anonymous_night import Transport
    pop=atom.population;names={ref:name for name,ref in atom.pins};used=set(names.values())
    for ref,person in enumerate(pop.people):
        if ref not in names:
            name=next(p for p in groups[person.group] if p not in used);names[ref]=name;used.add(name)
    free=[];cell_roles={}
    for cell in pop.cells:
        chosen=tuple(p for p in groups[cell.group] if p not in used)[:cell.count]
        if len(chosen)!=cell.count:raise ValueError('Anonymous representative capacity mismatch')
        free.append(chosen);used.update(chosen);cell_roles.update({p:cell.role for p in chosen})
    return hypothesis(pop,names,cell_roles),Transport(tuple(names[i] for i in range(len(pop.people))),tuple(free))

def source(belief,template):
    from .exact import replace_worlds
    from .phase_updates import acquisition_roster
    q=expand(belief.q,belief.groups);p=expand(belief.p,belief.groups)
    n=template.public.player_count
    rosters=tuple(acquisition_roster(n,belief.history,day) for day in range(1,belief.day+1))
    public=replace_worlds(template.public,public_worlds(q))
    physical=replace_worlds(template.physical,public_worlds(p))
    return replace(template,public=public,public_state=replace(template.public_state,hypotheses=q,rosters=rosters),
        private=replace(template.private,hypotheses=p,rosters=rosters),physical=physical,board_data=None,provenance=None)
