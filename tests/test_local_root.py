import unittest,copy
from fractions import Fraction as F
import tests.test_root_guard_max as root_cases
import tests.test_guard_no_repeat as guard_cases
from werewolf.local_reuse import reuse_scope
from werewolf.model_a_public import evaluate_public_game,clear_public_cache
from werewolf.exact import Strategy
from werewolf.seer_manual import replay
from werewolf.root_secret_flow import prepare_root_entry,RootSecretEngine
from werewolf.seer_future_uniform import FuturePending
from werewolf.actor_information import WolfInformation
from werewolf.exact_renaming import canonical_key
from benchmarks.player_match_groups.local_root import LocalRootEngine


class LocalRootTests(unittest.TestCase):
    def test_guard_root_max_both_rules_exact_values_and_all_rows(self):
        for repeat in (False,True):
            game=root_cases.RootGuardMaxTests().game(repeat);before=copy.deepcopy(game)
            rules,p=replay(game);strategy=Strategy(**game['policy']);clear_public_cache()
            with reuse_scope(False):old=evaluate_public_game(game,p.board,rules,strategy,max_seconds=15)
            with reuse_scope(True):new=evaluate_public_game(game,p.board,rules,strategy,max_seconds=15)
            self.assertNotIsInstance(old,FuturePending);self.assertEqual(old,new)
            self.assertEqual(old.village_win,F(1,30))
            self.assertEqual(game,before)

    def test_candidate_profile_and_actor_certificate_remain_in_complete_key(self):
        game=root_cases.RootGuardMaxTests().game(False);rules,p=replay(game);strategy=Strategy(**game['policy'])
        branch=prepare_root_entry(game,p.board,rules,strategy)
        original=RootSecretEngine(rules,strategy);fast=LocalRootEngine(rules,strategy)
        kernel=original.public_night_policies(branch.public,branch.public_law)
        self.assertEqual(kernel,fast.public_night_policies(branch.public,branch.public_law))
        profile=tuple((WolfInformation(mask,history),policy)for(mask,history),policy in kernel.items())
        kwargs=dict(wolf_profiles=((branch.public,branch.public_law,branch.past,profile),),actor_mask=1,physical=branch.physical,target=2)
        key=canonical_key(branch.public,branch.public_law,branch.past,branch.physical_law,None,rules,strategy,**kwargs)
        self.assertIsNotNone(key)
        self.assertEqual(key,fast.canonical_payoff_key(branch.public,branch.public_law,branch.past,branch.physical_law,None,rules,strategy,**kwargs))
        self.assertGreater(fast.local_key_calls,0)
        kwargs['actor_mask']=2
        self.assertNotEqual(key,fast.canonical_payoff_key(branch.public,branch.public_law,branch.past,branch.physical_law,None,rules,strategy,**kwargs))

    def test_two_successful_guards_keep_private_histories_and_conditional_law(self):
        for repeat in (True,False):
            game=guard_cases.NoRepeatGuardTests().fixture(repeat=repeat);before=copy.deepcopy(game)
            rules,p=replay(game);strategy=Strategy(**game['policy'])
            branch=prepare_root_entry(game,p.board,rules,strategy)
            self.assertNotIsInstance(branch,FuturePending)
            self.assertTrue(all(len(h.guards)==len(h.attacks)==2 for h in branch.physical_law.hypotheses))
            with reuse_scope(False):old=evaluate_public_game(game,p.board,rules,strategy,max_seconds=15)
            with reuse_scope(True):new=evaluate_public_game(game,p.board,rules,strategy,max_seconds=15)
            self.assertNotIsInstance(old,FuturePending);self.assertEqual(old,new)
            self.assertEqual(game,before)

    def test_existing_owner_history_and_wolf_information_controls_under_local_mode(self):
        with reuse_scope(True):
            guard_cases.NoRepeatGuardTests().test_owner_table_conditions_same_law_and_unknown_previous_stays_pending()
            root_cases.RootGuardMaxTests().test_guard_owner_secret_does_not_change_public_wolf_kernel()
