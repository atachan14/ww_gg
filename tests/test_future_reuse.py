import unittest
from dataclasses import replace
from unittest.mock import patch
from benchmarks.player_match_groups.future_reuse import FutureReuseForecast
from benchmarks.player_match_groups.initial_white import initial_white_source
from benchmarks.player_match_groups.measure_future_reuse import run
from fractions import Fraction as F
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.exact import initial_board,replace_worlds
from werewolf.actor_information import WolfInformation
from werewolf.exact_renaming import canonical_key
from werewolf.model_a_public import public_forecast


class FutureReuseTests(unittest.TestCase):
    def test_complete_table_and_less_actual_work(self):
        for n,w in((5,1),(6,2)):
            old=run(n,w);new=run(n,w,True,physical_reuse=True,retired_reuse=True,compact_keys=True,fast_parts=True)
            self.assertTrue(old['complete']);self.assertTrue(new['complete'])
            self.assertEqual((old['value'],old['table']),(new['value'],new['table']))
            self.assertLess(new['expansions']['actions'],old['expansions']['actions'])
            self.assertLess(new['stats']['generated_publication_branches'],old['stats']['generated_publication_branches'])

    def test_keys_keep_complete_private_law_and_configuration(self):
        _,_,b,s,past,rules,strategy,_=initial_white_source(6,2,actors=(1,2))
        e=FutureReuseForecast(rules,strategy,future_reuse=True)
        full=e.full_renamed_key(b,s,past,s,None,physical=b)
        self.assertEqual(full,canonical_key(b,s,past,s,None,rules,strategy,physical=b,max_mappings=120))
        own=WolfInformation(s.hypotheses[0].roles[0]).condition_public(s)
        self.assertNotEqual(full,e.full_renamed_key(b,s,past,own,None,physical=b))
        e.rules=replace(rules,allow_repeat_guard=False)
        self.assertNotEqual(full,e.full_renamed_key(b,s,past,s,None,physical=b))
        self.assertIsNone(e.full_renamed_key(b,s,past,s,lambda h,s:True,physical=b))
        e.strategy=replace(strategy,day='max')
        self.assertIsNone(e.full_renamed_key(b,s,past,s,None,physical=b))

    def test_external_private_entry_never_uses_new_reuse(self):
        _,_,b,s,past,rules,strategy,_=initial_white_source(5,1,actors=(1,2))
        e=FutureReuseForecast(rules,strategy,future_reuse=True,physical_reuse=True)
        expected=InformationSetForecast(rules,strategy).evaluate(b,s,past,mask=s.hypotheses[0].roles[0])
        with patch('benchmarks.player_match_groups.future_reuse.canonical_key',side_effect=AssertionError('private reused')):
            actual=e.evaluate(b,s,past,mask=s.hypotheses[0].roles[0])
        self.assertEqual(expected,actual)
        self.assertTrue(e.reuse_public_entry)
        self.assertEqual(e.reuse_stats['key_requests'],0)

    def test_existing_max_stays_on_original_path(self):
        _,_,b,s,past,rules,strategy,_=initial_white_source(5,1,actors=(1,2))
        strategy=replace(strategy,day='max',night='max')
        original=public_forecast(b,s,past,rules,strategy,max_seconds=10)
        engines=[]
        def factory(*args,**kwargs):
            e=FutureReuseForecast(*args,future_reuse=True,physical_reuse=True,**kwargs);engines.append(e);return e
        with patch('werewolf.model_a_public.InformationSetForecast',factory):
            trial=public_forecast(b,s,past,rules,strategy,max_seconds=10)
        from werewolf.seer_future_uniform import FuturePending
        self.assertNotIsInstance(original,FuturePending);self.assertNotIsInstance(trial,FuturePending)
        self.assertEqual(original,trial);self.assertEqual(engines[0].reuse_stats['key_requests'],0)

    def test_physical_kernel_keeps_joint_law_not_only_marginals(self):
        _,_,_,_,_,rules,strategy,_=initial_white_source(5,1,actors=(1,2))
        e=FutureReuseForecast(rules,strategy,physical_reuse=True)
        boards=[]
        for edges in [[(2,3),(3,4),(4,5),(5,6),(6,7),(7,2)],[(2,3),(3,4),(4,2),(5,6),(6,7),(7,5)]]:
            worlds=tuple((sum(1<<(p-1)for p in pair),0,1,0,F(1,6))for pair in edges)
            boards.append(replace(replace_worlds(initial_board(7,2,0,1),worlds),claims=('seer',)+('latent',)*6))
        self.assertEqual(tuple(boards[0].wolf_probability(p)for p in boards[0].alive),tuple(boards[1].wolf_probability(p)for p in boards[1].alive))
        a=e.physical_children(boards[0],2);b=e.physical_children(boards[1],2)
        self.assertNotEqual(a,b)
        self.assertIs(a,e.physical_children(boards[0],2))
        self.assertEqual(e.reuse_stats['kernel_computations'],2)
        self.assertEqual(e.reuse_stats['kernel_hits'],1)

    def test_fast_masks_equal_exact_bit_permutation(self):
        from itertools import permutations
        from benchmarks.player_match_groups.fast_key_parts import make_canonical
        _,masks,_=make_canonical()
        for n in range(1,7):
            for ids in permutations(range(1,n+1)):
                self.assertEqual(masks(ids),tuple(sum(1<<(ids[p]-1) for p in range(n) if mask&(1<<p)) for mask in range(1<<n)))
        for n in (7,8,9):
            for ids in (tuple(range(1,n+1)),tuple(range(n,0,-1))):
                self.assertEqual(masks(ids),tuple(sum(1<<(ids[p]-1) for p in range(n) if mask&(1<<p)) for mask in range(1<<n)))

    def test_fast_canonical_preserves_complete_key(self):
        from benchmarks.player_match_groups.fast_key_parts import make_canonical,RecentSerializations
        fast,_,_=make_canonical()
        for n,w in ((5,1),(6,2),(7,2)):
            _,_,b,s,past,rules,strategy,_=initial_white_source(n,w,actors=(1,2))
            private=WolfInformation(s.hypotheses[0].roles[0]).condition_public(s)
            for target in (None,3):
                kwargs=dict(physical=b,target=target,max_mappings=120)
                expected=canonical_key(b,s,past,private,None,rules,strategy,**kwargs)
                self.assertEqual(expected,fast(b,s,past,private,None,rules,strategy,serialization_cache={'boards':RecentSerializations(),'states':RecentSerializations()},**kwargs))

    def test_hash_collision_does_not_merge_evidence(self):
        from werewolf.board_future import EvidenceKey
        a=EvidenceKey(('joint-A',),(7,));b=EvidenceKey(('joint-B',),(7,))
        self.assertEqual(hash(a),hash(b));self.assertNotEqual(a,b)
        self.assertEqual(len({a:1,b:2}),2)

    def test_memoization_disabled_respected(self):
        _,_,b,s,past,rules,strategy,_=initial_white_source(5,1,actors=(1,2))
        e=FutureReuseForecast(rules,strategy,future_reuse=True,physical_reuse=True)
        e.memoize_flows=False
        self.assertIsNone(e.full_renamed_key(b,s,past,s,None,physical=b))
        e.physical_children(b,3);e.physical_children(b,3)
        self.assertEqual(e.reuse_stats['key_requests'],0)
        self.assertEqual(e.reuse_stats['kernel_hits'],0)
