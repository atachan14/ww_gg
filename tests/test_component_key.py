import unittest
from fractions import Fraction as F
from collections import Counter
from dataclasses import replace
from unittest.mock import patch
from benchmarks.player_match_groups.component_key import component_tuple_type,make_component_canonical
from benchmarks.player_match_groups.fast_key_parts import RecentSerializations
from benchmarks.player_match_groups.extension_cases import fixture,prepare_game
from werewolf.exact_renaming import canonical_key
from werewolf.board_future import EvidenceKey
from werewolf.seer_intervention import SeerObserver
from werewolf.seer_acquisition import Acquisition,SeerReport,normalize

class ComponentKeyTests(unittest.TestCase):
    def prepared(self):return prepare_game(fixture()[1])[2:7]

    def test_tuple_values_order_and_hash_unchanged_with_lazy_hash_reuse(self):
        stats=Counter();wrap=component_tuple_type(stats)
        raw=('law',((1,F(1,3)),(2,F(2,3))));expected=hash(raw);calls=[];original=F.__hash__
        def counted(value):calls.append(value);return original(value)
        with patch.object(F,'__hash__',counted):
            component=wrap(raw);self.assertEqual(calls,[])
            self.assertEqual(hash(component),expected);self.assertEqual(len(calls),2)
            hash(('one',component));hash(('two',component));self.assertEqual(len(calls),2)
        self.assertEqual(component,raw);self.assertFalse(component<raw);self.assertFalse(raw<component)
        self.assertEqual({component:'complete'}[raw],'complete')
        with self.assertRaises(AttributeError):component._component_hash=0
        with self.assertRaises(AttributeError):del component._component_hash

    def test_forced_hash_collision_still_compares_complete_values(self):
        wrap=component_tuple_type(Counter())
        a=EvidenceKey((wrap((F(1,3),)),),(0,));b=EvidenceKey((wrap((F(2,3),)),),(0,))
        self.assertEqual(hash(a),hash(b));self.assertNotEqual(a,b)
        self.assertEqual(len({a:'first',b:'second'}),2)

    def test_canonical_keys_and_mapping_sets_match_small_original_fixtures(self):
        for options in({},dict(n=6,wolves=2),dict(mediums=1)):
            _,_,b,s,past,rules,strategy,_=prepare_game(fixture(**options)[1])
            fn,stats,_=make_component_canonical();cache={'boards':RecentSerializations(),'states':RecentSerializations()}
            for target in(None,*b.alive):
                kwargs=dict(target=target,return_mapping=True,max_mappings=120)
                expected=canonical_key(b,s,past,s,None,rules,strategy,**kwargs)
                actual=fn(b,s,past,s,None,rules,strategy,serialization_cache=cache,**kwargs)
                self.assertEqual(actual,expected)
                self.assertEqual(hash(actual),hash(expected))
                again=fn(b,s,past,s,None,rules,strategy,serialization_cache=cache,**kwargs)
                self.assertEqual(again,expected);hash(again)
            self.assertGreater(stats['component_hash_hits'],0)

    def test_changed_weights_history_private_target_and_policy_never_alias(self):
        b,s,past,rules,strategy=self.prepared();fn,stats,_=make_component_canonical()
        cache={'boards':RecentSerializations(),'states':RecentSerializations()}
        def key(public=b,law=s,reports=past,private=s,observer=None,rule=rules,policy=strategy,target=3,physical=None):
            kw=dict(target=target,physical=physical,max_mappings=120)
            result=fn(public,law,reports,private,observer,rule,policy,serialization_cache=cache,**kw)
            expected=canonical_key(public,law,reports,private,observer,rule,policy,**kw)
            self.assertEqual(result,expected);self.assertEqual(hash(result),hash(expected));return result
        base=key()
        weighted=replace(s,hypotheses=normalize(tuple(replace(h,mass=h.mass*(3 if h.roles[2]&1 else 1))for h in s.hypotheses)))
        # A changed law is compared against the old Board only as key input;
        # no inconsistent posterior is passed to a numerical evaluator.
        self.assertNotEqual(base,key(law=weighted,private=weighted))
        self.assertNotEqual(base,key(private=weighted))
        self.assertNotEqual(base,key(reports=(*past,SeerReport(2,2,1,5,'white'))))
        self.assertNotEqual(base,key(rule=replace(rules,allow_repeat_guard=False)))
        self.assertNotEqual(base,key(policy=replace(strategy,day='max')))
        self.assertNotEqual(base,key(target=1))
        changed=replace(b,claims=('latent',)+b.claims[1:])
        self.assertNotEqual(base,key(physical=changed))

    def test_observer_and_secret_history_remain_complete(self):
        b,s,past,rules,strategy=self.prepared();fn,_,_=make_component_canonical()
        cache={'boards':RecentSerializations(),'states':RecentSerializations()}
        own=next(h.acquisitions for h in s.hypotheses if h.roles[2]&1)
        keys=[]
        for observer in(SeerObserver(1,own,2,3),SeerObserver(1,own,2,5)):
            actual=fn(b,s,past,s,observer,rules,strategy,serialization_cache=cache,max_mappings=120)
            self.assertEqual(actual,canonical_key(b,s,past,s,observer,rules,strategy,max_mappings=120));keys.append(actual)
        self.assertNotEqual(*keys)
        self.assertIsNone(fn(b,s,past,s,lambda h,s:True,rules,strategy,serialization_cache=cache))
    def test_root_candidate_context_and_actor_mask_are_not_omitted(self):
        from werewolf.exact import initial_board,Rules,Strategy
        from werewolf.seer_acquisition import from_board
        from werewolf.seer_future_uniform import TrueScanState
        from werewolf.actor_information import WolfInformation
        from werewolf.policy_choice import uniform_policy
        b=initial_board(5,1);s=TrueScanState(from_board(b),(b.alive,),initial_rule='none')
        rules=Rules(initial_seer='none');strategy=Strategy()
        profile=tuple((WolfInformation(h.roles[0]),uniform_policy(tuple(t for t in b.alive if not h.roles[0]&(1<<(t-1)))))for h in s.hypotheses)
        fn,_,_=make_component_canonical();cache={'boards':RecentSerializations(),'states':RecentSerializations()};keys=[]
        for actor in(1,2):
            kwargs=dict(target=1,wolf_profiles=((b,s,(),profile),),actor_mask=actor,max_mappings=120)
            actual=fn(b,s,(),s,None,rules,strategy,serialization_cache=cache,**kwargs)
            expected=canonical_key(b,s,(),s,None,rules,strategy,**kwargs)
            self.assertEqual(actual,expected);self.assertEqual(hash(actual),hash(expected));keys.append(actual)
        self.assertNotEqual(*keys)

    def test_private_correlations_with_equal_role_marginals_remain_distinct(self):
        # Serializer-only support fixture; no future forecast is evaluated.
        from werewolf.exact import initial_board,Rules,Strategy
        from werewolf.seer_acquisition import from_board
        from werewolf.seer_future_uniform import TrueScanState
        from werewolf.night_knowledge import WolfAttack
        b=initial_board(5,1);rosters=(b.alive,b.alive)
        hs=normalize(tuple(replace(h,attacks=(WolfAttack(1,t),),mass=F(1,20))for h in from_board(b)for t in b.alive if not h.roles[0]&(1<<(t-1))))
        public=TrueScanState(hs,rosters,initial_rule='none')
        maps=((2,3,4,5,1),(2,1,4,5,3));laws=[]
        for mapping in maps:laws.append(replace(public,hypotheses=normalize(tuple(h for h in hs if h.attacks[0].target==mapping[h.roles[0].bit_length()-1]))))
        self.assertEqual(laws[0].public_roles,laws[1].public_roles)
        fn,_,_=make_component_canonical();cache={'boards':RecentSerializations(),'states':RecentSerializations()};keys=[]
        for own in laws:
            actual=fn(b,public,(),own,None,Rules(initial_seer='none'),Strategy(),serialization_cache=cache,max_mappings=120)
            expected=canonical_key(b,public,(),own,None,Rules(initial_seer='none'),Strategy(),max_mappings=120)
            self.assertEqual(actual,expected);self.assertEqual(hash(actual),hash(expected));keys.append(actual)
        self.assertNotEqual(*keys)