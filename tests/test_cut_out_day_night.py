"""Small full-labelled official actor-flow oracle through one night."""
import itertools
import unittest
from collections import defaultdict
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.cut_out_model_a import adapt_model_a,InitialModelASpec
from benchmarks.player_match_groups.cut_out_day_night import CutOutDayNight
from werewolf.exact import action_outcomes,replace_worlds
from werewolf.actor_information import wolf_information_groups
from werewolf.fixed_actor_continuation import physical_actor_outcomes
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.belief_projection import project_private
from werewolf.seer_acquisition import SeerReport,normalize
from werewolf.seer_future_uniform import acquire_uniform
from werewolf.exact_renaming import board_signature,state_signature
import test_cut_out_model_a as initial_cases


def old_paths(engine,target):
    root=engine.baseline
    kernel=InformationSetForecast(root.rules,root.strategy,max_work=100000,exact_renaming=False,memoize_flows=False)
    paths=[]
    for day in action_outcomes(root.board,target,root.rules,root.strategy):
        law=project_private(root.state,day.board)
        if day.board.winner is not None:
            paths.append((None,day.probability,day.board,law));continue
        buckets={};templates={}
        for info,actor_mass,actor_law in wolf_information_groups(law):
            policy=kernel.wolf_policy(day.board,law,root.past,info.initial_roster,info.attacks)
            for bite,q in policy:
                physical=replace_worlds(day.board,actor_law.public_roles,wolf_count=None)
                for chance,board,st in physical_actor_outcomes(physical,actor_law,kernel,bite):
                    key=(bite,board.winner,board.day,board.phase,board.alive)
                    weight=actor_mass*q*chance
                    buckets.setdefault(key,[]).extend(replace(h,mass=h.mass*weight) for h in st.hypotheses)
                    templates[key]=board
        acquired=acquire_uniform(law,day.board.alive)
        for key,hs in buckets.items():
            bite=key[0];mass=sum((h.mass for h in hs),F())
            st=replace(acquired,hypotheses=normalize(hs))
            board=replace_worlds(templates[key],st.public_roles,wolf_count=None)
            # Public compatibility update must agree too: W1 uniform no-self
            # bite has a constant denominator in every compatible wolf world.
            public=kernel.public_children(day.board,bite,acquired)
            matching=[o.board for o in public if o.board.winner==board.winner and o.board.alive==board.alive]
            assert len(matching)==1
            assert tuple(sorted(matching[0].worlds))==st.public_roles
            paths.append((bite,day.probability*mass,board,st))
    return tuple(sorted(paths,key=lambda x:repr((x[0],x[2].winner))))


