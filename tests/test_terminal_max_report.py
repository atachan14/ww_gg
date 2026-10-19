import unittest
from dataclasses import asdict
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.closed_full_tree_fixture import case
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import tables
from werewolf.closed_calculation import ClosedCalculation
from werewolf.exact import Strategy,legal_targets
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.actor_information import PersonalInformation,WolfInformation
from werewolf.board_future import kernel_calculation
from werewolf.calculation_budget import calculation_budget
from werewolf.forecast_result import Forecast
from werewolf.model_a_public import horizon_for_action


def make(kind,target):
    data=case(5,kind).data.updated(policy=asdict(Strategy()))
    c=ClosedCalculation(data,grouped=True,aggregate_reports=True)
    n=next(r.node for r in c.root.action(target) if r.node.read().public.winner is None)
    n=next(r.node for r in n.action(5) if r.node.read().public.winner is None)
    return c,n


def ordinary(source,rules):
    e=InformationSetForecast(rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False)
    e.retain_joint_guard_history=True
    with kernel_calculation(),calculation_budget(250000,max_seconds=30):
        value=e.solve(*source,physical=source.physical)
        targets=legal_targets(source.physical,e.rules,e.strategy)
        actions=tuple((p,e.act(*source[:3],p,source.private,source.observer,physical=source.physical)) for p in targets)
        dawn=tuple((p,horizon_for_action(e,source.public,source.public_state,source.past,p,source.private,observer=source.observer)) for p in targets)
    return Forecast(value,actions,dawn),e


