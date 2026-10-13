import unittest
from fractions import Fraction
from werkzeug.datastructures import MultiDict

from app import create_app, percent


class WebTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only'})
        self.client = self.app.test_client()

    def state(self):
        with self.client.session_transaction() as session:
            return session.get('game')

    def start(self, n=5, allow=False, include=False):
        data = {'players': str(n), 'day': 'max', 'night': 'max'}
        if allow: data['allow_self_bite'] = '1'
        if include: data['include_self_bite'] = '1'
        response = self.client.post('/start', data=data)
        self.assertEqual(response.status_code, 303)
        return response

    def form(self, target=None, **changes):
        state = self.state()
        data = {'revision': str(state['revision']), 'day': state['policy']['day'], 'night': state['policy']['night']}
        if state['policy']['include_self_bite']: data['include_self_bite'] = '1'
        if target is not None: data['target'] = str(target)
        data.update(changes)
        return data

    def advance(self, target):
        response = self.client.post('/advance', data=self.form(target))
        self.assertEqual(response.status_code, 303)
        return response

    def page(self, path='/main'):
        return self.client.get(path, follow_redirects=True).get_data(as_text=True)

    def test_top_default_five_rule_and_strategy_defaults(self):
        html = self.page('/')
        self.assertIn('id="citizen-count" name="citizens" value="4"', html)
        self.assertNotIn('id="include-self-bite"', html)
        self.assertIn('id="allow-self-bite"', html)
        self.start()
        self.assertEqual(self.state()['rules'], {'allow_self_bite': False,'initial_seer':'random_white'})
        self.assertEqual(self.state()['policy'], {'day': 'max', 'night': 'max', 'include_self_bite': False})
        self.assertIn('data-fraction="7/15" data-percent="46.67%"', self.page())

    def test_self_bite_select_retains_boolean_and_legacy_form_contract(self):
        valid = {'players':'5', 'day':'max', 'night':'max'}
        for permission, expected in ((None,False), ('0',False), ('1',True)):
            data = {**valid, **({'allow_self_bite':permission} if permission is not None else {})}
            self.assertEqual(self.client.post('/start', data=data).status_code, 303)
            self.assertEqual(self.state()['rules']['allow_self_bite'], expected)
            self.assertFalse(self.state()['policy']['include_self_bite'])
            html = self.page()
            self.assertIn('id="view-self-bite" disabled', html)
            self.assertNotIn('name="allow_self_bite"', html)
        for permission in ('true','false','2',''):
            self.assertEqual(self.client.post('/start', data={**valid,'allow_self_bite':permission}).status_code, 400)
        duplicate = MultiDict([*valid.items(), ('allow_self_bite','0'), ('allow_self_bite','1')])
        self.assertEqual(self.client.post('/start', data=duplicate).status_code, 400)

    def test_three_player_terminal_both_chances_retained(self):
        self.start(3)
        response = self.advance(1)
        self.assertTrue(response.location.endswith('/result'))
        html = self.page('/result')
        self.assertIn('data-screen="result"', html)
        self.assertIn('data-fraction="1/3" data-percent="33.33%"', html)
        self.assertIn('data-fraction="2/3" data-percent="66.67%"', html)
        self.assertNotIn('id="advance-button"', html)

    def test_five_player_day_night_day_conditional_and_cumulative(self):
        self.start(5)
        self.advance(1)
        html = self.page()
        self.assertIn('Day 1 · 夜', html)
        self.assertIn('id="village-rate" class="probability" data-fraction="1/3"', html)
        self.assertIn('id="cumulative-village-rate" class="probability" data-fraction="7/15"', html)
        self.assertIn('value="1" aria-label="Player 1を対象にする" required  disabled', html)
        self.advance(2)
        self.assertIn('Day 2 · 昼', self.page())
        self.advance(3)
        html = self.page('/result')
        self.assertIn('id="village-rate" class="probability" data-fraction="1/3"', html)
        self.assertIn('id="cumulative-village-rate" class="probability" data-fraction="7/15"', html)
        self.assertEqual(len(self.state()['history']), 3)

    def test_four_player_terminal_night(self):
        self.start(4)
        self.advance(1)
        self.advance(2)
        html = self.page('/result')
        self.assertIn('id="village-rate" class="probability" data-fraction="0"', html)
        self.assertIn('id="cumulative-village-rate" class="probability" data-fraction="1/4"', html)

    def test_rule_allowed_strategy_excluded_then_included(self):
        self.start(5, allow=True)
        self.advance(1)
        response = self.client.post('/strategy', data=self.form(2, include_self_bite='1'))
        self.assertEqual(response.status_code, 303)
        html = self.page()
        self.assertIn('id="village-rate" class="probability" data-fraction="1/2"', html)
        self.assertIn('id="cumulative-village-rate" class="probability" data-fraction="3/5"', html)
        self.advance(2)
        self.advance(3)
        self.assertIn('id="cumulative-village-rate" class="probability" data-fraction="3/5"', self.page('/result'))

    def test_rule_forbidden_tampered_inclusion_rejected(self):
        response = self.client.post('/start', data={'players':'5','day':'max','night':'max','include_self_bite':'1'})
        self.assertEqual(response.status_code, 400)
        self.start()
        before = self.state()
        response = self.client.post('/strategy', data=self.form(include_self_bite='1'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.state(), before)

    def test_history_snapshots_do_not_change_when_strategy_changes(self):
        self.start(5, allow=True)
        self.advance(1)
        self.advance(2)
        history = self.state()['history']
        response = self.client.post('/strategy', data=self.form(3, day='random', night='random', include_self_bite='1'))
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.state()['history'], history)
        self.assertEqual(self.state()['selection'], 3)
        self.assertIn('id="cumulative-village-rate" class="probability" data-fraction="7/15"', self.page())

    def test_back_restores_policy_target_and_discards_suffix(self):
        self.start(5, allow=True)
        self.advance(1)
        self.client.post('/strategy', data=self.form(2, include_self_bite='1', night='random'))
        self.advance(2)
        self.advance(3)
        response = self.client.post('/back', data={'revision':str(self.state()['revision'])})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.state()['selection'], 3)
        self.assertEqual(len(self.state()['history']), 2)
        self.client.post('/back', data={'revision':str(self.state()['revision'])})
        self.assertEqual(self.state()['selection'], 2)
        self.assertEqual(self.state()['policy']['night'], 'random')
        self.assertTrue(self.state()['policy']['include_self_bite'])
        self.advance(4)
        self.assertEqual([s['target'] for s in self.state()['history']], [1, 4])

    def test_strategy_apply_without_target_does_not_advance(self):
        self.start()
        response = self.client.post('/strategy', data=self.form(day='random'))
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.state()['history'], [])
        self.assertEqual(self.state()['policy']['day'], 'random')
        self.assertIsNone(self.state()['selection'])
        self.client.post('/strategy', data=self.form(2))
        self.client.post('/strategy', data=self.form(night='random'))
        self.assertEqual(self.state()['selection'], 2)

    def test_missing_duplicate_invalid_and_dead_targets(self):
        self.start()
        data = self.form()
        for form in (data, {**data, 'target':'6'}, {**data,'target':'0'}, {**data,'role':'wolf'},
                     MultiDict([*data.items(), ('target','1'), ('target','2')])):
            self.assertEqual(self.client.post('/advance', data=form).status_code, 400)
        self.assertEqual(self.state()['history'], [])
        self.advance(1)
        self.assertEqual(self.client.post('/advance', data=self.form(1)).status_code, 400)

    def test_stale_and_rapid_repeated_posts_cannot_advance_twice(self):
        self.start()
        data = self.form(1)
        self.assertEqual(self.client.post('/advance', data=data).status_code, 303)
        self.assertEqual(self.client.post('/advance', data=data).status_code, 409)
        self.assertEqual(len(self.state()['history']), 1)
        self.assertEqual(self.client.post('/back', data={'revision':'0'}).status_code, 409)
        self.start(3)
        data = self.form(1)
        self.client.post('/advance', data=data)
        self.assertTrue(self.client.post('/advance', data=data).location.endswith('/result'))
        self.assertEqual(len(self.state()['history']), 1)

    def test_navigation_and_no_store(self):
        for path in ('/main', '/result'):
            self.assertTrue(self.client.get(path).location.endswith('/'))
        self.start()
        self.assertTrue(self.client.get('/result').location.endswith('/main'))
        response = self.client.get('/main')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')

    def test_no_role_state_and_malformed_session_returns_top(self):
        self.start()
        state = self.state()
        self.assertEqual(set(state), {'players','wolves','mediums','claims','claim_policy','rules','policy','history','selection','revision','model'})
        with self.client.session_transaction() as session:
            session['game'] = {**state, 'actual_roles': {1:'wolf'}}
        self.assertTrue(self.client.get('/main').location.endswith('/'))

    def test_exact_display_rounding_only(self):
        self.assertEqual(percent(Fraction(1,3)), '33.33')
        self.assertEqual(percent(Fraction(0)), '0')
        self.assertEqual(percent(Fraction(1)), '100')

    def test_one_two_player_initial_results_all_role_compositions(self):
        from itertools import combinations_with_replacement
        from werewolf.exact import initial_board, Progress, Rules, Strategy, legal_targets, advance
        roles = ('citizens', 'mediums', 'seers', 'hunters', 'wolves')
        for n in (1, 2):
            for cast in combinations_with_replacement(roles, n):
                data = {role:str(cast.count(role)) for role in roles}
                data.update(day='max', night='max')
                with self.subTest(cast=cast):
                    b = initial_board(n, cast.count('wolves'), cast.count('mediums'), cast.count('seers'), cast.count('hunters'))
                    expected = 'wolf' if 'wolves' in cast else 'village'
                    self.assertEqual(b.winner, expected)
                    progress = Progress.initial(b)
                    self.assertTrue(progress.finished)
                    self.assertEqual(progress.active_mass, 0)
                    self.assertEqual(progress.total_values().village_win, int(expected == 'village'))
                    self.assertEqual(sum(o.probability for o in progress.last_outcomes), 1)
                    self.assertEqual(legal_targets(b, Rules(), Strategy()), ())
                    with self.assertRaises(ValueError): advance(progress, 1, Rules(), Strategy())
                    response = self.client.post('/start', data=data, follow_redirects=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.request.path, '/result')
                    html = response.get_data(as_text=True)
                    self.assertIn('Day 1', html)
                    self.assertIn('data-fraction="0" data-percent="0%"', html)
                    self.assertIn('data-fraction="1" data-percent="100%"', html)
                    self.assertNotIn('id="advance-button"', html)
                    self.assertNotIn('id="back-button"', html)
                    state = self.state()
                    self.assertEqual(state['history'], [])
                    self.assertEqual(state['claims'], ['latent'] * n)
                    self.assertEqual(self.page('/result'), html)
                    self.assertEqual(self.client.post('/advance', data=self.form(1)).status_code, 303)
                    self.assertEqual(self.client.post('/strategy', data=self.form(co_1='wolf')).status_code, 303)
                    self.assertEqual(self.state(), state)
        for data in ({'citizens':'0','wolves':'0'}, {'citizens':'9','wolves':'1'}, {'players':'0'}, {'players':'10'}, {'players':'2','wolves':'2','mediums':'1'}, {'players':'2','wolves':'3'}):
            self.assertEqual(self.client.post('/start', data={**data,'day':'max','night':'max'}).status_code, 400)


    def test_cast_summary_uses_actual_total_and_compact_role_counts(self):
        response = self.client.post('/start', data={'citizens':'4','mediums':'1','seers':'1','hunters':'1','wolves':'2','day':'max','night':'max'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="game-cast"><span id="game-cast-label">配役</span> 9人村:市民4 · 霊能1 · 占い師1 · 狩人1（能力なし） · 狼2</p>', response.get_data(as_text=True))
        self.assertEqual(self.state()['players'], 9)
        self.assertIn('id="total-count">9人<small>（最大9人）</small>', self.page('/'))
        self.client.post('/start', data={'citizens':'1','wolves':'1','day':'max','night':'max'})
        self.assertIn('id="game-cast"><span id="game-cast-label">配役</span> 2人村:市民1 · 狼1</p>', self.page())


    def test_footer_phase_destinations_target_labels_and_terminal(self):
        self.assertIn('Day1・昼へ <span aria-hidden="true">→</span>', self.page('/'))
        self.start()
        html = self.page()
        self.assertIn('Day1・夜へ <span aria-hidden="true">→</span>', html)
        self.assertIn('処刑：Player1', html)
        self.assertIn('id="settings-return" href="/"', html)
        self.assertEqual(self.client.post('/strategy', data=self.form(2)).status_code, 303)
        self.assertIn('処刑：Player2', self.page())
        bad = self.client.post('/advance', data=self.form(0))
        self.assertEqual(bad.status_code, 400)
        self.assertIn('処刑：Player2', bad.get_data(as_text=True))
        self.advance(2)
        html = self.page()
        self.assertIn('<span aria-hidden="true">←</span> Day1・昼へ', html)
        self.assertIn('Day2・昼へ <span aria-hidden="true">→</span>', html)
        self.assertIn('data-action-label="襲撃"', html)
        self.assertNotIn('id="settings-return"', html)
        self.advance(1)
        html = self.page()
        self.assertIn('<span aria-hidden="true">←</span> Day1・夜へ', html)
        self.assertIn('Day2・夜へ <span aria-hidden="true">→</span>', html)
        self.assertIn('data-action-label="処刑"', html)
        self.client.post('/back', data={'revision':str(self.state()['revision'])})
        self.assertIn('Day2・昼へ', self.page())
        self.start(3)
        self.advance(1)
        html = self.page()
        self.assertNotIn('data-target-preview', html)
        self.assertNotIn('id="advance-button"', html)
        self.assertIn('<span aria-hidden="true">←</span> Day1・昼へ', html)
        for n in (1, 2):
            self.start(n)
            html = self.page()
            self.assertNotIn('data-target-preview', html)
            self.assertNotIn('id="advance-button"', html)
            self.assertNotIn('id="back-button"', html)
            self.assertIn('id="settings-return" href="/"', html)
            saved = self.state()
            self.client.get('/')
            self.assertEqual(self.state(), saved)


if __name__ == '__main__':
    unittest.main()
