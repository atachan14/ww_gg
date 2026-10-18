"""CO cancellation restores the official latent root, not a filtered parent."""
from dataclasses import replace
from itertools import product
from fractions import Fraction as F
from types import SimpleNamespace
import unittest
from benchmarks.player_match_groups.cut_out_model_a import adapt_model_a,source_game
from benchmarks.player_match_groups.cut_out_morning import CutOutMorning
from benchmarks.player_match_groups.cut_out_saved_recipes import SavedCutOutGraph,InvalidatedBranch
from werewolf.board_roles import reconstruct_saved,prepare_evaluation
from werewolf.public_prior import prepare_public_prior
from werewolf.seer_acquisition import Acquisition,Hypothesis,normalize,SeerReport
from werewolf.seer_future_uniform import TrueScanState
from werewolf.board_future import same_role_board
import test_cut_out_model_a as initial
import test_cut_out_morning as morning


def independent_root(spec):
    # Enumerate Model A original cast weights independently, then each actual
    # true seer's physical initial draw. No adapter/root/prior generator here.
    entries=[]
    for h in initial.independent_joint(spec):
        owners=tuple(p for p in range(1,spec.players+1) if h.roles[2]&(1<<(p-1))) if spec.rules.initial_seer!='none' else ()
        choices=tuple(tuple(p for p in range(1,spec.players+1) if p!=owner and
            (spec.rules.initial_seer!='random_white' or not h.roles[0]&(1<<(p-1)))) for owner in owners)
        denominator=1
        for options in choices:denominator*=len(options)
        for targets in product(*choices):
            acquisitions=tuple(Acquisition(1,owner,target,'black' if h.roles[0]&(1<<(target-1)) else 'white') for owner,target in zip(owners,targets))
            entries.append(Hypothesis(h.roles,acquisitions,h.mass/denominator))
    return TrueScanState(normalize(entries),(tuple(range(1,spec.players+1)),),spec.rules.initial_seer,None,0)


class CutOutCancellationTests(unittest.TestCase):
    def test_old_official_root_vs_fixed_co_prior_explains_support_without_role_loss(self):
        for n in (4,5):
            spec=replace(initial.cases(n)['single'],claims=('latent',)*n,reports=())
            game=source_game(spec);rules,progress=reconstruct_saved(game)
            kind,root=prepare_evaluation(game,progress.board,rules,spec.strategy)
            self.assertEqual(kind,'root')
            manual=independent_root(spec)
            self.assertEqual(root.public_law,manual)
            self.assertEqual(root.physical_law,manual)
            prior,past=prepare_public_prior(game,progress.board,rules)
            self.assertEqual(prior.public_roles,manual.public_roles)
            self.assertEqual(prior.tracked,())
            self.assertEqual(prior.observed_prefix,1)
            self.assertTrue(all(not h.acquisitions for h in prior.hypotheses))
            self.assertEqual(len(manual.hypotheses),len(prior.hypotheses)*(n-2))
            adapter=adapt_model_a(spec)
            self.assertEqual(adapter.baseline.state,manual)
            self.assertEqual(adapter.stats['official_root_entry'],1)
            # No candidate grafting: marginalizing physical draws recovers the
            # original fixed-CO role-only law exactly.
            marginal=normalize(tuple(replace(h,acquisitions=()) for h in manual.hypotheses))
            self.assertEqual(marginal,prior.hypotheses)

    def test_cancel_reco_correct_cancel_roundtrip_all_labels_against_official_kernels(self):
        branches=0
        for n in (4,5):
            start=initial.cases(n)['single'];cancelled=replace(start,claims=('latent',)*n,reports=())
            changed=replace(start,reports=(SeerReport(1,1,1,4,'white'),))
            graph=SavedCutOutGraph(adapt_model_a(start));previous=[];first_cancel=None
            for index,spec in enumerate((start,cancelled,start,changed,cancelled)):
                if index:
                    old=graph;graph=graph.corrected(spec)
                    self.assertIsInstance(graph,SavedCutOutGraph)
                    self.assertIs(graph.data.game_data,old.data.game_data)
                    self.assertIs(graph.data.runtime,old.data.runtime)
                expected=independent_root(spec) if spec==cancelled else replace(graph.engine.baseline.state,hypotheses=initial.independent_joint(spec))
                self.assertEqual(graph.engine.baseline.state,expected)
                # Old official selector, separately from SavedOrigin/adapter.
                game=source_game(spec);rules,progress=reconstruct_saved(game)
                kind,value=prepare_evaluation(game,progress.board,rules,spec.strategy)
                law=value.public_law if kind=='root' else value[0]
                self.assertEqual(law,expected)
                runner=CutOutMorning(graph.engine);result=runner.evaluate()
                bindings=graph.register_all(runner,result)
                reference_engine=SimpleNamespace(baseline=replace(graph.engine.baseline,state=expected))
                for target in range(1,n+1):
                    actual=runner.labelled_paths(result,target)
                    reference=morning.old_morning_paths(reference_engine,target)
                    self.assertEqual([(t,q,c.board,c.law,c.past) for t,q,c in actual],list(reference))
                    self.assertEqual(sum((q for t,q,c in actual),F()),1)
                for binding,q,child in bindings:
                    context=binding.read();self.assertNotIsInstance(context,InvalidatedBranch)
                    self.assertEqual(context.inputs.public_state,child.law)
                    self.assertEqual(context.inputs.private,child.law)
                    self.assertEqual(context.inputs.past,child.past)
                    self.assertTrue(same_role_board(context.inputs.physical,child.board))
                    self.assertEqual(binding.mass(),q)
                    self.assertEqual(tuple(context.inputs.public.worlds),tuple(child.board.worlds))
                    for p in range(1,n+1):
                        self.assertEqual(context.inputs.public.wolf_probability(p),child.board.wolf_probability(p))
                    branches+=1
                if index==1:first_cancel=(graph.engine.baseline.state,[(b.observation,q,c.law) for b,q,c in bindings])
                if index==4:self.assertEqual((graph.engine.baseline.state,[(b.observation,q,c.law) for b,q,c in bindings]),first_cancel)
                for saved,inputs,law in previous:
                    self.assertEqual(saved.data.inputs,inputs)
                    self.assertEqual(saved.origin().public_state,law)
                if index:
                    # Retargeting an old descriptor is either exactly a newly
                    # generated observation, or invalid; never stale reuse.
                    fresh={b.observation:(q,c) for b,q,c in bindings}
                    for old_binding,_,_ in old_bindings:
                        rebound=graph.bind(old_binding.observation)
                        if old_binding.observation in fresh:
                            q,c=fresh[old_binding.observation]
                            self.assertEqual(rebound.read().inputs.public_state,c.law)
                            self.assertEqual(rebound.mass(),q)
                        else:
                            self.assertIsInstance(rebound.read(),InvalidatedBranch)
                            self.assertIsInstance(rebound.mass(),InvalidatedBranch)
                old_bindings=bindings
                previous.append((graph,graph.data.inputs,expected))
            self.assertGreater(len(graph.engine.baseline.state.hypotheses),len(previous[0][2].hypotheses))
        print('CANCEL_ROUNDTRIP_LABELLED_BRANCHES',branches)