class CutOutDayNightTests(unittest.TestCase):
    def audit_groups(self,child):
        n=child.board.player_count;identity=tuple(range(1,n+1))
        def signature(ids):
            masks=tuple(sum(1<<(ids[p]-1) for p in range(n) if mask&(1<<p)) for mask in range(1<<n))
            return board_signature(child.board,ids,masks),state_signature(child.law,ids,masks)
        expected=signature(identity)
        for ids in itertools.permutations(identity):
            if all({ids[p-1] for p in group}==set(group) for group in child.groups):self.assertEqual(signature(ids),expected)

    def audit(self,spec):
        engine=adapt_model_a(spec);runner=CutOutDayNight(engine);result=runner.evaluate()
        self.assertEqual(sum((q for w,q in result.terminal_mass),F()),1)
        self.assertEqual(runner.stats['generator_checks'],0)
        for target in engine.start().alive:
            actual=runner.labelled_paths(result,target);expected=old_paths(engine,target)
            self.assertEqual(len(actual),len(expected))
            for (bite,q,child),(old_bite,old_q,board,law) in zip(actual,expected):
                self.assertEqual((bite,q),(old_bite,old_q))
                self.assertEqual(child.board,board)
                self.assertEqual(child.law,law)
                self.assertIs(child.past,engine.baseline.past)
                self.assertEqual(child.stage,'before_publication' if board.winner is None else 'terminal')
                self.audit_groups(child)
            self.assertEqual(sum((q for bite,q,child in actual),F()),1)
        self.assertEqual(sum((row.selection_mass for row in result.classes),F()),1)
        by_execution=defaultdict(lambda:F())
        for choice in result.night_choice_classes:
            self.assertEqual(choice.selection_mass,F(choice.multiplicity,spec.players-2))
            by_execution[choice.execution_target]+=choice.actor_mass*choice.selection_mass
        self.assertTrue(all(q==1 for q in by_execution.values()))
        for row in result.classes:self.assertEqual(row.selection_mass,F(len(row.targets),spec.players))
        return engine,runner,result

    def test_formal_child_and_next_night_match_full_labelled_actor_flow(self):
        for n in (4,5):
            cases=initial_cases.cases(n)
            for name in ('witness','same_reports'):
                with self.subTest(n=n,case=name):self.audit(cases[name])
        self.audit(initial_cases.cases()['insufficient'])
        # Exercises opportunity/history target transport in the full Board.
        self.audit(InitialModelASpec(5,('seer','seer','medium','latent','latent'),True,
            rules=initial_cases.Rules(initial_seer='random_white'),reports=(SeerReport(1,1,1,4,'white'),SeerReport(1,1,2,4,'white'))))

    def test_no_reallocation_no_swap_audit_and_owned_policy_before_new_scans(self):
        engine=adapt_model_a(initial_cases.cases()['same_reports']);runner=CutOutDayNight(engine)
        original=runner.kernel.wolf_policy;seen=[]
        def policy(board,public,past,mask,history=()):
            self.assertEqual(public.public_roles,tuple(sorted(board.worlds)))
            self.assertTrue(all(a.day==1 for h in public.hypotheses for a in h.acquisitions))
            self.assertEqual(mask.bit_count(),1);seen.append(mask)
            result=original(board,public,past,mask,history)
            self.assertTrue(all(not mask&(1<<(p-1)) for p,q in result))
            self.assertTrue(all(q==F(1,len(board.alive)-1) for p,q in result))
            return result
        with (patch('werewolf.exact.group_initial_board',side_effect=AssertionError('initial regroup')),
              patch('benchmarks.player_match_groups.cut_out_model_a.prepare_public_prior',side_effect=AssertionError('initial prior replay')),
              patch('werewolf.exact_renaming.canonical_key',side_effect=AssertionError('old canonical')),
              patch('benchmarks.player_match_groups.partitioned_match_groups._map_event',side_effect=AssertionError('swap audit')),
              patch.object(runner.kernel,'wolf_policy',policy)):
            result=runner.evaluate()
        self.assertTrue(seen);self.assertEqual(runner.stats['initial_reallocations'],0)
        self.assertLess(runner.stats['night_candidates'],runner.stats['full_night_candidates'])
        self.assertGreater(runner.stats['kernel_output_hypotheses'],0)

    def test_corpse_scan_and_later_owner_death_keep_results(self):
        engine,runner,result=self.audit(initial_cases.cases()['single'])
        killed_owner=[child for bite,q,child in runner.labelled_paths(result,4) if bite==1][0]
        self.assertNotIn(1,killed_owner.board.alive)
        self.assertTrue(all(any(a.player==1 and a.day==2 for a in h.acquisitions) for h in killed_owner.law.hypotheses))
        corpse_mass=sum((h.mass for h in killed_owner.law.hypotheses if any(a.player==1 and a.day==2 and a.target==4 for a in h.acquisitions)),F())
        self.assertEqual(corpse_mass,F(1,3))
        self.assertTrue(all(h.attacks[0].night==1 and h.attacks[0].target==1 for h in killed_owner.law.hypotheses))
        self.assertEqual([(e.day,e.phase,e.target) for e in killed_owner.board.history],[(1,'day',4),(1,'night',1)])
        for bite,q,child in runner.labelled_paths(result,1):
            self.assertTrue(all(any(a.player==1 and a.day==1 for a in h.acquisitions) for h in child.law.hypotheses))
            self.assertFalse(any(a.player==1 and a.day==2 for h in child.law.hypotheses for a in h.acquisitions))

    def test_group_multiplicity_and_full_mode_aggregate_match(self):
        engine=adapt_model_a(initial_cases.cases()['witness'])
        grouped=CutOutDayNight(engine);g=grouped.evaluate()
        labelled=CutOutDayNight(engine);f=labelled.evaluate(representatives=False)
        self.assertEqual(g.terminal_mass,f.terminal_mass)
        self.assertLess(grouped.stats['day_candidates'],labelled.stats['day_candidates'])
        self.assertLess(grouped.stats['night_candidates'],labelled.stats['night_candidates'])
        for target in engine.start().alive:
            a=grouped.labelled_paths(g,target);b=labelled.labelled_paths(f,target)
            self.assertEqual([(t,q,c.board,c.law) for t,q,c in a],[(t,q,c.board,c.law) for t,q,c in b])