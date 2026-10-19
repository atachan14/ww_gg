import unittest
from types import SimpleNamespace
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.closed_morning_reports_fixture import case,report_vector,audit
from benchmarks.player_match_groups.closed_saved_day_fixture import saved_day
from werewolf.closed_calculation import ClosedCalculation,_report_groups
from werewolf.seer_acquisition import SeerReport
from werewolf.actor_information import PersonalInformation
from werewolf.information_set_forecast import Pending


class ClosedMorningReportTests(unittest.TestCase):
    def test_named_generated_saved_and_cold_public_owner_outputs(self):
        from werewolf.acquisition_provenance import AcquisitionLedger,UniformAcquisitionCache
        with patch.object(AcquisitionLedger,'__init__',side_effect=AssertionError('ledger')),patch.object(AcquisitionLedger,'_owner_current',side_effect=AssertionError('owner check')),patch.object(AcquisitionLedger,'_groups_record',side_effect=AssertionError('frame check')),patch.object(UniformAcquisitionCache,'__init__',side_effect=AssertionError('proof cache')):
            result=audit()
        self.assertEqual(result['cases'][0]['generated_actual_probability'],'1/9')
        self.assertEqual(result['cases'][0]['observed_truth_support_mass'],'1/3')
        self.assertNotEqual(result['private_report']['public_probability'],result['private_report']['actual_probability'])
        self.assertFalse(result['state_pruning'])

    def test_refinement_never_merges_parent_classes_or_hides_incoming_timing(self):
        def state(reports):return SimpleNamespace(past=reports,public=SimpleNamespace(reports=(),report_resolved=()))
        same=(SeerReport(2,2,1,3,'white'),SeerReport(2,2,2,3,'white'))
        self.assertIn((1,2),_report_groups(((1,2),(3,4)),state(same)))
        self.assertNotIn((1,2),_report_groups(((1,),(2,),(3,4)),state(same)))
        later=(same[0],SeerReport(2,3,2,3,'white'))
        self.assertNotIn((1,2),_report_groups(((1,2),(3,4)),state(later)))
        incoming=(*same,SeerReport(2,2,4,1,'white'))
        self.assertNotIn((1,2),_report_groups(((1,2),(3,4)),state(incoming)))

    def test_missing_duplicate_delayed_personal_and_old_report_inputs_decline(self):
        graph,targets=case(5);node=ClosedCalculation(graph.data).root
        for t in targets:node=node.observe(t)[1]
        desired=report_vector(5)
        with self.assertRaises(Pending):node.observe_reports(desired[:1])
        with self.assertRaises(Pending):node.observe_reports((desired[0],desired[0]))
        with self.assertRaises(ValueError):node.observe_reports((SeerReport(2,3,1,4,'white'),desired[1]))
        _,published=node.observe_reports(desired)
        with self.assertRaises(ValueError):published.observe_reports(desired)
        _,own=node.personal(PersonalInformation(1,'seer'))
        with self.assertRaises(ValueError):own.observe_reports(desired)
        with self.assertRaises((Pending,ValueError)):node.observe_reports((SeerReport(2,2,1,3,'black'),SeerReport(2,2,2,3,'black')))

    def test_saved_new_rows_require_unchanged_nonlog_complete_snapshots(self):
        graph,targets=case(5);data=graph.data
        for t in targets:data=saved_day(data,t)
        initial=data.to_game()['seer_inputs'];new=[dict(day=2,reporter=r.player,target=r.target,color=r.color) for r in report_vector(5)]
        current=data.updated(seer_inputs=initial+new);old=ClosedCalculation(current);before=old.root.read()
        with self.assertRaisesRegex(Pending,'public_log'):ClosedCalculation(current.updated(public_log={'version':2}))
        with self.assertRaises(Pending):ClosedCalculation(current.updated(seer_inputs=initial+new[:1]))
        with self.assertRaises(Pending):ClosedCalculation(current.updated(seer_inputs=initial+[{**new[0],'day':3},new[1]]))
        with self.assertRaises(Pending):ClosedCalculation(current.updated(claims=['latent']*5))
        self.assertEqual(old.root.read(),before)
