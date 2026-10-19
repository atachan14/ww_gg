import unittest
from unittest.mock import patch
from benchmarks.player_match_groups.report_vector_fixture import audit,kernel_audit
from benchmarks.player_match_groups.representative_target_fixture import case,prepare
from benchmarks.player_match_groups.cut_out_compact_terminal_fixture import independent_cold
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import tables
from werewolf.actor_information import WolfInformation
from werewolf.closed_calculation import ClosedCalculation


class ReportVectorTests(unittest.TestCase):
    def raw(self,compact=True):
        graph=case(7);c,node,_=prepare(graph,True,aggregate_wolf=True,aggregate_reports=compact)
        return graph,c,node.action(5)[0].node

    def test_expanded_cold_public_own_seer_forecast_tables(self):
        result=audit();counts=result['cases'][1]['counts']
        self.assertTrue(all(row['expanded_cold_Forecast_Table_equal'] for row in result['cases']))
        # Unobserved terminal reports now use the scalar integral. The named
        # vector/cold tests below still require complete observable histories;
        # old expansion totals are not a semantic contract.
        self.assertLessEqual(counts[2]['values'],counts[1]['values'])
        self.assertGreater(counts[2]['report_vectors']['kernels'],0)
        self.assertEqual(counts[2]['report_vectors']['public_event_laws'],0)
        self.assertEqual(counts[2]['report_vectors']['newly_built_vectors'],0)

    def test_complete_vector_orbits_joint_laws_and_literal_targets(self):
        graph,c,node=self.raw();result=kernel_audit(node)
        self.assertEqual(result,dict(expanded=200,representatives=166,named_coverage=200))
        info=WolfInformation.from_hypothesis(node.read().private.hypotheses[0])
        mass,owned=node.personal(info);result=kernel_audit(owned)
        self.assertEqual((result['expanded'],result['representatives']),(200,188))

    def test_named_cache_before_after_compact_and_owned_public_order(self):
        graph,c,node=self.raw();engine=c._ClosedCalculation__engine
        old=node.reports()
        with engine.group_scope(node.groups):compact=engine.report_children(node.read())
        self.assertEqual([(r.public_probability,r.probability,r.node.read()) for r in old],[(r.public_probability,r.probability,r.node.read()) for r in node.reports()]);self.assertLess(len(compact),len(old))
        graph,c,fresh=self.raw();e=c._ClosedCalculation__engine
        with e.group_scope(fresh.groups):first=e.report_children(fresh.read())
        self.assertEqual(first,compact)
        self.assertEqual([(r.public_probability,r.probability,r.node.read()) for r in fresh.reports()],[(r.public_probability,r.probability,r.node.read()) for r in old])
        # The public cache must not retain a private stabilizer coefficient.
        info=WolfInformation.from_hypothesis(fresh.read().private.hypotheses[0]);_,owner=fresh.personal(info)
        with e.group_scope(owner.groups):e.report_children(owner.read())
        with e.group_scope(fresh.groups):self.assertEqual(e.report_children(fresh.read()),first)
        for r in fresh.reports()[:3]:self.assertEqual(independent_cold(graph,r.node.export_request()),r.node.read())

    def test_owned_wolf_forecast_table_cold(self):
        graph=case(7);out=[]
        for compact in (False,True):
            c,node,_=prepare(graph,True,aggregate_wolf=True,aggregate_reports=compact)
            info=WolfInformation.from_hypothesis(node.read().private.hypotheses[0]);mass,node=node.personal(info)
            f=node.forecast();out.append((mass,node.read(),f,tables(node.read(),f)))
            self.assertEqual(independent_cold(graph,node.export_request()),node.read())
        self.assertEqual(out[0],out[1])

    def test_pre_generation_and_option_validation(self):
        graph,c,node=self.raw();e=c._ClosedCalculation__engine
        with patch('werewolf.morning_publications.future_publications',side_effect=AssertionError('expanded generator')):
            with e.group_scope(node.groups):self.assertEqual(len(e.report_children(node.read())),166)
        self.assertEqual(e.groups,())
        with self.assertRaises(ValueError):ClosedCalculation(graph.data,aggregate_reports=True)
        with self.assertRaises(TypeError):ClosedCalculation(graph.data,grouped=True,aggregate_reports=1)

    def test_private_branch_masses_and_full_joint_law_are_single_event_not_average(self):
        graph,c,node=self.raw();e=c._ClosedCalculation__engine
        info=WolfInformation.from_hypothesis(node.read().private.hypotheses[0])
        for source in (node,node.personal(info)[1]):
            old={r.node.read().past:(r.public_probability,r.probability,r.node.read()) for r in source.reports()}
            with e.group_scope(source.groups):compact=e.report_children(source.read())
            from werewolf.morning_publications import compile_publications
            s=source.read();k=compile_publications(s.public_state,s.past,s.public.alive,s.public.claims,board=s.public)
            parts=e.report_partition(s.public,s.past) if e.groups else tuple(tuple(p for p in g if p in k.reporters) for g in source.groups if any(p in k.reporters for p in g))
            multiplicities={s.past+r.reports:r.multiplicity for r in k.representatives(parts)}
            self.assertEqual(sum(p for q,p,child in compact),1)
            if source is not node:
                self.assertEqual(len(multiplicities),188);self.assertEqual(len(compact),90)
                for r in source.reports()[:3]:self.assertEqual(independent_cold(graph,r.node.export_request()),r.node.read())
            for q,p,child in compact:
                oq,op,original=old[child.past];m=multiplicities[child.past]
                self.assertEqual((q,p),(oq*m,op*m));self.assertEqual(child,original)

    def test_targets_in_same_group_remain_distinct_and_incoming_reports_split(self):
        from werewolf.board_flow import BoardData
        from werewolf.morning_publications import compile_publications
        from werewolf.seer_acquisition import SeerReport
        graph=case(7);g=graph.data.to_game();g.update(seers=1,claims=['seer']*2+['latent']*5,seer_inputs=[dict(day=1,reporter=p,target=3,color='white') for p in (1,2)])
        c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_reports=True);node=c.root
        for target in (4,5):node=node.observe(target)[1]
        self.assertEqual(kernel_audit(node),dict(expanded=25,representatives=19,named_coverage=25))
        s=node.read();k=compile_publications(s.public_state,s.past,s.public.alive,s.public.claims,board=s.public)
        parts=tuple(tuple(p for p in g if p in k.reporters) for g in node.groups if any(p in k.reporters for p in g))
        rows={r.reports:r for r in k.representatives(parts)}
        for target in (6,7):
            reports=tuple(SeerReport(2,2,p,target,'white') for p in (1,2))
            self.assertIn(reports,rows);self.assertEqual(rows[reports].multiplicity,1)
        graph,c,node=self.raw()
        reports=(SeerReport(3,3,1,4,'white'),SeerReport(3,3,2,1,'white'),SeerReport(3,3,3,4,'white'))
        child=next(r.node for r in node.reports() if r.node.read().past[-3:]==reports)
        self.assertTrue(all(len(g)==1 for g in child.groups))

    def test_medium_composition_and_unknown_role_joint_laws(self):
        from werewolf.board_flow import BoardData
        from werewolf.exact import MediumReport
        from werewolf.seer_acquisition import SeerReport
        from tests.test_wolf_cell_orbits import WolfCellOrbitTests
        c,node=WolfCellOrbitTests().correlated_source()
        result=kernel_audit(node);self.assertLess(result['representatives'],result['expanded'])
        graph=case(7);g=graph.data.to_game();g.update(mediums=1,claims=['seer']*3+['medium']+['latent']*3)
        outputs=[]
        for compact in (False,True):
            c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=compact);node=c.root
            for target in (6,7):node=node.observe(target)[1]
            node=node.observe_reports(tuple(SeerReport(2,2,p,6,'white') for p in (1,2,3)),(MediumReport(2,4,6,'white'),))[1]
            node=node.observe(5)[1];f=node.forecast();outputs.append((node.read(),f,tables(node.read(),f)))
            from types import SimpleNamespace
            self.assertEqual(independent_cold(SimpleNamespace(data=c.data,engine=graph.engine),node.export_request()),node.read())
        self.assertEqual(outputs[0],outputs[1])

    def test_no_ledgers_runtime_permutation_proofs_and_cancel_restores_scope(self):
        from werewolf.acquisition_provenance import AcquisitionLedger,UniformAcquisitionCache
        from werewolf.information_set_forecast import Pending
        graph,c,node=self.raw();e=c._ClosedCalculation__engine
        with patch('werewolf.morning_publications.CompiledPublications.representatives',side_effect=Pending('cancelled')):
            with self.assertRaises(Pending):
                with e.group_scope(node.groups):e.report_children(node.read())
        self.assertEqual(e.groups,())
        with patch.object(AcquisitionLedger,'__init__',side_effect=AssertionError('ledger')),patch.object(AcquisitionLedger,'_owner_current',side_effect=AssertionError('owner check')),patch.object(AcquisitionLedger,'_groups_record',side_effect=AssertionError('frame check')),patch.object(UniformAcquisitionCache,'__init__',side_effect=AssertionError('proof cache')):
            with e.group_scope(node.groups):self.assertEqual(len(e.report_children(node.read())),166)
        self.assertEqual(e.groups,())
