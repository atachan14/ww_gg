"""Small exhaustive oracle for the independent cut-out grouping prototype."""
import itertools
import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.partitioned_match_groups import (
    make_baseline, PartitionedMatchGroups, Observation, UnsupportedPartition)
from werewolf.exact import Rules, Strategy, ClaimPolicy, initial_board, condition_claims, replace_worlds
from werewolf.exact_renaming import state_signature, canonical_key
from werewolf.seer_acquisition import Hypothesis, Acquisition, normalize


def old_initial(n, mediums, rule):
    # Independent legacy full labelled allocation enumeration; no prototype
    # constructor, partition, acquisition generator or public-role projection.
    entries = []
    for w, m, s, h, q in initial_board(n, 1, mediums, 1).worlds:
        owner = s.bit_length()
        targets = [None] if rule == 'none' else [p for p in range(1, n+1) if p != owner and (rule != 'random_white' or not w & (1<<(p-1)))]
        for target in targets:
            records = () if target is None else (Acquisition(1, owner, target, 'black' if w & (1<<(target-1)) else 'white'),)
            entries.append(Hypothesis((w, m, s, h), records, q/len(targets)))
    return tuple(entries)


def old_replay(base, events):
    entries = old_initial(base.players, base.mediums, base.rules.initial_seer)
    claims = ['latent']*base.players
    for event in events:
        if event.kind == 'co':
            for p, role in event.rows:claims[p-1] = role
            allowed = {w[:-1] for w in condition_claims(base.board, tuple(claims), base.claim_policy).worlds}
            entries = tuple(h for h in entries if h.roles in allowed)
        elif event.kind in ('report', 'private_result'):
            for p, t, color, day in event.rows:
                if event.kind == 'report':
                    entries = tuple(h for h in entries if not h.roles[2] & (1<<(p-1)) or any((a.player, a.target, a.color, a.day) == (p, t, color, day) for a in h.acquisitions))
                else:
                    entries = tuple(h for h in entries if any((a.player, a.target, a.color, a.day) == (p, t, color, day) for a in h.acquisitions))
        elif event.kind == 'private_role':
            p, role = event.rows[0]
            def actual(h):
                return next((r for r, mask in zip(('wolf','medium','seer','hunter'), h.roles) if mask & (1<<(p-1))), 'villager')
            entries = tuple(h for h in entries if actual(h) == role)
    mass = sum((h.mass for h in entries), F())
    return normalize(entries), mass


def evidence_signature(events, ids):
    # Independent encoder for exhaustive old-style graph/state permutation audit.
    result = []
    for event in events:
        records = []
        for row in event.rows:
            row = list(row); row[0] = ids[row[0]-1]
            if event.kind in ('report', 'private_result', 'select'):row[1] = ids[row[1]-1]
            records.append(tuple(row))
        result.append((event.kind, event.day, event.phase, tuple(sorted(records))))
    return tuple(result)


def full_signature(context, ids):
    masks = tuple(sum(1<<(ids[p]-1) for p in range(len(ids)) if value & (1<<p)) for value in range(1<<len(ids)))
    return (state_signature(context.public, ids, masks), state_signature(context.private, ids, masks),
            evidence_signature(context.events, ids),
            tuple(sorted((ids[p-1], c) for p, c in enumerate(context.claims, 1))),
            tuple(sorted(ids[p-1] for p in context.alive)))


