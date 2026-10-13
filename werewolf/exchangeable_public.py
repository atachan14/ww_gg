"""Model-A count reduction when PUBLIC locations are exchangeable and no
future disclosures remain. This never invokes the old public action law.
"""
from fractions import Fraction as F
from .exact import winner_for
from .information_set_forecast import exchangeable_value
from .by_dawn import HorizonValues
from .forecast_result import Forecast
from .calculation_budget import tick


def terminal_mass(n,w):
    winner=winner_for(n,w)
    return F(winner=='village'),F(winner=='wolf')


def night_mass(n,w,strategy):
    kinds=[(n-w,w)]
    if strategy.include_self_bite:kinds.append((w,w-1))
    if strategy.night=='max':
        scores=tuple(exchangeable_value(n-1,count,'day',strategy) for _,count in kinds)
        best=min(scores);kinds=[k for k,v in zip(kinds,scores) if v==best]
    total=sum(k for k,_ in kinds)
    return tuple(sum((F(k,total)*terminal_mass(n-1,count)[i] for k,count in kinds),F()) for i in (0,1))


def exchangeable_forecast(board,strategy):
    tick(len(board.belief))
    if board.winner:return Forecast(F(board.winner=='village'),())
    n=len(board.alive);counts=board.wolf_count_distribution
    value=sum((q*exchangeable_value(n,w,board.phase,strategy) for w,q in counts.items()),F())
    if board.phase=='night':return Forecast(value,(),pending_metrics=('night_actions','night_horizon'))
    village=wolf=F()
    for w,q in counts.items():
        for weight,remaining in ((F(w,n),w-1),(F(n-w,n),w)):
            if not weight:continue
            v,h=terminal_mass(n-1,remaining)
            if not (v or h):v,h=night_mass(n-1,remaining,strategy)
            village+=q*weight*v;wolf+=q*weight*h
    return Forecast(value,tuple((p,value) for p in board.alive),
                    tuple((p,HorizonValues(village,wolf)) for p in board.alive))
