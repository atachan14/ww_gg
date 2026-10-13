import copy,json,re,unittest
from app import create_app
from werewolf.exact import initial_board,Progress,Rules
from werewolf.dawn import advance_step


def replay(g):
    rules=Rules(**g['rules']);progress=Progress.initial(initial_board(g['players'],g['wolves']))
    for step in g['history']:progress=advance_step(progress,step,rules)
    return rules,progress


class NightFlagScopeTests(unittest.TestCase):
    def test_pending_corpse_does_not_condition_current_public_or_private_values(self):
        a=create_app({'TESTING':True,'SECRET_KEY':'night-flag-scope','HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True})
        c=a.test_client();c.post('/start',data={'citizens':'4','wolves':'1','initial_seer':'none','day':'max','night':'random'})
        def game():
            with c.session_transaction() as session:return copy.deepcopy(session['game'])
        g=game();c.post('/advance',data={'revision':str(g['revision']),'target':'5','day':'max','night':'random'})
        before=game();board_before=replay(before)[1].board
        fractions=lambda:re.findall(r'data-fraction="([^"]+)"',c.get('/main').get_data(as_text=True))
        public_values=fractions()
        def view():
            g=game();r=c.post('/private-view',data={'revision':str(g['revision']),'board_id':g['public_log']['board_id'],
                'payload':json.dumps({'role':'wolf','players':[1],'results':[]})})
            self.assertEqual(r.status_code,200)
            return r.get_json()['players']
        own_values=view();g=game()
        self.assertEqual(c.post('/dawn-report',data={'revision':str(g['revision']),'board_id':g['public_log']['board_id'],
                                                  'mode':'deaths','deaths':'2'}).status_code,303)
        marked=game()
        self.assertEqual(replay(marked)[1].board,board_before)
        self.assertEqual(fractions(),public_values)
        self.assertEqual(view(),own_values)
        g=game()
        self.assertEqual(c.post('/dawn-advance',data={'revision':str(g['revision']),'board_id':g['public_log']['board_id']}).status_code,303)
        next_board=replay(game())[1].board
        self.assertEqual((next_board.day,next_board.phase),(2,'day'))
        self.assertNotIn(2,next_board.alive)
        self.assertNotEqual(next_board,board_before)
