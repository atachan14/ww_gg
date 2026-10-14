import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.exact import initial_board,Rules,Strategy,Progress
from werewolf.dawn import advance_step,OBSERVATION
from werewolf.root_secret_flow import replay_root_secrets,root_branch_forecast,root_replay_eligible
from werewolf.seer_future_uniform import FuturePending
from werewolf.model_a_public import evaluate_public_game,clear_public_cache
from werewolf.public_prior import public_history_key

class RootReplayTests(unittest.TestCase):
    def fixture(self):
        rules=Rules();strategy=Strategy('random','random',fake_reports='random')
        steps=[{'target':5,'policy':{'day':'random','night':'random','fake_reports':'random'},
                'claims':['latent']*5,'claim_policy':{}},
               {'target':4,'policy':{'day':'random','night':'random','fake_reports':'random'},
                'claims':['latent']*5,'claim_policy':{},'observation':OBSERVATION,'deaths':[4]}]
        progress=Progress.initial(initial_board(5,1,1,1))
        for step in steps:progress=advance_step(progress,step,rules)
        game={'players':5,'wolves':1,'mediums':1,'seers':1,'hunters':0,'history':steps,
              'claims':['latent']*5,'policy':steps[0]['policy'],'rules':{},'seer_inputs':[]}
        return game,progress.board,rules,strategy

    def test_replay_preserves_acquisitions_dead_seers_and_attacks(self):
        game,b,r,s=self.fixture();root=replay_root_secrets(game,b,r,s)
        self.assertNotIsInstance(root,FuturePending)
        self.assertEqual(root.public,b)
        self.assertEqual(root.public_law.public_roles,tuple(sorted(b.worlds)))
        for h in root.physical_law.hypotheses:
            owner=next(p for p in range(1,6) if h.roles[2]&(1<<(p-1)))
            self.assertEqual(len(h.acquisitions),1 if owner==5 else 2)
            self.assertEqual(tuple(a.target for a in h.attacks),(4,))
        self.assertEqual(root.physical_law.rosters,((1,2,3,4,5),(1,2,3,4)))

    def test_screen_routes_replay_and_cache_matches_recalculation(self):
        game,b,r,s=self.fixture();clear_public_cache()
        with patch('werewolf.root_secret_flow.replay_root_secrets',wraps=replay_root_secrets) as replay:
            first=evaluate_public_game(game,b,r,s)
            second=evaluate_public_game({**game,'viewer':2},b,r,s)
        self.assertNotIsInstance(first,FuturePending)
        self.assertEqual(first.village_win,F(1,3));self.assertIs(first,second)
        self.assertEqual(replay.call_count,1)
        clear_public_cache();self.assertEqual(evaluate_public_game(game,b,r,s),first)
        edited={**game,'history':game['history'][:1]}
        self.assertNotEqual(public_history_key(game),public_history_key(edited))
        self.assertEqual(replay_root_secrets(edited,b,r,s),FuturePending('root_secret_replay_board_mismatch'))

    def test_pending_scope_does_not_replace_max(self):
        game,b,r,s=self.fixture()
        self.assertFalse(root_replay_eligible(game,b,r,Strategy()))

    def test_latent_private_table_conditions_joint_history_without_public_mutation(self):
        from werewolf.private_adapter import evaluate_private_table
        from copy import deepcopy
        game,b,r,s=self.fixture();before=deepcopy(game)
        root=replay_root_secrets(game,b,r,s)
        h=next(h for h in root.physical_law.hypotheses if h.roles[2]==1)
        results=[{'day':a.day,'target':a.target,'color':a.color} for a in h.acquisitions]
        with patch('werewolf.root_secret_flow.root_seer_forecast',wraps=__import__(
                'werewolf.root_secret_flow',fromlist=['root_seer_forecast']).root_seer_forecast) as forecast:
            table=evaluate_private_table(b,'seer',(1,),results,r,s,game_state=game)
        self.assertEqual(forecast.call_count,1)
        self.assertTrue(any(row['final'] is not None for row in table['players']))
        self.assertEqual(game,before)
        self.assertEqual(root.public_law.public_roles,tuple(sorted(b.worlds)))

    def test_observed_uniform_bite_likelihood_changes_physical_mass_only(self):
        r=Rules();s=Strategy('random','random',fake_reports='random')
        policy={'day':'random','night':'random','fake_reports':'random'}
        steps=[{'target':7,'policy':policy,'claims':['latent']*7,'claim_policy':{}},
               {'target':6,'policy':policy,'claims':['latent']*7,'claim_policy':{},
                'observation':OBSERVATION,'deaths':[6]}]
        p=Progress.initial(initial_board(7,2,0,1,experimental_cast=True))
        for step in steps:p=advance_step(p,step,r)
        game={'players':7,'wolves':2,'mediums':0,'seers':1,'hunters':0,'history':steps,
              'claims':['latent']*7,'policy':policy,'seer_inputs':[]}
        root=replay_root_secrets(game,p.board,r,s,max_work=1000000)
        self.assertNotIsInstance(root,FuturePending)
        self.assertEqual(root.public_law.public_roles,tuple(sorted(p.board.worlds)))
        self.assertNotEqual(root.physical_law.public_roles,root.public_law.public_roles)
        # Execution of a wolf leaves five legal enemies on that night;
        # execution of a villager leaves four. Their physical odds are 4:5.
        dead_wolf=sum(w[-1] for w in root.physical_law.public_roles if w[0]&(1<<6))
        public_dead_wolf=sum(w[-1] for w in root.public_law.public_roles if w[0]&(1<<6))
        self.assertEqual(dead_wolf/(1-dead_wolf),public_dead_wolf/(1-public_dead_wolf)*F(4,5))

    def test_initial_latent_scan_comparison_keeps_pre_scan_death_branches(self):
        from werewolf.private_adapter import evaluate_private_table
        table=evaluate_private_table(initial_board(5,1,1,1),'seer',(1,),
            ({'day':1,'target':2,'color':'white'},),Rules(),
            Strategy('random','random',fake_reports='random'))
        values={row['id']:row['final']['village'] for row in table['players'] if row['final']}
        self.assertEqual(values,{p:'7/15' for p in (3,4,5)})

    def reported_fixture(self):
        from werewolf.seer_manual import migrate_game,replay
        policy={'day':'random','night':'random','fake_reports':'random','disclosure_common':'none'}
        claims=['seer','medium']+['latent']*4
        steps=[{'target':6,'policy':policy,'claims':claims,'claim_policy':{}},
               {'target':5,'policy':policy,'claims':claims,'claim_policy':{},
                'observation':OBSERVATION,'deaths':[5]}]
        game=migrate_game({'players':6,'wolves':1,'mediums':1,'seers':1,'hunters':0,
              'history':steps,'claims':claims,'claim_policy':{},'policy':policy,'rules':{},
              'seer_inputs':[{'day':1,'reporter':1,'target':3,'color':'white'},
                             {'day':2,'reporter':1,'target':4,'color':'black'}],
              'reports':[{'day':2,'reporter':2,'target':6,'color':'white'}]})
        r,p=replay(game)
        return game,p.board,r,Strategy(**policy)

    def test_observed_reports_condition_truth_history_and_preserve_model_a(self):
        from werewolf.seer_acquisition import Acquisition
        game,b,r,s=self.reported_fixture()
        root=replay_root_secrets(game,b,r,s,max_work=1000000)
        self.assertNotIsInstance(root,FuturePending)
        self.assertEqual(root.public,b)
        self.assertEqual(root.public_law.public_roles,tuple(sorted(b.worlds)))
        self.assertEqual(len(root.past),2)
        truth=[h for h in root.public_law.hypotheses if h.roles[2]&1]
        self.assertTrue(truth)
        for h in truth:
            self.assertIn(Acquisition(1,1,3,'white'),h.acquisitions)
            self.assertIn(Acquisition(2,1,4,'black'),h.acquisitions)
        self.assertTrue(all(not h.roles[0]&(1<<5) for h in root.public_law.hypotheses if h.roles[1]&2))

    def test_report_edit_cancel_and_cache_rebuild_use_initial_joint_law(self):
        from copy import deepcopy
        from werewolf.seer_manual import replay
        game,b,r,s=self.reported_fixture()
        before=deepcopy(game)
        clear_public_cache()
        first=evaluate_public_game(game,b,r,s,max_work=1000000,max_seconds=30)
        self.assertNotIsInstance(first,FuturePending)
        self.assertIs(first,evaluate_public_game(game,b,r,s,max_work=1000000,max_seconds=30))
        clear_public_cache()
        self.assertEqual(first,evaluate_public_game(game,b,r,s,max_work=1000000,max_seconds=30))
        edited=deepcopy(game);edited['seer_inputs'][0]['target']=2
        _,p=replay(edited)
        changed=replay_root_secrets(edited,p.board,r,s,max_work=1000000)
        self.assertNotIsInstance(changed,FuturePending)
        self.assertNotEqual(changed.public_law,replay_root_secrets(game,b,r,s,max_work=1000000).public_law)
        cancelled=deepcopy(game);cancelled['seer_inputs']=cancelled['seer_inputs'][:1]
        _,p=replay(cancelled)
        root=replay_root_secrets(cancelled,p.board,r,s,max_work=1000000)
        self.assertNotIsInstance(root,FuturePending)
        self.assertEqual(len(root.past),1)
        self.assertEqual(game,before)

    def guard_fixture(self,two_nights=False):
        from werewolf.seer_manual import migrate_game,replay
        policy={'day':'random','night':'random','fake_reports':'random','disclosure_common':'none'}
        claims=['latent']*5
        steps=[{'target':5,'policy':policy,'claims':claims,'claim_policy':{}},
               {'target':None,'policy':policy,'claims':claims,'claim_policy':{},
                'observation':OBSERVATION,'deaths':[]}]
        if two_nights:
            steps += [{'target':4,'policy':policy,'claims':claims,'claim_policy':{}},
                      {'target':None,'policy':policy,'claims':claims,'claim_policy':{},
                       'observation':OBSERVATION,'deaths':[]}]
        game=migrate_game({'players':5,'wolves':1,'mediums':0,'seers':1,'hunters':1,
              'history':steps,'claims':claims,'claim_policy':{},'policy':policy,'rules':{},'seer_inputs':[]})
        r,p=replay(game)
        return game,p.board,r,Strategy(**policy)

    def test_two_gj_nights_keep_guard_attack_scan_joint_histories(self):
        game,b,r,s=self.guard_fixture(True)
        root=replay_root_secrets(game,b,r,s,max_work=2000000,max_seconds=30)
        self.assertNotIsInstance(root,FuturePending)
        self.assertEqual(root.public_law.public_roles,tuple(sorted(b.worlds)))
        self.assertEqual(root.public,b)
        self.assertTrue(root.physical_law.hypotheses)
        targets=set()
        for h in root.physical_law.hypotheses:
            self.assertEqual(tuple(g.night for g in h.guards),(1,2))
            self.assertEqual(tuple(a.night for a in h.attacks),(1,2))
            self.assertEqual(tuple(g.target for g in h.guards),tuple(a.target for a in h.attacks))
            self.assertTrue(all(g.actor!=g.target for g in h.guards))
            targets.add(h.attacks[0].target)
        self.assertGreater(len(targets),1)
        self.assertTrue(any(h.guards[0].target==h.guards[1].target for h in root.physical_law.hypotheses))
        self.assertTrue(any(any(a.player==4 for a in h.acquisitions) for h in root.physical_law.hypotheses))

    def test_guard_and_wolf_owner_views_condition_same_joint_law(self):
        from werewolf.root_secret_flow import root_actor_view
        game,b,r,s=self.guard_fixture()
        root=replay_root_secrets(game,b,r,s,max_work=2000000)
        self.assertNotIsInstance(root,FuturePending)
        h=root.physical_law.hypotheses[0];g=h.guards[0];attack=h.attacks[0]
        guard=root_actor_view(root,lambda x:bool(x.roles[3]&(1<<(g.actor-1))) and g in x.guards)
        wolf=root_actor_view(root,lambda x:x.roles[0]==h.roles[0] and attack in x.attacks)
        self.assertNotIsInstance(guard,FuturePending);self.assertNotIsInstance(wolf,FuturePending)
        self.assertTrue(all(g in x.guards for x in guard.belief.hypotheses))
        self.assertTrue(all(attack in x.attacks for x in wolf.belief.hypotheses))
        self.assertGreater(len({x.roles[2] for x in wolf.belief.hypotheses}),1)
        self.assertEqual(root.public,b)
        self.assertFalse(root_replay_eligible(game,b,Rules(allow_repeat_guard=False),s))
        self.assertFalse(root_replay_eligible(game,b,r,Strategy('max','max')))

    def test_gj_owner_tables_share_public_flow_without_mutation(self):
        from copy import deepcopy
        from werewolf.private_adapter import evaluate_private_table
        game,b,r,s=self.guard_fixture(True);before=deepcopy(game)
        root=replay_root_secrets(game,b,r,s,max_work=2000000,max_seconds=30)
        h=next(h for h in root.physical_law.hypotheses if h.roles[3]==1 and h.roles[0]==2)
        guards=[{'day':g.night,'target':g.target,'color':None} for g in h.guards]
        table=evaluate_private_table(b,'hunter',(1,),guards,r,s,game_state=game,max_work=2000000,max_seconds=30)
        self.assertTrue(any(row['final'] is not None for row in table['players']))
        attacks=[{'day':a.night,'target':a.target,'color':None} for a in h.attacks]
        wolf=evaluate_private_table(b,'wolf',(2,),attacks,r,s,game_state=game,max_work=2000000,max_seconds=30)
        self.assertTrue(any(row['final'] is not None for row in wolf['players']))
        clear_public_cache()
        value=evaluate_public_game(game,b,r,s,max_work=2000000,max_seconds=30)
        self.assertNotIsInstance(value,FuturePending)
        self.assertIs(value,evaluate_public_game(game,b,r,s,max_work=2000000,max_seconds=30))
        self.assertEqual(game,before)

    def test_owned_public_log_and_delayed_publication_survive_cache_snapshot(self):
        from copy import deepcopy
        from werewolf.public_log import migrate
        from werewolf.public_log_changes import upgrade
        from werewolf.seer_manual import replay
        game,b,r,s=self.reported_fixture()
        owned=deepcopy(game);owned['public_log']=upgrade(migrate(owned))
        owned['result_disclosure_model']='full-observed-v1'
        for step in owned['history']:step['result_disclosure_model']='full-observed-v1'
        owned['public_log']['report_publications']={'seer:1:1':{'slot':0,'published_day':1},
            'seer:2:1':{'slot':2,'published_day':2},'medium:2:2:6':{'slot':2,'published_day':2}}
        _,p=replay(owned)
        clear_public_cache()
        value=evaluate_public_game(owned,p.board,r,s,max_work=1000000,max_seconds=30)
        self.assertNotIsInstance(value,FuturePending)
        self.assertIs(value,evaluate_public_game({**owned,'private_results':[{}]},p.board,r,s,max_work=1000000,max_seconds=30))
        edited=deepcopy(owned);edited['public_log']['report_publications']['seer:1:1']['slot']=1
        self.assertNotEqual(public_history_key(owned),public_history_key(edited))

    def test_guard_branch_public_ledger_does_not_reveal_fixed_bite(self):
        from werewolf.root_secret_flow import prepare_root_secrets,step_root_action
        r=Rules();s=Strategy('random','random',fake_reports='random',disclosure_common='none')
        root=prepare_root_secrets(initial_board(5,1,0,1,1),r)
        day=step_root_action(root,5,r,s,publish=False)
        ongoing=next(c for _,c in day if not c.public.winner)
        night=step_root_action(ongoing,4,r,s,publish=False)
        gj=next(c for _,c in night if not c.public.winner and c.public.alive==ongoing.public.alive)
        self.assertTrue(all(h.guards and h.attacks for h in gj.public_law.hypotheses))
        self.assertGreater(len({h.attacks[-1].target for h in gj.public_law.hypotheses}),1)
        self.assertEqual({h.attacks[-1].target for h in gj.physical_law.hypotheses},{4})
        self.assertEqual(gj.public_law.public_roles,tuple(sorted(gj.public.worlds)))
        self.assertTrue(all(h.guards[-1].target==h.attacks[-1].target for h in gj.public_law.hypotheses))

    def test_uniform_guard_only_gj_replay_uses_common_public_observation(self):
        from copy import deepcopy
        from werewolf.seer_manual import replay
        game,b,r,s=self.guard_fixture()
        game=deepcopy(game);game['seers']=0
        _,p=replay(game)
        root=replay_root_secrets(game,p.board,r,s,max_work=1000000)
        self.assertNotIsInstance(root,FuturePending)
        self.assertEqual(root.public_law.public_roles,tuple(sorted(p.board.worlds)))
        self.assertTrue(all(h.guards and h.attacks and not h.acquisitions for h in root.public_law.hypotheses))

    def test_positive_public_truth_with_impossible_repeated_scan_is_pending(self):
        from copy import deepcopy
        from werewolf.seer_manual import replay
        game,b,r,s=self.reported_fixture();game=deepcopy(game)
        game['seer_inputs'][1].update(target=3,color='white')
        _,p=replay(game)
        self.assertTrue(any(w[2]&1 for w in p.board.worlds))
        self.assertEqual(replay_root_secrets(game,p.board,r,s,max_work=1000000),
                         FuturePending('root_secret_public_history_zero_support'))

    def test_day_guard_intervention_keeps_pre_guard_death_branches(self):
        from werewolf.root_secret_flow import prepare_root_secrets,root_guard_forecast
        from werewolf.exact import replace_worlds
        b=replace_worlds(initial_board(4,1,0,0,1),((2,0,0,1,F(1)),))
        r=Rules();s=Strategy('random','random',fake_reports='random')
        root=prepare_root_secrets(b,r)
        values,dawn=root_guard_forecast(root,1,(),r,s)
        # Wolf execution wins 1/4. If a citizen dies, a surviving fixed guard
        # blocks with 1/2; if its chosen target died, the uniform fallback
        # blocks with 1/4. The following public execution wins 1/3.
        self.assertEqual(values,{2:F(1,4),3:F(5,16),4:F(5,16)})
        self.assertEqual({p:h.village_win for p,h in dawn.items()},{2:F(1,4),3:F(1,4),4:F(1,4)})
        self.assertEqual({p:h.wolf_win for p,h in dawn.items()},{2:F(3,4),3:F(9,16),4:F(9,16)})
        self.assertEqual(root.public,b)
