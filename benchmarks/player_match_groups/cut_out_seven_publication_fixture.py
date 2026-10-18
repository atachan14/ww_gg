"""Two literal actions and one morning only; no recursive Forecast."""
from dataclasses import replace
from copy import copy
from fractions import Fraction as F
from unittest.mock import patch
import json
from pathlib import Path
from .cut_out_user_seven_source import *
from .cut_out_user_seven_source_fixture import ok
from .cut_out_candidate_context_fixture import zero_legacy
from .cut_out_day_night import moved_law,point_fix


def audit():
    from werewolf.action_flow import resolve_action
    from werewolf.exact import random_report_outcomes
    from werewolf.evaluation_branch import physical_board,ActionInputs
    from werewolf.board_future import remember,calculation_origin
    p=ok(prepare(comparison_game()[1]));r=ok(from_game(p.data.to_game(),p));w=ok(issue(r));e=SevenInitialEngine(r,witness=w)
    x=replace(w.source,physical=physical_board(w.source.public,w.source.private,w.source.physical))
    stack,mocks=zero_legacy()
    with stack,patch.object(e,'solve',side_effect=AssertionError('no Forecast')),patch.object(e,'act',side_effect=AssertionError('no action values')),calculation_budget(100000,max_seconds=1),calculation_origin(r.data):
        remember(e,r.root,x)
        for target in (1,4):
            payload=ActionInputs(x.public_state,x.past,x.private,x.observer,x.physical)
            acquired,outcomes=resolve_action(x.public,payload,target,e.action_policy)
            assert len(outcomes)==1
            x=e.action_policy.project(x.public,acquired,outcomes[0],target)
        b=x.public;s=x.public_state;past=x.past
        assert b.day==2 and b.wolf_count is None and len(s.hypotheses)==18
        cases=[];published=[]
        for o in random_report_outcomes(b):
            c=o.board;ns=e.project(s,c);context=e.inherited_groups.publication(b,s,past,c,ns,past,'medium')
            assert c.claims==b.claims and c.history==b.history and c.alive==b.alive and c.reports[0].target==1
            assert c.wolf_count==({'black':1,'white':2}[c.reports[0].color])
            assert context.new_fixed==(1,3) and context.groups==point_fix(context.parent.groups,1,3)
            cases.append(dict(color=c.reports[0].color,mass=str(o.probability),wolf_count=c.wolf_count,fixed=context.new_fixed))
            published.append((c,ns))
        # Full current morning publishes a vector, without evaluating its future.
        morning=e.morning(b,s,past);assert sum((q for q,*_ in morning),F())==1
        assert len(morning)>2
        swaps=0
        for context in e.inherited_groups.contexts.values():
            for group in context.groups:
                for target in group[1:]:
                    assert moved_law(context.state,group[0],target,7)==context.state;swaps+=1
        rejected=[]
        def refuse(name,source,law,oldpast,child,newlaw,newpast):
            try:e.inherited_groups.publication(source,law,oldpast,child,newlaw,newpast,'medium')
            except Pending:rejected.append(name)
            else:raise AssertionError(name+' accepted')
        c,ns=published[0]
        claims=list(c.claims);claims[4]='seer'
        refuse('new_CO',b,s,past,replace(c,claims=tuple(claims)),ns,past)
        claims=list(c.claims);claims[1]='latent'
        refuse('withdraw_CO',b,s,past,replace(c,claims=tuple(claims)),ns,past)
        refuse('withdraw_medium_result',c,ns,past,b,s,past)
        refuse('withdraw_seer_history',b,s,past,c,ns,past[:-1])
        refuse('change_phase',b,s,past,replace(c,phase='night'),ns,past)
        wrong=copy(c);object.__setattr__(wrong,'wolf_count',2 if c.wolf_count==1 else 1)
        refuse('forged_derived_wolf_count',b,s,past,wrong,ns,past)
        assert all(m.call_count==0 for m in mocks)
    return dict(status='verified',literal_actions=[1,4],day=2,alive=b.alive,source_hypotheses=len(s.hypotheses),
        cause='medium result narrows derived live wolf_count; no CO change',cases=cases,morning_vectors=len(morning),
        group_law_swaps=swaps,rejected=rejected,canonical_calls=0,CandidateRules_calls=0,recursive_forecasts=0)

if __name__=='__main__':
    result=audit();Path('benchmarks/player_match_groups/cut-out-seven-publication-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))