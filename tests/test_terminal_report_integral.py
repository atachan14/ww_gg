import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from threading import Event
from time import monotonic
from benchmarks.player_match_groups.report_integral_design import make,audit,oracle,full,terminal_named
from benchmarks.player_match_groups.closed_full_tree_fixture import case
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import tables
from werewolf.closed_calculation import ClosedCalculation
from werewolf.information_set_forecast import Pending
from werewolf.actor_information import PersonalInformation,WolfInformation
from werewolf.seer_intervention import SeerObserver
from werewolf.calculation_budget import calculation_budget,cancellation_scope,CalculationCancelled,CalculationBudgetExceeded,tick
from werewolf.seer_acquisition import Hypothesis,Acquisition,SeerReport
from werewolf.seer_future_uniform import TrueScanState
from werewolf.evaluation_branch import ContinuationInputs,physical_board
from werewolf.exact import replace_worlds


class TerminalReportIntegralTests(unittest.TestCase):
    def setUp(self):self.budget=calculation_budget(250000,max_seconds=30);self.budget.__enter__()
    def tearDown(self):self.budget.__exit__(None,None,None)
    def test_twelve_joint_cases_match_independent_reference_without_event_construction(self):
        for kind,day in [('single',3),('dual',3),('three',4),('medium-pair',4)]:
            c,n=make(5,kind,day,5);h=next(h for h in n.read().private.hypotheses if h.roles[2]&1)
            nodes=(n,n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],n.personal(WolfInformation.from_hypothesis(h))[1])
            e=c._ClosedCalculation__engine
            for selected in nodes:
                source=selected.read();rows,_=oracle(source)
                exact=sum((r['p']*sum(terminal_named(r['P'],source.public.alive).values(),F())/3 for r in rows.values() if r['p']),F())
                with patch('werewolf.morning_publications.CompiledPublications.event',side_effect=AssertionError('constructs an event')),patch.object(e,'report_children',side_effect=AssertionError('full report rows')),patch.object(e,'solve',side_effect=AssertionError('posterior solve')):
                    got=e.action_policy.morning_value(source)
                self.assertEqual(got,exact);self.assertEqual(source,selected.read())
                self.assertTrue(all(not kernel.events for kernel in e.report_kernels.values()))
    def test_observed_joint_reports_and_tables_remain_after_warming_scalar_indices(self):
        c,n=make(5,'three',4,5);e=c._ClosedCalculation__engine
        self.assertEqual(e.action_policy.morning_value(n.read()),F(1,3))
        self.assertEqual(sum(len(k.events) for k in e.report_kernels.values()),0)
        rows,counts=audit(n);self.assertEqual(counts['public_vectors'],109)
        for report in n.reports():
            source=report.node.read();event=(source.public.reports,source.past)
            f=report.node.forecast()
            self.assertEqual(dict(f.action_values),terminal_named(rows[event]['P'],source.public.alive))
            self.assertEqual(f.village_win,F(1,3))
            self.assertTrue(tables(source,f))
        self.assertGreater(sum(len(k.events) for k in e.report_kernels.values()),0)
    def test_opt_in_and_unsupported_modes_use_ordinary_path(self):
        c=ClosedCalculation(case(5,'dual').data,grouped=True,aggregate_wolf=True,aggregate_reports=False)
        n=next(r.node for r in c.root.action(3) if r.node.read().public.winner is None)
        n=next(r.node for r in n.action(5) if r.node.read().public.winner is None);e=c._ClosedCalculation__engine
        self.assertIsNone(e.terminal_report_value(n.read()));self.assertEqual(e.action_policy.morning_value(n.read()),F(1,3))
        self.assertEqual(e.report_kernels,{})
        c,n=make(5,'single',3,5);e=c._ClosedCalculation__engine
        self.assertIsNone(e.terminal_report_value(c.root.read()))
        with patch.object(type(e.strategy),'disclosure_for',return_value='none'):self.assertIsNone(e.terminal_report_value(n.read()))
        e.acquisition_provenance=object();self.assertIsNone(e.terminal_report_value(n.read()));e.acquisition_provenance=None
        e.retire_uninformative_scans=True;self.assertIsNone(e.terminal_report_value(n.read()))
    def test_private_zero_support_and_public_undefined_families_still_refuse(self):
        c,n=make(5,'single',3,5);s=n.read();e=c._ClosedCalculation__engine
        bad=Hypothesis((16,0,1,0),(Acquisition(1,1,3,'white'),Acquisition(2,1,2,'white')),F(1))
        with self.assertRaises(Pending) as caught:e.terminal_report_value(replace(s,private=replace(s.private,hypotheses=(bad,))))
        self.assertEqual(caught.exception.reason,'information_set_report_likelihood_incomplete')
        c,n=make(5,'three',4,5);base=n.read();e=c._ClosedCalculation__engine
        a=Hypothesis((4,0,3,0),(Acquisition(1,1,4,'white'),Acquisition(1,2,4,'white'),Acquisition(2,1,3,'black'),Acquisition(2,2,3,'black')),F(1,2))
        b=Hypothesis((4,0,9,0),(Acquisition(1,1,4,'white'),Acquisition(1,4,5,'white'),Acquisition(2,1,2,'white')),F(1,2))
        state=TrueScanState((a,b),((1,2,3,4,5),(1,2,3,5)))
        own=replace(state,hypotheses=(replace(a,mass=F(1)),));public=replace_worlds(base.public,state.public_roles)
        payload=ContinuationInputs(public,state,base.past,own,None,physical_board(public,own))
        for evaluate in (e.terminal_report_value,e.report_children):
            with self.assertRaises(Pending) as caught:evaluate(payload)
            self.assertEqual(caught.exception.reason,'multiple_fake_report_correlation_unselected')
    def test_cached_indices_still_poll_cancellation_time_and_exhausted_work(self):
        c,n=make(5,'dual',3,5);e=c._ClosedCalculation__engine;source=n.read()
        self.assertEqual(e.terminal_report_value(source),F(1,3))
        stop=Event();stop.set()
        with cancellation_scope(stop):
            with self.assertRaises(CalculationCancelled):e.terminal_report_value(source)
        with calculation_budget(100,max_seconds=1):
            with patch('werewolf.calculation_budget.monotonic',return_value=monotonic()+100):
                with self.assertRaises(CalculationBudgetExceeded):e.terminal_report_value(source)
        with calculation_budget(1):
            with self.assertRaises(CalculationBudgetExceeded):tick(2)
            with self.assertRaises(CalculationBudgetExceeded):e.terminal_report_value(source)
    def test_valid_future_scan_is_applied_before_integral_and_invalid_one_stays_pending(self):
        results=[]
        for expanded in (True,False):
            c=ClosedCalculation(case(5,'single').data,grouped=True,aggregate_wolf=True,aggregate_reports=True);e=c._ClosedCalculation__engine
            h=c.root.read().private.hypotheses[0];initial=tuple(a for a in h.acquisitions if a.player==1)
            node=c.root.personal(SeerObserver(1,initial,2,2))[1]
            from contextlib import nullcontext
            with patch.object(e,'terminal_report_value',return_value=None) if expanded else nullcontext():
                result=node.forecast();results.append((result,tables(node.read(),result)))
            invalid=c.root.personal(SeerObserver(1,initial,2,3))[1]
            with self.assertRaises(Pending) as caught:invalid.forecast()
            self.assertEqual(caught.exception.reason,'seer_view_scan_outside_public_support')
        self.assertEqual(results[0],results[1])
