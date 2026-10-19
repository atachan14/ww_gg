import unittest
from dataclasses import replace
from unittest.mock import patch
from benchmarks.player_match_groups.closed_full_tree_fixture import case,run
from werewolf.closed_calculation import ClosedCalculation
from werewolf.actor_information import PersonalInformation
from werewolf.information_set_forecast import Pending
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded


class ClosedFullTreeTests(unittest.TestCase):
    def checked(self,n,kind,view='public',part='all'):
        result=run(n,kind,view,part)
        self.assertIsNone(result['termination'],result);self.assertEqual(result['returncode'],0,result)
        worker=result['worker'];self.assertEqual(worker['status'],'verified',result)
        self.assertLessEqual(worker['budget']['work'],250000)
        self.assertLess(worker['seconds'],30);self.assertLess(result['observed_peak_working_set_bytes'],384*1024*1024)
        for row in worker['views']:
            self.assertTrue(row['expanded_cold_joint_sources_equal'])
            if row['counts'].get('action_edges',0)==0:self.assertEqual(row['expected_contribution'],'0')
            self.assertGreater(row['counts']['cold_joint_sources'],0);self.assertGreater(row['mass_checks'],0)
        for row in worker['forecasts']:self.assertTrue(row['expanded_cold_Forecast_Table_equal'])
        return worker

    def test_five_small_public_and_complete_owner_trees(self):
        for view in ('public','seer','wolf'):
            result=self.checked(5,'single',view);self.assertEqual(result['forecasts'][0]['village_win'],'7/15')

    def test_five_correlated_true_fake_complete_owner_trees(self):
        for view in ('public','seer','wolf'):
            result=self.checked(5,'dual',view);self.assertEqual(result['forecasts'][0]['village_win'],'7/15')

    def test_five_night_and_joint_medium_public_trees(self):
        self.assertEqual(self.checked(5,'night')['entry']['phase'],'night')
        self.assertGreater(self.checked(5,'medium-pair')['views'][0]['counts']['report_edges'],0)

    def test_undefined_multiple_fake_joint_kernel_is_rejected_before_recursion(self):
        g=case(5,'single').data.to_game();g.update(wolves=2,claims=['seer']*3+['latent']*2,seer_inputs=[dict(day=1,reporter=p,target=4,color='white') for p in (1,2,3)])
        from werewolf.board_flow import BoardData
        c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)
        for node in (c.root,c.root.personal(PersonalInformation(1,'seer'))[1]):
            with self.assertRaises(Pending) as caught:node.forecast()
            self.assertEqual(caught.exception.reason,'multiple_fake_report_correlation_unselected')
        self.assertEqual(c.stats()['values'],0);self.assertEqual(c.stats()['actions'],0)
        self.assertEqual(c._ClosedCalculation__engine.groups,())

    def test_budget_separate_scope_limit_and_no_ledger(self):
        data=case(5,'single').data;c=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)
        with self.assertRaises(CalculationBudgetExceeded):
            with calculation_budget(1):c.root.forecast()
        self.assertEqual(c._ClosedCalculation__engine.groups,());self.assertEqual(c.stats()['values'],0)
        from werewolf.acquisition_provenance import AcquisitionLedger,UniformAcquisitionCache
        with patch.object(AcquisitionLedger,'__init__',side_effect=AssertionError('ledger')),patch.object(UniformAcquisitionCache,'__init__',side_effect=AssertionError('proof cache')):
            self.assertEqual(str(c.root.forecast().village_win),'7/15')
        seven=ClosedCalculation(case(7,'single').data,max_work=250000,max_seconds=30)
        with self.assertRaises(Pending) as caught:seven.root.forecast()
        self.assertEqual(caught.exception.reason,'closed_forecast_six_alive_limit')
        self.assertEqual(seven.stats()['values'],0)

    def test_missing_initial_declaration_is_not_synthesized_as_future_policy(self):
        data=case(5,'dual').data;g=data.to_game();g['seer_inputs']=g['seer_inputs'][:1]
        from werewolf.board_flow import BoardData
        c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_reports=True,max_work=250000,max_seconds=30)
        with self.assertRaises(Pending) as caught:c.root.forecast()
        self.assertEqual(caught.exception.reason,'closed_forecast_initial_report_pending')
        self.assertEqual(c.stats()['values'],0)

    def verify_shards(self,n,kind,view):
        from fractions import Fraction as F
        complete=self.checked(n,kind,view,'forecast')
        row=complete['forecasts'][0];contributions={}
        for target,_ in row['actions']:
            shard=self.checked(n,kind,view,str(target))
            contributions[target]=F(shard['views'][0]['expected_contribution'])
            # These cases enter during day: the independent terminal tree's
            # contribution is uniform-day probability times the forced payoff.
            self.assertEqual(contributions[target]*n,F(dict(row['actions'])[target]))
        self.assertEqual(sum(contributions.values(),F()),F(row['village_win']))
        return complete

    def test_six_all_day_branches_public_and_complete_owners(self):
        for kind in ('single','dual'):
            for view in ('public','seer','wolf'):
                result=self.verify_shards(6,kind,view)
                self.assertEqual(result['forecasts'][0]['village_win'],'3/8')

    def test_six_joint_medium_all_branches_and_owned_medium(self):
        for view in ('public','medium'):
            self.verify_shards(6,'medium-pair',view)

    def test_five_multiple_true_seers_compiler_in_full_continuation(self):
        # Dense terminal recipe rebuilding exceeds the audit work ceiling.
        # Compare complete cold Forecasts and every correlated report law/P mass
        # separately; the stopped terminal-enumeration record remains evidence.
        for view in ('public','seer','wolf'):
            result=self.checked(5,'three',view,'forecast')
            self.assertEqual(result['forecasts'][0]['village_win'],'7/15')
        from benchmarks.player_match_groups.report_vector_fixture import kernel_audit
        graph=case(5,'three');c=ClosedCalculation(graph.data,grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30);node=c.root
        with calculation_budget(250000,max_seconds=30):
            for target in (4,5):node=node.observe(target)[1]
            result=kernel_audit(node);self.assertEqual(result['expanded'],result['named_coverage'])
            h=next(h for h in node.read().private.hypotheses if h.roles[2]&1)
            _,owner=node.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))
            self.assertEqual(kernel_audit(owner)['expanded'],result['expanded'])
            self.assertIs(owner.read().public_state,node.read().public_state)
            self.assertGreater(len(owner.read().private.hypotheses),1)
            e=c._ClosedCalculation__engine;mass_rows=[]
            for selected in (node,owner):
                old={r.node.read().past:(r.public_probability,r.probability,r.node.read()) for r in selected.reports()}
                with e.group_scope(selected.groups):rows=e.report_children(selected.read())
                self.assertEqual(sum(p for q,p,child in rows),1)
                for q,p,child in rows:
                    oq,op,expected=old[child.past];multiplicity=q/oq
                    self.assertEqual(multiplicity.denominator,1)
                    self.assertEqual(p,op*multiplicity);self.assertEqual(child,expected)
                mass_rows.append(dict(named_positive_P=len(old),compact_positive_P=len(rows)))
            import json
            from pathlib import Path
            Path('benchmarks/player_match_groups/closed-five-multiple-seers-kernel.json').write_text(json.dumps(dict(status='verified',prefix=[4,5],public_hypotheses=len(node.read().public_state.hypotheses),owner_private_hypotheses=len(owner.read().private.hypotheses),public= result,owner=kernel_audit(owner),branch_mass_checks=mass_rows),indent=2)+'\n',encoding='utf-8')


    def verify_night_shards(self,n,kind,view):
        from fractions import Fraction as F
        complete=self.checked(n,kind,view,'forecast');row=complete['forecasts'][0];parts={}
        for target in complete['entry']['alive']:
            shard=self.checked(n,kind,view,str(target))
            parts[target]=F(shard['views'][0]['expected_contribution'])
        self.assertEqual(sum(parts.values(),F()),F(row['village_win']))
        if len(complete['entry']['initial_wolf_masks'])==1:
            for target,value in row['actions']:self.assertEqual(parts[target]*len(row['actions']),F(value))
        return complete,parts

    def test_six_night_multiple_nights_complete_public_and_seer(self):
        for view in ('public','seer'):
            complete,parts=self.verify_night_shards(6,'known-night',view)
            self.assertEqual(complete['forecasts'][0]['village_win'],'2/15')

    def test_five_night_mixed_live_counts_actual_weights_not_forced_target_weights(self):
        from fractions import Fraction as F
        for view in ('public','wolf'):
            complete,parts=self.verify_night_shards(5,'mixed-night',view)
            self.assertEqual(complete['entry']['wolf_counts'],[1,2])
            if view=='public':
                self.assertEqual(complete['forecasts'][0]['village_win'],'1/12')
                self.assertEqual(parts[1],F(1,96));self.assertEqual(parts[3],F(1,48))

    def test_extended_entry_keeps_no_self_bite_scope(self):
        from werewolf.board_flow import BoardData
        g=case(5,'single').data.to_game();g['rules']['allow_self_bite']=True;g['policy']['include_self_bite']=True
        c=ClosedCalculation(BoardData.from_game(g),grouped=True,max_work=250000,max_seconds=30)
        with self.assertRaises(Pending) as caught:c.root.forecast()
        self.assertEqual(caught.exception.reason,'closed_forecast_self_bite_pending')
        self.assertEqual(c.stats()['values'],0);self.assertEqual(c._ClosedCalculation__engine.groups,())
