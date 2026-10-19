"""Independent enumeration/counterexamples for the DEVELOPMENT channel candidate."""
import unittest
from dataclasses import replace
from fractions import Fraction as F
from contextlib import ExitStack
from benchmarks.player_match_groups.exposed_fake_channel import (Census,exposed,terminal_exposed,TerminalOnlyExperiment,named_reference)
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import forecast,tables
from werewolf.board_future import kernel_calculation
from werewolf.calculation_budget import calculation_budget,budget_usage
from werewolf.seer_acquisition import SeerReport
from werewolf.seer_fake_uniform import fake_uniform_options
from werewolf.actor_information import PersonalInformation


class ExposedFakeChannelTests(unittest.TestCase):
    def test_role_independence_alone_does_not_preserve_history_policy_value(self):
        # R is independent of the sole hidden world. A configured continuation
        # using R chooses different actions. Replacing R by one row is invalid.
        noise=(('white',F(1,2)),('black',F(1,2)))
        payoff={'wait':F(0),'finish':F(1)}
        configured={'white':'wait','black':'finish'}
        expected=sum(q*payoff[configured[r]] for r,q in noise)
        self.assertEqual(expected,F(1,2))
        self.assertNotEqual(expected,payoff[configured['white']])
        # This is a counterexample to the generic inference, not an added
        # supported game policy.

    def test_independent_noise_cannot_be_averaged_before_max_without_action_invariance(self):
        # Each row has the same prior on hidden H, but public-history-dependent
        # legal/payoff continuation differs. E[max] != max of averaged scores.
        scores=((F(1),F(0)),(F(0),F(1)))
        self.assertEqual(sum(max(row) for row in scores)/2,1)
        self.assertEqual(max(sum(row[i] for row in scores)/2 for i in range(2)),F(1,2))

    def test_actual_fake_future_target_law_uses_report_history(self):
        roster=(1,2,3,4,5);initial=SeerReport(1,1,2,3,'black')
        left=fake_uniform_options(roster,2,(initial,))
        right=fake_uniform_options(roster,2,(initial,SeerReport(2,2,2,4,'white')))
        self.assertEqual(sum(q for r,q in left),1);self.assertEqual(sum(q for r,q in right),1)
        self.assertIn((4,'white'),dict(left));self.assertNotIn((4,'white'),dict(right))
        self.assertNotEqual(left,right)
        # Actual approved unvisited-target rule; role independence did not
        # make different public histories the same Markov transition.

    def test_terminal_only_full_enumeration_equal_source_cold_and_named_outputs(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=exposed();s=n.read();e=c._ClosedCalculation__engine;ref=named_reference(e,s)
            rows=ref.report_children(s)
            self.assertGreater(len(rows),1)
            self.assertEqual(sum(p for q,p,child in rows),1)
            # Exact complete posterior laws, not just role marginals.
            for q,p,child in rows:
                self.assertEqual(child.public_state,s.public_state)
                self.assertEqual(child.private,s.private)
                self.assertNotEqual(child.past,s.past)
            want=ref.action_policy.morning_value(s)
            before=budget_usage()['work'];e.action_policy=TerminalOnlyExperiment(e)
            got=e.action_policy.morning_value(s);used=budget_usage()['work']-before
            self.assertEqual(got,want);self.assertEqual(got,1);self.assertLess(used,21)
            # Current decision/named APIs remain full; experiment only replaces
            # its unobserved morning scalar in this terminal development test.
            expected=forecast(ref,s);actual=forecast(e,s)
            for q,p,child in rows:self.assertEqual(forecast(ref,child),expected)
            self.assertEqual(actual,expected);self.assertEqual(tables(s,actual),tables(s,expected))
            self.assertEqual(n.export_request().roles(),s);self.assertEqual(n.read(),s)
            self.assertEqual(tuple((r.public_probability,r.probability,r.node.read()) for r in n.reports()),rows)

    def test_observer_initial_declaration_and_nonterminal_boundaries(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=exposed();s=n.read();self.assertTrue(terminal_exposed(s))
            self.assertFalse(terminal_exposed(replace(s,observer=PersonalInformation(1,'seer'))))
            self.assertFalse(terminal_exposed(replace(s,past=())))
            self.assertFalse(terminal_exposed(c.root.read()))
            e=c._ClosedCalculation__engine;e.retire_uninformative_scans=True
            self.assertTrue(e.can_retire_scans(s.public,s.public_state,s.past))
            self.assertFalse(e.can_retire_scans(s.public,s.public_state,()))

    def test_true_report_changes_posterior_and_future_max_value(self):
        from tests.test_terminal_max_report import make
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=make('single',3);s=n.read();e=named_reference(c._ClosedCalculation__engine,s)
            rows=e.report_children(s);values=[e.solve(*child,physical=child.physical) for q,p,child in rows]
            self.assertGreater(len(set(values)),1)
            self.assertTrue(any(child.public_state!=s.public_state for q,p,child in rows))
            self.assertFalse(terminal_exposed(s))

    def test_disjoint_cost_accounting_and_root_completion_events(self):
        from benchmarks.player_match_groups.max_structure_design import calculation
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=calculation('single','baseline','public');e=c._ClosedCalculation__engine;a=Census(n.read());before=budget_usage()['work']
            with ExitStack() as stack:a.install(stack,e);n.forecast()
            delta=budget_usage()['work']-before
            self.assertTrue(a.events);self.assertTrue(all(x['completed'] for x in a.events))
            self.assertTrue(all(x['work']==x['finished_work']-x['started_work'] for x in a.events))
            self.assertTrue(all(x>=0 for x in a.work.values()))
            self.assertLessEqual(sum(a.work.values()),delta);self.assertGreater(a.work['report'],0)

if __name__=='__main__':unittest.main()
