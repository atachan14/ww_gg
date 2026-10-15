import unittest
from dataclasses import replace
from copy import deepcopy
from tests import test_root_guard_max as fixtures
from werewolf.seer_manual import migrate_game,replay
from werewolf.exact import Strategy
from werewolf.root_secret_flow import prepare_root_entry,step_root_action,RootSecretEngine
from werewolf.actor_information import WolfInformation
from werewolf.night_knowledge import WolfAttack
from werewolf.fixed_actor_continuation import physical_actor_outcomes
from werewolf.terminal_followup import terminal_physical_measures,terminal_physical_input

class TerminalPhysicalMeasureTests(unittest.TestCase):
    def test_complete_scan_expansion_and_terminal_measure_have_identical_physical_law(self):
        for repeat in (True,False):
            g=fixtures.RootGuardMaxTests().game(repeat,players=5)
            g.update(seers=1,claims=['latent']*5);g['history'][0]['claims']=['latent']*5
            g=migrate_game(g);rules,p=replay(g);strategy=Strategy(**g['policy'])
            root=prepare_root_entry(g,p.board,rules,strategy);past=replace(strategy,night='random')
            morning=next(b for q,b in step_root_action(root,2,rules,past) if len(b.public.alive)==4)
            for executed in (2,3):
                later=next(b for q,b in step_root_action(morning,executed,rules,past) if b.public.phase=='night')
                state=WolfInformation(1,(WolfAttack(1,2),)).condition_public(later.public_law)
                before=deepcopy((later,state));engine=RootSecretEngine(rules,strategy)
                self.assertTrue(any(h.roles[2]&later.public.alive_mask for h in state.hypotheses))
                def signature(outcomes):
                    return tuple((q,b.alive,b.day,b.phase,b.history,b.winner,b.worlds,joint.public_roles)
                                 for q,b,joint in outcomes)
                compiled=terminal_physical_input(state)
                self.assertIs(compiled.source,state)
                self.assertEqual(sum(mass for h,mass in compiled.entries),sum(h.mass for h in state.hypotheses))
                self.assertLess(len(compiled.entries),len(state.hypotheses))
                for target in later.public.alive:
                    if target==1:continue
                    actual=terminal_physical_measures(later.public,state,engine,target,physical_input=compiled)
                    expected=physical_actor_outcomes(later.public,state,engine,target)
                    self.assertEqual(signature(actual),signature(expected))
                self.assertEqual((later,state),before)
                claims=list(later.public.claims);claims[later.public.alive[-1]-1]='seer'
                reporting=RootSecretEngine(rules,replace(strategy,disclosure_common='all'))
                self.assertIsNone(terminal_physical_measures(replace(later.public,claims=tuple(claims)),
                                                           state,reporting,later.public.alive[-1]))
