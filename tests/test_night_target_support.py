"""Public target groups are not automatically symmetries of a conditioned P law."""
import unittest
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from werewolf.exact import initial_board,replace_worlds,PublicEvent,Rules,Strategy
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.phase_updates import acquisition_rosters
from werewolf.evaluation_branch import ContinuationInputs
from werewolf.seer_acquisition import normalize
from werewolf.public_convergence import public_night_observations,public_observation_orbits,public_key
from werewolf.closed_calculation import ClosedCalculation
from werewolf.board_flow import BoardData
from werewolf.calculation_tree import CalculationTree
from tests import test_manual_public_input as fixtures

class NightTargetSupportTests(unittest.TestCase):
    def case(self,weight=F(1)):
        base=initial_board(5,1)
        b=replace_worlds(base,((1,0,0,0,F(1,2)),(2,0,0,0,F(1,2))),wolf_count=None,
                         alive=(1,2,3,4),history=(PublicEvent(1,'day',5),),phase='night')
        # Construct a full-ledger fixture directly; do not normalize or compare
        # distinct tracking modes of an existing state. There are no abilities.
        state=TrueScanState(from_board(b),acquisition_rosters(b),Rules().initial_seer)
        own=replace(state,hypotheses=normalize(tuple(replace(h,mass=weight if h.roles[0]==1 else 1-weight) for h in state.hypotheses if (weight if h.roles[0]==1 else 1-weight))))
        physical=replace_worlds(b,own.public_roles,wolf_count=None)
        source=ContinuationInputs(b,state,(),own,None,physical)
        game=fixtures.ManualPublicInputTests().root().data.to_game();game.update(seers=0,mediums=0,hunters=0,wolves=1)
        calculation=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
        return calculation,source,((1,2),(3,4),(5,))

    def old_representatives(self,e,source,groups,*,counter=False,publish=True):
        rows=[]
        for group in groups:
            live=tuple(p for p in group if p in source.public.alive)
            if live:rows.extend((mass*len(live),after,live[0]) for mass,after in public_observation_orbits(e,source,live[0],groups,counter=counter,publish=publish))
        return tuple(rows)

    def test_counter_measure_retains_legal_member_when_group_head_is_wolf(self):
        for weight in (F(1),F(1,4),F(1,2)):
            with self.subTest(weight=weight):
                c,source,groups=self.case(weight);e=c._ClosedCalculation__engine
                with c._ClosedCalculation__kernel(),e.group_scope(groups):
                    old=self.old_representatives(e,source,groups,counter=True)
                    actual=public_night_observations(e,source,groups,counter=True)
                    self.assertEqual(sum(m for m,s,t in old),2*(1-weight)/3+F(2,3))
                    self.assertEqual(sum(m for m,s,t in actual),1)
                    co=[(m,s) for m,s,t in actual if s.public.history[-1].target==1]
                    gray=[(m,s) for m,s,t in actual if s.public.history[-1].target==3]
                    # Three concrete non-wolf victims per pack: one in the
                    # two-person Q group, two in the gray group.
                    self.assertEqual(sum(m for m,s in co),F(1,3))
                    self.assertEqual(sum(m for m,s in gray),F(2,3))
                    self.assertTrue(all(s.public.wolf_probability(2)==1 for m,s in co))
                    self.assertTrue(all(s.physical.wolf_probability(1)==weight for m,s in gray))
                    before=public_night_observations(e,source,groups)
                    legacy=self.old_representatives(e,source,groups)
                    self.assertEqual(before,legacy)

    def test_tree_links_zero_policy_inspection_without_missing_destination(self):
        c,source,groups=self.case();node=c._ClosedCalculation__node(source,groups,())
        tree=CalculationTree.from_node(node)
        with patch('werewolf.public_convergence.public_night_observations',side_effect=self.old_representatives):
            with self.assertRaises(KeyError):tree.read(tree.root,True,compact=True,defer_analysis=True)
        fresh=CalculationTree.from_node(node)
        shown=fresh.read(fresh.root,True,compact=True,defer_analysis=True)
        self.assertEqual(shown['village_win'],'1/2')
        def check(stage):
            if stage.get('branches'):
                self.assertEqual(sum(F(b['probability']) for b in stage['branches']),1)
                for b in stage['branches']:check(b['children'])
            for leaf in stage.get('leaves',[]):self.assertIn(leaf['node'],{fresh.root,*shown['items']})
        check(shown['night_stages'])
        zero=[key for key,row in fresh.nodes.items() if row.get('counterfactual') and row['node'].read().public.history[-1].target==1]
        self.assertTrue(zero)
        inspected=fresh.read(zero[0],True,compact=True,defer_analysis=True)
        # The counterfactual bite reveals which remaining player is the wolf;
        # the explicit inspection has a real exact win value, not a placeholder.
        self.assertEqual(inspected['village_win'],'1')
        self.assertEqual(fresh.value(fresh.root),F(1,2))
        self.assertEqual(source.physical.wolf_probability(1),1)
        self.assertEqual(source.public.wolf_probability(1),F(1,2))
