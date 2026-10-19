import unittest
from contextlib import ExitStack
from dataclasses import replace
from fractions import Fraction as F
from benchmarks.player_match_groups.report_history_summary import history_summary,calculation_key,ScalarKeyExperiment,small_six
from benchmarks.player_match_groups.exposed_fake_channel import named_reference
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import forecast,tables
from werewolf.calculation_budget import calculation_budget,budget_usage
from werewolf.board_future import kernel_calculation
from werewolf.actor_information import PersonalInformation
from werewolf.seer_fake_uniform import fake_uniform_options
from werewolf.morning_publications import fake_backlog_options
from werewolf.seer_acquisition import SeerReport,Hypothesis
from werewolf.seer_future_uniform import TrueScanState


class ReportHistorySummaryTests(unittest.TestCase):
    def test_actual_generated_color_pairs_share_only_summary_and_match_full_reference(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=small_six();e=c._ClosedCalculation__engine;buckets={}
            for r in n.reports():
                s=r.node.read();k=(s.public,s.public_state,history_summary(s.public,s.public_state,s.past),s.private,s.observer,s.physical,r.node.groups)
                buckets.setdefault(k,[]).append(r.node)
            self.assertEqual(len(buckets),16)
            for pair in buckets.values():
                self.assertEqual(len(pair),2);a,b=pair;left,right=a.read(),b.read()
                self.assertNotEqual(left.past,right.past)
                self.assertEqual(left.public_state,right.public_state);self.assertEqual(left.private,right.private)
                self.assertEqual(fake_uniform_options(left.public_state.rosters[0],2,left.past),fake_uniform_options(right.public_state.rosters[0],2,right.past))
                fa=forecast(named_reference(e,left),left);fb=forecast(named_reference(e,right),right)
                self.assertEqual(fa,fb);self.assertEqual(tables(left,fa),tables(right,fb))
                self.assertEqual(a.export_request().roles(),left);self.assertEqual(b.export_request().roles(),right)

    def test_seen_day_set_is_required_in_addition_to_seen_targets(self):
        # Isolated common-generator input, not a claimed reachable whole game.
        state=TrueScanState((Hypothesis((1,0,0,0),(),F(1)),),((1,2,3),)*4,'none',tracked=())
        past=(SeerReport(2,2,1,2,'white'),SeerReport(3,3,1,3,'black'))
        complete=(*past,SeerReport(4,4,1,2,'black'))
        self.assertEqual({r.target for r in past},{r.target for r in complete})
        pending=fake_backlog_options(state,(1,),past);done=fake_backlog_options(state,(1,),complete)
        self.assertTrue(all(rows and rows[0].acquired_day==4 for rows,p in pending))
        self.assertEqual(done,(((),F(1)),));self.assertNotEqual(pending,done)

    def test_true_colors_initial_declarations_and_seen_targets_remain_separate(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=small_six();s=n.reports()[0].node.read();base=history_summary(s.public,s.public_state,s.past)
            for select in (lambda r:r.player==1,lambda r:r.player==2 and r.acquired_day==1):
                altered=tuple(replace(r,color='black' if r.color=='white' else 'white') if select(r) else r for r in s.past)
                self.assertNotEqual(history_summary(s.public,s.public_state,altered),base)
            altered=tuple(replace(r,target=3) if r.player==2 and r.acquired_day==2 else r for r in s.past)
            self.assertNotEqual(history_summary(s.public,s.public_state,altered),base)

    def test_full_Q_P_and_selected_observer_remain_in_calculation_key(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=small_six();s=n.read();e=c._ClosedCalculation__engine;q=s.public_state
            self.assertGreater(len(q.hypotheses),1)
            a=replace(q,hypotheses=(replace(q.hypotheses[0],mass=F(1)),))
            b=replace(q,hypotheses=(replace(q.hypotheses[1],mass=F(1)),))
            self.assertEqual(a.public_roles,b.public_roles)
            key=lambda source:calculation_key(e,'solve',tuple(source),{'physical':source.physical})
            self.assertNotEqual(key(replace(s,private=a)),key(replace(s,private=b)))
            self.assertNotEqual(key(replace(s,public_state=a,private=a)),key(replace(s,public_state=b,private=b)))
            owner=PersonalInformation(1,'seer',tuple(r for r in q.hypotheses[0].acquisitions if r.player==1))
            self.assertNotEqual(key(s),key(replace(s,observer=owner,private=a)))

    def test_summary_key_reuses_scalars_without_reusing_named_history(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=small_six();e=c._ClosedCalculation__engine;exp=ScalarKeyExperiment(e);source=n.read();before=budget_usage()['work']
            with ExitStack() as stack:exp.install(stack);v=e.action_policy.morning_value(source)
            self.assertEqual(v,1);self.assertGreater(exp.stats['hits'],0);self.assertEqual(exp.counts()['distinct_full_aliases'],16)
            self.assertLess(budget_usage()['work']-before,463)
            rows=n.reports();self.assertEqual(len(rows),32)
            self.assertEqual(len({r.node.read().past for r in rows}),32)
            self.assertEqual(n.read(),source)

    def test_ambiguous_fake_and_diagnostic_scopes_are_not_extended(self):
        from benchmarks.player_match_groups.max_structure_design import calculation
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=calculation('dual','baseline','public');s=n.read();e=c._ClosedCalculation__engine
            self.assertIsNone(history_summary(s.public,s.public_state,s.past))
            c,n=small_six();s=n.read();e=c._ClosedCalculation__engine;e.trace={}
            self.assertIsNone(calculation_key(e,'solve',tuple(s),{'physical':s.physical}))

if __name__=='__main__':unittest.main()
