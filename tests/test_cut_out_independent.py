"""Independent bounded event-program audit and legacy one-execution oracle."""
import itertools
import json
import math
import random
import unittest
from fractions import Fraction as F
from unittest.mock import patch
import test_partitioned_match_groups as oracle
from benchmarks.player_match_groups.constructive_cut_out import ConstructiveCutOutGroups
from benchmarks.player_match_groups.partitioned_match_groups import make_baseline,Observation,UnsupportedPartition
from benchmarks.player_match_groups.cut_out_one_step import OneStepExecution
from werewolf.exact import (Rules,ClaimPolicy,group_initial_board,initial_board,replace_worlds,action_outcomes)
from werewolf.seer_acquisition import normalize


class CutOutIndependentTests(unittest.TestCase):
    def engine(self,n=5,mediums=1,**kw):return ConstructiveCutOutGroups(make_baseline(n,mediums=mediums,**kw))

    def check(self,engine,context):
        oracle.PartitionedMatchGroupTests.audit(self,engine,context)
        self.assertEqual(engine.stats['generator_checks'],0)
        self.assertEqual(engine.stats['symmetry_history_rows_read'],0)

    def test_exhaustive_small_co_and_death_subsets(self):
        audited=0
        for n,m in itertools.product((4,5),(0,1)):
            engine=self.engine(n,m,rules=Rules(initial_seer='none'))
            for size in (1,2):
                for subset in itertools.combinations(range(1,n+1),size):
                    for kind in ('co','death'):
                        event=Observation(kind,tuple((p,'seer') if kind=='co' else (p,) for p in subset))
                        context=engine.rebuild((event,));self.assertNotIsInstance(context,UnsupportedPartition)
                        self.check(engine,context);audited+=1
        self.assertEqual(audited,100)
        print('EVENT_EXHAUSTIVE '+json.dumps(dict(programs=audited)))

    def test_seeded_event_sequences_complete_joint_and_group_audit(self):
        seed=20261018;rng=random.Random(seed);accepted=zero=permutations=0;co_roles=set()
        for i in range(128):
            n=4+i%2;m=(i//2)%2;rule=('none','normal','random_white')[i%3]
            policy=ClaimPolicy() if i%2 else ClaimPolicy(villager='none',medium='none',seer='none',hunter='none')
            engine=self.engine(n,m,rules=Rules(initial_seer=rule),claim_policy=policy)
            actors=tuple(rng.sample(range(1,n+1),rng.choice((1,2))))
            roles=('villager','seer','wolf')+(('medium',) if m else ())
            declarations=tuple((p,rng.choice(roles)) for p in actors);co_roles.update(role for p,role in declarations)
            if i%4==0:
                program=[Observation('co',((p,role),)) for p,role in declarations]
            else:program=[Observation('co',declarations)]
            reporters=tuple(p for p,role in declarations if role=='seer')
            if rule!='none' and i%3!=0 and reporters:
                rows=tuple((p,rng.choice([t for t in range(1,n+1) if t!=p]),rng.choice(('white','black')),1) for p in reporters)
                program.append(Observation('report',rows))
            # Generate some private positive-support evidence from the independent
            # labelled oracle, never from a prototype posterior or group summary.
            try:entries,mass=oracle.old_replay(engine.baseline,program)
            except ValueError:entries=()
            if entries and i%3==0:
                h=rng.choice(entries);p=rng.randrange(1,n+1)
                role=next((r for r,mask in zip(('wolf','medium','seer','hunter'),h.roles) if mask&(1<<(p-1))),'villager')
                program.append(Observation('private_role',((p,role),)))
                if role=='seer' and h.acquisitions:
                    a=h.acquisitions[0];program.append(Observation('private_result',((p,a.target,a.color,a.day),)))
            if i%2:program.append(Observation('death',tuple((p,) for p in rng.sample(range(1,n+1),rng.choice((1,2)))),phase='night'))
            for length in range(1,len(program)+1):
                prefix=tuple(program[:length]);context=engine.rebuild(prefix)
                try:oracle.old_replay(engine.baseline,prefix)
                except ValueError:
                    self.assertIsInstance(context,UnsupportedPartition);self.assertIn('support',context.reason);zero+=1;break
                self.assertNotIsInstance(context,UnsupportedPartition)
                self.check(engine,context);accepted+=1;permutations+=math.factorial(n)
        self.assertGreater(zero,0)
        print('EVENT_RANDOM '+json.dumps(dict(seed=seed,programs=128,accepted_prefixes=accepted,zero_support=zero,permutation_candidates=permutations,co_roles=sorted(co_roles))))

    def test_fake_seer_support_and_model_a_weight_difference_are_explicit(self):
        engine=self.engine()
        context=engine.rebuild((Observation('co',((1,'seer'),(2,'seer'))),))
        rates={r.player:r.role_rates for r in engine.rows(context)}
        self.assertEqual(rates[1][0],F(1,2));self.assertEqual(rates[1][2],F(1,2))
        self.assertTrue(all(h.roles[2].bit_count()==1 for h in context.public.hypotheses))
        # A false reporter's statement is not required to be an actual scan.
        false=engine.update(context,Observation('report',((1,2,'white',1),)))
        self.check(engine,false)
        self.assertTrue(all(h.roles[0]&1 and not any(a.player==1 for a in h.acquisitions) for h in false.public.hypotheses))
        policy=ClaimPolicy(villager='none',medium='none',seer='none',hunter='none')
        other=self.engine(claim_policy=policy)
        co=other.rebuild((Observation('co',((5,'seer'),)),))
        model_a=group_initial_board(initial_board(5,1,1,1),('latent',)*4+('seer',),policy)
        self.assertEqual({r.player:r.role_rates for r in other.rows(co)}[5][0],F(1,2))
        self.assertEqual(model_a.wolf_probability(5),F(1,5))
        self.assertIsInstance(OneStepExecution(other).evaluate(co,view='public',law_semantics='model_a'),UnsupportedPartition)

    def audit_step(self,engine,context,view):
        evaluator=OneStepExecution(engine)
        with patch('werewolf.exact_renaming.canonical_key',side_effect=AssertionError('runtime matching')):
            result=evaluator.evaluate(context,view=view)
        self.assertNotIsInstance(result,UnsupportedPartition)
        events=context.events if view=='private' else tuple(e for e in context.events if not e.kind.startswith('private'))
        entries,mass=oracle.old_replay(engine.baseline,events)
        worlds={}
        for h in entries:worlds[h.roles]=worlds.get(h.roles,F())+h.mass
        board=replace_worlds(engine.baseline.board,tuple((*r,q) for r,q in sorted(worlds.items())),claims=context.claims)
        aggregate={}
        for target in board.alive:
            expected=action_outcomes(board,target,engine.baseline.rules,engine.baseline.strategy)
            actual=evaluator.materialize(result,target)
            self.assertEqual(len(actual),len(expected))
            for branch,old in zip(actual,expected):
                self.assertEqual((branch.winner,branch.mass,branch.alive,branch.phase),(old.board.winner,old.probability,old.board.alive,old.board.phase))
                self.assertEqual(branch.execution,old.board.history[-1])
                # Legacy world's exact conditional masses select the entire
                # hidden history mixture, not a product of role marginals.
                support={r[:-1] for r in old.board.worlds}
                hs=normalize(tuple(h for h in entries if h.roles in support))
                self.assertEqual(branch.posterior.hypotheses,hs)
                self.assertEqual(branch.posterior.public_roles,old.board.worlds)
                roles=[F()]*5
                for h in entries:
                    if h.roles not in support:continue
                    r=next((r for r,mask in enumerate(h.roles) if mask&(1<<(target-1))),4)
                    roles[r]+=h.mass
                self.assertEqual(branch.role_joint_mass,tuple(roles))
                for r,q in enumerate(roles):aggregate[branch.winner,r]=aggregate.get((branch.winner,r),F())+q/F(len(board.alive))
        self.assertEqual(result.aggregate,tuple(sorted(aggregate.items(),key=repr)))
        self.assertEqual(evaluator.stats['candidate_evaluations'],len(context.groups))
        self.assertEqual(evaluator.stats['hypotheses_scanned'],len(context.groups)*len(entries))
        self.assertEqual(evaluator.stats['generator_checks'],0)
        return evaluator,result

    def test_one_execution_public_and_private_representatives_match_full_legacy(self):
        reduced=0
        for n,m in itertools.product((4,5),(0,1)):
            engine=self.engine(n,m)
            program=(Observation('co',((1,'seer'),(2,'seer'))),Observation('report',((1,3,'white',1),(2,3,'white',1))))
            public=engine.rebuild(program)
            for context,view in ((engine.start(),'public'),(public,'public'),(engine.update(public,Observation('private_role',((1,'seer'),))),'private')):
                evaluator,result=self.audit_step(engine,context,view)
                self.assertLessEqual(evaluator.stats['candidate_evaluations'],n)
                reduced+=evaluator.stats['candidate_evaluations']<n
                self.assertEqual(sum((q for _,q in result.aggregate),F()),1)
            self.assertIsInstance(OneStepExecution(engine).evaluate(public,view='private'),UnsupportedPartition)
            own=engine.update(public,Observation('private_role',((1,'seer'),)))
            self.assertIsInstance(OneStepExecution(engine).evaluate(own,view='public'),UnsupportedPartition)
            dead=engine.update(public,Observation('death',((4,),),phase='night'))
            self.assertIsInstance(OneStepExecution(engine).evaluate(dead,view='public'),UnsupportedPartition)
        self.assertGreater(reduced,0)