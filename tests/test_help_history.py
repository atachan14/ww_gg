import copy, unittest
from app import create_app
from werewolf.help_history import VERSIONS
from tests.test_help_program import Links

class HistoryHelpTests(unittest.TestCase):
    def test_navigation_dates_scope_and_session_preservation(self):
        c=create_app({'TESTING':True,'SECRET_KEY':'history-fixture'}).test_client()
        c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
        with c.session_transaction() as s:before=copy.deepcopy(dict(s))
        paths=['/help/history/']+['/help/history/'+v['id'] for v in VERSIONS]+['/help/history/v0.5.2-design']
        for path in paths:
            response=c.get(path);self.assertEqual(response.status_code,200)
            html=response.get_data(as_text=True);parsed=Links();parsed.feed(html)
            for href in parsed.links:
                if href.startswith('/help/'):self.assertEqual(c.get(href).status_code,200,href)
            self.assertNotIn('C:\\Users',html);self.assertNotIn('G:\\source',html)
            self.assertNotIn('承認待ち',html);self.assertNotIn('source_thread',html)
            self.assertIn('<summary>開発履歴</summary>',html)
        overview=c.get(paths[0]).get_data(as_text=True)
        positions=[overview.index('<h2><a href="/help/history/'+v['id']+'">') for v in VERSIONS]
        self.assertEqual(positions,sorted(positions))
        self.assertIn('個別の公開日は確認できていません',overview)
        release=c.get('/help/history/v0.5.2').get_data(as_text=True)
        self.assertIn('役職率を先に表示し',release)
        self.assertNotIn('役職率先行表示と計算中の枝位置表示は',release)
        design=c.get(paths[-1]).get_data(as_text=True)
        self.assertIn('現在の基準ではありません',design)
        self.assertIn('C案',design)
        with c.session_transaction() as s:self.assertEqual(dict(s),before)
        for bad in ['unknown','../../app.py','v0.5.3']:
            self.assertEqual(c.get('/help/history/'+bad).status_code,404)
