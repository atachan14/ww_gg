import ast,copy,unittest
from fractions import Fraction as F
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
from app import create_app
from werewolf.help_program import PAGES,REFERENCES,FIVE_FIXTURE,TERMS

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])

class ProgramHelpTests(unittest.TestCase):
    def setUp(self):
        self.c=create_app({'TESTING':True,'SECRET_KEY':'help-fixture'}).test_client()
        self.c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
    def game(self):
        with self.c.session_transaction() as s:return copy.deepcopy(s['game'])
    def test_pages_links_anchors_and_game_are_stable(self):
        before=self.game();cache={}
        for page in PAGES:
            path='/help/program/'+page;r=self.c.get(path);self.assertEqual(r.status_code,200)
            html=r.get_data(as_text=True);p=Links();p.feed(html);cache[path]=p
            self.assertIn('id="program-content"',html);self.assertIn('v0.5.1実装',html)
            self.assertNotIn('github.com/atachan14/ww_gg/tree/eb8116d',html)
        for page_path,p in cache.items():
            for href in p.links:
                url=urlsplit(href)
                if url.scheme or url.netloc:continue
                r=self.c.get(url.path or page_path,follow_redirects=True);self.assertEqual(r.status_code,200,href)
                if url.fragment:
                    dest=Links();dest.feed(r.get_data(as_text=True));self.assertIn(url.fragment,dest.ids,href)
                r.close()
        self.assertEqual(self.game(),before)
        self.assertEqual(self.c.get('/help/program/unknown').status_code,404)
        self.assertEqual(self.c.get('/help/program/../../app.py').status_code,404)
        self.assertIn('プログラム詳細（仮）',self.c.get('/help').get_data(as_text=True))
    def test_fixture_matches_exact_formula_and_existing_public_solver(self):
        from werewolf.exact import initial_board,Rules,Strategy
        from werewolf.model_a_public import public_forecast
        from werewolf.public_prior import prepare_public_prior
        b=initial_board(5,1);rules=Rules(initial_seer='none')
        s,past=prepare_public_prior({},b,rules,track_live_seers=False)
        value=public_forecast(b,s,past,rules,Strategy()).village_win
        self.assertEqual(value,F(FIVE_FIXTURE['village_win']))
        self.assertEqual(F(FIVE_FIXTURE['execution_wolf'])+F(FIVE_FIXTURE['execution_other'])*F(FIVE_FIXTURE['three_value']),value)
    def test_reference_symbols_and_tests_exist(self):
        for _,file,symbols,test in REFERENCES:
            tree=ast.parse(Path('werewolf',file).read_text(encoding='utf-8'))
            names={n.name for n in ast.walk(tree) if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
            self.assertTrue(set(symbols.split(' / '))<=names,(file,symbols))
            self.assertTrue(Path('tests',test+'.py').exists())
        self.assertEqual(len({t[0] for t in TERMS}),len(TERMS))
    def test_documentation_has_no_external_runtime_or_raw_html_code(self):
        for page in PAGES:
            h=self.c.get('/help/program/'+page).get_data(as_text=True)
            self.assertNotIn('<script src="https://',h)
        h=self.c.get('/help/program/design').get_data(as_text=True)
        self.assertIn('提案中・未実装',h);self.assertIn('未承認・未実装',h)
        from unittest.mock import patch
        with patch.dict(FIVE_FIXTURE,{'village_win':'<unsafe>&'}):
            h=self.c.get('/help/program/verification').get_data(as_text=True)
            self.assertIn('&lt;unsafe&gt;&amp;',h);self.assertNotIn('<unsafe>',h)
