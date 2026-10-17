"""Compare complete labelled score vectors and original actor tie policies."""
from .extension_cases import fixture,prepare_game
from .extension_reuse import ExtensionForecast
from .checkpoint_audit import encode
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.evaluation_projection import project_evaluation
from werewolf.action_flow import resolve_action
from werewolf.evaluation_branch import ActionInputs,physical_board
from werewolf.actor_information import wolf_information_groups
from werewolf.calculation_budget import calculation_budget


def run(mediums=0,retirement=False):
    _,game=fixture(mediums=mediums,day='max',night='max',fake='max')
    _,_,b,s,past,rules,strategy,_=prepare_game(game);b,s=project_evaluation(b,s,strategy)
    engines=[InformationSetForecast(rules,strategy),ExtensionForecast(rules,strategy,future_reuse=True,physical_reuse=True,compact_keys=True,fast_parts=True,max_reuse=not mediums,combined_reuse=bool(mediums),retirement_proof=retirement,extended_retirement=retirement)]
    vectors=[]
    with calculation_budget(1000000,max_seconds=20):
        for e in engines:
            day=e.day_scores(b,s,past);night=[]
            for target in b.alive:
                acquired,outcomes=resolve_action(b,ActionInputs(s,past,s,None,physical_board(b,s)),target,e.action_policy,terminal_payoffs=True)
                for outcome in outcomes:
                    if outcome.board.winner is not None:continue
                    child,public,history,own,observer=e.continuation_context(*e.action_policy.project(b,acquired,outcome,target))
                    for info,mass,group in wolf_information_groups(own):
                        policy=e.wolf_policy(child,public,history,info.initial_roster,info.attacks)
                        assert sum(q for _,q in policy)==1
                        assert all(p in child.alive and not info.initial_roster&(1<<(p-1))for p,_ in policy)
                        night.append((target,outcome.probability,info,mass,policy))
            vectors.append((day,tuple(night)))
    assert vectors[0]==vectors[1]
    return encode(dict(mediums=mediums,retirement=retirement,complete_day_scores=day,night_actor_vectors=len(night),exact_vectors_and_ties_equal=True,night=night))
