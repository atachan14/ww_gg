"""Exact terminal-only physical partitions; ordinary display/replay stays full.

No continuation or report law is approximated. Future mixed branches decline.
"""
from dataclasses import dataclass,field
from fractions import Fraction as F
from .exact import action_world_groups,PublicEvent,winner_for
from .information_set_forecast import InformationSetForecast,InformationSetActionPolicy


class TerminalDetails:
    def __init__(self,board,payload,target,rules,strategy):
        self.board=board;self.payload=payload;self.target=target;self.rules=rules;self.strategy=strategy;self.rows=None
    def full(self,winner):
        if self.rows is None:
            fresh=InformationSetForecast(self.rules,self.strategy,exact_renaming=False,retire_uninformative_scans=False)
            fresh.retain_joint_guard_history=True
            self.rows=InformationSetActionPolicy.outcomes(fresh.action_policy,self.board,self.payload,self.target)
        return next(o for o in self.rows if o.board.winner==winner)


@dataclass(frozen=True)
class TerminalFacts:
    alive:tuple
    winner:str
    day:int
    phase:str
    history:tuple
    details:object=field(compare=False,repr=False)
    def materialize(self):return self.details.full(self.winner).board
    def __getattr__(self,name):return getattr(self.materialize(),name)


@dataclass(frozen=True)
class TerminalOutcome:
    probability:F
    board:TerminalFacts
    @property
    def context(self):return self.materialize().context
    def materialize(self):
        full=self.board.details.full(self.board.winner)
        if full.probability!=self.probability:raise ValueError('Terminal detail mass disagrees with scalar partition')
        return full


def terminal_death_outcomes(board,payload,target,engine):
    """H0 standard physical/public death laws, only if EVERY P branch ends.

    The common resolver calls this AFTER ordinary acquisition and observer
    validation. No ability-dependent casualty law or custom resolver is used.
    """
    if board.initial_hunter_count or payload.physical.initial_hunter_count:return None
    if (getattr(engine.public_children,'__func__',None) is not InformationSetForecast.public_children or
        getattr(engine.physical_children,'__func__',None) is not InformationSetForecast.physical_children):return None
    if (engine.strategy.day,engine.strategy.night,engine.strategy.fake_reports)!=('random',)*3:return None
    # The old public kernel is evaluated before P. Keep its unsupported-corpse
    # rejection even for a counterfactual physically terminal action.
    if board.phase=='night':
        try:
            compatible=tuple(world for world in board.worlds if engine.rules.allow_self_bite or not world[0]&(1<<(target-1)))
            if not compatible:raise ValueError('Night corpse has no compatible public hypothesis')
            current={winner_for(len(board.alive),(w[0]&board.alive_mask).bit_count()) for w in compatible}
            if len(current)==1 and None not in current:raise ValueError('A terminal Board cannot advance')
            if type(target)is not int or target not in board.alive:raise ValueError('Choose a living player')
        except ValueError:
            raise engine.pending('information_set_public_corpse_inconsistent') from None
    else:action_world_groups(board,target,engine.rules,engine.strategy)
    alive,groups=action_world_groups(payload.physical,target,engine.rules,engine.strategy)
    if None in groups:return None
    details=TerminalDetails(board,payload,target,engine.rules,engine.strategy)
    history=board.history+(PublicEvent(board.day,board.phase,target),)
    return tuple(TerminalOutcome(sum((w[-1] for w in groups[winner]),F()),
                 TerminalFacts(alive,winner,board.day,board.phase,history,details))
                 for winner in ('village','wolf') if winner in groups)
