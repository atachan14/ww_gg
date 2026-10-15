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

    def test_observed_independent_product_matches_original_cartesian_generation(self):
        from tests import test_uniform_terminal_cut as terminal_fixtures
        from werewolf.actor_information import wolf_information_keys
        from werewolf.seer_acquisition import Hypothesis
        from werewolf.guard_effect import GuardIntent,guard_blocks_attack
        from werewolf.night_knowledge import WolfAttack
        from werewolf.public_observation_support import condition_generated_support
        for repeat in (True,False):
            rules,strategy,later=terminal_fixtures.UniformTerminalCutTests().fixture(repeat)
            b,s=later.public,later.public_law;engine=FixedPublicWolfProfile(b,s,(),rules,strategy,())
            state=engine.acquire(b,s)
            infos=tuple(i for i,mass,group in wolf_information_groups(state))
            self.assertEqual(wolf_information_keys(state),infos)
            kernel={}
            for info in infos:
                actions=tuple(t for t in b.alive if not info.initial_roster&(1<<(t-1)))
                self.assertEqual(len(actions),2)
                kernel[info.initial_roster,info.attacks]=((actions[0],F(1,3)),(actions[1],F(2,3)))
            attack=b.alive[-1]
            for blocked in (True,False):
                child=(replace(guard.condition_guard_observation(b,(),rules,state=state),day=b.day+1,phase='day')
                       if blocked else next(o.board for o in engine.public_children(b,attack,state)
                                            if o.board.winner=='wolf'))
                entries=[]
                for h in state.hypotheses:
                    actor=next((p for p in b.alive if h.roles[3]&(1<<(p-1))),None)
                    if actor is None and blocked:continue
                    choices=((None,F(1)),) if actor is None else guard.guard_choices(b,actor,rules,strategy.guard_position,guards=h.guards)
                    for bite,qa in kernel[h.roles[0],h.attacks]:
                        if not blocked and bite!=attack:continue
                        for target,qg in choices:
                            intent=GuardIntent(b.day,actor,target) if actor is not None else None
                            if (intent is not None and guard_blocks_attack(intent,bite))!=blocked:continue
                            entries.append(Hypothesis(h.roles,h.acquisitions,h.mass*qa*qg,
                                h.guards+((intent,) if intent else ()),h.attacks+(WolfAttack(b.day,bite),)))
                expected=condition_generated_support(child,state,tuple(entries))
                actual=guard._public_guard_branch_law(b,state,child,attack,blocked,engine,policies=kernel)
                self.assertEqual(actual,expected)

    def test_configured_uniform_generation_reuses_complete_law_without_a_profile_resolver(self):
        from werewolf.root_secret_flow import RootSecretEngine
        g=fixtures.RootGuardMaxTests().game(players=5,night='random')
        rules,p=replay(g);strategy=Strategy(**g['policy']);root=prepare_root_entry(g,p.board,rules,strategy)
        b,s=root.public,root.public_law;engine=RootSecretEngine(rules,strategy)
        state=engine.acquire(b,s)
        child=replace(guard.condition_guard_observation(b,(),rules,state=state),day=b.day+1,phase='day')
        expected=guard._public_guard_branch_law(b,state,child,2,True,engine)
        with patch.object(guard,'_public_guard_branch_law',wraps=guard._public_guard_branch_law) as compute:
            self.assertEqual(guard.public_guard_branch_law(b,state,child,2,True,engine),expected)
            self.assertEqual(guard.public_guard_branch_law(b,state,child,3,True,engine),expected)
            self.assertEqual(compute.call_count,1)
        self.assertEqual(engine.public_support_stats,{'calls':2,'hits':1})
