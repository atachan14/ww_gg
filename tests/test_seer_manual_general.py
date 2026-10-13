import unittest,copy
from fractions import Fraction as F
from dataclasses import replace
from app import create_app
from werewolf.seer_manual import MODE,replay,pending,condition
from werewolf.exact import initial_board,condition_claims,ClaimPolicy
from werewolf import reports

class SeerManualGeneralTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SECRET_KEY':'general-test'});self.client=self.app.test_client()
    def game(self):
        with self.client.session_transaction() as s:return copy.deepcopy(s['game'])
    def start(self,n,w=1,s=1,m=0,h=0,initial="random_white"):
        data={'citizens':str(n-w-s-m-h),'wolves':str(w),'seers':str(s),'mediums':str(m),'hunters':str(h),'seer_mode':MODE,'day':'max','night':'max','initial_seer':initial}
        self.assertEqual(self.client.post('/start',data=data).status_code,303)
    def form(self,**extra):
        g=self.game();data={'revision':str(g['revision']),'day':g['policy']['day'],'night':g['policy']['night'],'include_self_bite':'0'};data.update(extra);return data
    def configure(self,**extra):
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_likelihood='compatibility',**extra)).status_code,303)
    def advance(self,target):self.assertEqual(self.client.post('/advance',data=self.form(target=str(target))).status_code,303)

    def test_one_through_nine_initial_casts_and_zero_co(self):
        for n in range(1,10):
            with self.subTest(n=n):
                self.start(n,w=0 if n==1 else 1,s=1 if n!=2 else 0)
                if n>2:self.configure()
                html=self.client.get('/main',follow_redirects=True).data;self.assertIn(b'id="village-rate"',html);self.assertNotIn(b'data-seer-pending',html)
                self.assertEqual(self.game()['claims'],['latent']*n)
                self.assertEqual(replay(self.game())[1].finished,n<=2)

    def test_no_wolves_or_initial_wolf_majority_are_defined_terminal_casts(self):
        for n in (3,5,9):
            for wolves in (0,n//2+1,n):
                with self.subTest(n=n,wolves=wolves):
                    self.start(n,w=wolves,s=1 if wolves<n else 0)
                    p=replay(self.game())[1];self.assertTrue(p.finished)
                    self.assertEqual(p.settled_village,F(int(wolves==0)))
                    html=self.client.get('/main',follow_redirects=True).data;self.assertIn(b'id="village-rate"',html);self.assertNotIn(b'data-seer-pending',html)
        with self.assertRaises(ValueError):initial_board(5,0,0,1)
        self.assertEqual(initial_board(5,0,0,1,experimental_cast=True).winner,'village')

    def test_zero_seers_manual_matches_ordinary_role_prior(self):
        self.start(5,s=0);self.configure();board=replay(self.game())[1].board
        self.assertEqual(board.worlds,initial_board(5,1).worlds)

    def test_one_co_true_report_and_latent_true_seers_allowed(self):
        self.start(5,s=2);self.configure(co_1='seer')
        board=replay(self.game())[1].board
        self.assertTrue(any(s&2 for w,m,s,h,q in board.worlds));self.assertIsNone(pending(self.game()))
        self.configure(seer_target_1_1='3',seer_color_1_1='black')
        board=replay(self.game())[1].board
        self.assertTrue(all(not s&1 for w,m,s,h,q in board.worlds))

    def test_multiple_true_seers_coupled_reports_and_contradiction_atomic(self):
        self.start(5,s=2,initial='normal');self.configure(co_1='seer',co_2='seer',seer_target_1_1='3',seer_color_1_1='white',seer_target_1_2='4',seer_color_1_2='black')
        board=replay(self.game())[1].board;self.assertTrue(all(w==8 and s==3 for w,m,s,h,q in board.worlds))
        old=self.game();response=self.client.post('/strategy',data=self.form(seer_target_1_2='3',seer_color_1_2='black'))
        self.assertEqual(response.status_code,400);self.assertEqual(self.game(),old)

    def test_many_co_and_multiple_wolves_preserve_joint_support(self):
        self.start(5,w=2,s=2);self.configure(**{f'co_{p}':'seer' for p in range(1,5)})
        board=replay(self.game())[1].board;self.assertEqual(len(board.worlds),6)
        self.assertTrue(all(s.bit_count()==2 and w.bit_count()==2 and (w|s)==15 for w,m,s,h,q in board.worlds))

    def test_high_player_ids_dynamic_fields_cache_and_terminal(self):
        self.start(9,w=2,s=1);self.configure(co_9='seer',seer_target_1_9='8',seer_color_1_9='white')
        g=self.game();board=replay(g)[1].board;self.assertEqual(board.role_probability(9,'seer'),1);self.assertEqual(board.wolf_probability(8),0)
        self.assertIn(b'name="seer_target_1_9"',self.client.get('/main',follow_redirects=True).data)
        self.start(3);self.configure();self.assertEqual(replay(self.game())[1].board.player_count,3)
        self.start(1,w=0,s=1);html=self.client.get('/main',follow_redirects=True).data;self.assertIn(b'data-fraction="1"',html)

    def test_ability_scope_is_in_help_not_permanent_main_prose(self):
        self.start(7,w=2,s=1,m=1,h=1)
        html=self.client.get('/main').data;help=self.client.get('/help/specs').get_data(as_text=True)
        self.assertNotIn(b'data-information-fixed-scope',html);self.assertIn('護衛・GJは未対応',help);self.assertIn('従来の未来報告モデル',help)

    def test_mixed_roles_abilityless_hunter_explicit_and_unmodified_prior(self):
        self.start(7,w=2,s=1,m=1,h=1);self.configure()
        board=replay(self.game())[1].board;self.assertEqual(board.worlds,initial_board(7,2,1,1,1).worlds)
        html=self.client.get('/main',follow_redirects=True).data;self.assertIn('狩人護衛・GJは未対応',self.client.get('/help/specs').get_data(as_text=True))
        self.assertEqual(board.initial_hunter_count,1)

    def mixed_progress(self):
        self.start(7,w=2,s=1,m=2,initial='normal')
        self.configure(co_1='seer',co_2='medium',co_3='medium')
        self.advance(4);self.advance(5)

    def test_medium_and_seer_reports_condition_same_joint_history(self):
        self.mixed_progress()
        self.configure(report_2_2_4='white',report_2_3_4='white',seer_target_2_1='6',seer_color_2_1='black')
        board=replay(self.game())[1].board
        self.assertEqual(len(board.reports),2)
        self.assertTrue(all(not w&8 and w&32 and m==6 and s==1 for w,m,s,h,q in board.worlds))
        old=self.game();self.assertEqual(self.client.post('/strategy',data=self.form(report_2_3_4='black')).status_code,400);self.assertEqual(self.game(),old)

    def test_medium_correction_replays_from_origin_and_keeps_actions(self):
        self.mixed_progress();self.configure(report_2_2_4='black')
        before=self.game();self.configure(report_2_2_4='white')
        after=self.game();self.assertEqual(after['history'],before['history'])
        board=replay(after)[1].board;self.assertTrue(all(not w&8 for w,m,s,h,q in board.worlds))
        self.assertEqual([e.target for e in board.history],[4,5])

    def test_mixed_report_back_and_cold_cookie_restore(self):
        self.mixed_progress();self.configure(report_2_2_4='white',seer_target_2_1='6',seer_color_2_1='black')
        self.advance(6)
        self.assertEqual(self.client.post('/back',data={'revision':str(self.game()['revision'])}).status_code,303)
        self.assertEqual(self.game()['reports'],[{'day':2,'reporter':2,'target':4,'color':'white'}])
        self.assertEqual(self.game()['seer_inputs'][0]['day'],2)
        cookie=self.client.get_cookie('session').value
        import werewolf.seer_manual as manual
        manual._replay.cache_clear()
        other=create_app({'TESTING':True,'SECRET_KEY':'general-test'}).test_client();other.set_cookie('session',cookie)
        self.assertEqual(other.get('/main',follow_redirects=True).status_code,200)
        self.assertEqual(self.client.post('/back',data={'revision':str(self.game()['revision'])}).status_code,303)
        self.assertEqual(self.game()['reports'],[]);self.assertEqual(self.game()['seer_inputs'],[])

    def test_budget_pending_and_recovery_with_cache(self):
        self.start(7,w=2,s=1,m=2,initial='normal');self.configure(co_1='seer',co_2='medium',co_3='medium')
        self.assertIn(b'id="village-rate"',self.client.get('/main',follow_redirects=True).data)
        self.app.config['MANUAL_CALC_MAX_WORK']=1
        html=self.client.get('/main',follow_redirects=True).data;self.assertIn(b'data-seer-pending',html);self.assertNotIn(b'id="village-rate"',html);self.assertIn('計算予算'.encode(),html)
        self.app.config['MANUAL_CALC_MAX_WORK']=250000
        self.assertIn(b'id="village-rate"',self.client.get('/main',follow_redirects=True).data)

    def test_later_co_uses_current_day_and_old_co_reports_survive_removal(self):
        self.start(7,w=2,initial='normal');self.configure()
        self.advance(2);self.advance(4)
        history=copy.deepcopy(self.game()['history'])
        self.configure(co_1='seer',seer_target_2_1='3',seer_color_2_1='white')
        self.assertEqual(self.game()['history'],history)
        html=self.client.get('/main').data
        self.assertIn(b'name="seer_target_2_1"',html);self.assertNotIn(b'name="seer_target_1_1"',html)
        self.advance(6)
        history=copy.deepcopy(self.game()['history'])
        self.configure(co_1='latent')
        html=self.client.get('/main').data
        self.assertIn('過去の占い報告'.encode(),html);self.assertIn(b'name="seer_target_2_1"',html)
        self.assertEqual(self.game()['history'],history)
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_target_1_1='3',seer_color_1_1='white')).status_code,400)

    def test_random_white_joint_likelihood_literal_two_true_seers(self):
        board=condition_claims(initial_board(5,1,0,2),('seer','seer','latent','latent','latent'),ClaimPolicy())
        rows=({'day':1,'reporter':1,'target':3,'color':'white'},{'day':1,'reporter':2,'target':3,'color':'white'})
        result=condition(board,rows,{'initial_rule':'random_white','likelihood':'compatibility'},board.alive)
        self.assertEqual({w:q for w,m,s,h,q in result.worlds},{8:F(1,2),16:F(1,2)})
        self.assertEqual(sum(q for w,m,s,h,q in result.worlds),1)

if __name__=='__main__':unittest.main()
