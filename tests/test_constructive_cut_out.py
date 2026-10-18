"""Exhaustive small-law audits; constructive runtime has no exchange tests."""
from fractions import Fraction as F
from unittest.mock import patch
import test_partitioned_match_groups as oracle
from benchmarks.player_match_groups.constructive_cut_out import ConstructiveCutOutGroups
from benchmarks.player_match_groups.partitioned_match_groups import make_baseline, Observation
from werewolf.exact import Rules


class ConstructiveCutOutTests(oracle.PartitionedMatchGroupTests):
    # Inherit all nine exact-law, history, private and correlation regression
    # contracts; each now constructs the event-proof engine, not generator one.
    def engine(self, n=5, **kwargs):
        return ConstructiveCutOutGroups(make_baseline(n,**kwargs))

    def test_comparisons_use_only_shared_reference_tokens(self):
        engine=self.engine(mediums=1)
        with (patch('benchmarks.player_match_groups.partitioned_match_groups._map_event',side_effect=AssertionError('runtime exchange audit')),
              patch('benchmarks.player_match_groups.partitioned_match_groups.PartitionedMatchGroups._refine_groups',side_effect=AssertionError('old refinement fallback'))):
            context=engine.rebuild((Observation('co',((1,'seer'),(2,'seer'))),
                Observation('report',((1,3,'white',1),(2,3,'white',1)))))
            rows={r.player:r for r in engine.rows(context)};before=engine.stats.copy()
            for _ in range(100):
                self.assertTrue(engine.equivalent(rows[1],rows[2]))
                self.assertFalse(engine.equivalent(rows[1],rows[3]))
            self.assertEqual(dict(engine.stats-before),{'comparisons':200})
            self.assertEqual(engine.stats['generator_checks'],0)
            self.assertEqual(engine.stats['full_permutation_searches'],0)
            self.assertEqual(engine.stats['constructive_events'],2)
            self.assertGreater(engine.stats['normalization_input_hypotheses'],0)
            self.assertGreater(engine.stats['law_condition_seconds'],0)
        self.audit(engine,context)

    def test_batch_death_keeps_only_proven_removed_and_remaining_sets(self):
        engine=self.engine()
        context=self.apply(engine,(Observation('death',((1,),(2,)),phase='night'),))
        self.assertEqual(context.groups,((1,2),(3,4,5)))
        self.assertEqual(context.public_support_mass,F(1))
        self.assertEqual(engine.stats['joint_normalizations'],0)
        self.assertEqual(engine.stats['generator_checks'],0)
        self.assertEqual(engine.stats['partition_positions_read'],5)

    def test_mutual_report_targets_are_fixed_conservatively(self):
        engine=self.engine(rules=Rules(initial_seer='normal'))
        program=(Observation('co',((1,'seer'),(2,'seer'))),
                 Observation('report',((1,2,'black',1),(2,1,'black',1))))
        context=self.apply(engine,program)
        self.assertEqual(context.groups,((1,),(2,),(3,4,5)))
        # The oracle can prove a larger swap, but runtime deliberately does not
        # discover it. Full law, rates and support mass still match exactly.
        old=oracle.PartitionedMatchGroups(engine.baseline)
        previous=old.rebuild(program)
        self.assertEqual(previous.groups,((1,2),(3,4,5)))
        self.assertEqual(context.public,previous.public)
        self.assertEqual(context.public_support_mass,previous.public_support_mass)
        self.assertEqual(engine.stats['generator_checks'],0)

    def test_runtime_update_and_rebuild_do_not_rescan_old_program_for_symmetry(self):
        engine=self.engine()
        program=(Observation('co',((1,'seer'),(2,'seer'))),
                 Observation('report',((1,3,'white',1),(2,3,'white',1))),
                 Observation('death',((4,),),phase='night'))
        with patch('benchmarks.player_match_groups.partitioned_match_groups._map_event',side_effect=AssertionError('old event graph scan')):
            context=engine.rebuild(program)
            corrected=engine.rebuild(program[:1]+(Observation('report',((1,5,'white',1),(2,5,'white',1))),)+program[2:])
            withdrawn=engine.rebuild(program[:1])
        for c in (context,corrected,withdrawn):self.audit(engine,c)
        self.assertEqual(engine.stats['generator_checks'],0)
        self.assertEqual(engine.stats['constructive_events'],7)
        self.assertEqual(engine.stats['partition_positions_read'],35)
        self.assertGreater(engine.stats['support_mass_input_hypotheses'],0)