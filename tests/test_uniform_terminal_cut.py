import unittest
from copy import deepcopy
from dataclasses import replace
from tests import test_root_guard_max as fixtures
from werewolf.seer_manual import migrate_game,replay
from werewolf.exact import Strategy,legal_targets,replace_worlds,forced_action_worlds
from werewolf.root_secret_flow import prepare_root_entry,step_root_action,RootSecretEngine
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.actor_information import WolfInformation
from werewolf.night_knowledge import WolfAttack
from werewolf.terminal_followup import uniform_terminal_action_value
from werewolf.belief_projection import project_private


class Unreduced(RootSecretEngine):
    def act(self,*args,**kwargs):return InformationSetForecast.act(self,*args,**kwargs)
    def solve(self,*args,**kwargs):return InformationSetForecast.solve(self,*args,**kwargs)


class UniformTerminalCutTests(unittest.TestCase):
    def fixture(self,repeat,executed=2):
        g=fixtures.RootGuardMaxTests().game(repeat,players=5,night='random')
        g.update(seers=1,claims=['latent']*5);g['history'][0]['claims']=['latent']*5
        g=migrate_game(g);rules,p=replay(g);strategy=Strategy(**g['policy'])
        root=prepare_root_entry(g,p.board,rules,strategy)
        morning=next(b for q,b in step_root_action(root,2,rules,strategy) if len(b.public.alive)==4)
        later=next(b for q,b in step_root_action(morning,executed,rules,strategy) if b.public.phase=='night')
        return rules,strategy,later

    def test_uniform_night_complete_common_flow_matches_with_full_public_and_owned_histories(self):
        for repeat in (True,False):
            for executed in (2,3):
                rules,strategy,later=self.fixture(repeat,executed)
                b,s=later.public,later.public_law
                owner=WolfInformation(1,(WolfAttack(1,2),)).condition_public(s)
                before=deepcopy((later,owner))
                engine=RootSecretEngine(rules,strategy);reference=Unreduced(rules,strategy)
                for private in (s,owner,later.physical_law):
                    physical=replace_worlds(b,private.public_roles,wolf_count=None)
                    for target in legal_targets(physical,rules,strategy):
                        forced=replace_worlds(physical,forced_action_worlds(physical,target,rules,strategy))
                        measure=project_private(private,forced,marginalize_private=False)
                        actual=uniform_terminal_action_value(b,s,measure,engine,target,physical=forced)
                        self.assertIsNotNone(actual)
                        self.assertEqual(actual,reference.act(b,s,(),target,measure,None,physical=forced))
                self.assertEqual((later,owner),before)

    def test_terminal_day_full_observation_history_matches_unreduced_execution(self):
        for repeat in (True,False):
            rules,strategy,later=self.fixture(repeat)
            morning=next(b for q,b in step_root_action(later,3,rules,strategy)
                         if b.public.winner is None and len(b.public.alive)==3)
            b,s=morning.public,morning.public_law
            engine=RootSecretEngine(rules,strategy);reference=Unreduced(rules,strategy)
            for private in (s,morning.physical_law):
                physical=replace_worlds(b,private.public_roles,wolf_count=None)
                for target in b.alive:
                    actual=uniform_terminal_action_value(b,s,private,engine,target,physical=physical)
                    self.assertEqual(actual,reference.act(b,s,(),target,private,None,physical=physical))

    def test_reporting_observer_and_max_night_keep_the_ordinary_path(self):
        rules,strategy,later=self.fixture(True);b,s=later.public,later.public_law
        target=b.alive[-1];engine=RootSecretEngine(rules,strategy)
        self.assertIsNone(uniform_terminal_action_value(b,s,s,engine,target,observer=object()))
        maximum=RootSecretEngine(rules,replace(strategy,night='max'))
        self.assertIsNone(uniform_terminal_action_value(b,s,s,maximum,target))
        claims=list(b.claims);claims[b.alive[-1]-1]='seer'
        reporting=RootSecretEngine(rules,replace(strategy,disclosure_common='all'))
        self.assertIsNone(uniform_terminal_action_value(replace(b,claims=tuple(claims)),s,s,reporting,target))
