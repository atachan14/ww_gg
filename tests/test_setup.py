import copy
from html.parser import HTMLParser
import unittest
from unittest.mock import patch

from werkzeug.datastructures import MultiDict
from app import create_app
from werewolf.exact import Rules
from werewolf.setup import CAST_PRESETS, RULE_PRESETS, GameConfig, SetupDraft, complete_rules, setup_count


class Controls(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.values = {}
        self.select = None
        self.options = []
        self.links = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('name'):
            self.values[attrs['name']] = attrs.get('value', '')
        if tag == 'a':
            self.links[attrs.get('id', attrs.get('class'))] = attrs.get('href')
        if tag == 'select':
            self.select = attrs.get('id')
            self.options = []
        if tag == 'option' and self.select:
            self.options.append((attrs.get('value', ''), 'selected' in attrs))

    def handle_endtag(self, tag):
        if tag == 'select' and self.select:
            self.values[self.select] = next((value for value, selected in self.options if selected), self.options[0][0])
            self.select = None


class SetupWebTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING':True, 'SECRET_KEY':'setup-tests-only'})
        self.client = self.app.test_client()
        self.sample = dict(citizens='4', mediums='0', seers='0', hunters='0', wolves='1', allow_self_bite='0', day='max', night='max')

    def state(self):
        with self.client.session_transaction() as session:
            return copy.deepcopy(session.get('game'))

    def top(self):
        return Controls(self.client.get('/').get_data(as_text=True))

    def start(self, **changes):
        return self.client.post('/start', data={**self.sample, **changes})

    def test_first_visit_and_invalid_session_use_samples_without_repairing_game(self):
        controls = self.top().values
        self.assertEqual(controls['cast-preset'], 'five_sample')
        self.assertEqual(controls['rule-preset'], 'sample')
        self.assertEqual(controls['allow-self-bite'], '0')
        self.assertEqual(controls['citizens'], '4')
        self.assertIsNone(self.state())
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('サンプル②', html)
        self.assertIn('>サンプル</option>', html)
        self.assertEqual(html.count('class="exclusive-field inactive-item"'), 2)
        for invalid in ({}, {'players':9}, {'players':5,'wolves':1,'rules':{'allow_self_bite':'false'},'policy':{'day':'max','night':'max'},'history':[],'selection':None,'revision':0}):
            with self.client.session_transaction() as session:
                session['game'] = invalid
            self.assertEqual(self.top().values['cast-preset'], 'five_sample')
            self.assertEqual(self.top().values['rule-preset'], 'sample')
            self.assertEqual(self.state(), invalid)

    def test_sample_three_cast_and_top_restore(self):
        self.assertEqual(CAST_PRESETS['seer_sample']['label'], 'サンプル⓷')
        self.assertEqual(CAST_PRESETS['seer_sample']['values'], dict(citizens=2,mediums=0,seers=1,hunters=0,wolves=2))
        html=self.client.get('/').get_data(as_text=True)
        self.assertIn('value="seer_sample"', html)
        self.assertIn('サンプル⓷', html)
        self.assertNotIn('5人サンプル', html)
        self.assertEqual(self.start(citizens='2',seers='1',wolves='2').status_code,303)
        self.assertEqual(self.top().values['cast-preset'],'seer_sample')
        self.assertEqual(self.state()['claims'], ['latent']*5)
        self.assertEqual(self.state()['rules']['initial_seer'], 'random_white')

    def test_logo_and_settings_return_restore_initial_config_not_current_board(self):
        self.assertEqual(self.start(citizens='4', mediums='1', seers='1', hunters='1', wolves='2', allow_self_bite='1').status_code, 303)
        state = self.state()
        main = Controls(self.client.get('/main').get_data(as_text=True))
        self.assertEqual(main.links['brand'], '/')
        self.assertEqual(main.links['settings-return'], '/')
        for route in (main.links['brand'], main.links['settings-return']):
            values = Controls(self.client.get(route).get_data(as_text=True)).values
            for role, count in dict(citizens='4',mediums='1',seers='1',hunters='1',wolves='2').items():
                self.assertEqual(values[role], count)
            self.assertEqual(values['allow-self-bite'], '1')
            self.assertEqual(values['cast-preset'], 'custom')
            self.assertEqual(values['rule-preset'], 'custom')
            self.assertEqual(self.state(), state)
        self.client.post('/advance', data={'revision':str(state['revision']),'target':'1','day':'max','night':'max'})
        self.assertEqual(len(self.state()['history']), 1)
        self.assertEqual(self.top().values['citizens'], '4')
        self.assertEqual(self.top().values['wolves'], '2')

    def test_presets_are_independent_and_numeric_values_are_normalized(self):
        cases = (({}, 'five_sample','sample'), ({'allow_self_bite':'1'},'five_sample','custom'), ({'citizens':'5'},'custom','sample'), ({'citizens':'5','allow_self_bite':'1'},'custom','custom'))
        for changes, cast_id, rule_id in cases:
            self.assertEqual(self.start(**changes).status_code, 303)
            self.assertEqual(self.top().values['cast-preset'], cast_id)
            self.assertEqual(self.top().values['rule-preset'], rule_id)
        self.assertEqual(self.start(citizens='4.0',mediums='0.00',wolves='01').status_code, 303)
        self.assertEqual(self.state()['players'], 5)
        self.assertEqual(self.state()['wolves'], 1)
        self.assertEqual(self.top().values['cast-preset'], 'five_sample')
        self.assertEqual(self.top().values['rule-preset'], 'sample')

    def test_error_preserves_draft_and_running_game_reload_returns_game(self):
        self.start(citizens='5')
        saved = self.state()
        response = self.start(citizens='8',mediums='1',wolves='2',allow_self_bite='1')
        self.assertEqual(response.status_code, 400)
        values = Controls(response.get_data(as_text=True)).values
        for role, count in dict(citizens='8',mediums='1',wolves='2').items():
            self.assertEqual(values[role], count)
        self.assertEqual(values['allow-self-bite'], '1')
        self.assertEqual(values['cast-preset'], 'custom')
        self.assertEqual(values['rule-preset'], 'custom')
        self.assertEqual(self.state(), saved)
        self.assertEqual(self.top().values['citizens'], '5')
        self.assertEqual(self.top().values['allow-self-bite'], '0')
        for invalid in ({'citizens':'-1'}, {'allow_self_bite':'2'}, {'citizens':'0.5'}, {'citizens':'NaN'}):
            response = self.start(**invalid)
            self.assertEqual(response.status_code, 400)
            controls = Controls(response.get_data(as_text=True)).values
            key = next(iter(invalid))
            self.assertEqual(controls['allow-self-bite' if key == 'allow_self_bite' else key], invalid[key])
            self.assertEqual(self.state(), saved)
        duplicate = MultiDict([*self.sample.items(), ('allow_self_bite','1')])
        response = self.client.post('/start',data=duplicate)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Controls(response.get_data(as_text=True)).values['allow-self-bite'], '0 / 1')
        self.assertEqual(self.state(), saved)

    def test_success_replaces_game_and_presets_never_include_board_strategy(self):
        self.start(citizens='2',day='random')
        state = self.state()
        self.client.post('/advance',data={'revision':str(state['revision']),'target':'1','day':'random','night':'max'})
        previous = self.state()
        self.assertEqual(len(previous['history']), 1)
        self.assertEqual(self.start().status_code, 303)
        game = self.state()
        self.assertEqual(game['history'], [])
        self.assertEqual(game['claims'], ['latent']*5)
        self.assertEqual(game['policy'], {'day':'max','night':'max','include_self_bite':False})
        self.assertEqual(game['revision'], previous['revision']+1)
        self.assertNotIn('preset', game)
        self.assertNotIn('draft', game)
        self.assertIn('data-fraction="7/15"', self.client.get('/main').get_data(as_text=True))

    def test_saved_actual_values_survive_preset_definition_change(self):
        self.start()
        saved = self.state()
        changed = {'five_sample':{'label':'サンプル②','values':dict(citizens=5,mediums=0,seers=0,hunters=0,wolves=1)}}
        with patch.dict(CAST_PRESETS, changed, clear=True):
            values = self.top().values
            self.assertEqual(values['citizens'], '4')
            self.assertEqual(values['cast-preset'], 'custom')
            self.assertEqual(self.state(), saved)
        with patch.dict(RULE_PRESETS, {'sample':{'label':'サンプル','values':{'allow_self_bite':True}}}, clear=True):
            values = self.top().values
            self.assertEqual(values['allow-self-bite'], '0')
            self.assertEqual(values['rule-preset'], 'custom')
            self.assertEqual(self.state(), saved)

    def test_one_two_initial_results_restore_real_config(self):
        for citizens, wolves in ((1,0),(1,1),(0,2)):
            self.assertEqual(self.start(citizens=str(citizens),wolves=str(wolves)).status_code, 303)
            result = self.client.get('/main',follow_redirects=True)
            self.assertEqual(result.request.path, '/result')
            saved = self.state()
            self.assertEqual(self.top().values['citizens'], str(citizens))
            self.assertEqual(self.top().values['wolves'], str(wolves))
            self.assertEqual(self.state(), saved)


