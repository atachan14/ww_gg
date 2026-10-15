import unittest
from dataclasses import asdict,replace
from fractions import Fraction as F
from copy import deepcopy
from unittest.mock import patch
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy
from werewolf.seer_manual import migrate_game,replay
from werewolf.root_secret_flow import RootSecretEngine,prepare_root_entry,prepare_root_secrets,step_root_action
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.fixed_actor_continuation import fixed_uniform_action_value
from werewolf.seer_acquisition import normalize
from werewolf.seer_future_uniform import FuturePending
from werewolf.model_a_public import evaluate_public_game,clear_public_cache


class FullCommonReference(RootSecretEngine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.memoize_flows=True
    def act(self,*args,**kwargs):return InformationSetForecast.act(self,*args,**kwargs)
    def solve(self,*args,**kwargs):return InformationSetForecast.solve(self,*args,**kwargs)


def game6(m,z,repeat):
    strategy=Strategy('random','random',fake_reports='random',disclosure_common='none')
    claims=['latent']*6;common={'claims':claims,'claim_policy':{'hunter':'none'},'policy':asdict(strategy)}
    return migrate_game({'players':6,'wolves':1,'hunters':1,'mediums':m,'seers':z,**common,
        'rules':asdict(Rules(allow_repeat_guard=repeat)),'seer_mode':'information-fixed-v1',
        'seer_inputs':[],'history':[dict(common,target=6)]})


class UniformFixedBackupTests(unittest.TestCase):
    def test_six_player_latent_abilities_match_full_common_inactive_role_reference(self):
        for repeat in (True,False):
            baseline=game6(0,0,repeat);rules,p=replay(baseline);strategy=Strategy(**baseline['policy'])
            clear_public_cache()
            with patch('werewolf.root_secret_flow.RootSecretEngine',FullCommonReference):
                expected=evaluate_public_game(baseline,p.board,rules,strategy)
            self.assertNotIsInstance(expected,FuturePending)
            for m,z in ((0,1),(1,0),(1,1)):
                with self.subTest(repeat=repeat,mediums=m,seers=z):
                    g=game6(m,z,repeat);before=deepcopy(g);rules,p=replay(g);clear_public_cache()
                    actual=evaluate_public_game(g,p.board,rules,strategy)
                    self.assertEqual(actual,expected);self.assertEqual(g,before)
                    self.assertEqual(evaluate_public_game(g,p.board,rules,strategy),actual)
                    clear_public_cache();self.assertEqual(evaluate_public_game(g,p.board,rules,strategy),actual)

    def fixture(self,repeat):
        rules=Rules(allow_repeat_guard=repeat);strategy=Strategy('random','random',disclosure_common='none')
        board=replace_worlds(initial_board(5,1,1,1,1),
            ((1,2,4,8,F(1,4)),(1,8,2,4,F(1,2)),(1,4,2,8,F(1,4))))
        root=prepare_root_secrets(board,rules)
        later=step_root_action(root,5,rules,strategy)[0][1]
        return rules,strategy,later

    def test_no_repeat_six_player_two_gj_replay_matches_inactive_role_reference(self):
        from werewolf.dawn import OBSERVATION
        forecasts=[]
        for m,z in ((0,0),(1,1)):
            g=game6(m,z,False);base=deepcopy(g['history'][0])
            gj=dict(deepcopy(base),target=None,observation=OBSERVATION,deaths=[])
            g['history'] += [gj,dict(deepcopy(base),target=5),deepcopy(gj)]
            before=deepcopy(g);rules,p=replay(g);clear_public_cache()
            forecast=evaluate_public_game(g,p.board,rules,Strategy(**g['policy']))
            self.assertNotIsInstance(forecast,FuturePending)
            forecasts.append(forecast);self.assertEqual(g,before)
        self.assertEqual(forecasts[0],forecasts[1])
        self.assertEqual(forecasts[1].village_win,F(13,48))

    def test_saved_observation_filter_equals_complete_children_with_original_mass(self):
        for repeat in (True,False):
            rules,strategy,branch=self.fixture(repeat)
            for target in (2,3,4):
                full=step_root_action(branch,target,rules,strategy,publish=False)
                self.assertNotIsInstance(full,FuturePending)
                for alive in (branch.public.alive,tuple(p for p in branch.public.alive if p!=target)):
                    expected=tuple((q,c) for q,c in full if c.public.alive==alive)
                    observed=step_root_action(branch,target,rules,strategy,publish=False,
                                              _observed_alive=alive)
                    self.assertEqual(observed,expected)
                    self.assertLessEqual(sum((q for q,c in observed),F()),F(1))
                self.assertEqual(step_root_action(branch,target,rules,strategy,publish=False,
                                                  _observed_alive=()),())

    def test_correlated_unknown_roles_and_separate_q_p_match_unreduced_common_flow(self):
        for repeat in (True,False):
            rules,strategy,later=self.fixture(repeat);b,s=later.public,later.public_law
            private=replace(s,hypotheses=normalize(tuple(replace(h,mass=h.mass*(2 if h.roles[1]==4 else 1))
                                                       for h in s.hypotheses)))
            before=deepcopy((later,private));engine=RootSecretEngine(rules,strategy)
            reference=FullCommonReference(rules,strategy);values=[]
            for measure in (s,private):
                physical=replace_worlds(b,measure.public_roles,wolf_count=None);row=[]
                for target in (2,3,4):
                    value=fixed_uniform_action_value(b,s,measure,engine,target,physical=physical)
                    self.assertIsNotNone(value)
                    self.assertEqual(value,reference.act(b,s,(),target,measure,None,physical=physical));row.append(value)
                values.append(tuple(row))
            self.assertNotEqual(values[0],values[1])
            self.assertEqual((later,private),before)
            changed=replace(s,hypotheses=normalize(tuple(replace(h,mass=h.mass*(3 if h.roles[3]==4 else 1))
                                                       for h in s.hypotheses)))
            public=replace_worlds(b,changed.public_roles,wolf_count=None)
            physical=replace_worlds(b,private.public_roles,wolf_count=None)
            self.assertEqual(fixed_uniform_action_value(public,changed,private,engine,3,physical=physical),values[1][1])

    def test_unsupported_secret_support_reports_observers_and_max_do_not_use_cut(self):
        rules,strategy,later=self.fixture(True);b,s=later.public,later.public_law
        role=s.hypotheses[0].roles
        same_role=[h for h in s.hypotheses if h.roles==role]
        source=replace(s,hypotheses=normalize(tuple(same_role[:1])))
        private=replace(s,hypotheses=normalize(tuple(same_role[1:2])))
        public=replace_worlds(b,source.public_roles,wolf_count=None)
        engine=RootSecretEngine(rules,strategy)
        self.assertIsNone(fixed_uniform_action_value(public,source,private,engine,2))
        self.assertIsNone(fixed_uniform_action_value(b,s,s,engine,2,observer=object()))
        self.assertIsNone(fixed_uniform_action_value(b,s,s,RootSecretEngine(rules,replace(strategy,night='max')),2))
        claims=list(b.claims);claims[2]='seer'
        self.assertIsNone(fixed_uniform_action_value(replace(b,claims=tuple(claims)),s,s,
            RootSecretEngine(rules,replace(strategy,disclosure_common='all')),2))

    def test_completed_day_horizon_matches_full_common_flow_without_new_scan_expansion(self):
        from werewolf.model_a_public import horizon_for_action
        for repeat in (True,False):
            rules,strategy,later=self.fixture(repeat)
            morning=next(b for q,b in step_root_action(later,2,rules,strategy)
                         if b.public.winner is None and len(b.public.alive)==4)
            b,s=morning.public,morning.public_law;private=morning.physical_law
            engine=RootSecretEngine(rules,strategy);reference=FullCommonReference(rules,strategy)
            physical=replace_worlds(b,private.public_roles,wolf_count=None)
            for target in b.alive:
                actual=engine.act(b,s,(),target,private,None,physical=physical)
                self.assertEqual(actual,reference.act(b,s,(),target,private,None,physical=physical))
                with patch.object(engine.action_policy,'acquire',side_effect=AssertionError('No unused scan expansion')):
                    horizon=horizon_for_action(engine,b,s,(),target,private)
                self.assertEqual(horizon,horizon_for_action(reference,b,s,(),target,private))

    def test_own_scan_candidates_match_complete_controlled_scan_reference(self):
        from werewolf.root_secret_flow import root_seer_forecast
        for repeat in (True,False):
            rules,strategy,later=self.fixture(repeat)
            results=(next(a for h in later.physical_law.hypotheses if h.roles[2]==2
                          for a in h.acquisitions if a.target==3),)
            before=deepcopy(later)
            actual=root_seer_forecast(later,2,results,rules,strategy)
            with patch('werewolf.root_secret_flow.RootSecretEngine',FullCommonReference),                 patch('werewolf.fixed_actor_continuation.fixed_uniform_action_value',return_value=None):
                expected=root_seer_forecast(later,2,results,rules,strategy)
            self.assertEqual(actual,expected)
            self.assertEqual({t for t,v in actual},{1,4})
            self.assertEqual(len({v for t,v in actual}),1)
            self.assertEqual(later,before)
