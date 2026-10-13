"""Victory mass through the upcoming dawn, under the existing action policy."""
from dataclasses import dataclass
from fractions import Fraction as F
from .exact import action_outcomes, legal_targets, value_for_action

@dataclass(frozen=True)
class HorizonValues:
    village_win: F
    wolf_win: F
    def __post_init__(self):
        if min(self.village_win,self.wolf_win)<0 or self.village_win+self.wolf_win>1:
            raise ValueError('Invalid horizon victory mass')

def immediate(board,target,rules,strategy):
    outcomes=action_outcomes(board,target,rules,strategy)
    return HorizonValues(*(sum((o.probability for o in outcomes if o.board.winner==winner),F()) for winner in ('village','wolf')))

def action_by_dawn(board,target,rules,strategy,night_values=None):
    """A fixed execution plus one night, or a fixed bite on legacy night Boards.

    night_values supplies full-continuation village probabilities, never horizon
    probabilities. Exact optimal ties are averaged only for this auxiliary metric.
    """
    village=wolf=F()
    for outcome in action_outcomes(board,target,rules,strategy):
        b=outcome.board
        if b.winner:
            v=F(b.winner=='village');w=F(b.winner=='wolf')
        elif board.phase=='night':
            v=w=F() # Reached dawn alive; tomorrow's execution is outside horizon.
        else:
            targets=legal_targets(b,rules,strategy)
            values={t:immediate(b,t,rules,strategy) for t in targets}
            selected=targets
            if strategy.night=='max' and len(set(values.values()))>1:
                scores=dict(night_values(b) if night_values else
                            ((t,value_for_action(b,t,rules,strategy).village_win) for t in targets))
                best=min(scores.values())
                selected=tuple(t for t in targets if scores[t]==best)
            v=sum((values[t].village_win for t in selected),F())/len(selected)
            w=sum((values[t].wolf_win for t in selected),F())/len(selected)
        village+=outcome.probability*v;wolf+=outcome.probability*w
    return HorizonValues(village,wolf)
