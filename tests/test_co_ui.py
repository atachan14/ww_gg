import re
import unittest
from app import create_app
from werewolf.co_ui import medium_timeline, CO_RENDERERS
from werewolf.exact import initial_board, condition_claims, ClaimPolicy, Progress, advance, Rules, Strategy


class COUITests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING':True,'SECRET_KEY':'co-ui-only'})
        self.c = self.app.test_client()
        self.c.post('/start',data={'citizens':'3','mediums':'1','wolves':'1','day':'max','night':'max','cco_medium':'none'})

    def state(self):
        with self.c.session_transaction() as session:
            return session['game']

    def post(self, route, **changes):
        state=self.state()
        return self.c.post(route,data={'revision':str(state['revision']),'day':'max','night':'max',**changes})

    def html(self):
        return self.c.get('/main',follow_redirects=True).get_data(as_text=True)

    def day2(self, early=True):
        if early:self.post('/strategy',co_1='medium')
        self.post('/advance',target='2')
        self.post('/advance',target='3')
        if not early:self.post('/strategy',co_1='medium')

    def test_summary_is_display_control_and_exactly_one_role_input_per_player(self):
        html=self.html()
        for player in range(1,6):
            base=re.search(r'<tr[^>]*data-player="'+str(player)+r'"[^>]*>(.*?)</tr>',html,re.S).group(1)
            self.assertIn('class="co-summary"',base)
            self.assertNotIn('co-select',base)
            self.assertEqual(html.count('name="co_'+str(player)+'"'),0)
            self.assertIn('id="system-log"',html)
            self.assertIn('id="co-add-'+str(player)+'"',html)
        self.assertNotIn('霊能申告</h2>',html)

    def test_claimed_role_is_text_with_one_hidden_submission_field(self):
        self.post('/strategy',co_1='medium')
        row=re.search(r'<tr[^>]*id="co-role-1"[^>]*>(.*?)</tr>',self.html(),re.S).group(1)
        self.assertIn('class="co-role-label">霊能</span>',row)
        self.assertNotIn('<select',row)
        self.assertIn('type="hidden" class="co-select" name="co_1" value="medium"',row)
        base=re.search(r'<tr[^>]*data-player="2"[^>]*>(.*?)</tr>',self.html(),re.S).group(1)
        button=re.search(r'<button[^>]*class="co-summary"[^>]*>(.*?)</button>',base,re.S).group(1)
        self.assertNotIn('潜伏',button)
        self.assertIn('co-arrow',button)

    def test_display_game_identity_stays_across_boards_and_resets_only_on_successful_start(self):
        def key():
            return re.search(r'data-co-game="([^"]+)"',self.html()).group(1)
        initial=key()
        self.post('/strategy',co_1='medium')
        self.assertEqual(key(),initial)
        self.post('/advance',target='2')
        self.assertEqual(key(),initial)
        self.c.post('/back',data={'revision':str(self.state()['revision'])})
        self.assertEqual(key(),initial)
        self.assertNotIn("co_display_game",self.state())
        self.assertEqual(self.c.post('/start',data={'citizens':'invalid'}).status_code,400)
        self.assertEqual(key(),initial)
        self.c.post('/start',data={'citizens':'3','mediums':'1','wolves':'1','day':'max','night':'max'})
        self.assertNotEqual(key(),initial)

    def test_day1_none_and_night_next_day_do_not_create_report_input(self):
        self.post('/strategy',co_1='medium')
        html=self.html()
        self.assertIn('Day1：なし / --',html)
        self.assertNotIn('name="report_',html)
        self.post('/advance',target='2')
        html=self.html()
        self.assertIn('Day2：Player2 / 翌日昼に入力',html)
        self.assertNotIn('name="report_2_1_2"',html)

    def test_medium_report_belongs_to_single_role_row_and_changes_exact_board(self):
        self.day2()
        html=self.html()
        row=re.search(r'<tr[^>]*id="co-role-1"[^>]*>(.*?)</tr>',html,re.S).group(1)
        self.assertIn('name="report_2_1_2"',row)
        self.assertIn('value="" selected>未公開',row)
        self.assertEqual(html.count('name="report_2_1_2"'),1)
        before=self.state()['history'][:]
        self.assertEqual(self.post('/strategy',report_2_1_2='black').status_code,303)
        self.assertEqual(self.state()['reports'],[{'day':2,'reporter':1,'target':2,'color':'black'}])
        self.assertEqual(self.state()['history'],before)
        reported_row=re.search(r'<tr[^>]*data-player="1"[^>]*>(.*?)</tr>',self.html(),re.S).group(1)
        self.assertRegex(reported_row,r'<td data-value-cell="wolf" class="wolf-text"><strong[^>]*data-fraction="1"')
        self.assertEqual(self.post('/strategy',report_2_1_2='').status_code,303)
        self.assertEqual(self.state()['reports'],[])
        self.assertIn('value="" selected>未公開',self.html())
        self.c.post('/back',data={'revision':str(self.state()['revision'])})
        self.assertNotIn('name="report_2_1_2"',self.html())

    def test_late_co_is_not_an_eligible_medium_observation(self):
        self.day2(early=False)
        html=self.html()
        self.assertIn('Day2：Player2 / 報告機会なし',html)
        self.assertNotIn('name="report_2_1_2"',html)
        saved=self.state().copy()
        self.assertEqual(self.post('/strategy',report_2_1_2='white').status_code,400)
        self.assertEqual(self.state(),saved)

    def test_co_edit_remove_and_multiple_submission_does_not_enable_gidora(self):
        self.assertEqual(self.post('/strategy',co_1='medium').status_code,303)
        self.assertIn('data-co-remove="1"',self.html())
        self.assertEqual(self.post('/strategy',co_1='latent').status_code,303)
        self.assertNotIn('id="co-role-1"',self.html())
        self.assertEqual(self.post('/strategy',co_1='medium,seer').status_code,400)
        self.assertEqual(self.state()['claims'][0],'latent')
        self.assertEqual(self.post('/strategy',co_1='medium').status_code,303)
        self.assertEqual(self.html().count('name="co_1"'),1)

    def test_role_renderer_does_not_invent_other_ability_inputs(self):
        self.c.post('/start',data={'citizens':'2','mediums':'1','seers':'1','hunters':'1','wolves':'1','day':'max','night':'max'})
        self.post('/strategy',co_1='seer',co_2='hunter')
        html=self.html()
        self.assertEqual(html.count('能力未対応'),1)
        self.assertIn('name="seer_target_1_1"',html)
        self.assertNotIn('name="report_',html)
        self.assertNotEqual(CO_RENDERERS['medium'],CO_RENDERERS['seer'])

    def test_current_co_edit_keeps_prior_reports_and_does_not_rewrite_history(self):
        self.day2()
        self.post('/strategy',report_2_1_2='black')
        reports=self.state()['reports'][:]
        history=self.state()['history'][:]
        self.assertEqual(self.post('/strategy',co_1='latent').status_code,303)
        self.assertEqual(self.state()['reports'],reports)
        self.assertEqual(self.state()['history'],history)
        self.assertEqual(self.post('/strategy',co_1='medium').status_code,303)
        self.assertIn('value="black" selected>黒',self.html())
        self.assertEqual(self.state()['reports'],reports)

    def test_finished_co_detail_is_read_only_without_future_report_day(self):
        self.day2()
        self.post('/strategy',report_2_1_2='white')
        self.post('/advance',target='4')
        html=self.html()
        self.assertIn('data-screen="result"',html)
        self.assertIn('Day2：Player2 / 白',html)
        self.assertNotIn('name="report_',html)
        self.assertNotIn('翌日昼に入力',html)
        self.assertIn('data-co-toggle="1"',html)

    def test_timeline_presentation_is_pure_and_dates_are_ordered(self):
        board=condition_claims(initial_board(5,1,1),('medium',)+('latent',)*4,ClaimPolicy(medium='none'))
        progress=advance(Progress(board),2,Rules(),Strategy())
        self.assertEqual([entry['day'] for entry in medium_timeline(progress.board,1)],[1,2])
        self.assertEqual(medium_timeline(progress.board,1)[1]['state'],'next_day')
        progress=advance(progress,3,Rules(),Strategy())
        self.assertEqual(medium_timeline(progress.board,1)[1]['state'],'input')
        self.assertTrue(medium_timeline(progress.board,1)[1]['editable'])
        self.assertFalse(medium_timeline(progress.board,1,finished=True)[1]['editable'])
        self.assertEqual(progress.board.reports,())


if __name__=='__main__':unittest.main()
