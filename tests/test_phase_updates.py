import unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import initial_board, PublicEvent, Rules, Strategy, Progress, replace_worlds, action_outcomes
from werewolf.phase_updates import acquisition_roster, acquisition_rosters, night_observation_outcomes
from werewolf.dawn import observe
from werewolf.private_adapter import private_slots
from werewolf.seer_acquisition import Acquisition, SeerReport, Hypothesis
from werewolf.seer_future_uniform import TrueScanState, acquire_uniform, true_reports
from werewolf.morning_publications import GeneratedPublication, public_report_branches, future_publications


class PhaseBoundaryTests(unittest.TestCase):
    def test_shared_roster_excludes_execution_but_keeps_night_casualty(self):
        history=(PublicEvent(1,'day',7),PublicEvent(1,'night',6),PublicEvent(2,'day',5),PublicEvent(2,'night',4))
        board=replace_worlds(initial_board(7,1,0,1),((1,0,2,0,F(1)),))
        for target in (7,6,5,4):board=action_outcomes(board,target,Rules(),Strategy())[0].board
        self.assertEqual(board.history,history)
        self.assertEqual(acquisition_rosters(board),((1,2,3,4,5,6,7),(1,2,3,4,5,6),(1,2,3,4)))
        self.assertEqual(acquisition_roster(7,history,2),(1,2,3,4,5,6))
        self.assertEqual(private_slots(board,1,Rules(initial_seer='normal')),
                         [{'day':day,'targets':[2,3,4,5,6,7]}for day in(1,2,3)]
        )
        self.assertEqual(private_slots(board,1,Rules(),role='hunter'),
                         [{'day':1,'targets':[2,3,4,5,6]}, {'day':2,'targets':[2,3,4]}])

    def test_observed_update_matches_progress_for_both_self_bite_rules(self):
        board=replace(initial_board(5,1),phase='night')
        for allowed in (False,True):
            rules=Rules(allowed);strategy=Strategy('max','random')
            outcomes=night_observation_outcomes(board,3,rules,strategy)
            self.assertEqual(sum((o.probability for o in outcomes),F()),1)
            progress=observe(Progress.initial(board),{'deaths':[3]},rules,strategy)
            self.assertEqual(progress.board,next(o.board for o in outcomes if o.board.winner is None))
            self.assertEqual(progress.board.day,2)
            self.assertEqual(progress.board.phase,'day')
            self.assertEqual(board,replace(initial_board(5,1),phase='night'))

    def test_acquire_before_casualty_publish_only_survivor_without_redating(self):
        state=TrueScanState((Hypothesis((8,0,1,0),(Acquisition(1,1,2,'white'),),F(1)),),
                            ((1,2,3,4),),initial_rule='normal',tracked=(1,))
        acquired=acquire_uniform(state,(1,2,3,4))
        self.assertTrue(any(a.target==4 and a.day==2 for h in acquired.hypotheses for a in h.acquisitions))
        h=acquired.hypotheses[0]
        self.assertEqual(true_reports(h,(),(2,3,4),('seer','latent','latent','latent'),2),())
        # Late publication preserves Day1 acquisition, while the disclosure is Day2.
        reports=true_reports(h,(),(1,2,3),('seer','latent','latent','latent'),2)
        self.assertIn(SeerReport(1,2,1,2,'white'),reports)
        board=replace(initial_board(4,1,0,1),day=2)
        branch=public_report_branches(board,(),(GeneratedPublication(reports,F(1),acquired),))[0]
        self.assertEqual(branch[2].hypotheses,acquired.hypotheses)
        self.assertEqual(branch[3],reports)
        self.assertEqual(state.rosters,((1,2,3,4),))

    def test_legacy_export_uses_shared_morning_generator(self):
        from werewolf.seer_future_forecast import future_publications as legacy_export
        self.assertIs(legacy_export,future_publications)
