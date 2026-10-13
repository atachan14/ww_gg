import unittest
from dataclasses import replace
from types import SimpleNamespace as Obj
from fractions import Fraction as F
from werewolf.seer_acquisition import Hypothesis
from werewolf.seer_future_uniform import TrueScanState
from werewolf.night_acquisition import acquire_laws
from werewolf.information_weights import observer_report_weights


class InformationPlumbingTests(unittest.TestCase):
    def fixture(self):
        return TrueScanState((Hypothesis((1,0,0,0),(),F(1,2)),Hypothesis((2,0,0,0),(),F(1,2))),
                             initial_rule='none',tracked=())

    def test_generation_uses_same_predeath_roster_and_only_own_law_is_filtered(self):
        source=self.fixture();seen=[]
        def generate(state,alive):seen.append((state,alive));return state
        actual=acquire_laws(Obj(alive=(1,2,3)),source,generate,private=source,
                           observer=lambda h,s:h.roles[0]==1,inconsistent=lambda:ValueError('secret'))
        self.assertEqual(seen,[(source,(1,2,3)),(source,(1,2,3))])
        self.assertEqual(actual.public,source)
        self.assertEqual(actual.private.hypotheses,(replace(source.hypotheses[0],mass=F(1)),))
        self.assertEqual(source.hypotheses[0].mass,F(1,2))

    def test_empty_private_support_returns_no_completed_laws(self):
        source=self.fixture()
        with self.assertRaisesRegex(ValueError,'secret'):
            acquire_laws(Obj(alive=(1,2,3)),source,lambda s,a:s,private=source,
                         observer=lambda h,s:False,inconsistent=lambda:ValueError('secret'))

    def test_public_branch_weights_stay_separate_from_observer_weights(self):
        source=self.fixture();states=tuple(replace(source,hypotheses=(replace(h,mass=F(1)),)) for h in source.hypotheses)
        branches=tuple((F(1,2),None,s,()) for s in states)
        private=replace(source,hypotheses=tuple(replace(h,mass=q) for h,q in zip(source.hypotheses,(F(3,4),F(1,4)))))
        actual=observer_report_weights(source,private,branches,incomplete=lambda:ValueError('incomplete'))
        self.assertEqual(tuple(q for q,*_ in actual),(F(3,4),F(1,4)))
        self.assertEqual(tuple(q for q,*_ in branches),(F(1,2),F(1,2)))
        self.assertEqual(sum((q for q,*_ in actual),F()),1)
        self.assertTrue(all(sum((h.mass for h in own.hypotheses),F())==1 for *_,own in actual))

    def test_incomplete_report_measure_is_not_normalized_into_a_valid_result(self):
        source=self.fixture()
        with self.assertRaisesRegex(ValueError,'incomplete'):
            observer_report_weights(source,source,((F(1,2),None,source,()),),
                                    incomplete=lambda:ValueError('incomplete'))
