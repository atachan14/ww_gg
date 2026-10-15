import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from tests import test_root_guard_max as fixtures
from werewolf.seer_manual import replay
from werewolf.exact import Strategy
from werewolf.root_secret_flow import prepare_root_entry
from werewolf.actor_information import wolf_information_groups
from werewolf.policy_choice import uniform_policy
from werewolf.wolf_profile_certificate import WolfProfileResolver,FixedPublicWolfProfile
import werewolf.guard_model as guard


class PublicSupportCacheTests(unittest.TestCase):
    def test_gj_hidden_bite_reuses_full_joint_law_but_changed_policy_does_not(self):
        for repeat in (True,False):
            g=fixtures.RootGuardMaxTests().game(repeat,players=5)
            rules,p=replay(g);strategy=Strategy(**g['policy'])
            root=prepare_root_entry(g,p.board,rules,strategy);b,s=root.public,root.public_law
            profile=tuple((i,uniform_policy(tuple(t for t in b.alive if not i.initial_roster&(1<<(t-1)))))
                          for i,mass,group in wolf_information_groups(s))
            resolver=WolfProfileResolver(rules,strategy)
            engine=FixedPublicWolfProfile(b,s,(),rules,strategy,profile,resolver=resolver)
            state=engine.acquire(b,s)
            day=replace(guard.condition_guard_observation(b,(),rules,state=state),day=b.day+1,phase='day')
            kernel={(i.initial_roster,i.attacks):row for i,row in profile}
            reference=guard._public_guard_branch_law(b,state,day,2,True,engine,policies=kernel)
            with patch.object(guard,'_public_guard_branch_law',wraps=guard._public_guard_branch_law) as generate:
                first=guard.public_guard_branch_law(b,state,day,2,True,engine,policies=kernel)
                second=guard.public_guard_branch_law(b,state,day,3,True,engine,policies=kernel)
                self.assertEqual(first,reference);self.assertEqual(second,reference)
                self.assertEqual(generate.call_count,1)
                changed=dict(kernel);info,row=profile[0]
                changed[info.initial_roster,info.attacks]=((row[-1][0],F(1)),)
                actual=guard.public_guard_branch_law(b,state,day,2,True,engine,policies=changed)
                self.assertEqual(generate.call_count,2)
            expected=guard._public_guard_branch_law(b,state,day,2,True,engine,policies=changed)
            self.assertEqual(actual,expected)
            self.assertNotEqual(first[1],actual[1])
            self.assertEqual(resolver.support_stats,{'calls':3,'hits':1})

    def test_same_role_marginal_does_not_merge_different_secret_history_mixtures(self):
        from werewolf.seer_manual import migrate_game
        from werewolf.seer_acquisition import normalize
        g=fixtures.RootGuardMaxTests().game(players=5)
        g.update(seers=1,claims=['latent']*5);g['history'][0]['claims']=['latent']*5
        g=migrate_game(g);rules,p=replay(g);strategy=Strategy(**g['policy'])
        root=prepare_root_entry(g,p.board,rules,strategy);b,s=root.public,root.public_law
        profile=tuple((i,uniform_policy(tuple(t for t in b.alive if not i.initial_roster&(1<<(t-1)))))
                      for i,mass,group in wolf_information_groups(s))
        resolver=WolfProfileResolver(rules,strategy)
        engine=FixedPublicWolfProfile(b,s,(),rules,strategy,profile,resolver=resolver)
        state=engine.acquire(b,s)
        day=replace(guard.condition_guard_observation(b,(),rules,state=state),day=b.day+1,phase='day')
        kernel={(i.initial_roster,i.attacks):row for i,row in profile}
        role_mass={w[:-1]:w[-1] for w in state.public_roles};totals={}
        def factor(h):return 2 if any(a.target==3 for a in h.acquisitions) else 1
        for h in state.hypotheses:totals[h.roles]=totals.get(h.roles,F())+h.mass*factor(h)
        changed=replace(state,hypotheses=normalize(tuple(replace(h,
            mass=role_mass[h.roles]*h.mass*factor(h)/totals[h.roles]) for h in state.hypotheses)))
        self.assertEqual(changed.public_roles,state.public_roles);self.assertNotEqual(changed,state)
        first=guard.public_guard_branch_law(b,state,day,2,True,engine,policies=kernel)
        actual=guard.public_guard_branch_law(b,changed,day,2,True,engine,policies=kernel)
        expected=guard._public_guard_branch_law(b,changed,day,2,True,engine,policies=kernel)
        self.assertEqual(actual,expected);self.assertNotEqual(first[1],actual[1])
        self.assertEqual(resolver.support_stats,{'calls':2,'hits':0})
