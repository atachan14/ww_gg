"""Rules-only finite oracles, deliberately independent of production kernels.

The second fixture has a publicly known true seer1, a known-white3 and one
surviving wolf at4/5 after wolf2 was executed. We enumerate scan slots and the
last public execution, not the implementation's future-value algorithm.
"""
from fractions import Fraction as F

def terminal_three_alive_scan_values(night_start=(1,2,3),seer=1,wolf=2):
    targets=tuple(p for p in night_start if p!=seer)
    bites=tuple(p for p in night_start if p!=wolf)
    value=sum((F(int(wolf not in tuple(p for p in night_start if p!=victim))) for victim in bites),F())/len(bites)
    # With two survivors and the wolf alive, parity ends the game immediately.
    assert len(night_start)==3 and value==0
    return {target:value for target in targets}

def known_seer_forced_bite(actual_wolf,victim):
    night_start=(1,3,4,5);seer=1;visited=(3,);possible_wolves=(4,5)
    if victim not in night_start or victim==actual_wolf:raise ValueError('Illegal self-bite or dead target')
    scans=tuple(p for p in night_start if p!=seer and p not in visited)
    survivors=tuple(p for p in night_start if p!=victim);rows=[]
    assert len(survivors)==3
    for target in scans:
        color='black' if target==actual_wolf else 'white'
        report=(target,color) if seer in survivors else None
        compatible=tuple(w for w in possible_wolves if w!=victim and (report is None or (target==w)==(color=='black')))
        probabilities={p:F(sum(w==p for w in compatible),len(compatible)) for p in survivors}
        maximum=max(probabilities.values());chosen=tuple(p for p in survivors if probabilities[p]==maximum)
        payoff=F(sum(p==actual_wolf for p in chosen),len(chosen))
        rows.append(dict(target=target,color=color,report=report,probability=F(1,len(scans)),executions=chosen,village=payoff))
    return sum((row['probability']*row['village'] for row in rows),F()),tuple(rows)
