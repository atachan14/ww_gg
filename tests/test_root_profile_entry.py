import unittest
from dataclasses import replace
from fractions import Fraction as F
from copy import deepcopy
from unittest.mock import patch
from tests import test_root_guard_max as fixtures
from werewolf.exact import Strategy,Rules,initial_board,replace_worlds
from werewolf.seer_manual import migrate_game,replay
from werewolf.root_secret_flow import prepare_root_entry,root_screen_eligible,RootSecretEngine
from werewolf.model_a_public import evaluate_public_game,clear_public_cache,public_cache_info
from werewolf.private_adapter import evaluate_private_table
from werewolf.seer_future_uniform import FuturePending
from werewolf.information_set_forecast import Pending
from werewolf.policy_certificates import ProfileSearch
from werewolf.wolf_profile_certificate import WolfProfileResolver,FixedPublicWolfProfile,wolf_candidate_profile
from werewolf.actor_information import WolfInformation,wolf_information_groups
from werewolf.policy_choice import uniform_policy
from werewolf.candidate_policy import CandidateRules
from werewolf.night_knowledge import WolfAttack


class RootProfileEntryTests(unittest.TestCase):
    def game(self,repeat=True):
        g=fixtures.RootGuardMaxTests().game(repeat)
        g['policy']['day']='max';g['history'][0]['policy']['day']='max'
        return migrate_game(g)

    def test_candidate_profiles_share_only_exact_branch_inputs(self):
        g=self.game();r,p=replay(g);s=Strategy(**g['policy'])
        b=prepare_root_entry(g,p.board,r,s);resolver=WolfProfileResolver(r,s)
        legal=tuple((info,tuple(t for t in b.public.alive if not info.initial_roster&(1<<(t-1))))
                    for info,mass,group in wolf_information_groups(b.public_law))
        first=tuple((info,uniform_policy(actions)) for info,actions in legal)
        second=tuple((info,uniform_policy(actions[:1])) for info,actions in legal)
        a=FixedPublicWolfProfile(b.public,b.public_law,(),r,s,first,resolver=resolver)
        c=FixedPublicWolfProfile(b.public,b.public_law,(),r,s,second,resolver=resolver)
        target=b.public.alive[-1]
        physical=a.physical_children(b.public,target)
        self.assertIs(c.physical_children(b.public,target),physical)
        public=a.public_children(b.public,target,b.public_law)
        self.assertIs(c.public_children(b.public,target,b.public_law),public)
        self.assertEqual(resolver.branch_stats,{'calls':4,'hits':2})
        # A physical input with different role support cannot use that entry.
        changed=replace_worlds(b.public,((*b.public.worlds[0][:-1],F(1)),))
        self.assertIsNot(c.physical_children(changed,target),physical)
        self.assertEqual(a.policy_reads+c.policy_reads,0)
        self.assertEqual(resolver.branch_stats['hits'],2)
        for unused in range(2):
            with self.assertRaises(Pending):
                resolver.branch(('failed',),lambda:(_ for _ in ()).throw(Pending('test')))
        self.assertNotIn(('failed',),resolver.branch_cache)

    def test_normal_public_owner_and_cache_both_rules(self):
        for repeat in (True,False):
            g=self.game(repeat);before=deepcopy(g);r,p=replay(g);s=Strategy(**g['policy'])
            clear_public_cache();v=evaluate_public_game(g,p.board,r,s)
            self.assertNotIsInstance(v,FuturePending);self.assertEqual(v.village_win,F(1,10))
            self.assertEqual(dict(v.action_values),{1:F(),2:F(1,8),3:F(1,8)})
            self.assertEqual({t:h.wolf_win for t,h in v.by_dawn_values},{1:F(1),2:F(3,4),3:F(3,4)})
            self.assertIs(evaluate_public_game(g,p.board,r,s),v)
            self.assertGreaterEqual(public_cache_info().hits,1)
            owner=evaluate_private_table(p.board,'wolf',[1],[],r,s,game_state=g)
            self.assertEqual([row['final']['village'] for row in owner['players'][1:3]],['1/6','1/6'])
            self.assertIsNone(owner['players'][0]['final']);self.assertIsNone(owner['players'][3]['final'])
            self.assertEqual(g,before)
            clear_public_cache();self.assertEqual(evaluate_public_game(g,p.board,r,s),v)

    def test_saved_day_max_gj_replays_its_original_profile(self):
        for repeat in (True,False):
            g=self.game(repeat)
            gj={'target':None,'claims':g['claims'],'claim_policy':g['claim_policy'],
                'policy':deepcopy(g['policy']),'observation':'night-deaths-v1','deaths':[]}
            g=migrate_game({**g,'history':[*g['history'],gj]});before=deepcopy(g)
            r,p=replay(g);s=Strategy(**g['policy']);b=prepare_root_entry(g,p.board,r,s)
            self.assertNotIsInstance(b,FuturePending)
            self.assertEqual(len(b.public.worlds),4)
            v=evaluate_public_game(g,p.board,r,s);self.assertEqual(v.village_win,F(1,2))
            self.assertEqual(dict(v.action_values),{1:F(1,2),2:F(1,4),3:F(1,4)})
            own=WolfInformation(1,(WolfAttack(1,2),)).condition_public(b.public_law)
            self.assertEqual({h.roles[3] for h in own.hypotheses},{4})
            changed=migrate_game({**g,'policy':{**g['policy'],'day':'random'}})
            _,q=replay(changed)
            self.assertEqual(q.board.worlds,p.board.worlds)
            self.assertEqual(changed['history'][-1]['policy']['day'],'max')
            self.assertEqual(g,before)

    def test_fixed_known_hunter_legacy_entry_is_preserved(self):
        g=self.game();g['claim_policy']=g['history'][0]['claim_policy']={'hunter':'filled'}
        r,p=replay(g);s=Strategy(**g['policy'])
        self.assertIsNone(prepare_root_entry(g,p.board,r,s))
        initial=replace(initial_board(4,1,0,0,1),claims=('hunter','latent','latent','latent'))
        from werewolf.exact import condition_claims,ClaimPolicy
        initial=condition_claims(initial,initial.claims,ClaimPolicy(hunter='filled'))
        self.assertFalse(root_screen_eligible(initial,r,s))

    def test_failed_profile_classes_never_install_a_kernel(self):
        g=self.game();r,p=replay(g);s=Strategy(**g['policy']);b=prepare_root_entry(g,p.board,r,s)
        for status in ('multiple','no_admissible_profile','undefined_observations','budget_unfinished','dependency_unfinished'):
            e=RootSecretEngine(r,s)
            with patch.object(WolfProfileResolver,'resolve',return_value=ProfileSearch(status,1,0)):
                with self.assertRaises(Pending) as stopped:e.public_night_policies(b.public,b.public_law)
            self.assertEqual(stopped.exception.reason,'root_guard_profile_'+status)
            self.assertEqual(e.night_kernels,{})

    def test_actual_later_night_reuses_a_complete_policy_independence_proof(self):
        from werewolf.root_secret_flow import prepare_root_secrets,step_root_action
        from werewolf.night_knowledge import WolfAttack
        for repeat in (True,False):
            r=Rules(allow_repeat_guard=repeat);old=Strategy('random','random',disclosure_common='none')
            seed=replace_worlds(initial_board(6,1,0,0,1),((1,0,0,32,F(1)),))
            root=prepare_root_secrets(seed,r)
            parent=step_root_action(root,6,r,old)[0][1]
            later=step_root_action(parent,5,r,old)[0][1]
            later=step_root_action(later,4,r,old)[0][1];before=deepcopy(later)
            s=replace(old,day='max',night='max');resolver=WolfProfileResolver(r,s,max_profiles=1)
            parent_profile=((WolfInformation(1),uniform_policy((2,3,4,5))),)
            e=FixedPublicWolfProfile(parent.public,parent.public_law,(),r,s,parent_profile,resolver=resolver)
            k=e.public_night_policies(later.public,later.public_law)
            self.assertEqual(k,{(1,(WolfAttack(1,5),)):uniform_policy((2,3))})
            result=resolver.cache[later.public,later.public_law,()]
            self.assertEqual(result.proof,'policy_independent_scores')
            self.assertEqual((result.total,result.evaluated),(3,1))
            self.assertTrue(all(v==0 for info,row in result.selected.scores for t,v in row))
            used=resolver.profiles_evaluated;e.public_night_policies(later.public,later.public_law)
            self.assertEqual(resolver.profiles_evaluated,used)
            self.assertEqual(resolver.active,set());self.assertEqual(resolver.dependencies.stack,[])
            self.assertEqual(later,before)
            self.assertTrue(all(h.attacks==(WolfAttack(1,5),) for h in later.public_law.hypotheses))

    def test_later_2187_profiles_use_exact_terminal_public_classes(self):
        from werewolf.root_secret_flow import step_root_action
        for repeat in (True,False):
            g=fixtures.RootGuardMaxTests().game(repeat,players=5)
            r,p=replay(g);old=Strategy(**g['policy']);root=prepare_root_entry(g,p.board,r,old)
            random=replace(old,night='random')
            morning=next(b for q,b in step_root_action(root,2,r,random) if len(b.public.alive)==4)
            later=next(b for q,b in step_root_action(morning,2,r,random) if b.public.phase=='night')
            self.assertEqual(later.public.alive,(1,3,4));self.assertEqual(len(later.public_law.hypotheses),10)
            before=deepcopy(later);s=replace(old,day='max');resolver=WolfProfileResolver(r,s)
            result=resolver.resolve(later.public,later.public_law)
            self.assertEqual((result.status,result.total,result.evaluated),('unique',2187,2187))
            self.assertLess(resolver.profiles_evaluated,20)
            # Independently recompute EVERY selected legal deviation using the
            # ordinary full common flow, with no score-class memo provider.
            engine=FixedPublicWolfProfile(later.public,later.public_law,(),r,s,result.selected.profile)
            candidates=CandidateRules(later.public,later.public_law,(),r,s)
            expected=tuple((info,tuple((target,FixedPublicWolfProfile(later.public,later.public_law,(),r,s,wolf_candidate_profile(result.selected.profile,info,target,rules=candidates)).act(later.public,later.public_law,(),target,group,None))
                for target in later.public.alive if not info.initial_roster&(1<<(target-1))))
                for info,mass,group in wolf_information_groups(later.public_law))
            self.assertEqual(result.selected.scores,expected);self.assertEqual(later,before)

    def test_unpublished_seer_medium_later_rows_match_full_joint_common_flow(self):
        from werewolf.root_secret_flow import step_root_action
        for medium,seer in ((0,1),(1,0),(1,1)):
            g=fixtures.RootGuardMaxTests().game(False,players=6)
            g.update(mediums=medium,seers=seer)
            r,p=replay(g);old=Strategy(**g['policy']);root=prepare_root_entry(g,p.board,r,old)
            random=replace(old,night='random')
            morning=next(b for q,b in step_root_action(root,2,r,random)
                         if len(b.public.alive)==4 and b.public.winner is None)
            later=next(b for q,b in step_root_action(morning,3,r,random) if b.public.phase=='night')
            self.assertEqual(later.public.alive,(1,4,5))
            # A bounded public cast condition, still retaining EVERY compatible
            # acquisition/guard/attack history, permits a full independent check.
            from werewolf.seer_acquisition import normalize,public_worlds
            law=replace(later.public_law,hypotheses=normalize(tuple(h for h in later.public_law.hypotheses
                if h.roles[0]==1 and h.roles[1]==(4 if medium else 0)
                and h.roles[2]==(2 if seer else 0) and h.roles[3] in (8,16))))
            board=replace_worlds(later.public,public_worlds(law.hypotheses),wolf_count=None)
            later=replace(later,public=board,physical=board,public_law=law,physical_law=law)
            before=deepcopy(later)
            resolver=WolfProfileResolver(r,old);result=resolver.resolve(later.public,later.public_law)
            self.assertEqual(result.status,'unique')
            engine=FixedPublicWolfProfile(later.public,later.public_law,(),r,old,result.selected.profile)
            candidates=CandidateRules(later.public,later.public_law,(),r,old)
            expected=tuple((info,tuple((target,FixedPublicWolfProfile(later.public,later.public_law,(),r,old,wolf_candidate_profile(result.selected.profile,info,target,rules=candidates)).act(later.public,later.public_law,(),target,group,None))
                for target in later.public.alive if not info.initial_roster&(1<<(target-1))))
                for info,mass,group in wolf_information_groups(later.public_law))
            self.assertEqual(result.selected.scores,expected);self.assertEqual(later,before)
            if seer:self.assertTrue(any(h.acquisitions for h in later.public_law.hypotheses))

    def test_five_six_candidate_search_does_not_misclassify_legal_alternatives(self):
        for n in (5,6):
            g=fixtures.RootGuardMaxTests().game(players=n)
            g['policy']['day']=g['history'][0]['policy']['day']='max'
            r,p=replay(g);s=Strategy(**g['policy']);root=prepare_root_entry(g,p.board,r,s)
            resolver=WolfProfileResolver(r,s);result=resolver.resolve(root.public,root.public_law)
            self.assertNotEqual(result.status,'undefined_observations')
            self.assertTrue(all(issue.kind!='undefined_observation' for issue in result.issues))
            if result.status!='unique':
                self.assertIsNone(result.selected)
                self.assertNotIn((root.public,root.public_law,()),resolver.cache)

    def test_public_known_live_hunter_legal_candidates_are_not_off_path(self):
        from werewolf.wolf_profile_certificate import certify_wolf_profiles
        for repeat in (True,False):
            g=fixtures.RootGuardMaxTests().game(repeat)
            g['claim_policy']=g['history'][0]['claim_policy']={'hunter':'filled'}
            r,p=replay(g);old=Strategy(**g['policy']);b=prepare_root_entry(g,p.board,r,old)
            result=certify_wolf_profiles(b.public,b.public_law,(),r,replace(old,day='max'))
            self.assertEqual((result.total,result.evaluated),(9,9))
            self.assertEqual(result.status,'unique');self.assertEqual(result.issues,())
            self.assertTrue(all(policy==((1,F(1)),) for info,policy in result.selected.profile))

    def test_profile_dependent_over_limit_context_stays_pending_and_uncached(self):
        g=self.game();r,p=replay(g);s=Strategy(**g['policy']);b=prepare_root_entry(g,p.board,r,s)
        resolver=WolfProfileResolver(r,s,max_profiles=1)
        result=resolver.resolve(b.public,b.public_law)
        self.assertEqual(result.status,'budget_unfinished');self.assertIsNone(result.selected)
        self.assertEqual(resolver.cache,{})
        self.assertEqual(resolver.active,set());self.assertEqual(resolver.dependencies.stack,[])


