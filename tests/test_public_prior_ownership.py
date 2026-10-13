import unittest,json
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import initial_board,replace_worlds,action_outcomes,Rules,Strategy
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.public_prior import prepare_public_prior,public_history_key,clear_public_prior_cache,public_prior_cache_info


class PublicPriorOwnershipTests(unittest.TestCase):
    def setUp(self):clear_public_prior_cache()

    def test_public_prior_cache_excludes_viewer_and_invalidates_on_board_and_initial_rule(self):
        b=initial_board(5,1);r=Rules(initial_seer='none')
        first=prepare_public_prior({},b,r,track_live_seers=False)
        self.assertIs(prepare_public_prior({'secret':'black','viewer':1},b,r,track_live_seers=False),first)
        self.assertEqual(public_prior_cache_info().hits,1)
        self.assertNotIn('black',public_history_key({'secret':'black'}))
        next_board=action_outcomes(b,5,r,Strategy())[1].board
        self.assertIsNot(prepare_public_prior({},next_board,r,track_live_seers=False),first)
        self.assertIsNot(prepare_public_prior({},b,Rules(initial_seer='normal'),track_live_seers=False),first)
        self.assertEqual(public_prior_cache_info().misses,3)

    def test_only_public_evidence_and_publication_time_change_history_key(self):
        g={'seer_inputs':[{'day':1,'reporter':1,'target':2,'color':'white'}],
           'public_log':{'version':2,'report_publications':{'seer:1:1':{'published_day':1,'owner':'old'}}}}
        before=public_history_key(g)
        changed=json.loads(json.dumps(g));changed['public_log']['report_publications']['seer:1:1']['owner']='new'
        self.assertEqual(public_history_key(changed),before)
        changed['public_log']['report_publications']['seer:1:1']['published_day']=2
        self.assertNotEqual(public_history_key(changed),before)
        changed=json.loads(json.dumps(g));changed['seer_inputs'][0]['color']='black'
        self.assertNotEqual(public_history_key(changed),before)

    def test_shared_engine_does_not_alias_different_private_observers(self):
        seed=replace(replace_worlds(initial_board(5,1,0,1),tuple((m,0,1,0,q)
                     for m,q in ((2,F(3,5)),(4,F(3,10)),(8,F(1,10))))),
                     claims=('seer','latent','latent','latent','latent'))
        b=next(o.board for o in action_outcomes(seed,5,Rules(initial_seer='none'),Strategy()) if o.board.winner is None)
        s=TrueScanState(from_board(b),((1,2,3,4,5),),initial_rule='none')
        e=InformationSetForecast(Rules(initial_seer='none'),Strategy('max','random'))
        def observer(target):
            return lambda h,state:len(state.rosters)<2 or any(a.player==1 and a.day==2 and a.target==target for a in h.acquisitions)
        first=e.evaluate(b,s,(),observer=observer(2))
        roots={key:value for key,value in e.policies.items() if key[0]==b}
        second=e.evaluate(b,s,(),observer=observer(4))
        self.assertEqual((first,second),(F(5,6),F(23,30)))
        self.assertEqual(roots,{key:value for key,value in e.policies.items() if key[0]==b})

    def test_incomplete_public_ledger_is_not_cached(self):
        from werewolf.seer_future_uniform import FuturePending
        b=replace(initial_board(5,1,0,1),claims=('seer','latent','latent','latent','latent'))
        g={'players':5,'rules':{'initial_seer':'normal'},'seer_options':{'initial_rule':'normal'},
           'seer_inputs':[],'public_log':{'version':2}}
        for _ in range(2):
            self.assertIsInstance(prepare_public_prior(g,b,Rules(initial_seer='normal')),FuturePending)
        self.assertEqual(public_prior_cache_info().currsize,0)
        self.assertEqual(public_prior_cache_info().misses,2)
