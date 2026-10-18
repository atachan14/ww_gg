"""Formal Model A weights and official-prior reference adapter audit."""
import itertools
import unittest
from collections import defaultdict
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.cut_out_model_a import (
    InitialModelASpec,adapt_model_a,ModelAInitialGroups,ModelAOneStepExecution)
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition,make_baseline,Observation
from benchmarks.player_match_groups.constructive_cut_out import ConstructiveCutOutGroups
from werewolf.exact import (Rules,Strategy,ClaimPolicy,initial_board,condition_claims,action_outcomes)
from werewolf.exact_renaming import board_signature,state_signature
from werewolf.seer_acquisition import Hypothesis,Acquisition,SeerReport,normalize
import test_partitioned_match_groups as metadata_oracle


def cases(n=5):
    none=ClaimPolicy(villager='none',medium='none',seer='none',hunter='none')
    def spec(claims,**kw):return InitialModelASpec(n,claims,True,**kw)
    latent=('latent',)*n
    return dict(
        witness=spec(latent[:-1]+('seer',),claim_policy=none),
        single=spec(('seer',)+latent[1:],rules=Rules(initial_seer='random_white'),reports=(SeerReport(1,1,1,3,'white'),)),
        insufficient=spec(('seer',)+latent[1:],seers=2),
        same_reports=spec(('seer','seer')+latent[2:],rules=Rules(initial_seer='random_white'),reports=(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'white'))),
        one_side_received=spec(('latent','latent','seer')+latent[3:],rules=Rules(initial_seer='random_white'),reports=(SeerReport(1,1,3,1,'white'),)),
        omitted_result=spec(('seer','seer')+latent[2:],rules=Rules(initial_seer='random_white'),reports=(SeerReport(1,1,1,3,'white'),)))


def independent_joint(spec):
    # Independent Model A weight construction: enumerate all legal role worlds,
    # put EQUAL MASS on each possible wolf/bluffer placement, then its legal
    # completions. Apply report/support/omission filters WITHOUT regrouping.
    seed=initial_board(spec.players,1,spec.mediums,spec.seers)
    legal=condition_claims(seed,spec.claims,spec.claim_policy)
    by_wolf=defaultdict(list)
    for world in legal.worlds:by_wolf[world[0]].append(world[:-1])
    entries=[];rows={r.player:r for r in spec.reports}
    tracked=tuple(p for p,c in enumerate(spec.claims,1) if c=='seer')
    for configs in by_wolf.values():
        mass=F(1,len(by_wolf)*len(configs))
        for roles in configs:
            acqs=[];valid=True
            for p in tracked:
                if not roles[2]&(1<<(p-1)):continue
                if spec.rules.initial_seer=='none':continue
                r=rows.get(p)
                if r is None:valid=False;break
                if ((r.color=='black')!=bool(roles[0]&(1<<(r.target-1))) or
                    spec.rules.initial_seer=='random_white' and r.color!='white'):
                    valid=False;break
                acqs.append(Acquisition(1,p,r.target,r.color))
            if valid:entries.append(Hypothesis(roles,tuple(sorted(acqs)),mass))
    return normalize(entries)


