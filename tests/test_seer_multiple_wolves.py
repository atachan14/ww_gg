import copy
import json
import unittest
from dataclasses import replace
from fractions import Fraction as F
from app import create_app
from werewolf.exact import initial_board,replace_worlds,action_outcomes,Rules,Strategy
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState,FuturePending
from werewolf.seer_future_forecast import project_private
from werewolf.seer_view_forecast import seer_forecast


class MultipleWolfSeerTests(unittest.TestCase):
    def test_two_live_wolves_and_mixed_counts_are_not_blanket_pending(self):
        for worlds,counts in ((((6,0,1,0,F(1)),),{2}),
                              (((6,0,1,0,F(1,4)),(10,0,1,0,F(1,4)),(66,0,1,0,F(1,2))),{1,2})):
            with self.subTest(counts=counts):
                seed=replace(replace_worlds(initial_board(7,2,0,1),worlds),claims=('seer',)+('latent',)*6)
                b=next(o.board for o in action_outcomes(seed,7,Rules(initial_seer='none'),Strategy()) if o.board.winner is None)
                s=project_private(TrueScanState(from_board(seed),((1,2,3,4,5,6,7),),initial_rule='none',tracked=(1,)),b)
                before=copy.deepcopy((b,s))
                self.assertEqual(set(b.wolf_count_distribution),counts)
                values=seer_forecast(b,1,(),Rules(initial_seer='none'),Strategy(),scan_state=s)
                self.assertNotIsInstance(values,FuturePending)
                self.assertEqual(set(dict(values)),{2,3,4,5,6,7})
                self.assertTrue(all(0<=v<=1 for _,v in values));self.assertEqual((b,s),before)

    def test_private_count_prior_is_preserved_and_illegal_public_instruction_is_pending(self):
        from werewolf.wolf_view_forecast import wolf_forecast
        seed=replace(replace_worlds(initial_board(7,2,0,1),
             ((12,0,1,0,F(1,3)),(68,0,1,0,F(1,3)),(9,0,2,0,F(1,3)))),claims=('seer',)+('latent',)*6)
        b=next(o.board for o in action_outcomes(seed,7,Rules(initial_seer='none'),Strategy()) if o.board.winner is None)
        s=project_private(TrueScanState(from_board(seed),((1,2,3,4,5,6,7),),initial_rule='none',tracked=(1,)),b)
        trace={}
        wolf_forecast(b,None,Rules(initial_seer='none'),Strategy('max','random'),scan_state=s,
                      observer=lambda h,st:bool(h.roles[2]&1),trace=trace,max_work=1000000)
        root=next(x for x in trace['private_transitions'] if x['history']==((1,'day',7),) and x['target']==1)
        self.assertEqual(root['prior_counts'],{1:F(1,2),2:F(1,2)})
        self.assertEqual(root['child_counts'],((F(1),{1:F(1,2),2:F(1,2)}),))
        self.assertIn({1:F(1,3),2:F(2,3)},root['public_child_counts'])
        # Include a false-CO world at each count where player3 is not a wolf,
        # while the true viewer's private hypotheses all identify player3 as wolf.
        worlds=((12,0,1,0,F(1,4)),(68,0,1,0,F(1,4)),(9,0,2,0,F(1,4)),(65,0,2,0,F(1,4)))
        seed=replace_worlds(seed,worlds)
        b=next(o.board for o in action_outcomes(seed,7,Rules(initial_seer='none'),Strategy()) if o.board.winner is None)
        s=project_private(TrueScanState(from_board(seed),((1,2,3,4,5,6,7),),initial_rule='none',tracked=(1,)),b)
        result=wolf_forecast(b,None,Rules(initial_seer='none'),Strategy('max','random'),scan_state=s,
                             observer=lambda h,st:bool(h.roles[2]&1),max_work=1000000)
        self.assertIsInstance(result,FuturePending)
        self.assertEqual(result.reason,'seer_view_public_instruction_private_illegal')

    def test_requested_five_player_same_white_co_example_and_terminal_branch(self):
        a=create_app({'TESTING':True,'SECRET_KEY':'multi-seer','HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True})
        c=a.test_client()
        def game():
            with c.session_transaction() as session:return copy.deepcopy(session['game'])
        def start():
            c.post('/start',data={'citizens':'2','seers':'1','wolves':'2','initial_seer':'normal','day':'max','night':'random'})
            g=game();r=c.post('/table-publish',data={'revision':str(g['revision']),'payload':json.dumps({'claims':['seer','seer','latent','latent','latent'],'seers':[{'day':1,'reporter':p,'target':3,'color':'white'} for p in (1,2)],'mediums':[]})})
            self.assertEqual(r.status_code,200,r.get_data(as_text=True))
        start();g=game()
        self.assertEqual(c.post('/advance',data={'revision':str(g['revision']),'target':'1','day':'max','night':'random'}).status_code,303)
        before=game();cookie=c.get_cookie('session').value
        r=c.post('/private-view',data={'revision':str(before['revision']),'board_id':before['public_log']['board_id'],'payload':json.dumps({'role':'seer','players':[2],'results':[{'day':1,'target':3,'color':'white'}]})})
        self.assertEqual(r.status_code,200,r.get_data(as_text=True))
        self.assertEqual(r.get_json()['players'][3]['final'],{'village':'5/6','wolf':'1/6'})
        self.assertEqual(r.get_json()['players'][4]['final'],{'village':'5/6','wolf':'1/6'})
        self.assertEqual(game(),before);self.assertEqual(c.get_cookie('session').value,cookie)
        # Executing the publicly nonwolf target leaves two wolves among four:
        # every branch ends immediately; there is no continuing night to scan.
        start();g=game();r=c.post('/advance',data={'revision':str(g['revision']),'target':'3','day':'max','night':'random'})
        self.assertEqual(r.status_code,303);self.assertEqual(r.location,'/result')
        self.assertNotIn('id="board-viewpoint-seed"',c.get('/result').get_data(as_text=True))
