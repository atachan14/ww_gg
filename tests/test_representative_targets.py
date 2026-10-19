import unittest
from unittest.mock import patch
from benchmarks.player_match_groups.representative_target_fixture import audit,case,prepare
from benchmarks.player_match_groups.closed_morning_reports_fixture import case as morning_case
from werewolf.closed_calculation import ClosedCalculation
from werewolf.seer_future_uniform import TrueScanState
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.calculation_budget import CalculationBudgetExceeded
import tests.test_closed_calculation as closed_api_tests


class RepresentativeTargetTests(unittest.TestCase):
    def test_same_joint_trace_named_outputs_and_cold_with_fewer_expansions(self):
        result=audit()
        for row in result['cases'][:2]:
            self.assertLess(row['representative']['values'],row['ordinary']['values'])
            self.assertLess(row['representative']['expansions']['actions'],row['ordinary']['expansions']['actions'])
        asym=result['cases'][2]
        self.assertEqual(asym['ordinary']['values'],asym['representative']['values'])
        self.assertEqual(asym['ordinary']['expansions']['actions'],asym['representative']['expansions']['actions'])

    def test_representatives_skip_named_action_generation_without_permutation_audits(self):
        from werewolf.acquisition_provenance import AcquisitionLedger,UniformAcquisitionCache
        from contextlib import ExitStack
        graph=case(6);c,node,_=prepare(graph,True);engine=c._ClosedCalculation__engine
        seen=[];original=engine.uncached_act
        def record(b,s,past,target,private,observer,**kw):seen.append((b.day,b.phase,b.alive,target));return original(b,s,past,target,private,observer,**kw)
        with ExitStack() as stack:
            for cls,name in ((AcquisitionLedger,'__init__'),(AcquisitionLedger,'_owner_current'),(AcquisitionLedger,'_groups_record'),(UniformAcquisitionCache,'__init__'),(InformationSetForecast,'equivalent_targets'),(InformationSetForecast,'full_target_equivalence'),(InformationSetForecast,'actor_equivalent_targets')):
                stack.enter_context(patch.object(cls,name,side_effect=AssertionError('runtime proof '+name)))
            for target in ('werewolf.joint_value_key.public_variants','werewolf.medium_value_key.public_descriptor','werewolf.exact_renaming.canonical_key'):
                stack.enter_context(patch(target,side_effect=AssertionError('runtime permutation discovery')))
            stack.enter_context(patch.object(engine,'uncached_act',record))
            node.forecast()
        root=[t for day,phase,alive,t in seen if (day,phase,alive)==(2,'day',(1,2,3,5))]
        self.assertEqual(set(root),{1,5})
        self.assertNotIn(2,root);self.assertNotIn(3,root)
        self.assertEqual(engine.groups,())

    def test_nested_partition_restoration_snapshot_and_export_isolation(self):
        c,node,_=prepare(case(6),True);e=c._ClosedCalculation__engine;before=node.read()
        with self.assertRaises(RuntimeError):
            with e.group_scope(((1,2,3),(4,5,6))):
                with e.group_scope(((1,),(2,3))):raise RuntimeError('cancel')
        self.assertEqual(e.groups,())
        a=node.forecast();request=node.export_request();request.history[0].engine.values['foreign']=0
        other=ClosedCalculation(c.data.updated(revision=12),grouped=True)
        self.assertEqual(other.stats()['values'],0);self.assertEqual(node.read(),before);self.assertEqual(node.forecast(),a)
        with self.assertRaises(TypeError):ClosedCalculation(c.data,grouped=1)
        with self.assertRaises(Pending):ClosedCalculation(c.data.updated(policy={'day':'max','night':'random','fake_reports':'random'}),grouped=True)

    def test_existing_structured_owner_intervention_and_budget_still_match(self):
        helper=closed_api_tests.ClosedCalculationTests()
        graph,_=morning_case(5)
        # Existing known single-seer fixture, including a selected own next scan.
        from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import make_role_filter_scope
        data=make_role_filter_scope().graph.data
        ordinary=helper.night(ClosedCalculation(data));fast=helper.night(ClosedCalculation(data,grouped=True))
        self.assertEqual(fast.read(),ordinary.read());self.assertEqual(fast.forecast(),ordinary.forecast())
        c,node,_=prepare(case(6),True);e=c._ClosedCalculation__engine
        with patch.object(e,'uncached_act',side_effect=Pending('cancelled')):
            with self.assertRaises(Pending):node.forecast()
        self.assertEqual(e.groups,());self.assertEqual(node.forecast(),prepare(case(6),False)[1].forecast())
