"""Nonexchangeable shared history flow with a hunter uncertain even to wolves."""
import copy
import unittest
from dataclasses import replace
from fractions import Fraction as F

from werewolf.action_flow import resolve_action
from werewolf.dawn import observe
from werewolf.exact import initial_board,replace_worlds,Progress,Rules,Strategy,advance
from werewolf.guard_effect import GuardIntent
from werewolf.guard_history_prior import seed_history,hero_deducible
from werewolf.guard_model import condition_guard_observation
from werewolf.guard_view_forecast import guard_forecast
from werewolf.information_set_forecast import InformationSetForecast,information_forecast
from werewolf.model_a_public import public_forecast
from werewolf.night_knowledge import WolfAttack
from werewolf.public_prior import prepare_public_prior


class SharedGuardHistoryTests(unittest.TestCase):
    rules=Rules(initial_seer='none')
    strategy=Strategy()

    def fixture(self):
        b=replace_worlds(initial_board(6,1,0,0,1),
                        ((1,0,0,2,F(3,4)),(1,0,0,4,F(1,4))))
        progress=Progress.initial(b);previous=Strategy('random','random')
        for victim in (6,5):
            progress=advance(progress,victim,self.rules,previous)
            progress=observe(progress,{'deaths':[]},self.rules,previous)
        b=advance(progress,4,self.rules,previous).board
        state,_=prepare_public_prior({},b,self.rules,track_live_seers=False)
        entries=tuple(replace(h,
                      guards=tuple(GuardIntent(n,2 if h.roles[3]==2 else 3,4) for n in (1,2)),
                      attacks=tuple(WolfAttack(n,4) for n in (1,2))) for h in state.hypotheses)
        return b,replace(state,hypotheses=entries)

    def test_two_night_records_enable_uncertain_hunter_max_with_hand_values(self):
        b,state=self.fixture();before=copy.deepcopy((b,state))
        self.assertEqual((b.day,b.phase,b.alive),(3,'night',(1,2,3)))
        self.assertFalse(hero_deducible(b))
        self.assertEqual(seed_history(b,state),state)
        result=public_forecast(b,state,(),self.rules,self.strategy)
        # A success is followed by executing the publicly known wolf. A death
        # leaves wolf parity. Biting 2 can only be blocked by hunter 3 guarding
        # 2: 1/4 * 1/2. Biting 3 instead gives 3/4 * 1/2.
        self.assertEqual(result.village_win,F(1,8))
        self.assertEqual(dict(result.action_values),{2:F(1,8),3:F(3,8)})
        engine=InformationSetForecast(self.rules,self.strategy)
        self.assertEqual(engine.wolf_policy(b,state,(),1,state.hypotheses[0].attacks),((2,F(1)),))
        self.assertEqual((b,state),before)

    def test_terminal_flow_keeps_records_and_model_a_ignores_attack_likelihood(self):
        b,state=self.fixture();engine=InformationSetForecast(self.rules,self.strategy)
        _,outcomes=resolve_action(b,(state,(),state,None,b),2,engine.action_policy)
        success=next(o for o in outcomes if o.board.alive==b.alive)
        self.assertEqual(success.probability,F(1,8))
        self.assertEqual(success.context.public.role_probability(2,'hunter'),F(3,4))
        self.assertEqual(success.board.role_probability(3,'hunter'),1)
        self.assertEqual(success.context.public_state.public_roles,
                         tuple(sorted(success.context.public.worlds)))
        self.assertTrue(all(len(h.guards)==len(h.attacks)==2
                            for h in success.context.public_state.hypotheses))
        for o in outcomes:
            self.assertTrue(all(len(h.guards)==len(h.attacks)==3
                                for h in o.context.private.hypotheses))
            self.assertTrue(all(h.attacks[-1]==WolfAttack(3,2)
                                for h in o.context.private.hypotheses))
        # There is no feasible guard action for hunter 2 to stop attack 2.
        # Therefore a policy-only success ledger cannot preserve that world's
        # positive Model A public mass; do not silently invent such a record.
        self.assertEqual(condition_guard_observation(b,(),self.rules).worlds,b.worlds)

    def test_hunter_view_cannot_change_public_wolf_policy(self):
        b,state=self.fixture();before=copy.deepcopy((b,state))
        engine=InformationSetForecast(self.rules,self.strategy)
        public_policy=engine.wolf_policy(b,state,(),1,state.hypotheses[0].attacks)
        for actor,expected in ((2,{1:F(),3:F()}),(3,{1:F(),2:F(1)})):
            worlds=tuple(w for w in b.worlds if w[3]==1<<(actor-1))
            total=sum(w[-1] for w in worlds)
            private=replace_worlds(b,tuple((*w[:-1],w[-1]/total) for w in worlds))
            guards=tuple(GuardIntent(n,actor,4) for n in (1,2))
            values,_=guard_forecast(b,actor,private,state,(),self.rules,self.strategy,guards=guards)
            self.assertEqual(values,expected)
        self.assertEqual(engine.wolf_policy(b,state,(),1,state.hypotheses[0].attacks),public_policy)
        self.assertEqual((b,state),before)

    def test_missing_or_partial_history_cannot_become_a_complete_information_set(self):
        from werewolf.seer_future_uniform import FuturePending
        b,state=self.fixture()
        for nights in (0,1):
            partial=replace(state,hypotheses=tuple(replace(h,guards=h.guards[:nights],
                           attacks=h.attacks[:nights]) for h in state.hypotheses))
            self.assertEqual(seed_history(b,partial),partial)
            result=public_forecast(b,partial,(),self.rules,self.strategy)
            self.assertEqual(result,FuturePending('guard_hidden_attack_max_unimplemented'))

    def test_observer_without_attack_knowledge_keeps_the_public_latent_ledger(self):
        b,state=self.fixture();before=copy.deepcopy((b,state))
        # A viewer with no attack evidence averages over the public mixture.
        # Empty viewer input does not mean every world had an empty ledger.
        result=information_forecast(b,state,(),self.rules,self.strategy,
                                    observer=lambda h,s:True)
        self.assertEqual(result,F(1,8))
        known=information_forecast(b,state,(),self.rules,self.strategy,mask=1,
                                   private_attacks=(WolfAttack(1,4),WolfAttack(2,4)))
        self.assertEqual(dict(known),{2:F(1,8),3:F(3,8)})
        self.assertEqual((b,state),before)

    def test_record_merge_does_not_hide_duplicate_owner_actions(self):
        b,state=self.fixture()
        with self.assertRaisesRegex(ValueError,'One personal action per night'):
            information_forecast(b,state,(),self.rules,self.strategy,mask=1,
                                 private_attacks=(WolfAttack(1,4),WolfAttack(1,4),WolfAttack(2,4)))


