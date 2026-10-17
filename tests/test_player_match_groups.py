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
    def test_seven_root_stays_fallback_without_completed_audit(self):
        data,roles,b,s,past,rules,strategy,view=source(7,1)
        engine=make_engine(b,s,past,rules,strategy,enabled=True,view=view)
        self.assertFalse(engine.grouping)
        self.assertFalse(engine.supported(b,None))
        data,roles,b,s,past,rules,strategy,view=source(7,2)
        self.assertFalse(make_engine(b,s,past,rules,strategy,enabled=True,view=view).grouping)

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