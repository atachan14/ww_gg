import unittest
from types import SimpleNamespace as Obj
from fractions import Fraction as F
from werewolf.action_flow import action_flow, FlowOutcome


class RecordingPolicy:
    acquire_terminal=False
    def __init__(self,branches):self.branches=branches;self.events=[]
    def acquire(self,b,state):
        self.events.append(('acquire',b.alive))
        return state+('new-secret',)
    def outcomes(self,b,state,target):
        self.events.append(('action',target))
        return self.branches
    def project(self,b,state,outcome,target):
        self.events.append(('death',outcome.board.alive,state))
        return outcome.board,state
    def morning_value(self,payload):
        self.events.append(('morning',payload[0].alive,payload[1]))
        self.events.append(('next',))
        return F(1,4)
    def day_value(self,payload):self.events.append(('next',));return F(3,4)


class ActionFlowContractTests(unittest.TestCase):
    def test_acquisition_uses_predeath_roster_and_branches_stop_before_reports(self):
        b=Obj(phase='night',alive=(1,2,3,4))
        terminal=Obj(winner='wolf',alive=(1,2,3))
        child=Obj(winner=None,alive=(1,2,3))
        p=RecordingPolicy((FlowOutcome(F(1,3),terminal),FlowOutcome(F(2,3),child)))
        self.assertEqual(action_flow(b,(),4,p),F(1,6))
        self.assertEqual(p.events,[('action',4),('acquire',(1,2,3,4)),
            ('death',(1,2,3),('new-secret',)),('morning',(1,2,3),('new-secret',)),('next',)])

    def test_day_skips_acquisition_and_morning(self):
        p=RecordingPolicy((FlowOutcome(F(1),Obj(winner=None,alive=(1,2,3))),))
        self.assertEqual(action_flow(Obj(phase='day'),(),4,p),F(3,4))
        self.assertEqual(p.events,[('action',4),('death',(1,2,3),()),('next',)])

    def test_terminal_acquisition_contract_is_explicit_but_payoff_is_identical(self):
        for eager in (False,True):
            p=RecordingPolicy((FlowOutcome(F(1),Obj(winner='village')),));p.acquire_terminal=eager
            self.assertEqual(action_flow(Obj(phase='night',alive=(1,2,3)),(),3,p),1)
            self.assertEqual(p.events,([('acquire',(1,2,3))] if eager else [])+[('action',3)])

    def test_acquisition_failure_does_not_publish_or_return_partial_payoff(self):
        p=RecordingPolicy((FlowOutcome(F(1),Obj(winner=None)),))
        def failed(b,s):raise RuntimeError('unsupported ability')
        p.acquire=failed
        with self.assertRaisesRegex(RuntimeError,'unsupported ability'):
            action_flow(Obj(phase='night'),(),3,p)
        self.assertEqual(p.events,[('action',3)])
