import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.wolf_cell_fixture import audit,cell_audit
from benchmarks.player_match_groups.representative_target_fixture import case,prepare
from benchmarks.player_match_groups.closed_morning_reports_fixture import case as morning_case
from benchmarks.player_match_groups.cut_out_first_cycle_coverage import base
from werewolf.closed_calculation import ClosedCalculation
from werewolf.board_flow import BoardData
from werewolf.actor_information import wolf_information_groups,wolf_information_orbits
from werewolf.seer_acquisition import normalize
from werewolf.night_knowledge import WolfAttack
from werewolf.information_set_forecast import Pending


class WolfCellOrbitTests(unittest.TestCase):
    def test_expanded_target_only_cells_and_independent_cold_public_owner_outputs(self):
        result=audit();seven=result['cases'][1]
        self.assertEqual(seven['target_only']['values'],433)
        self.assertEqual(seven['target_and_cells']['values'],289)
        self.assertEqual(seven['target_and_cells']['expansions']['actions'],839)
        self.assertEqual(seven['root_cells']['expanded_cells'],3)
        self.assertEqual(seven['root_cells']['representative_cells'],1)
        self.assertEqual(result['report_orbit_census'][1]['actual_vectors'],328)
        self.assertEqual(result['report_orbit_census'][1]['possible_vector_orbits'],118)

    def correlated_source(self):
        graph,_=morning_case(5);g=graph.data.to_game();g.update(players=6,seers=1,mediums=1,claims=['seer','seer']+['latent']*4,seer_inputs=[dict(day=1,reporter=p,target=5,color='white') for p in (1,2)])
        data=BoardData.from_game(g);c=ClosedCalculation(data,grouped=True,aggregate_wolf=True);node=c.root
        for target in (4,6):node=node.observe(target)[1]
        return c,node

    def test_conditional_joint_law_keeps_unknown_roles_and_scan_histories(self):
        c,node=self.correlated_source();result=cell_audit(node.read(),node.groups,c._ClosedCalculation__engine)
        self.assertEqual(result['expanded_cells'],2);self.assertEqual(result['representative_cells'],1)
        rows=wolf_information_orbits(node.read().private,node.groups);info,mass,state=rows[0]
        self.assertEqual(mass,1);self.assertGreater(len({h.roles for h in state.hypotheses}),1)
        self.assertGreater(len({h.acquisitions for h in state.hypotheses}),1)
        self.assertTrue(all(h.roles[0]==info.initial_roster and h.attacks==info.attacks for h in state.hypotheses))
        self.assertEqual(state.rosters,node.read().private.rosters)
        self.assertEqual((state.tracked,state.observed_prefix),(node.read().private.tracked,node.read().private.observed_prefix))

    def test_dead_teammates_keep_different_information_and_policy_denominators(self):
        graph=base()[0];c=ClosedCalculation(graph.data,grouped=True,aggregate_wolf=True);node=c.root.observe(1)[1];e=c._ClosedCalculation__engine
        result=cell_audit(node.read(),node.groups,e)
        self.assertEqual((result['expanded_cells'],result['representative_cells']),(6,2))
        choices={dict(e.wolf_policy(node.read().public,node.read().public_state,node.read().past,info.initial_roster,info.attacks))[4] for info,mass,state in wolf_information_orbits(node.read().private,node.groups)}
        self.assertEqual(choices,{F(1,5),F(1,4)})

    def test_owned_attack_histories_are_not_merged_and_only_representatives_normalize(self):
        c,node=self.correlated_source();s=node.read().private
        entries=tuple(replace(h,attacks=(WolfAttack(1,target),),mass=h.mass*weight) for target,weight in ((5,F(1,3)),(6,F(2,3))) for h in s.hypotheses)
        # Abstract complete joint-law test; these are not new saved H0 inputs.
        mixed=replace(s,hypotheses=normalize(entries));old=wolf_information_groups(mixed)
        with patch('werewolf.actor_information.normalize',wraps=normalize) as normalization:
            rows=wolf_information_orbits(mixed,node.groups)
        self.assertEqual(len(old),4);self.assertEqual(len(rows),2);self.assertEqual(normalization.call_count,2)
        self.assertEqual({(i.attacks[0].target,mass) for i,mass,law in rows},{(5,F(1,3)),(6,F(2,3))})
        for info,mass,law in rows:
            expected=next(state for old_info,old_mass,state in old if old_info==info)
            self.assertEqual(law,expected)

    def test_singleton_no_gain_path_skips_aggregation_and_cancel_restores_scope(self):
        c,node,_=prepare(case(6),True,aggregate_wolf=True,asymmetric=True)
        with patch('werewolf.actor_information.wolf_information_orbits',side_effect=AssertionError('no useful symmetry')):value=node.forecast()
        self.assertEqual(value,prepare(case(6),True,asymmetric=True)[1].forecast())
        c,node,_=prepare(case(7),True,aggregate_wolf=True);e=c._ClosedCalculation__engine
        with patch('werewolf.actor_information.wolf_information_orbits',side_effect=Pending('cancelled')):
            with self.assertRaises(Pending):node.forecast()
        self.assertEqual(e.groups,())
        self.assertEqual(node.forecast(),prepare(case(7),True)[1].forecast())
        with self.assertRaises(ValueError):ClosedCalculation(c.data,aggregate_wolf=True)
        with self.assertRaises(TypeError):ClosedCalculation(c.data,grouped=True,aggregate_wolf=1)

    def test_wolf_owned_joint_view_matches_expanded_and_independent_cold(self):
        from werewolf.actor_information import WolfInformation
        from benchmarks.player_match_groups.cut_out_compact_terminal_fixture import independent_cold
        from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import tables
        graph=case(7);plain,node,_=prepare(graph,False);fast,other,_=prepare(graph,True,aggregate_wolf=True)
        info=WolfInformation.from_hypothesis(node.read().private.hypotheses[0])
        mass,owned=node.personal(info);other_mass,representative=other.personal(info)
        self.assertEqual(mass,other_mass);self.assertEqual(owned.read(),representative.read())
        cold=independent_cold(graph,representative.export_request());self.assertEqual(cold,representative.read())
        a,b=owned.forecast(),representative.forecast();self.assertEqual(a,b)
        self.assertEqual(tables(owned.read(),a),tables(cold,b))
        self.assertEqual(fast._ClosedCalculation__engine.groups,())

    def test_original_seven_structured_scan_view_keeps_joint_conditional_future(self):
        from werewolf.actor_information import PersonalInformation
        from werewolf.seer_intervention import SeerObserver
        from benchmarks.player_match_groups.cut_out_compact_terminal_fixture import independent_cold
        from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import tables
        graph=base()[0];out=[]
        for aggregate in (False,True):
            c=ClosedCalculation(graph.data,grouped=True,aggregate_wolf=aggregate);node=c.root
            h=next(h for h in node.read().private.hypotheses if h.roles[2]&2)
            known=tuple(a for a in h.acquisitions if a.player==2)
            node=node.personal(PersonalInformation(2,'seer',known))[1]
            node=next(r.node for r in node.action(1) if r.node.read().public.winner is None)
            node=node.personal(SeerObserver(2,known,2,5))[1]
            node=next(r.node for r in node.action(4) if r.node.read().public.winner is None)
            node=next(r.node for r in node.reports() if any(v.reporter==3 and v.target==1 and v.color=='black' for v in r.node.read().public.reports) and any(v.player==2 and v.acquired_day==2 and v.target==5 and v.color=='white' for v in r.node.read().past))
            node=next(r.node for r in node.action(3) if r.node.read().public.winner is None)
            cold=independent_cold(graph,node.export_request());self.assertEqual(cold,node.read())
            value=node.forecast();out.append((node.read(),value,tables(node.read(),value)))
            self.assertEqual(c._ClosedCalculation__engine.groups,())
        self.assertEqual(out[0],out[1])
