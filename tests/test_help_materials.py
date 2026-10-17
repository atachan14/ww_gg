import copy,hashlib,re,unittest
from html.parser import HTMLParser
from app import create_app
from werewolf.help_materials import MATERIALS,STEP3_SCRIPT_SHA256,CALCULATION_SCRIPT_SHA256
class Tags(HTMLParser):
    def __init__(self):super().__init__();self.ids=set();self.lanes=0;self.steps=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);self.ids.add(a.get('id'))
        self.lanes+='lane' in a.get('class','').split();self.steps+='step' in a.get('class','').split()
class HelpMaterialsTests(unittest.TestCase):
    def setUp(self):
        self.c=create_app({'TESTING':True,'SECRET_KEY':'materials-fixture'}).test_client()
        self.c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
    def raw(self,page):
        response=self.c.get('/help/history/materials/raw/'+page)
        try:return response.get_data(as_text=True)
        finally:response.close()
    def test_all_routes_navigation_privacy_and_session(self):
        with self.c.session_transaction() as session:before=copy.deepcopy(dict(session))
        root=self.c.get('/help/history/materials/');self.assertEqual(root.status_code,200)
        overview=root.get_data(as_text=True)
        for page in MATERIALS:
            self.assertIn('/help/history/materials/'+page,overview)
            wrapper=self.c.get('/help/history/materials/'+page);self.assertEqual(wrapper.status_code,200)
            self.assertIn('当時',wrapper.get_data(as_text=True));self.assertIn('sandbox=',wrapper.get_data(as_text=True))
            raw=self.c.get('/help/history/materials/raw/'+page);self.assertEqual(raw.status_code,200)
            text=raw.get_data(as_text=True)
            self.assertIn('sandbox allow-scripts',raw.headers['Content-Security-Policy'])
            self.assertIn("connect-src 'none'",raw.headers['Content-Security-Policy'])
            for bad in ('source_thread_id','Sentinel_','親レビュー','親経由','完了確認','完了承認','C:\\Users','G:\\source','file://'):
                self.assertNotIn(bad,text,page)
            self.assertIsNone(re.search('ユーザー[^<。]{0,35}[「『]',text),page)
            self.assertNotIn('Set-Cookie',raw.headers);raw.close()
        for bad in ('unknown','../../app.py','step3.html','step3?file=app.py'):
            if '?' in bad:continue
            self.assertEqual(self.c.get('/help/history/materials/raw/'+bad).status_code,404)
        self.assertIn('Step別の元資料',self.c.get('/help/history/v0.5.2').get_data(as_text=True))
        with self.c.session_transaction() as session:self.assertEqual(dict(session),before)
    def test_original_diagram_scripts_and_lane_structure_are_preserved(self):
        for page,expected in [('step3',STEP3_SCRIPT_SHA256),('calculation-flow',CALCULATION_SCRIPT_SHA256)]:
            text=self.raw(page)
            script=re.findall(r'<script>(.*?)</script>',text,re.S)[0]
            self.assertEqual(hashlib.sha256(script.replace('\r\n','\n').encode()).hexdigest(),expected)
        text=self.raw('step3');tags=Tags();tags.feed(text)
        self.assertTrue({'proposal-a','proposal-b','proposal-c'}<=tags.ids)
        for key in ('a','b','c'):self.assertIn('data-graph="'+key+'"',text)
        text=self.raw('step4');tags=Tags();tags.feed(text)
        self.assertEqual(tags.lanes,4);self.assertEqual(tags.steps,24)
        self.assertTrue({'flow-existing','flow-a','flow-b','flow-c'}<=tags.ids)
    def test_step1_is_honest_markdown_conversion_and_current_b_is_separate(self):
        text=self.raw('step1')
        self.assertIn('独立した旧HTMLがありません',text);self.assertIn('比較対象の1盤面',text)
        text=self.c.get('/help/history/materials/step3').get_data(as_text=True)
        self.assertIn('採用後のB案フロー',text);self.assertIn('検討時点',text)
