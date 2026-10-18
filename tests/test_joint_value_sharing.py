import unittest,gc,weakref,sys
from dataclasses import replace,FrozenInstanceError
from fractions import Fraction as F
from types import SimpleNamespace
from werewolf.joint_value_sharing import share_joint_values,independent_joint_values,JointPoolOwnerChanged
from werewolf.seer_acquisition import Hypothesis,Acquisition
from werewolf.seer_future_uniform import TrueScanState
from werewolf.night_knowledge import WolfAttack
from werewolf.guard_effect import GuardIntent


def hypothesis(*,mass=F(1),target=3,attack=3,roles=(1,0,2,0),guards=()):
    player=next(p for p in range(1,5) if roles[2]&(1<<(p-1)))
    return Hypothesis(roles,(Acquisition(2,player,target,'black' if roles[0]&(1<<(target-1)) else 'white'),),mass,guards,(WolfAttack(1,attack),))


def law(entries,**kw):return TrueScanState(tuple(entries),((1,2,3,4),(1,2,3,4)),initial_rule='none',**kw)


class JointValueSharingTests(unittest.TestCase):
    def test_full_immutable_hypotheses_and_records_share_but_law_containers_do_not(self):
        owner=SimpleNamespace(data=object())
        with share_joint_values(owner) as pool:
            a=law((hypothesis(),));b=law((hypothesis(),))
            self.assertIsNot(a,b);self.assertEqual(a,b)
            self.assertIs(a.hypotheses[0],b.hypotheses[0])
            different_mass=hypothesis(mass=F(1,2))
            self.assertIs(different_mass.acquisitions[0],a.hypotheses[0].acquisitions[0])
            self.assertIs(different_mass.attacks[0],a.hypotheses[0].attacks[0])
            with self.assertRaises(FrozenInstanceError):a.hypotheses[0].mass=F(1,3)
            with self.assertRaises(FrozenInstanceError):a.hypotheses[0].attacks[0].target=4
        self.assertFalse(pool.records);self.assertFalse(pool.hypotheses);self.assertIsNone(pool.owner)
        self.assertEqual(a,b)

    def test_equal_role_and_seer_marginals_do_not_merge_different_joint_correlation(self):
        owner=SimpleNamespace(data=object())
        with share_joint_values(owner):
            a=law((hypothesis(mass=F(1,2),roles=(1,0,2,0)),hypothesis(mass=F(1,2),roles=(4,0,8,0),target=2)))
            b=law((hypothesis(mass=F(1,2),roles=(1,0,8,0),target=2),hypothesis(mass=F(1,2),roles=(4,0,2,0))))
        marginal=lambda s,i:{m:sum(h.mass for h in s.hypotheses if h.roles[i]==m) for m in {h.roles[i] for h in s.hypotheses}}
        self.assertEqual(marginal(a,0),marginal(b,0));self.assertEqual(marginal(a,2),marginal(b,2))
        self.assertNotEqual(a,b)
        self.assertFalse({id(h) for h in a.hypotheses}&{id(h) for h in b.hypotheses})

    def test_every_private_history_mass_and_law_metadata_remains_distinct(self):
        with share_joint_values(SimpleNamespace(data=object())) as pool:
            a=law((hypothesis(),));attack=law((hypothesis(attack=4),));scan=law((hypothesis(target=4),))
            self.assertNotEqual(a,attack);self.assertNotEqual(a,scan)
            guarded=law((hypothesis(roles=(1,0,2,4),guards=(GuardIntent(1,3,4),)),))
            other=law((hypothesis(roles=(1,0,2,4),guards=(GuardIntent(1,3,2),)),))
            self.assertNotEqual(guarded,other)
            metadata=replace(a,tracked=(2,),observed_prefix=1)
            self.assertNotEqual(a,metadata)
            self.assertIs(a.hypotheses[0],metadata.hypotheses[0])
            roster=replace(a,rosters=((1,2,3,4),(1,2,3)))
            self.assertNotEqual(a,roster)
            h1=hypothesis(mass=F(1));h2=hypothesis(mass=F(1,sys.hash_info.modulus+1))
            self.assertEqual(hash(h1),hash(h2));self.assertNotEqual(h1,h2)
            first,second=pool.joint((h1,h2));self.assertIsNot(first,second)

    def test_scope_owner_revision_and_nested_request_isolation(self):
        a=SimpleNamespace(data=object());b=SimpleNamespace(data=object());old=a.data
        with share_joint_values(a):
            first=law((hypothesis(),))
            with share_joint_values(b):second=law((hypothesis(),))
            third=law((hypothesis(),))
            self.assertIs(first.hypotheses[0],third.hypotheses[0]);self.assertIsNot(first.hypotheses[0],second.hypotheses[0])
            a.data=object()
            with self.assertRaises(JointPoolOwnerChanged):hypothesis()
            a.data=old
        with share_joint_values(a):fourth=law((hypothesis(),))
        self.assertIsNot(first.hypotheses[0],fourth.hypotheses[0])

    def test_weak_indices_do_not_retain_discarded_hypotheses_or_records(self):
        with share_joint_values(SimpleNamespace(data=object())) as pool:
            value=law((hypothesis(),));h=weakref.ref(value.hypotheses[0]);a=weakref.ref(value.hypotheses[0].acquisitions[0])
            self.assertTrue(pool.hypotheses);del value;gc.collect()
            self.assertIsNone(h());self.assertIsNone(a());self.assertFalse(pool.hypotheses);self.assertFalse(pool.records)

    def test_unshared_or_mutable_inputs_never_become_canonical_joint_values(self):
        a=law((hypothesis(),));b=law((hypothesis(),));self.assertIsNot(a.hypotheses[0],b.hypotheses[0])
        with share_joint_values(SimpleNamespace(data=object())) as pool:
            h1=hypothesis(roles=[1,0,2,0]);h2=hypothesis(roles=[1,0,2,0])
            x,y=pool.joint((h1,h2));self.assertIsNot(x,y)
            with independent_joint_values():other=law((hypothesis(),));fresh=law((hypothesis(),))
            self.assertIsNot(other.hypotheses[0],fresh.hypotheses[0])