class SetupModelTests(unittest.TestCase):
    def test_rule_schema_defaults_and_invalid_values_are_not_silently_repaired(self):
        self.assertEqual(complete_rules({}), Rules(False))
        with self.assertRaises(ValueError): complete_rules({'allow_self_bite':1})
        with self.assertRaises(TypeError): complete_rules({'unsupported_rule':True})
        for invalid in ('', 'NaN', 'Infinity', '-1', '0.5', '10', 'abc', '0_4', ' 4 ', True, '１'):
            with self.assertRaises(ValueError): setup_count(invalid)

    def test_default_config_excludes_strategy_and_draft_edits_do_not_mutate_game(self):
        config = GameConfig.default()
        draft = config.draft()
        self.assertEqual(draft.cast_preset, 'five_sample')
        self.assertEqual(draft.rule_preset, 'sample')
        draft.counts['citizens'] = '5'
        self.assertEqual(draft.cast_preset, 'custom')
        self.assertEqual(config.citizens, 4)
        draft.counts['citizens'] = '4.0'
        self.assertEqual(draft.cast_preset, 'five_sample')
        changed = SetupDraft(dict(draft.counts),'1')
        self.assertEqual(changed.cast_preset,'five_sample')
        self.assertEqual(changed.rule_preset,'custom')
        self.assertEqual(config.rules, Rules(False))


if __name__ == '__main__':
    unittest.main()
