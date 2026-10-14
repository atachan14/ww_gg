import copy
import unittest
from fractions import Fraction as F

from app import create_app
from werewolf.dawn import observe, validate_observation, advance_step, OBSERVATION
from werewolf.exact import Progress, initial_board, advance, Rules, Strategy


class DawnObservationTests(unittest.TestCase):
    def test_public_death_conditions_globally_not_per_count(self):
        rules, policy = Rules(), Strategy()
        before = advance(Progress.initial(initial_board(7, 2)), 1, rules, policy)
        forced = advance(before, 2, rules, policy)
        observed = observe(before, {'deaths': [2]}, rules, policy)
        mass = sum(w[-1] for w in before.board.worlds if not w[0] & 2)
        expected = {w[:4]: w[-1] / mass for w in before.board.worlds if not w[0] & 2}
        self.assertEqual({w[:4]: w[-1] for w in observed.board.worlds}, expected)
        self.assertNotEqual(forced.board.wolf_count_distribution, observed.board.wolf_count_distribution)
        self.assertEqual(observed.board.wolf_probability(2), 0)
        self.assertEqual((observed.board.day, observed.board.phase), (2, 'day'))
        self.assertEqual(observed.settled_village, before.settled_village)

    def test_self_bite_rule_not_action_preference_controls_evidence(self):
        rules, policy = Rules(True), Strategy(include_self_bite=False)
        before = advance(Progress.initial(initial_board(7, 2)), 1, rules, policy)
        observed = observe(before, {'deaths': [2]}, rules, policy)
        self.assertGreater(observed.board.wolf_probability(2), 0)

    def test_missing_empty_multiple_and_invalid_records(self):
        before = advance(Progress.initial(initial_board(7, 2)), 1, Rules(), Strategy())
        for record in (None, {'deaths': []}, {'deaths': [2, 3]}):
            with self.subTest(record=record), self.assertRaises(ValueError):
                observe(before, record, Rules(), Strategy())
        self.assertIsNone(validate_observation(None, (1, 2)))
        self.assertEqual(validate_observation({'deaths': []}, (1, 2)), {'deaths': []})
        for record in ({'deaths': [True]}, {'deaths': [2, 2]}, {'deaths': [9]}, {'deaths': ['2']}, {'deaths': [], 'x': 1}):
            with self.subTest(record=record), self.assertRaises(ValueError):
                validate_observation(record, before.board.alive)
        with self.assertRaises(ValueError):
            advance_step(before, {'target': 2, 'policy': {}, 'observation': OBSERVATION, 'deaths': [3]}, Rules())


class DawnBoardTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'dawn-tests',
                               'HYBRID_TABLE_PREVIEW': True, 'DAWN_BOARD_PREVIEW': True})
        self.c = self.app.test_client()
        self.start()

    def start(self, **extra):
        data = {'citizens': '6', 'wolves': '1', 'day': 'max', 'night': 'max'}
        data.update(extra)
        self.assertEqual(self.c.post('/start', data=data).status_code, 303)

    def g(self):
        with self.c.session_transaction() as session:
            return copy.deepcopy(session['game'])

    def post(self, route, **extra):
        g = self.g()
        return self.c.post(route, data={'revision': str(g['revision']),
                          'board_id': g['public_log']['board_id'], **extra})

    def execute(self, target=1):
        r = self.c.post('/advance', data={'revision': str(self.g()['revision']),
                      'target': str(target), 'day': 'max', 'night': 'max'})
        self.assertEqual(r.status_code, 303, r.data)

    def report(self, deaths=(2,)):
        r = self.post('/dawn-report', mode='deaths' if deaths else 'none', deaths=[str(p) for p in deaths])
        self.assertEqual(r.status_code, 303, r.data)

    def back(self):
        self.assertEqual(self.c.post('/back', data={'revision': str(self.g()['revision'])}).status_code, 303)

    def test_day_dawn_day_loop_and_log_ownership(self):
        root = self.g()['public_log']['board_id']
        self.assertIn('Day1・夜へ', self.c.get('/main').get_data(as_text=True))
        self.execute()
        dawn = self.g()['public_log']['board_id']
        node = self.g()['public_log']['board_graph']['nodes'][dawn]
        self.assertEqual((node['phase'], node['day']), ('dawn', 2))
        html = self.c.get('/main').get_data(as_text=True)
        self.assertIn('Day 1 · 夜', html)
        self.assertNotIn('name="target"', html)
        self.assertNotIn('data-table-update', html)
        self.assertEqual(self.post('/dawn-advance').status_code, 400)
        self.report()
        self.assertIn('D1 襲撃', self.c.get('/main').get_data(as_text=True))
        self.assertEqual(self.post('/dawn-advance').status_code, 303)
        g = self.g()
        self.assertEqual(g['history'][-1]['observation'], OBSERVATION)
        self.assertEqual(g['public_log']['board_graph']['nodes'][dawn]['system_observation'], {'deaths': [2]})
        html = self.c.get('/main').get_data(as_text=True)
        self.assertIn('Day 2 · 昼', html)
        self.assertNotIn('data-system-log', html)
        self.assertIn('Day1・夜へ', html)
        self.back()
        self.assertEqual(self.g()['public_log']['board_id'], dawn)
        self.assertIn('D1 襲撃', self.c.get('/main').get_data(as_text=True))
        self.back()
        self.assertEqual(self.g()['public_log']['board_id'], root)

    def test_shared_table_and_death_dates(self):
        import re
        day = self.c.get('/main').get_data(as_text=True)
        self.execute()
        night = self.c.get('/main').get_data(as_text=True)
        self.assertEqual(re.search(r'<thead>.*?</thead>', day, re.S).group(),
                         re.search(r'<thead>.*?</thead>', night, re.S).group())
        self.assertIn('data-night-board', night)
        self.assertIn('data-dawn-open', night)
        self.assertNotIn('data-system-log', night)
        self.assertIn('data-value-cell="final"', night)
        self.assertIn('D1 処刑', night)
        self.assertNotIn('data-status-target="1"', night)
        self.assertNotIn('data-co-toggle', night)
        self.report()
        night = self.c.get('/main').get_data(as_text=True)
        self.assertIn('D1 襲撃', night)
        self.assertEqual(self.post('/dawn-advance').status_code, 303)
        day2 = self.c.get('/main').get_data(as_text=True)
        self.assertIn('D1 処刑', day2)
        self.assertIn('D1 襲撃', day2)
        self.assertNotIn('data-status-target="2"', day2)

    def test_result_back_uses_previous_action_day(self):
        self.start(citizens='2')
        self.execute()
        html = self.c.get('/result').get_data(as_text=True)
        self.assertIn('Day1・昼へ', html)
        self.assertNotIn('Day0', html)

    def test_missing_no_death_and_multiple_are_distinct_and_saved(self):
        self.execute()
        self.report(())
        g = self.g()
        self.assertEqual(g['public_log']['board_graph']['nodes'][g['public_log']['board_id']]['system_observation'], {'deaths': []})
        self.assertIn('data-system-log', self.c.get('/main').get_data(as_text=True))
        self.assertEqual(self.post('/dawn-advance').status_code, 400)
        self.assertEqual(self.g(), g)
        self.report((2, 3))
        self.assertEqual(self.g()['public_log']['board_graph']['nodes'][self.g()['public_log']['board_id']]['system_observation'], {'deaths': [2,3]})
        self.assertEqual(self.post('/dawn-advance').status_code, 400)
        self.assertEqual(self.post('/dawn-report', mode='clear').status_code, 303)
        self.assertIn('data-dawn-open', self.c.get('/main').get_data(as_text=True))
        self.assertNotIn('data-system-log', self.c.get('/main').get_data(as_text=True))
        self.assertIsNone(self.g()['public_log']['board_graph']['nodes'][self.g()['public_log']['board_id']].get('system_observation'))

    def test_edit_retires_following_boards_and_noop_does_not(self):
        self.execute(); self.report()
        dawn = self.g()['public_log']['board_id']
        self.post('/dawn-advance')
        child = self.g()['public_log']['board_id']
        self.back(); self.report()
        self.assertTrue(self.g()['public_log']['board_graph']['nodes'][child]['active'])
        self.report((3,))
        self.assertFalse(self.g()['public_log']['board_graph']['nodes'][child]['active'])
        self.post('/dawn-advance')
        self.assertNotEqual(self.g()['public_log']['board_id'], child)
        self.assertEqual(self.g()['public_log']['board_graph']['nodes'][dawn]['system_observation'], {'deaths': [3]})

    def test_day_edits_retire_dawn_observation(self):
        import json
        self.execute(); self.report()
        old = self.g()['public_log']['board_id']
        self.back()
        g = self.g()
        payload = {'claims': ['villager'] + ['latent']*6, 'seers': [], 'mediums': []}
        self.assertEqual(self.post('/table-publish', payload=json.dumps(payload)).status_code, 200)
        self.execute()
        self.assertNotEqual(self.g()['public_log']['board_id'], old)
        self.assertIn('data-dawn-open', self.c.get('/main').get_data(as_text=True))
        self.assertNotIn('data-system-log', self.c.get('/main').get_data(as_text=True))
        self.assertIsNone(self.g()['public_log']['board_graph']['nodes'][self.g()['public_log']['board_id']].get('system_observation'))

    def test_stale_repeated_invalid_and_wrong_phase_writes(self):
        self.assertEqual(self.post('/dawn-report', mode='none').status_code, 409)
        self.execute()
        before = self.g()
        for deaths in (['1'], ['99'], ['2', '2'], ['no'], ['２']):
            self.assertEqual(self.post('/dawn-report', mode='deaths', deaths=deaths).status_code, 400)
            self.assertEqual(self.g(), before)
        self.assertEqual(self.post('/dawn-report', mode='none', board_id='wrong').status_code, 409)
        self.assertEqual(self.post('/dawn-report', mode='none', revision='999').status_code, 409)
        self.assertEqual(self.post('/table-preview', payload='{}').status_code, 400)
        self.assertEqual(self.post('/public-log', operation='draft', payload='{}').status_code, 400)
        self.assertEqual(self.c.post('/advance', data={'revision': str(before['revision']), 'target': '2', 'day': 'max', 'night': 'max'}).status_code, 400)
        self.report()
        payload = {'revision': str(self.g()['revision']), 'board_id': self.g()['public_log']['board_id']}
        self.assertEqual(self.c.post('/dawn-advance', data=payload).status_code, 303)
        self.assertEqual(self.c.post('/dawn-advance', data=payload).status_code, 409)

    def test_cookie_reload_and_seer_replay(self):
        self.start(citizens='5', seers='1')
        self.execute(); self.report()
        cookie = self.c.get_cookie('session')
        cold = self.app.test_client(); cold.set_cookie('session', cookie.value)
        self.assertIn('D1 襲撃', cold.get('/main').get_data(as_text=True))
        self.assertEqual(self.post('/dawn-advance').status_code, 303)
        from werewolf.seer_manual import replay
        _, p = replay(self.g())
        self.assertEqual((p.board.day, p.board.phase), (2, 'day'))
        self.assertEqual(p.board.wolf_probability(2), F(0))
        self.assertEqual(self.c.get('/main').status_code, 200)

    def test_terminal_execution_skips_dawn(self):
        self.start(citizens='2')
        r = self.c.post('/advance', data={'revision': str(self.g()['revision']), 'target': '1', 'day': 'max', 'night': 'max'})
        self.assertEqual(r.location, '/result')
        self.assertEqual(self.c.get('/result').status_code, 200)

    def test_all_disclosure_day2_is_editable_after_dawn(self):
        import json
        self.app.config['SEER_UNIFORM_FUTURE_PREVIEW'] = True
        self.start(citizens='5', seers='1', seer_disclosure='all')
        payload = {'claims': ['seer'] + ['latent']*6, 'seers': [
            {'day': 1, 'reporter': 1, 'target': 3, 'color': 'white'}], 'mediums': []}
        self.assertEqual(self.post('/table-publish', payload=json.dumps(payload)).status_code, 200)
        self.execute(2); self.report((3,))
        self.assertEqual(self.post('/dawn-advance').status_code, 303)
        html = self.c.get('/main').get_data(as_text=True)
        self.assertIn('data-table-update', html)
        payload['seers'].append({'day': 2, 'reporter': 1, 'target': 4, 'color': 'white'})
        r = self.post('/table-publish', payload=json.dumps(payload))
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.c.get('/main').status_code, 200)

    def test_medium_report_acquisition_day_survives_dawn(self):
        import json
        self.start(citizens='5', mediums='1')
        self.execute(); self.report()
        self.assertEqual(self.post('/dawn-advance').status_code, 303)
        payload = {'claims': ['latent', 'latent', 'medium'] + ['latent']*4, 'seers': [],
                   'mediums': [{'day': 2, 'reporter': 3, 'target': 1, 'color': 'white'}]}
        r = self.post('/table-publish', payload=json.dumps(payload))
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.c.get('/main').status_code, 200)

    def test_report_deletion_retires_children(self):
        self.execute(); self.report(); self.post('/dawn-advance')
        child = self.g()['public_log']['board_id']
        self.back()
        self.assertEqual(self.post('/dawn-report', mode='clear').status_code, 303)
        self.assertFalse(self.g()['public_log']['board_graph']['nodes'][child]['active'])
        self.assertEqual(self.post('/dawn-advance').status_code, 400)

    def test_terminal_night_death_goes_to_result(self):
        self.start(citizens='3')
        self.execute(); self.report()
        r = self.post('/dawn-advance')
        self.assertEqual(r.status_code, 303, r.data)
        self.assertEqual(r.location, '/result')
        self.assertEqual(self.c.get('/result').status_code, 200)

    def test_preview_opt_in_does_not_change_legacy_games(self):
        app = create_app({'TESTING': True, 'SECRET_KEY': 'legacy'})
        c = app.test_client()
        c.post('/start', data={'citizens': '4', 'wolves': '1', 'day': 'max', 'night': 'max'})
        self.assertIn('Day1・夜へ', c.get('/main').get_data(as_text=True))
        with c.session_transaction() as session:
            self.assertNotIn('board_flow', session['game'])
        self.assertEqual(c.post('/dawn-report').status_code, 404)


if __name__ == '__main__':
    unittest.main()
