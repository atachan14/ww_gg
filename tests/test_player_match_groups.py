import unittest,copy
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.run import run,source
from werewolf.match_groups import PublicRelations,make_engine
from werewolf.exact import Strategy,Rules,initial_board,replace_worlds
from werewolf.seer_acquisition import Hypothesis
from werewolf.seer_future_uniform import TrueScanState
from werewolf.exact_renaming import canonical_key
from werewolf.player_view import PlayerData,ReadMap
import tests.test_player_view as view_helpers

class PlayerMatchGroupTests(unittest.TestCase):
    def test_complete_public_table_and_every_audited_branch(self):
        for n,w,value in((5,1,'7/15'),(6,1,'3/8'),(6,2,'1/12')):
            with self.subTest(n=n,w=w):
                old=run(n,w);new=run(n,w,True,True)
                self.assertTrue(old['complete']);self.assertTrue(new['complete'])
                self.assertEqual(old['value'],value);self.assertEqual(new['value'],value)
                self.assertEqual(old['table'],new['table']);self.assertTrue(new['stats']['active'])
                if n==6:self.assertLess(new['stats']['actual_action_expansions'],old['stats']['actual_action_expansions'])
    def test_seven_roots_keep_recursive_survivor_boundary(self):
        data,roles,b,s,past,rules,strategy,view=source(7,1)
        engine=make_engine(b,s,past,rules,strategy,enabled=True,view=view)
        self.assertTrue(engine.grouping)
        self.assertFalse(engine.supported(b,None))
        data,roles,b,s,past,rules,strategy,view=source(7,2)
        engine=make_engine(b,s,past,rules,strategy,enabled=True,view=view)
        self.assertTrue(engine.grouping)
        self.assertFalse(engine.supported(b,None))

    def test_nonuniform_full_support_joint_preserves_correlations_and_terminal_table(self):
        from benchmarks.player_match_groups.weighted_joint import weighted_source
        prepared=weighted_source(6,2,'cycle')
        _,_,b,state,past,rules,strategy,view=prepared
        self.assertEqual({b.role_probability(p,'wolf')for p in range(2,7)},{F(2,5)})
        self.assertEqual(b.joint_wolf_probability((2,3)),F(2,15))
        self.assertEqual(b.joint_wolf_probability((2,4)),F(1,15))
        old=run(6,2,prepared=prepared);new=run(6,2,True,True,prepared=prepared)
        self.assertTrue(old['complete']);self.assertTrue(new['complete'])
        self.assertEqual((old['value'],old['table']),(new['value'],new['table']))
        self.assertTrue(new['stats']['active']);self.assertGreater(new['stats']['audited_batches'],0)
        engine=make_engine(b,state,past,rules,strategy,enabled=True,view=view)
        self.assertTrue(engine.grouping);self.assertFalse(hasattr(engine,'audit_oracle'))
        # A different public joint law cannot borrow this weighted secret prior.
        _,_,uniform,_,_,_,_,_=source(6,2)
        self.assertFalse(make_engine(uniform,state,past,rules,strategy,enabled=True,view=view).grouping)

    def test_actual_initial_white_joint_and_report_correction_withdrawal(self):
        from benchmarks.player_match_groups.initial_white import initial_white_source,publish,prepare
        from werewolf.public_prior import prepare_public_prior
        import json
        prepared,client=initial_white_source(return_client=True)
        _,_,b,state,past,rules,strategy,view=prepared
        self.assertEqual(len(state.hypotheses),3)
        self.assertEqual(b.role_probability(3,'wolf'),0)
        self.assertTrue(all(h.acquisitions[0].target==3 for h in state.hypotheses))
        old=run(5,1,prepared=prepared);new=run(5,1,True,True,prepared=prepared)
        self.assertEqual((old['value'],old['table']),(new['value'],new['table']))
        self.assertTrue(new['stats']['active']);self.assertGreater(new['stats']['audited_batches'],0)
        with client.session_transaction()as session:g=copy.deepcopy(session['game'])
        self.assertEqual(prepare_public_prior(g,b,rules),(state,past))
        publish(client,4);corrected=prepare(client)
        self.assertEqual(corrected[2].role_probability(4,'wolf'),0)
        self.assertNotEqual(state.public_roles,corrected[3].public_roles)
        self.assertEqual(state.hypotheses[0].acquisitions[0].target,3)
        self.assertTrue(make_engine(*corrected[2:7],enabled=True,view=corrected[7]).grouping)
        # A stale ledger cannot be paired with a corrected public relation.
        self.assertFalse(make_engine(b,state,past,rules,strategy,enabled=True,view=corrected[7]).grouping)
        self.assertFalse(make_engine(b,state,past+past,rules,strategy,enabled=True,view=view).grouping)
        self.assertFalse(make_engine(b,state,past,rules,replace(strategy,day='max'),enabled=True,view=view).grouping)
        with client.session_transaction()as session:g=copy.deepcopy(session['game'])
        self.assertEqual(prepare_public_prior(g,corrected[2],rules),corrected[3:5])
        payload={'claims':['latent']*5,'seers':[],'mediums':[]}
        response=client.post('/table-publish',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps(payload)})
        self.assertEqual(response.status_code,200)
        with client.session_transaction()as session:g=copy.deepcopy(session['game'])
        from werewolf.board_flow import BoardData
        data=BoardData.from_game(g);roles=data.roles()
        self.assertFalse(make_engine(roles.board,state,past,rules,strategy,enabled=True,view=view).grouping)
        self.assertEqual(view.by_id(3).received_claims[0].target,3)
        with client.session_transaction()as session:g=copy.deepcopy(session['game'])
        payload={'claims':['seer','seer']+['latent']*3,'seers':[{'day':1,'reporter':p,'target':3,'color':'white'}for p in (1,2)],'mediums':[]}
        response=client.post('/table-publish',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps(payload)})
        self.assertEqual(response.status_code,200)
        competing=prepare(client)
        self.assertTrue(make_engine(*competing[2:7],enabled=True,view=competing[7]).grouping)
        # Different initial white targets are a separate, unproved condition.
        with client.session_transaction()as session:g=copy.deepcopy(session['game'])
        payload['seers'][1]['target']=4
        response=client.post('/table-publish',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps(payload)})
        self.assertEqual(response.status_code,200)
        mixed=prepare(client)
        self.assertFalse(make_engine(*mixed[2:7],enabled=True,view=mixed[7]).grouping)

    def test_actual_two_co_same_white_keeps_true_fake_secret_mixture(self):
        from benchmarks.player_match_groups.initial_white import initial_white_source
        prepared=initial_white_source(5,1,actors=(1,2))
        _,_,b,state,past,rules,strategy,view=prepared
        self.assertEqual(tuple(b.role_probability(p,'seer')for p in(1,2)),(F(1,2),F(1,2)))
        self.assertEqual(tuple(b.role_probability(p,'wolf')for p in(1,2)),(F(1,2),F(1,2)))
        self.assertEqual(b.joint_wolf_probability((1,2)),0)
        self.assertEqual(len(past),2)
        for h in state.hypotheses:
            self.assertEqual(len(h.acquisitions),1)
            acquisition=h.acquisitions[0]
            self.assertTrue(h.roles[2]&(1<<(acquisition.player-1)))
            self.assertFalse(h.roles[0]&(1<<(acquisition.player-1)))
            self.assertEqual(acquisition.target,3)
        old=run(5,1,prepared=prepared);new=run(5,1,True,True,prepared=prepared)
        self.assertTrue(old['complete']);self.assertTrue(new['complete'])
        self.assertEqual((old['value'],old['table']),(new['value'],new['table']))
        self.assertTrue(new['stats']['active']);self.assertGreater(new['stats']['audited_batches'],0)
        self.assertFalse(make_engine(b,state,past,rules,replace(strategy,night='max'),enabled=True,view=view).grouping)
        self.assertFalse(make_engine(b,state,past[:1],rules,strategy,enabled=True,view=view).grouping)
        seven=initial_white_source(7,2,actors=(1,2))
        self.assertFalse(make_engine(*seven[2:7],enabled=True,view=seven[7]).grouping)

    def test_default_entry_never_selects_experimental_engine(self):
        from werewolf.model_a_public import public_forecast
        data,roles,b,s,past,rules,strategy,view=source(5,1)
        with patch('werewolf.match_groups.make_engine',side_effect=AssertionError('default changed')):
            result=public_forecast(b,s,past,rules,strategy,max_seconds=3)
        self.assertEqual(result.village_win,F(7,15))
    def test_max_private_hunter_and_nine_are_fallback(self):
        data,roles,b,s,past,rules,strategy,view=source()
        self.assertFalse(make_engine(b,s,past,rules,Strategy(),enabled=True,view=view).grouping)
        self.assertFalse(make_engine(b,s,past,rules,strategy,enabled=True,view=replace(view,scope=view.scope.personal('seer',(1,),[]))).grouping)
        hunter=initial_board(5,1,0,1,1)
        self.assertFalse(make_engine(hunter,s,past,rules,strategy,enabled=True,view=view).grouping)
        data,roles,b,s,past,rules,strategy,view=source(9,2)
        self.assertFalse(make_engine(b,s,past,rules,strategy,enabled=True,view=view).grouping)
    def test_candidate_information_ignores_names_and_display_rates(self):
        *_,view=source()
        before=PublicRelations.from_view(view)
        players=tuple(replace(p,display_name='different',legacy=ReadMap(tuple((k,F(1,2)if k=='wolf_probability'else v)for k,v in p.legacy.items_tuple)))for p in view.players)
        self.assertEqual(before,PublicRelations.from_view(replace(view,players=players)))
        self.assertEqual(before.candidate_groups(),((1,),(2,3,4,5,6)))
    def test_received_claim_correction_and_withdraw_regenerate_relations(self):
        h=view_helpers.PlayerViewTests();h.setUp();h.start(1)
        claims=['seer']+['latent']*4
        h.table(claims,[{'day':1,'reporter':1,'target':3,'color':'white'}]);old=h.build()[3]
        a=PublicRelations.from_view(old);self.assertFalse(any(3 in g and 4 in g for g in a.candidate_groups()))
        h.table(claims,[{'day':1,'reporter':1,'target':4,'color':'white'}]);new=h.build()[3]
        self.assertNotEqual(a,PublicRelations.from_view(new));self.assertEqual(old.by_id(3).received_claims[0].target,3)
        h.table(['latent']*5,[]);withdrawn=h.build()[3]
        self.assertEqual(PublicRelations.from_view(withdrawn).reports,())
    def test_joint_counterexample_same_rates_remains_different(self):
        keys=[];rates=[]
        for edges in [[(2,3),(3,4),(4,5),(5,6),(6,7),(7,2)],[(2,3),(3,4),(4,2),(5,6),(6,7),(7,5)]]:
            worlds=tuple((sum(1<<(p-1)for p in pair),0,1,0,F(1,6))for pair in edges)
            b=replace(replace_worlds(initial_board(7,2,0,1),worlds),claims=('seer',)+('latent',)*6)
            s=TrueScanState(tuple(Hypothesis(w[:-1],(),w[-1])for w in worlds),((1,2,3,4,5,6,7),),'none')
            rates.append(tuple(b.role_probability(p,'wolf')for p in b.alive))
            keys.append(canonical_key(b,s,(),s,None,Rules(initial_seer='none'),Strategy('random','random'),max_mappings=1000))
        self.assertEqual(*rates);self.assertTrue(all(k is not None for k in keys));self.assertNotEqual(*keys)
    def test_secret_candidates_are_joint_distributions_not_independent_players(self):
        data,roles,b,s,past,rules,strategy,view=source(6,2)
        self.assertEqual(b.joint_wolf_probability((2,3)),F(1,10))
        self.assertNotEqual(b.joint_wolf_probability((2,3)),b.role_probability(2,'wolf')*b.role_probability(3,'wolf'))
        self.assertGreater(len({h.roles for h in s.hypotheses}),1)
        self.assertTrue(make_engine(b,s,past,rules,strategy,enabled=True,view=view).grouping)

if __name__=='__main__':unittest.main()