import unittest
from types import SimpleNamespace as Obj
from fractions import Fraction as F
from werewolf.exact import BoardOutcome
from werewolf.morning_flow import report_flow, continuation_value


class MorningFlowTests(unittest.TestCase):
    def test_nested_chance_weights_and_history_reach_continuation(self):
        class Policy:
            def project(self,source,board):return source+board
            def publications(self,board,state,past):
                return ((F(1,4),board,state,past+('white',)),(F(3,4),board,state,past+('black',)))
        outcomes=(BoardOutcome(F(1,3),1),BoardOutcome(F(2,3),2))
        branches=tuple(report_flow(outcomes,10,('old',),Policy()))
        self.assertEqual(tuple(q for q,*_ in branches),(F(1,12),F(1,4),F(1,6),F(1,2)))
        seen=[]
        def evaluate(b,s,past):
            seen.append((b,s,past));return F(past[-1]=='white')
        self.assertEqual(continuation_value(branches,evaluate),F(1,4))
        self.assertEqual(seen,[(1,11,('old','white')),(1,11,('old','black')),
                              (2,12,('old','white')),(2,12,('old','black'))])

    def test_generation_and_recursive_evaluation_remain_lazy_in_original_order(self):
        events=[]
        class Policy:
            def project(self,source,board):events.append(('project',board));return source
            def publications(self,board,state,past):
                events.append(('publish',board));return ((F(1),board,state,past),)
        def evaluate(board,state,past):events.append(('evaluate',board));return F(1)
        flow=report_flow((BoardOutcome(F(1,2),1),BoardOutcome(F(1,2),2)),None,(),Policy())
        self.assertEqual(events,[])
        self.assertEqual(continuation_value(flow,evaluate),1)
        self.assertEqual(events,[('project',1),('publish',1),('evaluate',1),
                                 ('project',2),('publish',2),('evaluate',2)])

    def test_observer_weight_measure_is_preserved_and_failure_has_no_partial_value(self):
        # Already reweighted viewer branches stay 3/4 and 1/4; public mass is
        # not substituted or normalized inside the mechanical aggregator.
        branches=((F(3,4),'village'),(F(1,4),'wolf'))
        self.assertEqual(continuation_value(branches,lambda winner:F(winner=='village')),F(3,4))
        def incomplete():
            yield F(1,2),'village'
            raise RuntimeError('unresolved report law')
        with self.assertRaisesRegex(RuntimeError,'unresolved report law'):
            continuation_value(incomplete(),lambda winner:F(1))
