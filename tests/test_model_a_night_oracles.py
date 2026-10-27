"""Tiny independent public-choice versus wolf-information-set chance laws.

No production transition, acquisition, posterior, policy or evaluator is used.
The reductions below are proved by the final three-person execution game.
"""
import unittest
from collections import defaultdict
from fractions import Fraction as F


def one_night_value(*, physical):
    # Seer2 already reported3white. Wolf4/5 each1/2; player1 was executed.
    # Night-start alive2,3,4,5; unvisited legal scan targets4,5.
    alive=(2,3,4,5);groups=defaultdict(lambda:defaultdict(F));total=F()
    for corpse in alive:
        compatible=tuple(w for w in (4,5) if w!=corpse)
        for wolf in compatible:
            for scan in (4,5):
                # Legacy chooses a public target uniformly, then conditions roles.
                # Physical law chooses a non-pack target uniformly in each world.
                mass=(F(1,2)*F(1,3) if physical else F(1,4)/len(compatible))*F(1,2)
                report=None if corpse==2 else (scan,scan==wolf)
                groups[(corpse,report)][wolf]+=mass;total+=mass
    assert total==1
    # At3alive/1wolf, optimal public execution succeeds with largest wolf mass.
    return sum((max(worlds.get(p,F()) for p in alive if p!=corpse)
                for (corpse,report),worlds in groups.items()),F())


def two_seer_attack_score(corpse):
    assert corpse in (1,2)
    survivor=3-corpse;alive=tuple(range(1,7))
    targets=tuple(p for p in alive if p!=survivor)
    worlds=({3,4},{4,5});value=F()
    for target in targets:
        color=target in worlds[0]
        compatible=tuple(w for w in worlds if (target in w)==color)
        if len(compatible)==1:
            # Both wolves identified: two executions with5alive suffice.
            continuation=F(1)
        else:
            # Execute knownwolf4. With4alive, biting the remaining true seer
            # before publication achieves1/2; public can always execute one of
            # equiprobable3/5 next, proving the matching lower bound.
            continuation=F(1,2)
        value+=continuation/F(len(targets))
    return value


class IndependentNightOracleTests(unittest.TestCase):
    def test_distinct_exact_public_and_physical_measures(self):
        self.assertEqual(one_night_value(physical=False),F(7,8))
        self.assertEqual(one_night_value(physical=True),F(5,6))
    def test_both_seer_attacks_have_same_night_start_score(self):
        self.assertEqual(tuple(two_seer_attack_score(p) for p in (1,2)),(F(7,10),F(7,10)))