class TerminalMaxReportTests(unittest.TestCase):
    def test_complete_forecast_tables_history_and_cache_match_ordinary(self):
        for kind,target in [('single',3),('dual',3),('three',4),('medium-pair',4)]:
            c,n=make(kind,target);engine=c._ClosedCalculation__engine
            h=next(h for h in n.read().private.hypotheses if h.roles[2]&1)
            views=(n,n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],n.personal(WolfInformation.from_hypothesis(h))[1])
            for selected in views:
                source=selected.read()
                with kernel_calculation(),calculation_budget(250000,max_seconds=30):
                    expected,e=ordinary(source,engine.rules)
                    # The scalar path must not construct a seer posterior.
                    with patch('werewolf.morning_publications.CompiledPublications.event',side_effect=AssertionError('event construction')):
                        value=engine.action_policy.morning_value(source)
                    self.assertEqual(value,e.action_policy.morning_value(source))
                    # Node forecasts represent the current decision. This
                    # prepublication source is tested separately above.
                    actual=selected.forecast()
                    self.assertEqual(actual,expected)
                    self.assertEqual(tables(source,actual),tables(source,expected))
                    self.assertEqual(selected.forecast(),actual)
                    self.assertEqual(selected.export_request().roles(),source)
                    got=selected.reports()
                    reference=e.report_children(source)
                    self.assertEqual(tuple((r.public_probability,r.probability,r.node.read()) for r in got),reference)
                    for report in got:
                        child=report.node;f,unused=ordinary(child.read(),engine.rules)
                        self.assertEqual(child.forecast(),f)
                        self.assertEqual(tables(child.read(),child.forecast()),tables(child.read(),f))
                self.assertEqual(selected.read(),source)

    def test_medium_conditioning_precedes_surviving_fake_seer_kernel(self):
        # Seven is only the immutable origin roster. Force four actions without
        # forecasting that root; compare the small final-three report frame.
        from werewolf.board_flow import BoardData
        game=case(7,'dual').data.to_game()
        game.update(wolves=2,mediums=1,
            claims=['seer','seer','medium','medium','latent','latent','latent'],
            seer_inputs=[dict(day=1,reporter=p,target=6,color='white') for p in (1,2)],
            policy=asdict(Strategy()))
        data=BoardData.from_game(game)
        c=ClosedCalculation(data,grouped=True,aggregate_reports=True);e=c._ClosedCalculation__engine
        node=c.root
        for target in (2,5,4,7):
            node=next(r.node for r in node.action(target) if r.node.read().public.winner is None)
        source=node.read()
        self.assertEqual(source.public.alive,(1,3,6))
        self.assertEqual({bool(h.roles[2]&1) for h in source.public_state.hypotheses},{False,True})
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            reference,old=ordinary(source,e.rules)
            self.assertEqual(e.action_policy.morning_value(source),old.action_policy.morning_value(source))
            self.assertEqual(node.forecast(),reference)
            self.assertEqual(tables(source,node.forecast()),tables(source,reference))
            self.assertEqual(tuple((r.public_probability,r.probability,r.node.read()) for r in node.reports()),old.report_children(source))

    def test_opt_in_and_nonterminal_diagnostic_boundaries(self):
        from werewolf.information_set_forecast import Pending
        data=case(5,'single').data.updated(policy=asdict(Strategy()))
        with self.assertRaises(Pending):ClosedCalculation(data)
        c,n=make('single',3);e=c._ClosedCalculation__engine
        self.assertIsNone(e.terminal_report_value(c.root.read()))
        e.trace={};self.assertIsNone(e.terminal_report_value(n.read()));e.trace=None
        e.acquisition_provenance=object();self.assertIsNone(e.terminal_report_value(n.read()));e.acquisition_provenance=None
        e.retire_uninformative_scans=True;self.assertIsNone(e.terminal_report_value(n.read()));e.retire_uninformative_scans=False
        with patch.object(type(e.strategy),'disclosure_for',return_value='none'):
            self.assertIsNone(e.terminal_report_value(n.read()))

    def test_initial_max_day_night_and_reports_match_ordinary(self):
        for kind in ('single','dual','three','medium-pair'):
            data=case(5,kind).data.updated(policy=asdict(Strategy()))
            c=ClosedCalculation(data,grouped=True,aggregate_reports=True);e=c._ClosedCalculation__engine
            root=c.root;h=next(h for h in root.read().private.hypotheses if h.roles[2]&1)
            views=(root,root.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],root.personal(WolfInformation.from_hypothesis(h))[1])
            for selected in views:
                expected,ordinary_engine=ordinary(selected.read(),e.rules)
                actual=selected.forecast()
                self.assertEqual(actual,expected)
                self.assertEqual(tables(selected.read(),actual),tables(selected.read(),expected))

    def test_zero_private_support_and_zero_mass_public_undefined_family_refuse(self):
        from dataclasses import replace
        from werewolf.seer_acquisition import Hypothesis,Acquisition
        from werewolf.seer_future_uniform import TrueScanState
        from werewolf.evaluation_branch import ContinuationInputs,physical_board
        from werewolf.exact import replace_worlds
        from werewolf.information_set_forecast import Pending
        c,n=make('single',3);source=n.read();e=c._ClosedCalculation__engine
        bad=Hypothesis((16,0,1,0),(Acquisition(1,1,3,'white'),Acquisition(2,1,2,'white')),F(1))
        with self.assertRaises(Pending) as failure:
            e.terminal_report_value(replace(source,private=replace(source.private,hypotheses=(bad,))))
        self.assertEqual(failure.exception.reason,'information_set_report_likelihood_incomplete')
        c,n=make('three',4);base=n.read();e=c._ClosedCalculation__engine
        a=Hypothesis((4,0,3,0),(Acquisition(1,1,4,'white'),Acquisition(1,2,4,'white'),Acquisition(2,1,3,'black'),Acquisition(2,2,3,'black')),F(1,2))
        b=Hypothesis((4,0,9,0),(Acquisition(1,1,4,'white'),Acquisition(1,4,5,'white'),Acquisition(2,1,2,'white')),F(1,2))
        state=TrueScanState((a,b),((1,2,3,4,5),(1,2,3,5)))
        own=replace(state,hypotheses=(replace(a,mass=F(1)),));public=replace_worlds(base.public,state.public_roles)
        payload=ContinuationInputs(public,state,base.past,own,None,physical_board(public,own))
        for evaluate in (e.terminal_report_value,e.report_children):
            with self.assertRaises(Pending) as failure:evaluate(payload)
            self.assertEqual(failure.exception.reason,'multiple_fake_report_correlation_unselected')

    def test_future_owner_observation_matches_expanded_path(self):
        from werewolf.seer_intervention import SeerObserver
        from werewolf.information_set_forecast import Pending
        from contextlib import nullcontext
        results=[]
        for expanded in (True,False):
            data=case(5,'single').data.updated(policy=asdict(Strategy()))
            c=ClosedCalculation(data,grouped=True,aggregate_reports=True);e=c._ClosedCalculation__engine
            h=c.root.read().private.hypotheses[0]
            initial=tuple(a for a in h.acquisitions if a.player==1)
            node=c.root.personal(SeerObserver(1,initial,2,2))[1]
            with patch.object(e,'terminal_report_value',return_value=None) if expanded else nullcontext():
                f=node.forecast();results.append((f,tables(node.read(),f)))
            invalid=c.root.personal(SeerObserver(1,initial,2,3))[1]
            with self.assertRaises(Pending) as failure:invalid.forecast()
            self.assertEqual(failure.exception.reason,'seer_view_scan_outside_public_support')
        self.assertEqual(*results)

    def test_tied_medium_instructions_merge_before_private_evaluation(self):
        from werewolf.exact import initial_board,replace_worlds,PublicEvent,Rules
        from werewolf.seer_acquisition import from_board
        from werewolf.seer_future_uniform import TrueScanState
        from werewolf.evaluation_branch import ContinuationInputs,physical_board
        from werewolf.grouped_forecast import GroupedForecast
        from dataclasses import replace
        b=replace_worlds(initial_board(7,2,1),((17,2,0,0,F(1,3)),(18,8,0,0,F(1,3)),(12,2,0,0,F(1,3))),
            alive=(1,2,3),day=3,wolf_count=None,claims=('latent','medium')+('latent',)*5,
            history=(PublicEvent(1,'day',5),PublicEvent(1,'night',6),PublicEvent(2,'day',4),PublicEvent(2,'night',7)),
            medium_opportunities=((3,2,4),))
        s=TrueScanState(from_board(b),(tuple(range(1,8)),(1,2,3,4,7),(1,2,3)),initial_rule='none',tracked=())
        own=replace(s,hypotheses=(replace(next(h for h in s.hypotheses if h.roles[0]==18),mass=F(1)),))
        source=ContinuationInputs(b,s,(),own,None,physical_board(b,own))
        e=GroupedForecast(Rules(),Strategy(),aggregate_reports=True,retire_uninformative_scans=False,exact_renaming=False)
        ordinary_engine=InformationSetForecast(Rules(),Strategy(),retire_uninformative_scans=False,exact_renaming=False)
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            self.assertEqual(e.action_policy.morning_value(source),0)
            self.assertEqual(ordinary_engine.action_policy.morning_value(source),0)
            self.assertEqual(e.morning(b,s,()),ordinary_engine.morning(b,s,()))
        # Supplied finite frame tests kernel order; it is not a generated
        # full-disclosure DEFAULT prefix (earlier medium reports are absent).

    def test_cached_kernel_still_obeys_cancellation_and_work_limit(self):
        from threading import Event
        from werewolf.calculation_budget import cancellation_scope,CalculationCancelled,CalculationBudgetExceeded
        c,n=make('three',4);e=c._ClosedCalculation__engine
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            e.action_policy.morning_value(n.read())
        stopped=Event();stopped.set()
        with cancellation_scope(stopped),self.assertRaises(CalculationCancelled):
            e.action_policy.morning_value(n.read())
        from werewolf.calculation_budget import tick
        with calculation_budget(1,max_seconds=30):
            with self.assertRaises(CalculationBudgetExceeded):tick(2)
            with self.assertRaises(CalculationBudgetExceeded):e.action_policy.morning_value(n.read())

    def test_max_does_not_use_uniform_constant_or_target_orbits(self):
        c,n=make('single',3);e=c._ClosedCalculation__engine
        self.assertFalse(e.terminal_uniform_day(n.read().public))
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            self.assertEqual(e.action_policy.morning_value(n.read()),F(5,6))
        self.assertEqual(e.target_orbits((1,2,4)),((1,),(2,),(4,)))
        self.assertFalse(any(k[0]=='uniform-terminal-day' for k in e.values))

if __name__=='__main__':unittest.main()
