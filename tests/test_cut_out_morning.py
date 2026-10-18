"""Full-labelled public report oracle and death/secret boundary contracts."""
import itertools
import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
import test_cut_out_day_night as night_oracle
import test_cut_out_model_a as initial_cases
from benchmarks.player_match_groups.cut_out_model_a import adapt_model_a,InitialModelASpec
from benchmarks.player_match_groups.cut_out_morning import CutOutMorning,MorningResult
from werewolf.exact import Rules,report_actions,random_report_outcomes,BoardOutcome
from werewolf.belief_projection import project_private
from werewolf.morning_publications import future_publications,public_report_branches
from werewolf.seer_acquisition import SeerReport
from werewolf.seer_future_uniform import FuturePending
from werewolf.board_future import register_origin
from werewolf.evaluation_branch import ActionInputs,physical_board


def medium_spec():
    return InitialModelASpec(5,('seer','medium','medium','latent','latent'),True,
        rules=Rules(initial_seer='random_white'),reports=(SeerReport(1,1,1,4,'white'),))


def old_morning_paths(engine,target):
    result=[];base=engine.baseline
    for bite,physical_mass,board,state in night_oracle.old_paths(engine,target):
        if board.winner is not None:
            result.append((bite,physical_mass,board,state,base.past));continue
        outcomes=random_report_outcomes(board) if report_actions(board) else (BoardOutcome(F(1),board),)
        for medium in outcomes:
            law=project_private(state,medium.board)
            generated=future_publications(law,base.past,medium.board.alive,medium.board.claims,
                fake_policy=base.strategy.fake_seer_policy)
            if isinstance(generated,FuturePending):raise AssertionError(generated.reason)
            for q,b,s,p in public_report_branches(medium.board,base.past,generated):
                result.append((bite,physical_mass*medium.probability*q,b,s,p))
    return tuple(sorted(result,key=lambda row:repr((row[0],row[2].reports,row[4],row[2].winner))))


