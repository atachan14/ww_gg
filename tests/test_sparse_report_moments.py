import unittest
from dataclasses import replace
from fractions import Fraction as F
from contextlib import ExitStack
from unittest.mock import patch
from threading import Event
from benchmarks.player_match_groups.sparse_report_moments import sparse_joint_rows,sparse_moments,dense_joint_rows,independent_joint_rows
from benchmarks.player_match_groups.max_structure_design import calculation
from benchmarks.player_match_groups.exposed_fake_channel import named_reference
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import forecast,tables
from tests.test_terminal_max_report import make
from werewolf.board_future import kernel_calculation
from werewolf.calculation_budget import calculation_budget,cancellation_scope,CalculationCancelled,CalculationBudgetExceeded
from werewolf.morning_publications import compile_publications,CompiledPublications,PublicMomentCache
from werewolf.exact import initial_board,replace_worlds
from werewolf.seer_acquisition import Hypothesis,Acquisition
from werewolf.seer_future_uniform import TrueScanState
from werewolf.policy_choice import optimal_targets
from werewolf.information_set_forecast import Pending


def incomplete():return Pending('information_set_report_likelihood_incomplete')


def overlap_kernel():
    # Isolated normalized common report-kernel input, not a claimed reachable
    # three-player whole-game timeline. Each false identity gives same event.
    worlds=((1,0,2,0,F(1,2)),(2,0,1,0,F(1,2)))
    b=replace_worlds(initial_board(3,1,0,1),worlds,claims=('seer','seer','latent'),day=2)
    hs=tuple(Hypothesis(row[:-1],(Acquisition(2,2 if row[0]==1 else 1,3,'white'),),row[-1]) for row in worlds)
    q=TrueScanState(hs,((1,2,3),(1,2,3)),initial_rule='none')
    k=compile_publications(q,(),b.alive,b.claims,board=b,fake_policy=('uniform',))
    return k


class SparseReportMomentTests(unittest.TestCase):
    def test_complete_positive_joint_laws_match_cartesian_and_expanded_generator(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            for kind,target in (('single',3),('dual',3),('three',4),('medium-pair',4)):
                c,n=make(kind,target);s=n.read();e=c._ClosedCalculation__engine;k=e.publication_kernel(s.public,s.public_state,s.past)
                sparse=sparse_joint_rows(k);dense,count=dense_joint_rows(k)
                self.assertEqual(sparse,dense);self.assertEqual(sparse,independent_joint_rows(k))
                self.assertTrue(all(rows and all(m>0 for m in rows.values()) for rows in sparse.values()))
                self.assertEqual(sum(sum(rows.values(),F()) for rows in sparse.values()),1)
                self.assertLessEqual(len(sparse),count)
                self.assertEqual(dict(sparse_moments(k,s.public.alive,incomplete=incomplete)),dict(k.terminal_execution_moments(s.public.alive,incomplete=incomplete)))

    def test_same_public_event_is_combined_before_MAX_and_tie_distribution(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            k=overlap_kernel();events=sparse_joint_rows(k)
            self.assertEqual(events,independent_joint_rows(k,fake_policy=('uniform',)))
            common=next(rows for rows in events.values() if len(rows)==2)
            scores=tuple((t,sum(m for (roles,acq),m in common.items() if roles[0]&(1<<(t-1)))) for t in (1,2,3))
            chosen=optimal_targets(scores,maximize=True);self.assertEqual(chosen,(1,2))
            mass=sum(common.values());correct=sum(m*F(sum(bool(roles[0]&(1<<(t-1))) for t in chosen),len(chosen)) for (roles,acq),m in common.items())
            self.assertEqual(correct,mass/2)
            # Selecting within each hidden truth/fake component would always
            # hit its own wolf, spuriously doubling this event's contribution.
            premature=sum(common.values());self.assertNotEqual(correct,premature)
            self.assertEqual(dict(sparse_moments(k,(1,2,3),incomplete=incomplete)),dict(k.terminal_execution_moments((1,2,3),incomplete=incomplete)))

    def test_positive_Q_zero_P_events_stay_and_private_does_not_rerank(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            k=overlap_kernel();q=k.state;events=sparse_joint_rows(k)
            private=replace(q,hypotheses=(replace(q.hypotheses[0],mass=F(1)),))
            supported={(h.roles,h.acquisitions) for h in private.hypotheses}
            self.assertTrue(any(not supported.intersection(rows) for rows in events.values()))
            expected=k.terminal_execution_value(private,(1,2,3),incomplete=incomplete)
            cache=PublicMomentCache()
            with patch.object(CompiledPublications,'terminal_execution_moments',sparse_moments):
                self.assertEqual(k.terminal_execution_value(private,(1,2,3),incomplete=incomplete,cache=cache),expected)
                self.assertEqual(k.terminal_execution_value(q,(1,2,3),incomplete=incomplete,cache=cache),k.terminal_execution_value(q,(1,2,3),incomplete=incomplete))
            self.assertEqual(sparse_joint_rows(k),events)

    def test_full_five_public_personal_Forecast_Table_named_history_and_cold(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            # All comparisons share one finite test budget; none is seven.
            for kind in ('single','dual','three','medium-pair'):
                for view in ('public','seer','wolf'):
                    c,n=calculation(kind,'baseline',view);s=n.read();e=c._ClosedCalculation__engine;ref=named_reference(e,s)
                    expected=forecast(ref,s)
                    with patch.object(CompiledPublications,'terminal_execution_moments',sparse_moments):actual=n.forecast()
                    self.assertEqual(actual,expected);self.assertEqual(tables(s,actual),tables(s,expected))
                    self.assertEqual(n.read(),s);self.assertEqual(n.export_request().roles(),s)
            c,n=make('three',4);e=c._ClosedCalculation__engine;before=tuple((r.public_probability,r.probability,r.node.read()) for r in n.reports())
            with patch.object(CompiledPublications,'terminal_execution_moments',sparse_moments):e.action_policy.morning_value(n.read())
            self.assertEqual(tuple((r.public_probability,r.probability,r.node.read()) for r in n.reports()),before)

    def test_zero_payoff_no_event_construction_and_resource_boundaries(self):
        from tests.test_public_moment_cache import zero_frame
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            b,q=zero_frame();k=compile_publications(q,(),b.alive,b.claims,board=b)
            self.assertEqual(sparse_moments(k,(3,),incomplete=incomplete),())
            with patch.object(CompiledPublications,'event',side_effect=AssertionError('posterior event')):
                sparse_moments(k,b.alive,incomplete=incomplete)
            k=overlap_kernel()
            stop=Event();stop.set()
            with cancellation_scope(stop),self.assertRaises(CalculationCancelled):sparse_moments(k,(1,2,3),incomplete=incomplete)
            with calculation_budget(1),self.assertRaises(CalculationBudgetExceeded):sparse_moments(k,(1,2,3),incomplete=incomplete)

if __name__=='__main__':unittest.main()