class RootProfileRouteTests(unittest.TestCase):
    def test_normal_routes_day_max_saved_gj_reload_and_back_both_rules(self):
        from app import create_app
        import json
        for repeat in ('1','0'):
            app=create_app({'TESTING':True,'SECRET_KEY':'root-profile-route',
                            'HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True})
            c=app.test_client()
            form={'citizens':'2','hunters':'1','wolves':'1','day':'max','night':'max',
                  'fake_reports':'random','disclosure_common':'none','allow_repeat_guard':repeat,
                  'seer_mode':'information-fixed-v1'}
            self.assertEqual(c.post('/start',data=form).status_code,303)
            self.assertIn(b'data-fraction="7/24"',c.get('/main').data)
            def game():
                with c.session_transaction() as session:return deepcopy(session['game'])
            g=game();self.assertEqual(c.post('/advance',data={'revision':str(g['revision']),'target':'4',
                'day':'max','night':'max'}).status_code,303)
            g=game();night=c.get('/main').data
            self.assertIn(b'data-fraction="1/18"',night)
            self.assertIn(b'data-dawn-open',night)
            self.assertIn(b'name="mode" value="none"',night)
            before=deepcopy(g)
            own=c.post('/private-view',data={'revision':str(g['revision']),'board_id':g['public_log']['board_id'],
                'payload':json.dumps({'role':'wolf','players':[1],'results':[]})})
            self.assertEqual(own.status_code,200);self.assertEqual(own.json['players'][1]['final']['village'],'1/18')
            self.assertEqual(game(),before)
            self.assertEqual(c.post('/dawn-report',data={'revision':str(g['revision']),
                'board_id':g['public_log']['board_id'],'mode':'none'}).status_code,303)
            g=game();self.assertEqual(c.post('/dawn-advance',data={'revision':str(g['revision']),
                'board_id':g['public_log']['board_id']}).status_code,303)
            saved=game();self.assertEqual(saved['history'][-1]['policy']['day'],'max')
            self.assertIn(b'data-fraction="1/3"',c.get('/main').data)
            with c.session_transaction() as session:stored=deepcopy(dict(session))
            reopened=app.test_client()
            with reopened.session_transaction() as session:session.update(stored)
            self.assertIn(b'data-fraction="1/3"',reopened.get('/main').data)
            self.assertEqual(c.post('/back',data={'revision':str(saved['revision'])}).status_code,303)
            self.assertEqual(game()['policy']['day'],'max')
            self.assertIn(b'data-fraction="1/18"',c.get('/main').data)