class PartitionedMatchGroupTests(unittest.TestCase):
    def engine(self, n=5, **kwargs):return PartitionedMatchGroups(make_baseline(n, **kwargs))

    def apply(self, engine, events):
        context = engine.start()
        for event in events:
            context = engine.update(context, event)
            self.assertNotIsInstance(context, UnsupportedPartition)
            self.audit(engine, context)
        return context

    def audit(self, engine, context):
        public_events = tuple(e for e in context.events if not e.kind.startswith('private'))
        expected, public_mass = old_replay(engine.baseline, public_events)
        own, private_mass = old_replay(engine.baseline, context.events)
        self.assertEqual(context.public.hypotheses, expected)
        self.assertEqual(context.private.hypotheses, own)
        self.assertEqual((context.public_support_mass, context.private_support_mass), (public_mass, private_mass))
        self.assertEqual(sum((h.mass for h in context.public.hypotheses), F()), 1)
        self.assertEqual(sum((h.mass for h in context.private.hypotheses), F()), 1)
        rows = engine.rows(context)
        for row in rows:
            self.assertIs(row.context, context)
            expected_rates = tuple(sum((h.mass for h in own if ((h.roles+(((1<<engine.baseline.players)-1)^sum(h.roles),))[r] & (1<<(row.player-1)))), F()) for r in range(5))
            self.assertEqual(row.role_rates, expected_rates)
            self.assertEqual(sum(row.role_rates), 1)
        # Full n! oracle is TEST ONLY: every claimed within-block permutation
        # preserves complete secret/role laws AND ordered relation history.
        identity = tuple(range(1, engine.baseline.players+1)); original = full_signature(context, identity)
        for ids in itertools.permutations(identity):
            inherited = all({ids[p-1] for p in group} == set(group) for group in context.groups)
            if inherited:self.assertEqual(full_signature(context, ids), original)
        cells = engine.role_cells(context)
        self.assertEqual(sum(c.secret_multiplicity for c in cells), len(own))
        self.assertEqual(sum(c.world_multiplicity for c in cells), len({h.roles for h in own}))
        self.assertEqual(sum((c.mass for c in cells), F()), 1)

    def test_symmetric_four_five_complete_laws_and_multiplicities(self):
        for n, medium, rule in itertools.product((4,5), (0,1), ('none','normal','random_white')):
            with self.subTest(n=n, medium=medium, rule=rule):
                engine = self.engine(n, mediums=medium, rules=Rules(initial_seer=rule))
                context = engine.start();self.audit(engine, context)
                self.assertEqual(context.groups, (tuple(range(1,n+1)),))
                self.assertEqual(len(engine.role_cells(context)), 1)
                choices = engine.uniform_choices(context, context.alive)
                self.assertEqual((choices[0].multiplicity, choices[0].mass), (n, F(1)))
                rows = engine.rows(context)
                for row in rows:self.assertTrue(engine.equivalent(rows[0], row))

    def test_simultaneous_two_seers_white_target_then_relation_propagation(self):
        engine = self.engine(mediums=1)
        events = (Observation('co',((1,'seer'),(2,'seer'))),
                  Observation('report',((1,3,'white',1),(2,3,'white',1))))
        context = self.apply(engine, events)
        self.assertEqual(context.groups, ((1,2),(3,),(4,5)))
        self.assertEqual(len(context.public.hypotheses), 6)
        self.assertEqual([c.mass for c in engine.role_cells(context)], [F(2,3),F(1,3)])
        choices = engine.uniform_choices(context, context.alive)
        self.assertEqual([(c.targets,c.multiplicity,c.mass) for c in choices], [((1,2),2,F(2,5)),((3,),1,F(1,5)),((4,5),2,F(2,5))])
        # Independent existing FULL canonical constructor agrees for all player
        # targets in each retained group. No prototype routine calls it.
        b = replace_worlds(engine.baseline.board, context.public.public_roles, claims=context.claims)
        keys = {p:canonical_key(b,context.public,(),context.private,None,engine.baseline.rules,engine.baseline.strategy,target=p,max_mappings=120) for p in context.alive}
        self.assertTrue(all(key is not None for key in keys.values()))
        self.assertEqual(keys[1],keys[2]);self.assertEqual(keys[4],keys[5]);self.assertNotEqual(keys[1],keys[3])
        selected = engine.update(context,Observation('select',((4,1),)))
        self.audit(engine,selected);self.assertEqual(selected.groups,((1,),(2,),(3,),(4,),(5,)))

    def test_private_role_result_and_death_keep_secrets_public_and_masses(self):
        engine=self.engine(mediums=1)
        events=(Observation('co',((1,'seer'),(2,'seer'))),Observation('report',((1,3,'white',1),(2,3,'white',1))),
                Observation('private_role',((1,'seer'),)),Observation('private_result',((1,3,'white',1),)),Observation('death',((1,),),phase='night'))
        context=self.apply(engine,events)
        self.assertNotEqual(context.public.hypotheses,context.private.hypotheses)
        self.assertTrue(all(any(a.player==1 and a.target==3 for a in h.acquisitions) for h in context.private.hypotheses))
        self.assertEqual(context.groups,((1,),(2,),(3,),(4,5)))
        self.assertNotIn(1,context.alive)
        self.assertEqual(sum((c.mass for c in engine.uniform_choices(context,context.alive)),F()),1)
        for role in ('wolf','medium','villager'):
            own=self.apply(engine,(Observation('private_role',((1,role),)),))
            index={'wolf':0,'medium':1,'villager':4}[role]
            self.assertEqual({r.player:r for r in engine.rows(own)}[1].role_rates[index],1)
        # Public reporting after private conditioning must update each law
        # separately, without using the private evidence for public inference.
        reordered=self.apply(engine,(events[0],events[2],events[1],events[3],events[4]))
        self.assertEqual(reordered.public,context.public)
        self.assertEqual(reordered.private,context.private)

    def test_ordered_updates_do_not_merge_and_rebuild_can_restore(self):
        engine=self.engine()
        p1=Observation('co',((1,'seer'),));p2=Observation('co',((2,'seer'),))
        first=self.apply(engine,(p1,p2));second=self.apply(engine,(p2,p1))
        self.assertEqual(first.claims,second.claims)
        # Earlier filled-CO support is itself observed evidence; reversing
        # it can change the posterior, despite equal final declarations.
        self.assertNotEqual(first.public,second.public)
        self.assertNotEqual(first.events,second.events)
        self.assertFalse(engine.equivalent(engine.rows(first)[0],engine.rows(second)[0]))
        self.assertEqual(first.groups,((1,),(2,),(3,4,5)))
        withdrawn=engine.rebuild((p1,));self.audit(engine,withdrawn)
        self.assertEqual(withdrawn.groups,((1,),(2,3,4,5)))
        self.assertEqual(engine.rebuild(()).groups,((1,2,3,4,5),))
        corrected=engine.rebuild((Observation('co',((1,'seer'),(2,'seer'))),Observation('report',((1,4,'white',1),(2,4,'white',1)))))
        self.audit(engine,corrected);self.assertEqual(corrected.groups,((1,2),(3,5),(4,)))

    def test_same_degree_cycle_is_not_a_proved_exchangeable_block(self):
        engine=self.engine(4)
        cycle=Observation('select',((1,2),(2,3),(3,4),(4,1)))
        context=self.apply(engine,(cycle,))
        self.assertEqual(context.groups,((1,),(2,),(3,),(4,)))
        # All vertices have identical in/out degree and one global rotation is
        # valid, but not all pair swaps. Singleton under-sharing is intentional.
        self.assertEqual(full_signature(context,(2,3,4,1)),full_signature(context,(1,2,3,4)))
        self.assertNotEqual(full_signature(context,(2,1,3,4)),full_signature(context,(1,2,3,4)))

    def test_comparisons_use_only_shared_reference_tokens(self):
        engine=self.engine()
        with patch('werewolf.exact_renaming.canonical_key',side_effect=AssertionError('old fallback')):
            context=engine.rebuild((Observation('co',((1,'seer'),(2,'seer'))),))
            rows={row.player:row for row in engine.rows(context)};before=engine.stats.copy()
            for _ in range(100):
                self.assertTrue(engine.equivalent(rows[1],rows[2]));self.assertFalse(engine.equivalent(rows[1],rows[3]))
            delta=engine.stats-before
            self.assertEqual(dict(delta),{'comparisons':200})
            self.assertEqual(engine.stats['full_permutation_searches'],0)
            self.assertGreater(engine.stats['generator_checks'],0)

    def test_known_seer_random_white_keeps_twelve_roles_thirty_six_secrets(self):
        engine=self.engine(mediums=1)
        own=engine.update(engine.start(),Observation('private_role',((1,'seer'),)))
        self.audit(engine,own)
        self.assertIs(own.public,engine.baseline.state)
        self.assertEqual(len({h.roles for h in own.private.hypotheses}),12)
        self.assertEqual(len(own.private.hypotheses),36)
        for target in (2,3,4,5):
            q=sum((h.mass for h in own.private.hypotheses if h.acquisitions[0].target==target),F())
            self.assertEqual(q,F(1,4))
        result=engine.update(own,Observation('private_result',((1,3,'white',1),)))
        self.audit(engine,result)
        rows={r.player:r for r in engine.rows(result)}
        self.assertEqual(rows[3].role_rates,(F(0),F(1,3),F(0),F(0),F(2,3)))
        self.assertEqual(result.private_support_mass,F(1,20))
        self.assertFalse(any(h.roles[0]&1 and h.roles[0]&2 for h in own.public.hypotheses))
        self.assertEqual(rows[1].role_rates[2],1)

    def test_all_small_report_positions_follow_the_same_construction(self):
        for n in (4,5):
            engine=self.engine(n)
            for owners in itertools.combinations(range(1,n+1),2):
                for target in range(1,n+1):
                    if target in owners:continue
                    context=engine.rebuild((Observation('co',tuple((p,'seer') for p in owners)),
                            Observation('report',tuple((p,target,'white',1) for p in owners))))
                    self.audit(engine,context)
                    blocks={frozenset(g) for g in context.groups}
                    self.assertIn(frozenset(owners),blocks)
                    self.assertIn(frozenset((target,)),blocks)
    def test_unsupported_is_explicit_without_old_fallback_or_policy_substitution(self):
        for base in (make_baseline(7),make_baseline(strategy=Strategy()),make_baseline(rules=Rules(allow_self_bite=True)),make_baseline(strategy={'day':'random'})):
            self.assertIsInstance(base,UnsupportedPartition)
        engine=self.engine();context=engine.start()
        bad=(Observation('unknown',((1,),)),Observation('report',((1,2,'white',1),)),Observation('private_result',((1,2,'white',1),)),
             Observation('co',((True,'seer'),)),Observation('co',((1,[]),)),Observation('co',((1,'seer'),(1,'seer'))),Observation('select',((1,1),)),Observation('death',((1,),),day=2))
        for event in bad:self.assertIsInstance(engine.update(context,event),UnsupportedPartition)
        self.assertIsInstance(engine.update(self.engine().start(),Observation('death',((1,),))),UnsupportedPartition)
        self.assertIsInstance(engine.uniform_choices(context,(1,2)),UnsupportedPartition)
        co=engine.update(context,Observation('co',((1,'seer'),)))
        self.assertIsInstance(engine.update(co,Observation('co',((1,'latent'),))),UnsupportedPartition)
        no_scan=self.engine(rules=Rules(initial_seer='none'))
        no_scan_co=no_scan.update(no_scan.start(),Observation('co',((1,'seer'),)))
        self.assertIsInstance(no_scan.update(no_scan_co,Observation('report',((1,2,'white',1),))),UnsupportedPartition)
        # Contradictory acquisition support is never filled uniformly.
        self.assertIsInstance(engine.update(co,Observation('report',((1,2,'black',1),))),UnsupportedPartition)
        other=self.engine(strategy=Strategy(day='random',night='random',fake_reports='random',fake_seer_policy=('uniform',)))
        self.assertFalse(engine.equivalent(engine.rows(context)[0],other.rows(other.start())[0]))


if __name__=='__main__':unittest.main()