"""Prepared-joint fixtures only, not a new game observation or policy rule."""
from dataclasses import replace
from .run import source
from werewolf.exact import replace_worlds,ROLES
from werewolf.seer_acquisition import normalize
from werewolf.player_view import build_public_view,ResultFrame


def weighted_source(n=6,wolves=2,kind='cycle'):
    data,roles,b,s,past,rules,strategy,view=source(n,wolves)
    edges={frozenset((p,2+(p-1)%(n-1)))for p in range(2,n+1)}
    def likelihood(h):
        if kind=='point':return 2 if h.roles[0]&2 else 1
        assert wolves==2
        pair=frozenset(p for p in range(2,n+1)if h.roles[0]&(1<<(p-1)))
        return 2 if pair in edges else 1
    # Exact Bayes multiplication and normalization on already complete support.
    # Likelihoods are synthetic acceptance fixtures, never persisted evidence.
    s=replace(s,hypotheses=normalize(tuple(replace(h,mass=h.mass*likelihood(h))for h in s.hypotheses)))
    b=replace_worlds(b,s.public_roles)
    rates=tuple(tuple((r,b.role_probability(p,r))for r in ROLES)for p in range(1,n+1))
    roles=replace(roles,progress=replace(roles.progress,board=b),rates=rates)
    view=build_public_view(data,roles,b,ResultFrame(view.scope,'roles'),state=data.to_game(),event_history=b.history,alive=b.alive,action_values={},by_dawn_values={})
    return data,roles,b,s,past,rules,strategy,view