class ModelAAdapterTests(unittest.TestCase):
    def audit(self,spec):
        engine=adapt_model_a(spec);self.assertIsInstance(engine,ModelAInitialGroups)
        context=engine.start();expected=independent_joint(spec)
        self.assertIs(context.public,engine.baseline.state)
        self.assertEqual(context.public.hypotheses,expected)
        self.assertEqual(context.public.public_roles,tuple(sorted(engine.baseline.board.worlds)))
        rates={r.player:r.role_rates for r in engine.rows(context)}
        for p in range(1,spec.players+1):
            self.assertEqual(rates[p][:4],tuple(engine.baseline.board.role_probability(p,r) for r in ('wolf','medium','seer','hunter')))
            self.assertEqual(sum(rates[p]),1)
        identity=tuple(range(1,spec.players+1))
        def signature(ids):
            masks=tuple(sum(1<<(ids[p]-1) for p in range(spec.players) if m&(1<<p)) for m in range(1<<spec.players))
            return (board_signature(engine.baseline.board,ids,masks),state_signature(context.public,ids,masks),
                    metadata_oracle.evidence_signature(context.events,ids))
        reference=signature(identity)
        for ids in itertools.permutations(identity):
            if all({ids[p-1] for p in group}==set(group) for group in context.groups):self.assertEqual(signature(ids),reference)
        evaluator=ModelAOneStepExecution(engine);result=evaluator.evaluate(context)
        self.assertEqual(result.law_semantics,'model_a_initial_public')
        for target in context.alive:
            branches=evaluator.materialize(result,target)
            old=action_outcomes(engine.baseline.board,target,spec.rules,spec.strategy)
            for branch,o in zip(branches,old):
                self.assertEqual((branch.mass,branch.winner,branch.alive,branch.execution),(o.probability,o.board.winner,o.board.alive,o.board.history[-1]))
                self.assertEqual(branch.role_joint_mass,tuple(o.probability*o.board.role_probability(target,r) for r in ('wolf','medium','seer','hunter','villager')))
                support={w[:-1] for w in o.board.worlds}
                self.assertEqual(branch.posterior.hypotheses,normalize(tuple(h for h in expected if h.roles in support)))
                self.assertEqual(branch.posterior.public_roles,tuple(sorted(o.board.worlds)))
            self.assertEqual(len(branches),len(old))
        full=ModelAOneStepExecution(engine).evaluate(context,representatives=False)
        self.assertEqual(result.aggregate,full.aggregate)
        self.assertEqual(engine.stats['upstream_permutation_checks'],0)
        return engine,result

    def test_requested_small_cases_weighted_joint_rates_and_one_step(self):
        for n in (4,5):
            for name,spec in cases(n).items():
                with self.subTest(n=n,case=name):self.audit(spec)

    def test_p5_wolf_one_fifth_replaces_no_prototype_law(self):
        spec=cases()['witness'];engine,result=self.audit(spec)
        self.assertEqual(engine.baseline.board.wolf_probability(5),F(1,5))
        proto=ConstructiveCutOutGroups(make_baseline(mediums=1,rules=spec.rules,claim_policy=spec.claim_policy))
        context=proto.rebuild((Observation('co',((5,'seer'),)),))
        self.assertEqual({r.player:r.role_rates for r in proto.rows(context)}[5][0],F(1,2))
        self.assertIsInstance(ModelAOneStepExecution(engine).evaluate(engine.start(),law_semantics='prototype_joint_support'),UnsupportedPartition)
        self.assertIsInstance(ModelAOneStepExecution(engine).evaluate(engine.start(),view='private'),UnsupportedPartition)

    def test_official_objects_retained_by_reference_and_past_order_preserved(self):
        import benchmarks.player_match_groups.cut_out_model_a as adapter
        actual=adapter.prepare_public_prior;seen=[]
        def spy(*a,**kw):
            result=actual(*a,**kw);seen.append(result);return result
        spec=cases()['same_reports'];spec=replace(spec,reports=tuple(reversed(spec.reports)))
        with patch.object(adapter,'prepare_public_prior',spy):engine=adapt_model_a(spec)
        self.assertIs(engine.start().public,seen[0][0])
        self.assertIs(engine.baseline.past,seen[0][1])
        self.assertEqual(tuple(r.player for r in engine.baseline.past),(2,1))
        self.assertIn((1,2),engine.start().groups)
        # Guarantee is the snapshot joint law/one-step result, NOT bytewise
        # invariance of the legacy ordered-past tuple or future cache reuse.

    def test_constructive_groups_never_use_upstream_permutation_audit(self):
        with (patch('werewolf.exact_renaming.canonical_key',side_effect=AssertionError('old key')),
              patch('benchmarks.player_match_groups.partitioned_match_groups._map_event',side_effect=AssertionError('swap audit')),
              patch('benchmarks.player_match_groups.partitioned_match_groups.PartitionedMatchGroups._refine_groups',side_effect=AssertionError('old refine'))):
            for spec in cases().values():
                engine=adapt_model_a(spec);self.assertIsInstance(engine,ModelAInitialGroups)
                self.assertEqual(engine.stats['generator_checks'],0)
                self.assertEqual(engine.stats['symmetry_history_rows_read'],0)

    def test_one_side_received_and_omission_split_only_justified_groups(self):
        engine,_=self.audit(cases()['one_side_received'])
        self.assertNotEqual(next(g for g in engine.start().groups if 1 in g),next(g for g in engine.start().groups if 2 in g))
        same,_=self.audit(cases()['same_reports']);self.assertIn((1,2),same.start().groups)
        omitted,_=self.audit(cases()['omitted_result'])
        self.assertEqual(omitted.baseline.board.role_probability(1,'seer'),1)
        self.assertEqual(omitted.baseline.board.role_probability(2,'wolf'),1)
        insufficient,_=self.audit(cases()['insufficient'])
        self.assertTrue(any(h.roles[2]&~1 for h in insufficient.start().public.hypotheses))

    def test_unsupported_inputs_never_recondition_or_guess(self):
        spec=cases()['witness']
        for bad in ({'board':'arbitrary'},replace(spec,simultaneous_snapshot=False),replace(spec,players=7),replace(spec,strategy=Strategy()),
                    replace(spec,reports=(SeerReport(2,2,5,1,'white'),))):
            self.assertIsInstance(adapt_model_a(bad),UnsupportedPartition)
        # Mandatory disclosed result cannot be rescued by an invented history.
        missing=replace(cases()['single'],reports=())
        self.assertIsInstance(adapt_model_a(missing),UnsupportedPartition)
        engine=adapt_model_a(spec)
        self.assertIsInstance(engine.update(engine.start(),Observation('co',((1,'seer'),))),UnsupportedPartition)
        self.assertIsInstance(engine.rebuild(()),UnsupportedPartition)
        self.assertIsInstance(ModelAOneStepExecution(engine).evaluate(replace(engine.start())),UnsupportedPartition)