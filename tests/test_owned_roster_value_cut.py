import unittest
from dataclasses import replace
from fractions import Fraction as F
from copy import deepcopy
from tests import test_root_guard_max as fixtures
from werewolf.exact import Strategy,replace_worlds
from werewolf.seer_manual import replay,migrate_game
from werewolf.root_secret_flow import prepare_root_entry,step_root_action
from werewolf.seer_acquisition import normalize,public_worlds
from werewolf.actor_information import condition_actor_state,wolf_information_groups
from werewolf.wolf_profile_certificate import FixedPublicWolfProfile,WolfProfileResolver,wolf_candidate_profile
from werewolf.candidate_policy import CandidateRules
from werewolf.policy_choice import uniform_policy
from werewolf.information_set_forecast import InformationSetForecast

class OwnedRosterValueCutTests(unittest.TestCase):
    def test_conditional_value_equals_unreduced_public_flow_with_live_hidden_seer(self):
        for repeat in (True,False):
            g=fixtures.RootGuardMaxTests().game(repeat,players=6)
            g.update(seers=1,mediums=1,claims=['latent']*6)
            g['history'][0]['claims']=['latent']*6
            g=migrate_game(g);rules,p=replay(g);strategy=Strategy(**g['policy'])
            root=prepare_root_entry(g,p.board,rules,strategy);old=replace(strategy,night='random')
            morning=next(b for q,b in step_root_action(root,2,rules,old) if len(b.public.alive)==5)
            later=next(b for q,b in step_root_action(morning,2,rules,old) if b.public.phase=='night')
            selected=tuple(h for h in later.public_law.hypotheses if h.roles[0] in (1,4) and
                h.roles[3] in (8,16) and h.roles[2] in (8,16) and h.roles[1]==32)
            state=replace(later.public_law,hypotheses=normalize(selected))
            board=replace_worlds(later.public,public_worlds(state.hypotheses),wolf_count=None)
            before=deepcopy((board,state));groups=wolf_information_groups(state)
            candidates=CandidateRules(board,state,(),rules,strategy)
            for info,mass,group in groups:
                if tuple(a.target for a in info.attacks)!=(2,):continue
                law=condition_actor_state(state,lambda h:h.roles[0]==info.initial_roster)
                own_board=replace_worlds(board,law.public_roles,wolf_count=None)
                for mode in (0,1,2):
                    base=tuple((i,uniform_policy(tuple(t for t in board.alive if not i.initial_roster&(1<<(t-1)))
                        if mode==0 or mode==1 and i.initial_roster==info.initial_roster else
                        (next(t for t in board.alive if not i.initial_roster&(1<<(t-1))),))) for i,m,st in groups)
                    for target in board.alive:
                        if info.initial_roster&(1<<(target-1)):continue
                        profile=wolf_candidate_profile(base,info,target,rules=candidates)
                        owned=tuple((i,policy) for i,policy in profile if i.initial_roster==info.initial_roster)
                        reference_engine=FixedPublicWolfProfile(board,state,(),rules,strategy,profile,
                            resolver=WolfProfileResolver(rules,strategy))
                        reference=InformationSetForecast.act(reference_engine,board,state,(),target,group,None)
                        actual=FixedPublicWolfProfile(own_board,law,(),rules,strategy,owned,
                            resolver=WolfProfileResolver(rules,strategy)).act(own_board,law,(),target,group,None)
                        self.assertEqual(actual,reference,(repeat,info,mode,target))
            self.assertEqual((board,state),before)
            self.assertTrue(any(h.acquisitions for h in state.hypotheses))
