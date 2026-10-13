import copy
import unittest
from dataclasses import replace
from fractions import Fraction as F
from itertools import permutations
from werewolf.exact import initial_board, replace_worlds, action_outcomes, Rules, Strategy, PublicEvent
from werewolf.seer_acquisition import from_board, Acquisition, Hypothesis
from werewolf.seer_future_uniform import TrueScanState, FuturePending
from werewolf.seer_future_forecast import project_private
from werewolf.seer_view_forecast import seer_forecast


def fixture(weights=(F(3,5),F(3,10),F(1,10))):
    seed=replace(replace_worlds(initial_board(5,1,0,1),tuple((mask,0,1,0,q) for mask,q in zip((2,4,8),weights))),
                 claims=('seer','latent','latent','latent','latent'))
    b=next(o.board for o in action_outcomes(seed,5,Rules(initial_seer='none'),Strategy()) if o.board.winner is None)
    s=project_private(TrueScanState(from_board(seed),((1,2,3,4,5),),initial_rule='none'),b)
    return b,s


class SeerForecastTests(unittest.TestCase):
    def test_target_information_values_are_computed_not_constant(self):
        b,s=fixture();before=copy.deepcopy((b,s))
        result=seer_forecast(b,1,(),Rules(initial_seer='none'),Strategy('max','random'),scan_state=s)
        self.assertEqual(dict(result),{2:F(5,6),3:F(5,6),4:F(23,30)})
        self.assertEqual((b,s),before)

    def test_symmetric_targets_and_max_ties_are_equal(self):
        b,s=fixture((F(1,3),)*3)
        result=seer_forecast(b,1,(),Rules(initial_seer='none'),Strategy(),scan_state=s)
        self.assertEqual(len(set(dict(result).values())),1)

    def test_none_disclosure_and_latent_co_remain_explicit_pending(self):
        b,s=fixture()
        self.assertIsInstance(seer_forecast(b,1,(),Rules(),Strategy(seer_disclosure='none'),scan_state=s),FuturePending)
        b=replace(b,claims=('latent',)*5)
        self.assertIsInstance(seer_forecast(b,1,(),Rules(),Strategy(),scan_state=s),FuturePending)

    def test_secret_past_results_are_truth_and_acquisition_days_are_distinct(self):
        from werewolf.seer_acquisition import normalize
        b,s=fixture();s=replace(s,initial_rule='normal',hypotheses=normalize(tuple(Hypothesis(h.roles,(Acquisition(1,1,2,'white'),),h.mass) for h in s.hypotheses if h.roles[0]!=2)))
        b=replace_worlds(b,s.public_roles)
        result=seer_forecast(b,1,(Acquisition(1,1,2,'white'),),Rules(initial_seer='normal'),Strategy(),scan_state=s)
        self.assertEqual(set(dict(result)),{3,4})
        with self.assertRaises(ValueError):
            seer_forecast(b,1,(Acquisition(1,1,2,'black'),),Rules(initial_seer='normal'),Strategy(),scan_state=s)

    def test_relabeling_of_asymmetric_public_prior_and_seer_is_invariant(self):
        b,s=fixture();expected=dict(seer_forecast(b,1,(),Rules(initial_seer='none'),Strategy('max','random'),scan_state=s))
        for ids in permutations((1,2,3,4)):
            mapping=dict(zip((1,2,3,4,5),(*ids,5)))
            def mask(v):return sum(1<<(mapping[p]-1) for p in mapping if v&(1<<(p-1)))
            hs=tuple(Hypothesis(tuple(mask(v) for v in h.roles),(),h.mass) for h in s.hypotheses)
            st=TrueScanState(hs,s.rosters,initial_rule='none')
            claims=['latent']*5;claims[mapping[1]-1]='seer'
            renamed=replace(replace_worlds(b,st.public_roles),claims=tuple(claims),history=tuple(PublicEvent(e.day,e.phase,mapping[e.target]) for e in b.history))
            actual=dict(seer_forecast(renamed,mapping[1],(),Rules(initial_seer='none'),Strategy('max','random'),scan_state=st))
            self.assertEqual(actual,{mapping[p]:v for p,v in expected.items()})

    def test_private_scan_choice_never_changes_public_scores(self):
        b,s=fixture();trace={}
        seer_forecast(b,1,(),Rules(initial_seer='none'),Strategy('max','random'),scan_state=s,trace=trace)
        roots=[x for x in trace['wolf_policies'] if tuple((e.day,e.phase,e.target) for e in x['history'])==((1,'day',5),)]
        self.assertTrue(roots)
        for mask in (2,4,8):
            policies=[x['policy'] for x in roots if x['mask']==mask]
            # Three private targets now reuse one public roster policy. Existing
            # black-holder/permutation tests independently check its invariance.
            self.assertEqual(len(policies),1)



class SeerRouteTests(unittest.TestCase):
    def test_public_co_scope_secret_history_none_and_public_cookie_identity(self):
        import json
        from app import create_app
        a=create_app({'TESTING':True,'SECRET_KEY':'seer-view-tests','HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True})
        c=a.test_client();c.post('/start',data={'citizens':'3','seers':'1','wolves':'1','initial_seer':'normal','day':'max','night':'random'})
        def game():
            with c.session_transaction() as session:return copy.deepcopy(session['game'])
        g=game();payload={'claims':['seer','latent','latent','latent','latent'],'seers':[{'day':1,'reporter':1,'target':2,'color':'white'}],'mediums':[]}
        r=c.post('/table-publish',data={'revision':str(g['revision']),'payload':json.dumps(payload)})
        self.assertEqual(r.status_code,200,r.get_data(as_text=True));g=game()
        self.assertEqual(c.post('/advance',data={'revision':str(g['revision']),'target':'5','day':'max','night':'random'}).status_code,303)
        before=game();cookie=c.get_cookie('session').value
        def view(results):
            g=game();return c.post('/private-view',data={'revision':str(g['revision']),'board_id':g['public_log']['board_id'],'payload':json.dumps({'role':'seer','players':[1],'results':results})})
        for results in ([],[{'day':1,'target':2,'color':'white'}]):
            response=view(results);self.assertEqual(response.status_code,200,response.get_data(as_text=True))
            if not results: self.assertEqual(response.get_json()['acquisitions'],[])
            self.assertTrue(any(row['final'] is not None for row in response.get_json()['players']))
            self.assertEqual(game(),before);self.assertEqual(c.get_cookie('session').value,cookie)
        self.assertEqual(view([{'day':1,'target':2,'color':'black'}]).status_code,400)
        self.assertEqual(view([{'day':1,'target':3,'color':'white'}]).status_code,400)
        self.assertEqual(game(),before)
        with c.session_transaction() as session:
            session['game']={**session['game'],'policy':{**session['game']['policy'],'seer_disclosure':'none'}}
        response=view([]);self.assertEqual(response.status_code,200)
        self.assertTrue(all(row['final'] is None for row in response.get_json()['players']))
        self.assertIn('なし開示',response.get_json()['reason'])
