import unittest
from fractions import Fraction as F
from werewolf.seer_acquisition import Hypothesis,Acquisition,normalize
from werewolf.guard_effect import GuardIntent


class NormalizationValidationTests(unittest.TestCase):
    def test_unvalidated_subclasses_still_receive_complete_record_validation(self):
        class Unvalidated(Hypothesis):
            def __post_init__(self):pass
        cases=(Unvalidated((1,1,4,8),(),F(1)),
               Unvalidated((1,2,4,8),(Acquisition(1,3,2,'black'),),F(1)),
               Unvalidated((1,2,4,8),(),F(1),(GuardIntent(1,2,3),)))
        for bad in cases:
            with self.subTest(input=bad):
                with self.assertRaises(ValueError):normalize((bad,))
