import copy,unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.actor_information import WolfInformation,wolf_information_groups,condition_actor_state
from werewolf.night_knowledge import WolfAttack
from werewolf.guard_effect import GuardIntent
from werewolf.seer_acquisition import Hypothesis,normalize,Acquisition
from werewolf.seer_future_uniform import TrueScanState
from werewolf.exact import initial_board,Rules,Strategy,replace_worlds,action_outcomes
from werewolf.public_prior import prepare_public_prior
from werewolf.information_set_forecast import InformationSetForecast

class ActorInformationTests(unittest.TestCase):
    def mixed_state(self):
        return TrueScanState((
            Hypothesis((1,2,4,8),(Acquisition(1,3,5,'white'),),F(1,4),
                       (GuardIntent(1,4,5),),(WolfAttack(1,5),)),
            Hypothesis((1,2,4,8),(Acquisition(1,3,4,'white'),),F(3,4),
                       (GuardIntent(1,4,3),),(WolfAttack(1,5),))),
            ((1,2,3,4,5),)*3,initial_rule='normal',tracked=(3,),observed_prefix=3)

    def test_seer_condition_preserves_other_owners_and_public_source(self):
        source=self.mixed_state();before=copy.deepcopy(source)
        known=Acquisition(1,3,5,'white')
        own=condition_actor_state(source,lambda h:known in h.acquisitions)
        self.assertEqual(own.hypotheses,(replace(source.hypotheses[0],mass=F(1)),))
        self.assertEqual((own.rosters,own.initial_rule,own.tracked,own.observed_prefix),
                         (source.rosters,source.initial_rule,source.tracked,source.observed_prefix))
        self.assertEqual(source,before)

    def test_guard_evidence_merges_without_dropping_scans_or_attacks(self):
        source=self.mixed_state();known=(GuardIntent(2,4,5),)
        own=condition_actor_state(source,lambda h:True,guards=known)
        for h,before in zip(own.hypotheses,sorted(source.hypotheses,key=lambda h:h.acquisitions)):
            self.assertEqual(h.guards,before.guards+known)
            self.assertEqual((h.roles,h.acquisitions,h.attacks,h.mass),
                             (before.roles,before.acquisitions,before.attacks,before.mass))

    def test_medium_and_villager_conditions_do_not_invent_private_histories(self):
        source=self.mixed_state()
        for compatible in (lambda h:bool(h.roles[1]&2),
                           lambda h:not any(mask&16 for mask in h.roles)):
            own=condition_actor_state(source,compatible)
            self.assertEqual(own,replace(source,hypotheses=normalize(source.hypotheses)))
        with self.assertRaisesRegex(ValueError,'No compatible'):
            condition_actor_state(source,lambda h:False)

    def test_guard_truth_is_not_an_information_key_and_mass_is_aggregated(self):
        alive=(1,2,3,4)
        state=TrueScanState((Hypothesis((1,0,0,2),(),F(1,4),(GuardIntent(1,2,4),),(WolfAttack(1,4),)),
                             Hypothesis((1,0,0,4),(),F(1,2),(GuardIntent(1,3,4),),(WolfAttack(1,4),)),
                             Hypothesis((2,0,0,4),(),F(1,4),(GuardIntent(1,3,4),),(WolfAttack(1,4),))),
                             (alive,alive),initial_rule='none',tracked=(),observed_prefix=2)
        before=copy.deepcopy(state);groups=wolf_information_groups(state)
        self.assertEqual(len(groups),2)
        info,mass,law=groups[0]
        self.assertEqual(info,WolfInformation(1,(WolfAttack(1,4),)))
        self.assertEqual(mass,F(3,4));self.assertEqual(len(law.hypotheses),2)
        self.assertEqual(sum(mass for _,mass,_ in groups),1)
        self.assertEqual(state,before)

    def test_known_records_are_not_shortened_to_public_prefix(self):
        alive=(1,2,3,4)
        state=TrueScanState((Hypothesis((1,0,0,2),(),F(1),
                             (GuardIntent(1,2,4),GuardIntent(2,2,4)),(WolfAttack(1,4),)),),
                             (alive,alive,alive),initial_rule='none',tracked=(),observed_prefix=3)
        info=WolfInformation(1,(WolfAttack(1,4),WolfAttack(2,4)))
        own=info.condition_public(state)
        self.assertEqual(own.hypotheses[0].attacks,info.attacks)
        self.assertEqual(own.hypotheses[0].guards,state.hypotheses[0].guards)
        self.assertEqual(len(state.hypotheses[0].attacks),1)

    def test_roster_keeps_dead_teammate_and_has_one_common_policy(self):
        seed=replace_worlds(initial_board(5,2),((3,0,0,0,F(1)),))
        b=next(o.board for o in action_outcomes(seed,1,Rules(),Strategy()) if o.board.winner is None)
        s,_=prepare_public_prior({},b,Rules(),track_live_seers=False)
        info,mass,own=wolf_information_groups(s)[0]
        self.assertEqual(info.initial_roster,3);self.assertEqual(mass,1)
        e=InformationSetForecast(Rules(),Strategy('random','random'))
        self.assertEqual(e.wolf_policy(b,s,(),info.initial_roster,info.attacks),
                         ((3,F(1,3)),(4,F(1,3)),(5,F(1,3))))

    def test_viewer_role_restriction_cannot_replace_public_policy_source(self):
        b=initial_board(5,1,0,0,1);s,_=prepare_public_prior({},b,Rules(),track_live_seers=False)
        e=InformationSetForecast(Rules(),Strategy())
        private=replace(s,hypotheses=normalize(tuple(h for h in s.hypotheses if h.roles[3]==2)))
        with self.assertRaisesRegex(ValueError,'public role prior'):
            e.wolf_policy(b,private,(),1)
        self.assertEqual(e.policies,{})

    def test_incompatible_and_duplicate_owner_records_are_not_fabricated(self):
        alive=(1,2,3)
        state=TrueScanState((Hypothesis((1,0,0,2),(),F(1),(),(WolfAttack(1,3),)),),
                             (alive,alive),initial_rule='none',tracked=(),observed_prefix=2)
        with self.assertRaisesRegex(ValueError,'outside public support'):
            WolfInformation(1,(WolfAttack(1,2),)).condition_public(state)
        with self.assertRaisesRegex(ValueError,'One personal action'):
            WolfInformation(1,(WolfAttack(1,2),WolfAttack(1,2)))
