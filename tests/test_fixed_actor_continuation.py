import unittest
from dataclasses import asdict,replace
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.exact import Rules,Strategy
from werewolf.seer_manual import migrate_game,replay
from werewolf.seer_acquisition import from_board,normalize
from werewolf.seer_future_uniform import TrueScanState
from werewolf.actor_information import WolfInformation
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.fixed_actor_continuation import fixed_actor_value
import werewolf.fixed_actor_continuation as suffix

class FixedActorContinuationTests(unittest.TestCase):
    def fixture(self,n,repeat=True):
        policy=Strategy(day='random',night='max',fake_reports='random',disclosure_common='none')
        claims=['hunter']+['latent']*(n-1);cp={'hunter':'none'}
        game=migrate_game({'players':n,'wolves':1,'hunters':1,'mediums':0,'seers':0,
            'claims':claims,'claim_policy':cp,'policy':asdict(policy),'rules':asdict(Rules()),
            'seer_mode':'information-fixed-v1','seer_inputs':[],
            'history':[{'target':n,'claims':claims,'claim_policy':cp,'policy':asdict(policy)}]})
        rules,p=replay(game)
        rules=replace(rules,allow_repeat_guard=repeat)
        state=TrueScanState(from_board(p.board),rosters=(tuple(range(1,n+1)),))
        return p.board,state,InformationSetForecast(rules,policy)

    def test_unknown_roles_four_player_candidates_need_no_later_max(self):
        b,s,e=self.fixture(4)
        self.assertEqual(fixed_actor_value(b,s,e,info=WolfInformation(1),target=2),F(1,18))
        self.assertEqual(fixed_actor_value(b,s,e,info=WolfInformation(1),target=3),F(1,18))
        self.assertEqual(fixed_actor_value(b,s,e,info=WolfInformation(2),target=1),0)
        self.assertEqual(fixed_actor_value(b,s,e,info=WolfInformation(2),target=3),F(1,6))

    def test_known_actor_six_player_suffix_really_evaluates_later_max(self):
        for repeat,expected in ((True,F(3,10)),(False,F(43,144))):
            b,s,e=self.fixture(6,repeat)
            # W2 knows H1 from PUBLIC CO; all other roles are citizens.
            own=WolfInformation(2).condition_public(s)
            self.assertEqual(len({h.roles for h in own.hypotheses}),1)
            with patch.object(suffix,'optimal_targets',wraps=suffix.optimal_targets) as choices:
                self.assertEqual(fixed_actor_value(b,s,e,info=WolfInformation(2),target=3),expected)
                self.assertGreater(choices.call_count,0)
            self.assertEqual(fixed_actor_value(b,s,e,info=WolfInformation(2),target=1),F(1,4))
            self.assertIsNone(fixed_actor_value(b,s,e,info=WolfInformation(1),target=2))

    def test_viewer_restriction_and_other_public_decisions_are_not_used(self):
        b,s,e=self.fixture(6)
        private=WolfInformation(2).condition_public(s)
        with self.assertRaisesRegex(ValueError,'Complete public input'):
            fixed_actor_value(b,private,e,info=WolfInformation(2),target=3)
        e.strategy=replace(e.strategy,day='max')
        self.assertIsNone(fixed_actor_value(b,s,e,info=WolfInformation(2),target=3))

    def test_unknown_role_payoff_weights_cannot_be_used_as_actor_belief(self):
        b,s,e=self.fixture(6)
        own=WolfInformation(1).condition_public(s)
        altered=replace(own,hypotheses=normalize(tuple(replace(h,mass=F(1,2) if i==0 else F(1,8)) for i,h in enumerate(own.hypotheses))))
        self.assertIsNone(fixed_actor_value(b,s,e,info=WolfInformation(1),target=2,measure=altered,allow_actor_only=True))
        self.assertIsNone(fixed_actor_value(b,s,e,info=WolfInformation(1),target=2))

    def test_completed_candidate_reuse_keeps_dependency_cut_modes_separate(self):
        b,s,e=self.fixture(6)
        with patch.object(suffix,'physical_actor_outcomes',wraps=suffix.physical_actor_outcomes) as physical:
            proposal=fixed_actor_value(b,s,e,info=WolfInformation(1),target=2,allow_actor_only=True)
            self.assertIsNotNone(proposal)
            physical.reset_mock()
            self.assertEqual(fixed_actor_value(b,s,e,info=WolfInformation(1),target=2,allow_actor_only=True),proposal)
            physical.assert_not_called()
        self.assertIsNone(fixed_actor_value(b,s,e,info=WolfInformation(1),target=2))
