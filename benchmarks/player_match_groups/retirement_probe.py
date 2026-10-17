"""Observe retirement provenance loss without changing solver behavior."""
import json
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from .initial_white import initial_white_source
from .checkpoint_audit import encode
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.action_flow import resolve_action
from werewolf.evaluation_branch import ActionInputs,physical_board


def probe(n=5,wolves=1,expose_truth=False):
    _,_,b,s,past,rules,strategy,_=initial_white_source(n,wolves,actors=(1,2))
    if expose_truth:
        # Controlled PUBLIC-support counterfactual, not an own secret or an
        # inference that P1 death by itself reveals P1's role.
        from werewolf.seer_acquisition import normalize
        from werewolf.exact import replace_worlds
        s=replace(s,hypotheses=normalize(tuple(h for h in s.hypotheses if h.roles[2]&1)))
        b=replace_worlds(b,s.public_roles)
    e=InformationSetForecast(rules,strategy)
    inputs=ActionInputs(s,past,s,None,physical_board(b,s))
    acquired,outcomes=resolve_action(b,inputs,1,e.action_policy,terminal_payoffs=True)
    rows=[]
    for outcome in outcomes:
        if outcome.board.winner is not None:continue
        child,st,hist,own,observer=e.action_policy.project(b,acquired,outcome,1)
        if not e.can_retire_scans(child,st,hist):continue
        projected,ps,ph,po,obs=e.continuation_context(child,st,hist,own,observer)
        if e.can_retire_scans(projected,ps,ph):continue
        next_state=e.acquire(projected,ps)
        morning=replace(projected,phase='day')
        branches=e.publications(morning,next_state,ph)
        from werewolf.actor_information import wolf_information_groups
        private_checks=[]
        for info,mass,group in wolf_information_groups(next_state):
            pushed=e.push(next_state,group,branches)
            private_checks.append(sum(q for q,_,_,_,_ in pushed)==1 and all(priv==group for _,_,_,_,priv in pushed))
        rows.append(dict(wolf_information_groups=len(private_checks),private_conditional_laws_unchanged=all(private_checks),incoming_probability=outcome.probability,alive=child.alive,claims=child.claims,initial_seers_before=child.initial_seer_count,initial_seers_after=projected.initial_seer_count,initial_rule=st.initial_rule,past_before=hist,past_after=ph,can_retire_before=True,can_retire_after=False,generated_branches=len(branches),total_probability=sum((q for q,_,_,_ in branches),F()),all_role_posteriors_unchanged=all(ns.public_roles==next_state.public_roles for _,_,ns,_ in branches),generated_acquired_days=sorted({r.acquired_day for _,_,_,h in branches for r in h})))
    if n==5 or expose_truth:assert rows,'Expected concrete retirement witness not found'
    return encode(dict(changes_solver=False,explicit_public_truth_support=expose_truth,meaning='Local diagnostic only; no whole-value or behavior correction claimed',rows=rows))

if __name__=='__main__':
    result=probe();Path('benchmarks/player_match_groups/retirement-provenance-probe.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
