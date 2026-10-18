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

from functools import lru_cache

@lru_cache(maxsize=2)
def owned_matrix_fixture(repeat):
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
    return board,state,rules,strategy,WolfProfileResolver(rules,strategy),WolfProfileResolver(rules,strategy)

class OwnedRosterValueCutTests(unittest.TestCase):
    def check_row(self,repeat,mode,mask,target):
        board,state,rules,strategy,reference_pool,actual_pool=owned_matrix_fixture(repeat)
        before=deepcopy((board,state));groups=wolf_information_groups(state)
        info,mass,group=next((i,m,g)for i,m,g in groups if i.initial_roster==mask and tuple(a.target for a in i.attacks)==(2,))
        self.assertIn(target,board.alive);self.assertFalse(mask&(1<<(target-1)))
        law=condition_actor_state(state,lambda h:h.roles[0]==info.initial_roster)
        own_board=replace_worlds(board,law.public_roles,wolf_count=None)
        base=tuple((i,uniform_policy(tuple(t for t in board.alive if not i.initial_roster&(1<<(t-1)))
            if mode==0 or mode==1 and i.initial_roster==info.initial_roster else
            (next(t for t in board.alive if not i.initial_roster&(1<<(t-1))),))) for i,m,st in groups)
        profile=wolf_candidate_profile(base,info,target,rules=CandidateRules(board,state,(),rules,strategy))
        owned=tuple((i,policy)for i,policy in profile if i.initial_roster==info.initial_roster)
        reference_engine=FixedPublicWolfProfile(board,state,(),rules,strategy,profile,resolver=reference_pool)
        reference=InformationSetForecast.act(reference_engine,board,state,(),target,group,None)
        actual=FixedPublicWolfProfile(own_board,law,(),rules,strategy,owned,resolver=actual_pool).act(own_board,law,(),target,group,None)
        self.assertEqual(actual,reference,(repeat,info,mode,target))
        self.assertEqual((board,state),before)
        self.assertTrue(any(h.acquisitions for h in state.hypotheses))
        self.last_row=dict(repeat=repeat,mode=mode,mask=mask,target=target,value=str(actual),hypotheses=len(state.hypotheses))

# Same full matrix as the original monolithic loop: 2 rules *3 base profiles
# *2 wolf information sets *3 legal actions. Every row is independently visible.
def row_test(repeat,mode,mask,target):
    def test(self):self.check_row(repeat,mode,mask,target)
    return test
for repeat in(True,False):
    for mode in(0,1,2):
        for mask in(1,4):
            for target in(1,3,4,5):
                if not mask&(1<<(target-1)):
                    setattr(OwnedRosterValueCutTests,f'test_row_repeat_{int(repeat)}_mode_{mode}_mask_{mask}_target_{target}',row_test(repeat,mode,mask,target))