class CutOutMorningTests(unittest.TestCase):
    def audit(self,spec):
        engine=adapt_model_a(spec);runner=CutOutMorning(engine);result=runner.evaluate()
        self.assertIsInstance(result,MorningResult)
        self.assertEqual(sum((q for w,q in result.terminal_mass),F()),1)
        self.assertEqual(runner.stats['generator_checks'],0)
        for target in engine.start().alive:
            actual=runner.labelled_paths(result,target);expected=old_morning_paths(engine,target)
            self.assertEqual(len(actual),len(expected))
            for (bite,q,child),(old_bite,old_q,board,law,past) in zip(actual,expected):
                self.assertEqual((bite,q),(old_bite,old_q))
                self.assertEqual(child.board,board);self.assertEqual(child.law,law);self.assertEqual(child.past,past)
                self.assertEqual(child.law.public_roles,tuple(sorted(board.worlds)))
                self.assertEqual(child.past[:len(engine.baseline.past)],engine.baseline.past)
                night_oracle.CutOutDayNightTests.audit_groups(self,child)
                self.assertEqual(child.stage,'terminal' if board.winner else 'after_morning_publication')
            self.assertEqual(sum((q for bite,q,child in actual),F()),1)
        return engine,runner,result

    def test_all_labels_public_board_joint_masses_and_report_vectors_match(self):
        for spec in (initial_cases.cases(4)['same_reports'],initial_cases.cases()['single'],initial_cases.cases()['same_reports'],
                     replace(initial_cases.cases()['same_reports'],reports=tuple(reversed(initial_cases.cases()['same_reports'].reports))),medium_spec()):
            with self.subTest(n=spec.players,claims=spec.claims):self.audit(spec)

    def test_dead_before_acquisition_and_dead_after_acquisition_are_distinct(self):
        engine,runner,result=self.audit(initial_cases.cases()['single'])
        # Executed before the acquisition: no slot2 record, no new publication
        # request, but the already acquired/published slot1 remains exact.
        for bite,q,child in runner.labelled_paths(result,1):
            self.assertEqual(child.past,engine.baseline.past)
            self.assertFalse(any(a.player==1 and a.day==2 for h in child.law.hypotheses for a in h.acquisitions))
            self.assertTrue(all(any(a.player==1 and a.day==1 for a in h.acquisitions) for h in child.law.hypotheses))
        # Acquired before the bite: results remain SECRET history after death;
        # a dead reporter does NOT newly publish them next morning.
        killed=[c for bite,q,c in runner.labelled_paths(result,4) if bite==1]
        self.assertTrue(killed)
        for child in killed:
            self.assertEqual(child.past,engine.baseline.past)
            self.assertTrue(all(any(a.player==1 and a.day==2 for a in h.acquisitions) for h in child.law.hypotheses))
            # Hidden targets 2 and5 must not cut the public group into singletons.
            self.assertIn((2,5),child.groups)
            self.assertTrue(any(a.day==2 and a.target==2 for h in child.law.hypotheses for a in h.acquisitions))
            self.assertTrue(any(a.day==2 and a.target==5 for h in child.law.hypotheses for a in h.acquisitions))
        # Surviving reporter must publish an acquired corpse-target result.
        paths=[(q,c) for bite,q,c in runner.labelled_paths(result,4) if bite==3]
        total=sum((q for q,c in paths),F())
        corpse=sum((q for q,c in paths if SeerReport(2,2,1,4,'white') in c.past),F())
        self.assertEqual(corpse/total,F(1,3))
        self.assertGreater(corpse,0)

    def test_common_morning_weight_and_generated_board_recipe_round_trip(self):
        engine=adapt_model_a(initial_cases.cases()['single']);runner=CutOutMorning(engine)
        with (patch('benchmarks.player_match_groups.cut_out_model_a.reconstruct_saved',side_effect=AssertionError('initial replay')),
              patch('benchmarks.player_match_groups.cut_out_model_a.prepare_public_prior',side_effect=AssertionError('initial prior')),
              patch('werewolf.exact_renaming.canonical_key',side_effect=AssertionError('old matching'))):
            result=runner.evaluate()
            child=next(c for bite,q,c in runner.labelled_paths(result,2) if bite==3 and SeerReport(2,2,1,2,'white') in c.past)
            request=register_origin(runner.kernel,child.board,ActionInputs(child.law,child.past,child.law,None,physical_board(child.board,child.law)))
            self.assertTrue(request.history) # generated public evidence, not only a new opaque origin
            restored=request.roles()
        self.assertEqual((restored.public,restored.public_state,restored.past,restored.private),(child.board,child.law,child.past,child.law))
        transported=next(c for bite,q,c in runner.labelled_paths(result,4) if bite==3 and SeerReport(2,2,1,4,'white') in c.past)
        recipe=register_origin(runner.kernel,transported.board,ActionInputs(transported.law,transported.past,transported.law,None,physical_board(transported.board,transported.law)))
        self.assertFalse(recipe.history) # labelled value transport is not yet an action/publication recipe chain
        self.assertGreater(runner.stats['morning_calls'],0)
        self.assertEqual(runner.stats['initial_reallocations'],0)
        self.assertEqual(runner.stats['full_permutation_searches'],0)
        medium_engine=adapt_model_a(medium_spec());medium_runner=CutOutMorning(medium_engine)
        medium_result=medium_runner.evaluate()
        medium_child=next(c for bite,q,c in medium_runner.labelled_paths(medium_result,4) if bite==5 and any(r.color=='black' for r in c.board.reports))
        medium_request=register_origin(medium_runner.kernel,medium_child.board,ActionInputs(medium_child.law,medium_child.past,medium_child.law,None,physical_board(medium_child.board,medium_child.law)))
        self.assertTrue(medium_request.history)
        restored_medium=medium_request.roles()
        self.assertEqual((restored_medium.public,restored_medium.public_state,restored_medium.past),(medium_child.board,medium_child.law,medium_child.past))

    def test_terminal_skip_and_representative_transport_match_full_mode(self):
        engine=adapt_model_a(initial_cases.cases(4)['same_reports']);runner=CutOutMorning(engine)
        result=runner.evaluate();self.assertEqual(runner.stats['morning_calls'],0)
        self.assertTrue(all(c.stage=='terminal' for t,q,c in runner.labelled_paths(result,1)))
        engine=adapt_model_a(medium_spec());grouped=CutOutMorning(engine);g=grouped.evaluate()
        full=CutOutMorning(engine);f=full.evaluate(representatives=False)
        self.assertEqual(g.terminal_mass,f.terminal_mass)
        for target in engine.start().alive:
            a=grouped.labelled_paths(g,target);b=full.labelled_paths(f,target)
            self.assertEqual([(t,q,c.board,c.law,c.past) for t,q,c in a],[(t,q,c.board,c.law,c.past) for t,q,c in b])