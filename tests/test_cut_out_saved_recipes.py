"""All labels replay from saved inputs; corrected roots never reuse old evidence."""
from dataclasses import replace
from fractions import Fraction as F
import unittest
from unittest.mock import patch
from benchmarks.player_match_groups.cut_out_model_a import adapt_model_a
from benchmarks.player_match_groups.cut_out_morning import CutOutMorning
from benchmarks.player_match_groups.cut_out_saved_recipes import (SavedCutOutGraph,InvalidatedBranch,equivalent)
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition
from werewolf.board_future import SavedOrigin,same_role_board
from werewolf.seer_acquisition import SeerReport
import test_cut_out_model_a as cases
import test_cut_out_morning as morning_cases


class CutOutSavedRecipeTests(unittest.TestCase):
    def prepared(self,spec=None):
        spec=cases.cases()['single'] if spec is None else spec
        engine=adapt_model_a(spec);runner=CutOutMorning(engine);result=runner.evaluate()
        graph=SavedCutOutGraph(engine)
        return spec,runner,graph,graph.register_all(runner,result)

    def test_all_labelled_branches_have_saved_origin_recipes_roles_and_mass(self):
        count=0
        for spec in (cases.cases(4)['same_reports'],cases.cases()['single'],cases.cases()['same_reports'],morning_cases.medium_spec()):
            _,runner,graph,bindings=self.prepared(spec)
            for binding,mass,expected in bindings:
                context=binding.read();self.assertNotIsInstance(context,InvalidatedBranch)
                self.assertIsInstance(binding.request.origin,SavedOrigin)
                self.assertIs(binding.request.origin,graph.origin)
                self.assertIs(binding.request.game_data,graph.data.game_data)
                self.assertIs(context.inputs.board_data,binding.request)
                self.assertTrue(binding.request.history)
                self.assertTrue(same_role_board(context.inputs.public,expected.board))
                self.assertEqual(context.inputs.public_state,expected.law)
                self.assertEqual(context.inputs.private,expected.law)
                self.assertEqual(context.inputs.past,expected.past)
                self.assertEqual(binding.mass(),mass)
                rows=binding.rows();self.assertTrue(all(r.context is context for r in rows))
                for row in rows:
                    self.assertTrue(row.valid_for(binding))
                    self.assertIs(row.data.frame,context.frame)
                    self.assertEqual(row.data.metric('action').status,'pending')
                    self.assertEqual(row.data.wolf_probability,expected.board.wolf_probability(row.data.id))
                for a in rows:
                    for b in rows:self.assertEqual(equivalent(a,b),a.block==b.block)
                count+=1
            self.assertEqual(graph.stats['child_prior_reallocations'],0)
            self.assertEqual(graph.stats['generator_checks'],0)
        self.assertGreater(count,200)
        print('SAVED_LABELLED_BRANCHES',count)

    def select(self,bindings,execution=2,bite=3):
        return next(row for row in bindings if row[0].observation.execution==execution and row[0].observation.bite==bite
                    and row[0].observation.seers==(SeerReport(2,2,1,execution,'white'),))

    def test_corrected_input_replays_relative_new_evidence_not_old_prefix(self):
        spec,runner,graph,bindings=self.prepared()
        previous_inputs=graph.data.inputs
        corrected=graph.corrected(replace(spec,reports=(SeerReport(1,1,1,4,'white'),)))
        self.assertIsInstance(corrected,SavedCutOutGraph)
        self.assertIs(graph.data.game_data,corrected.data.game_data)
        self.assertIs(graph.data.runtime,corrected.data.runtime)
        self.assertNotEqual(graph.data.inputs,corrected.data.inputs)
        new_runner=CutOutMorning(corrected.engine);fresh=corrected.register_all(new_runner,new_runner.evaluate())
        for bite in (3,5):
            old,old_mass,old_expected=self.select(bindings,bite=bite)
            old_rows=old.rows();new=corrected.bind(old.observation)
            expected_binding,expected_mass,expected=self.select(fresh,bite=bite)
            self.assertIs(new,expected_binding)
            current=new.read();self.assertNotIsInstance(current,InvalidatedBranch)
            self.assertTrue(same_role_board(current.inputs.public,expected.board))
            self.assertEqual(current.inputs.public_state,expected.law)
            self.assertEqual(new.mass(),expected_mass)
            self.assertEqual(current.inputs.past[0],SeerReport(1,1,1,4,'white'))
            self.assertEqual(len(current.inputs.past),2) # corrected prefix + ONE new observation
            self.assertTrue(all(a.target==4 for h in current.inputs.public_state.hypotheses for a in h.acquisitions if a.day==1))
            self.assertEqual(old_rows[0].data.metric('wolf_probability',current_frame=new.frame).status,'stale')
            self.assertFalse(old_rows[0].valid_for(new))
            self.assertFalse(equivalent(old_rows[0],new.rows()[0]))
            self.assertEqual(old.read().inputs.public_state,old_expected.law)
            self.assertEqual(old.mass(),old_mass)
            if bite==3:
                self.assertNotEqual(old_mass,expected_mass)
                self.assertIn((4,5),old.read().groups)
                self.assertNotIn((4,5),current.groups)
            else:
                self.assertEqual(old.read().inputs.public.wolf_probability(4),1)
                self.assertEqual(current.inputs.public.wolf_probability(3),1) # obsolete P3-white NOT reapplied
        self.assertEqual(graph.data.inputs,previous_inputs)

    def test_unreachable_observation_invalidates_instead_of_filling_or_reusing(self):
        spec,runner,graph,bindings=self.prepared()
        old,q,expected=self.select(bindings)
        corrected=graph.corrected(replace(spec,reports=(SeerReport(1,1,1,2,'white'),)))
        invalid=corrected.bind(old.observation)
        # Now slot1 already visited2; the configured unvisited rule cannot
        # produce the retained slot2 target2 observation in this small history.
        self.assertIsInstance(invalid.read(),InvalidatedBranch)
        self.assertIsInstance(invalid.mass(),InvalidatedBranch)
        self.assertIsInstance(invalid.rows(),InvalidatedBranch)
        self.assertEqual(old.read().inputs.public_state,expected.law)
        cancelled=graph.corrected(replace(spec,claims=('latent',)*5,reports=()))
        self.assertIsInstance(cancelled,UnsupportedPartition)
        self.assertIn('SavedOrigin',cancelled.reason)
        self.assertIsInstance(graph.corrected(replace(spec,strategy=cases.Strategy())),UnsupportedPartition)

    def test_reference_reconstruction_and_real_playerdata_board_context_scope(self):
        spec,runner,graph,bindings=self.prepared()
        targets=[self.select(bindings,bite=3)[0],self.select(bindings,bite=5)[0],bindings[0][0]]
        from werewolf import board_roles
        original=board_roles.prepare_evaluation
        with (patch.object(board_roles,'prepare_evaluation',wraps=original) as rebuild,
              patch('werewolf.exact_renaming.canonical_key',side_effect=AssertionError('old match'))):
            for binding in targets:
                cached=binding.read();reference=binding.read(reference=True)
                self.assertEqual(cached.inputs,reference.inputs)
                self.assertIs(cached.request,binding.request)
            self.assertGreaterEqual(rebuild.call_count,len(targets))
        a=self.select(bindings,bite=3)[0];b=self.select(bindings,bite=5)[0]
        left=a.rows()[0];right=b.rows()[0]
        self.assertFalse(left.valid_for(b));self.assertFalse(equivalent(left,right))
        self.assertEqual(left.data.metric('wolf_probability',current_frame=b.frame).status,'stale')
        self.assertEqual(left.data.frame.scope.kind,'public')