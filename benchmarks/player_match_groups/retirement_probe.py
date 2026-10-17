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


def probe():
    _,_,b,s,past,rules,strategy,_=initial_white_source(5,1,actors=(1,2))
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
        rows.append(dict(incoming_probability=outcome.probability,alive=child.alive,claims=child.claims,initial_seers_before=child.initial_seer_count,initial_seers_after=projected.initial_seer_count,initial_rule=st.initial_rule,past_before=hist,past_after=ph,can_retire_before=True,can_retire_after=False,generated_branches=len(branches),total_probability=sum((q for q,_,_,_ in branches),F()),all_role_posteriors_unchanged=all(ns.public_roles==next_state.public_roles for _,_,ns,_ in branches),generated_acquired_days=sorted({r.acquired_day for _,_,_,h in branches for r in h})))
    assert rows,'Expected concrete retirement witness not found'
    return encode(dict(changes_solver=False,meaning='Local diagnostic only; no whole-value or behavior correction claimed',rows=rows))

if __name__=='__main__':
    result=probe();Path('benchmarks/player_match_groups/retirement-provenance-probe.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
