import copy
import json
import unittest
from fractions import Fraction as F

from app import create_app
from werewolf.exact import Rules, Strategy, initial_board, action_outcomes
from werewolf.private_adapter import evaluate_private_table, viewpoint_roles, private_slots


class PrivateAdapterTests(unittest.TestCase):
    def test_wolf_horizon_and_final_are_exact_without_public_mutation(self):
        public = next(o.board for o in action_outcomes(initial_board(5), 1, Rules(), Strategy()) if o.board.winner is None)
        before = copy.deepcopy(public)
        result = evaluate_private_table(public, 'wolf', [2], [], Rules(), Strategy())
        self.assertEqual(public, before)
        self.assertTrue(all(row['final'] is not None for row in result['players'] if row['legal']))
        self.assertTrue(all(row['final'] is None for row in result['players'] if not row['legal']))
        self.assertIsNone(result['players'][1]['dawn'])
        for row in result['players'][2:]:
            self.assertEqual(row['dawn'], {'village': '0', 'wolf': '0'})
        # Three living players: a bite immediately wins for the wolf.
        next_day = next(o.board for o in action_outcomes(public, 3, Rules(), Strategy()) if o.board.winner is None)
        # With three alive on a day Board, advance to its two-alive night is terminal.
        # Use an even initial cast to reach a continuing three-alive night.
        next_night = next(o.board for o in action_outcomes(initial_board(4), 1, Rules(), Strategy()) if o.board.winner is None)
        result = evaluate_private_table(next_night, 'wolf', [2], [], Rules(), Strategy())
        self.assertEqual(result['players'][3]['dawn'], {'village': '0', 'wolf': '1'})

    def test_dead_wolf_combinations_and_acquisition_roster(self):
        public = next(o.board for o in action_outcomes(initial_board(7, 2, 0, 1), 1, Rules(), Strategy()) if o.board.winner is None)
        roles = viewpoint_roles(public)
        self.assertIn((1, 2), roles['wolf']['combinations'])
        self.assertNotIn((1,), roles['seer']['combinations'])
        self.assertNotIn('hunter', roles)
        slots = private_slots(public, 2, Rules(initial_seer='none'))
        self.assertEqual(slots, [])

    def test_wolf_budget_does_not_replace_missing_final_with_public_rate(self):
        public = next(o.board for o in action_outcomes(initial_board(5), 1, Rules(), Strategy()) if o.board.winner is None)
        result = evaluate_private_table(public, 'wolf', [2], [], Rules(), Strategy(), max_work=1)
        self.assertTrue(all(row['final'] is None for row in result['players']))
        self.assertIn('未計算', result['reason'])
        self.assertIsNotNone(result['players'][2]['dawn'])

    def test_secrets_filter_roles_but_never_generate_ability_values(self):
        public = next(o.board for o in action_outcomes(initial_board(7, 1, 0, 1), 7, Rules(), Strategy()) if o.board.winner is None)
        result = evaluate_private_table(public, 'seer', [1], [{'day': 1, 'target': 2, 'color': 'black'}], Rules(initial_seer='normal'), Strategy())
        self.assertEqual(result['players'][1]['probabilities']['wolf'], '1')
        self.assertTrue(all(row['dawn'] is None and row['final'] is None for row in result['players']))
        self.assertEqual(result['acquisitions'], [{'day': 1, 'player': 1, 'target': 2, 'color': 'black'}])
        self.assertEqual(public.wolf_probability(2), F(1, 6))


class PrivateRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'private-tests', 'DAWN_BOARD_PREVIEW': True, 'HYBRID_TABLE_PREVIEW': True})
        self.c = self.app.test_client()
        self.c.post('/start', data={'citizens': '5', 'wolves': '1', 'seers': '1', 'day': 'random', 'night': 'random', 'initial_seer': 'normal'})

    def game(self):
        with self.c.session_transaction() as session:
            return copy.deepcopy(session['game'])

    def execute(self):
        g = self.game()
        response = self.c.post('/advance', data={'revision': str(g['revision']), 'target': '7', 'day': 'random', 'night': 'random'})
        self.assertEqual(response.status_code, 303, response.get_data(as_text=True))

    def view(self, role='seer', players=None, results=None, **extra):
        g = self.game()
        data = {'revision': str(g['revision']), 'board_id': g['public_log']['board_id'],
                'payload': json.dumps({'role': role, 'players': players or [1], 'results': results or []})}
        return self.c.post('/private-view', data={**data, **extra})

    def test_night_mount_private_edit_and_public_state_identity(self):
        self.assertNotIn('id="board-viewpoint-seed"', self.c.get('/main').get_data(as_text=True))
        self.execute()
        html = self.c.get('/main').get_data(as_text=True)
        self.assertIn('id="board-viewpoint-seed"', html)
        self.assertNotIn('id="system-log"', html)
        before = self.game()
        cookie = self.c.get_cookie('session').value
        for results in ([], [{'day': 1, 'target': 2, 'color': None}], [{'day': 1, 'target': 2, 'color': 'black'}]):
            response = self.view(results=results)
            self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
            self.assertEqual(self.game(), before)
            self.assertEqual(self.c.get_cookie('session').value, cookie)
        self.assertEqual(self.c.get('/main').get_data(as_text=True), html)

    def test_invalid_secrets_stale_board_and_return_to_day(self):
        self.assertEqual(self.view().status_code, 400)
        self.execute()
        before = self.game()
        for kwargs, status in (({'revision': '999'}, 409), ({'board_id': 'other'}, 409),
                               ({'role': 'seer', 'players': [7]}, 400),
                               ({'results': [{'day': 2, 'target': 2, 'color': 'white'}]}, 400),
                               ({'results': [{'day': 1, 'target': 1, 'color': 'white'}]}, 400),
                               ({'public_co': 'wolf'}, 400)):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.view(**kwargs).status_code, status)
                self.assertEqual(self.game(), before)
        response = self.c.post('/back', data={'revision': str(before['revision'])})
        self.assertEqual(response.status_code, 303)
        self.assertNotIn('id="board-viewpoint-seed"', self.c.get('/main').get_data(as_text=True))

    def test_wolf_roster_changes_final_values_without_changing_public_cookie(self):
        self.c.post('/start', data={'citizens': '4', 'wolves': '1', 'day': 'max', 'night': 'max'})
        g = self.game()
        self.assertEqual(self.c.post('/advance', data={'revision': str(g['revision']), 'target': '5',
                         'day': 'max', 'night': 'max'}).status_code, 303)
        before = self.game(); cookie = self.c.get_cookie('session').value
        first = self.view(role='wolf', players=[2]).get_json()
        other = self.view(role='wolf', players=[3]).get_json()
        self.assertEqual(first['players'][0]['final'], {'village': '1', 'wolf': '0'})
        self.assertEqual(first['players'][2]['final'], {'village': '0', 'wolf': '1'})
        self.assertEqual(other['players'][1]['final'], {'village': '0', 'wolf': '1'})
        self.assertEqual(self.game(), before)
        self.assertEqual(self.c.get_cookie('session').value, cookie)
