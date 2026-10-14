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

    def test_pending_scope_does_not_replace_max_or_published_entries(self):
        game,b,r,s=self.fixture()
        self.assertFalse(root_replay_eligible(game,b,r,Strategy()))
        self.assertFalse(root_replay_eligible({**game,'claims':['seer']+['latent']*4},b,r,s))
        self.assertFalse(root_replay_eligible({**game,'seer_inputs':[{}]},b,r,s))

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
