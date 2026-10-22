"""Labels for correlated canonical actor allocations and residual targets."""
def marked(members,representatives):
    members=tuple(sorted(members));reps=set(representatives)
    return '['+','.join('('+str(p)+')' if p in reps else str(p) for p in members)+']' if len(members)>1 else str(members[0])

def stage_label(branch):
    step=branch.step;actor_groups=[]
    if step.kind in ('seer_target','guard_target'):
        actors=sorted({named.actor for named,leaves,mapping in branch.images})
        actor_groups=[dict(members=actors,representatives=[step.actor],count=1)]
        owner=marked(actors,(step.actor,))
    elif step.kind=='wolf_target':
        rosters={named.actors for named,leaves,mapping in branch.images}
        remaining=set(p for roster in rosters for p in roster)
        while remaining:
            orbit={min(remaining)};changed=True
            while changed:
                changed=False
                for named,leaves,mapping in branch.images:
                    for p in tuple(orbit):
                        for q in (mapping[p-1],next(i+1 for i,v in enumerate(mapping) if v==p)):
                            if q in remaining and q not in orbit:orbit.add(q);changed=True
            representatives=tuple(p for p in step.actors if p in orbit)
            if representatives:actor_groups.append(dict(members=sorted(orbit),representatives=list(representatives),count=len(representatives)))
            remaining-=orbit
        owner='\u3068'.join(marked(g['members'],g['representatives'])+(f"\uff08{g['count']}\u4eba\uff09" if g['count']>1 else '') for g in actor_groups)
    else:owner=''
    if step.kind in ('seer_target','guard_target','wolf_target'):
        targets=branch.targets or (step.value,)
        positions=marked(targets,(step.value,))
        action='\u304b\u3089\u5360\u3044' if step.kind=='seer_target' and len(targets)>1 else ('\u3092\u5360\u3044' if step.kind=='seer_target' else '\u3092\u8972\u6483')
        if step.kind=='guard_target':action='を護衛'
        label=owner+'\u304c'+positions+action
    elif step.kind=='seer_result':label={'white':'\u767d','black':'\u9ed2'}[step.value]
    elif step.kind=='medium_result':label=str(step.actor)+'：'+str(step.value[0])+('黒' if step.value[1]=='black' else '白')
    elif step.kind=='death_notice':label='襲撃死：'+('なし' if step.value is None else str(step.value))
    elif step.kind=='publication':label=step.value
    else:label=step.kind
    choices=[dict(actors=list(named.actors) if named.kind=='wolf_target' else [named.actor],target=named.value,transport=list(mapping)) for named,leaves,mapping in branch.images] if step.kind.endswith('_target') else []
    return label,actor_groups,choices
