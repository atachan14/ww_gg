"""Supplied information-set kernels: public mass and physical owners differ."""
import copy
import unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.guard_effect import GuardIntent
from werewolf.guard_history_mixture import enumerate_guard_history_mixture
from werewolf.night_knowledge import WolfAttack
from werewolf.seer_acquisition import Hypothesis,normalize
from werewolf.seer_future_uniform import TrueScanState,FuturePending


class GuardHistoryMixtureTests(unittest.TestCase):
    alive=(1,2,3,4)

    def source(self):
        return TrueScanState(tuple(Hypothesis((1,0,0,1<<(actor-1)),(),mass)
                             for actor,mass in ((2,F(1,2)),(3,F(1,3)),(4,F(1,6)))),
                             (self.alive,self.alive),initial_rule='none',tracked=(),observed_prefix=2)

    def policy(self):return {(1,()):((2,F(1,2)),(3,F(1,3)),(4,F(1,6)))}

    def test_supported_kernel_keeps_public_mass_and_exact_conditional_histories(self):
        source=self.source();policy=self.policy();before=copy.deepcopy((source,policy))
        mix=enumerate_guard_history_mixture(source,source.public_roles,1,self.alive,policy)
        self.assertEqual(mix.public.public_roles,source.public_roles)
        self.assertEqual(mix.physical_mass,F(11,54))
        self.assertEqual(mix.zero_support_roles,())
        self.assertEqual(dict(mix.role_support),{(1,0,0,2):F(1,6),(1,0,0,4):F(2,9),(1,0,0,8):F(5,18)})
        masses={(h.roles[3],h.attacks[0].target):h.mass for h in mix.public.hypotheses}
        self.assertEqual(masses,{(2,3):F(1,3),(2,4):F(1,6),(4,2):F(1,4),
                                 (4,4):F(1,12),(8,2):F(1,10),(8,3):F(1,15)})
        self.assertEqual(dict((w[3],w[-1]) for w in mix.physical.public_roles),
                         {2:F(9,22),4:F(4,11),8:F(5,22)})
        self.assertEqual((source,policy),before)

    def test_owner_views_use_physical_law_not_public_world_renormalization(self):
        source=self.source()
        mix=enumerate_guard_history_mixture(source,source.public_roles,1,self.alive,self.policy())
        before=copy.deepcopy(mix)
        wolf=mix.wolf_view(1,(WolfAttack(1,2),))
        self.assertEqual(dict((w[3],w[-1]) for w in wolf.public_roles),{4:F(2,3),8:F(1,3)})
        # Directly filtering the public per-world mixture would give 5/7 : 2/7.
        public=normalize(tuple(h for h in mix.public.hypotheses if h.attacks==(WolfAttack(1,2),)))
        self.assertEqual({h.roles[3]:h.mass for h in public},{4:F(5,7),8:F(2,7)})
        hunter=mix.hunter_view(2,(GuardIntent(1,2,3),))
        self.assertTrue(all(h.roles[3]==2 and h.attacks==(WolfAttack(1,3),) for h in hunter.hypotheses))
        self.assertEqual(mix,before)

    def test_zero_support_is_explicit_and_no_world_or_history_is_fabricated(self):
        source=self.source()
        mix=enumerate_guard_history_mixture(source,source.public_roles,1,self.alive,{(1,()):((4,F(1)),)})
        self.assertEqual(mix.public,FuturePending('guard_public_history_zero_support'))
        self.assertEqual(mix.role_prior,source.public_roles)
        self.assertEqual(mix.zero_support_roles,((1,0,0,8),))
        self.assertEqual(mix.physical_mass,F(5,18))
        self.assertTrue(all(h.roles[3]!=8 and h.attacks==(WolfAttack(1,4),) for h in mix.physical.hypotheses))
        self.assertEqual(mix.hunter_view(4,(GuardIntent(1,4,2),)),
                         FuturePending('guard_private_history_zero_support'))

    def test_policy_has_to_be_supplied_for_wolf_information_not_guard_truth(self):
        source=self.source()
        with self.assertRaisesRegex(ValueError,'Missing explicit'):
            enumerate_guard_history_mixture(source,source.public_roles,1,self.alive,{})
        with self.assertRaisesRegex(ValueError,'legal'):
            enumerate_guard_history_mixture(source,source.public_roles,1,self.alive,{(1,()):((1,F(1)),)})
        with self.assertRaisesRegex(ValueError,'Normalized'):
            enumerate_guard_history_mixture(source,source.public_roles,1,self.alive,{(1,()):((2,F(1,2)),)})

    def test_existing_ledger_selects_history_key_and_original_rosters_are_preserved(self):
        source=self.source()
        source=replace(source,rosters=(self.alive,self.alive,self.alive),observed_prefix=3,
                       hypotheses=tuple(replace(h,guards=(GuardIntent(1,h.roles[3].bit_length(),
                                          3 if h.roles[3]==2 else 2),),
                                          attacks=(WolfAttack(1,3 if h.roles[3]==2 else 2),))
                                        for h in source.hypotheses))
        policy={(1,(WolfAttack(1,3),)):((3,F(1,2)),(4,F(1,2))),
                (1,(WolfAttack(1,2),)):((2,F(1,2)),(4,F(1,2)))}
        mix=enumerate_guard_history_mixture(source,source.public_roles,2,self.alive,policy)
        self.assertEqual(mix.public.public_roles,source.public_roles)
        self.assertTrue(all(len(h.guards)==len(h.attacks)==2 for h in mix.public.hypotheses))
        self.assertEqual(mix.public.rosters,source.rosters)
        self.assertTrue(all(h.attacks[1].target in dict(policy[(h.roles[0],h.attacks[:1])])
                            for h in mix.physical.hypotheses))

    def test_public_prior_is_independent_of_physical_parent_mass(self):
        source=self.source()
        physical=replace(source,hypotheses=tuple(replace(h,mass=q) for h,q in
                         zip(source.hypotheses,(F(1,3),F(1,3),F(1,3)))))
        mix=enumerate_guard_history_mixture(physical,source.public_roles,1,self.alive,self.policy())
        self.assertEqual(mix.public.public_roles,source.public_roles)
        self.assertNotEqual(mix.physical.public_roles,source.public_roles)

    def test_same_enumeration_handles_six_alive_without_population_exception(self):
        alive=(1,2,3,4,5,6)
        source=replace(self.source(),rosters=(alive,alive))
        mix=enumerate_guard_history_mixture(source,source.public_roles,1,alive,self.policy())
        self.assertEqual(mix.public.public_roles,source.public_roles)
        self.assertEqual(mix.physical_mass,F(11,90))
        self.assertEqual(len(mix.public.hypotheses),6)

    def test_death_observation_enumerates_only_matching_unblocked_attacks(self):
        source=self.source()
        prior=tuple((*w[:-1],q) for w,q in zip(source.public_roles,(F(3,5),F(4,15),F(2,15))))
        mix=enumerate_guard_history_mixture(source,prior,1,self.alive,
                                           self.policy(),deaths=(2,))
        self.assertEqual(mix.public.public_roles,prior)
        self.assertEqual(mix.physical.public_roles,prior)
        self.assertEqual(mix.physical_mass,F(5,12))
        self.assertTrue(all(h.attacks==(WolfAttack(1,2),) and h.guards[0].target!=2
                            for h in mix.physical.hypotheses))
