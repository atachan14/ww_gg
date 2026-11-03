"""The v0.8 screen's HTTP: the same values as the core, and every refusal kept apart."""
import unittest
from fractions import Fraction as F
from unittest import mock

from app import create_app
from werewolf.calculation_budget import CalculationBudgetExceeded

FIVE = {'cast': {'villager': 4, 'wolf': 1}}
SEVEN = {'cast': {'villager': 4, 'medium': 1, 'wolf': 2}, 'strategy': {'bite': 'uniform'}}


def col(*acts):
    return {'kind': 'col', 'acts': list(acts)}


class CoreBoard(unittest.TestCase):
    def setUp(self):
        self.client = create_app({'SECRET_KEY': 'core-http-test'}).test_client()

    def post(self, body, query=''):
        return self.client.post('/core/board' + query, json=body)

    def test_page(self):
        response = self.client.get('/core')
        self.assertEqual(response.status_code, 200)
        self.assertIn('core.js', response.text)

    def test_five_players_value(self):
        data = self.post(FIVE).get_json()
        self.assertEqual(data['win_rates']['village'], '7/15')
        self.assertEqual(data['stage'], 'closed')
        self.assertEqual(data['alive_wolves'], {'1': '1'})
        self.assertEqual(data['role_rates']['1']['wolf'], '1/5')
        self.assertEqual(data['action_ends']['1'], {'village': '1/5', 'wolf': '0'})
        self.assertEqual(sum(F(b['probability']) for b in data['branches']), 1)
        self.assertTrue(data['complete'])

    def test_read_scope_has_no_future(self):
        data = self.post(FIVE, '?scope=read').get_json()
        self.assertEqual(data['win_rates'], {})
        self.assertEqual(data['action_rates'], {})
        self.assertEqual(data['role_rates']['1']['wolf'], '1/5')
        self.assertFalse(data['complete'])

    def test_board_c_reading(self):
        log = [col(), {'kind': 'exec', 'player': 1}, {'kind': 'bite', 'player': 2},
               col({'kind': 'co', 'player': 3, 'role': 'medium'},
                   {'kind': 'report', 'player': 3, 'target': 1, 'color': 'black'})]
        data = self.post({**SEVEN, 'log': log}, '?scope=read').get_json()
        self.assertEqual(data['role_rates']['1']['wolf'], '1/3')
        self.assertEqual(data['role_rates']['3']['medium'], '23/75')

    def test_settling_action_has_full_ends(self):
        log = [col(), {'kind': 'exec', 'player': 1}, {'kind': 'bite', 'player': 2}, col()]
        data = self.post({**FIVE, 'log': log}).get_json()
        self.assertEqual(data['action_ends']['3'], {'village': '1/3', 'wolf': '2/3'})

    def test_contradiction_is_not_a_value(self):
        log = [col({'kind': 'report', 'player': 1, 'target': 2, 'color': 'white'})]
        self.assertEqual(self.post({**FIVE, 'log': log}).status_code, 400)
        log = [col(), {'kind': 'exec', 'player': 1}, {'kind': 'bite', 'player': 2}, col(),
               {'kind': 'exec', 'player': 3}]
        response = self.post({**FIVE, 'log': log})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()['kind'], 'contradiction')

    def test_invalid_input(self):
        for body in ({'cast': {'villager': 'x'}}, {'cast': {'villager': 10, 'wolf': 1}}, {'cast': {'villager': 1, 'wolf': 1}},
                     {**FIVE, 'log': [{'kind': 'nope'}]}, {**FIVE, 'log': 'x'}, {**FIVE, 'rules': {'self_bite': 'yes'}},
                     {**FIVE, 'strategy': {'bite': 'nope'}}, {**FIVE, 'strategy': {'seer_target': ['unseen']}}, []):
            self.assertEqual(self.post(body).status_code, 400, body)

    def test_large_body_within_the_screen_limit(self):
        padding = 'x' * 8000
        self.assertEqual(self.post({**FIVE, 'padding': padding}).status_code, 200)
        self.assertEqual(self.post({**FIVE, 'padding': 'x' * 70000}).status_code, 413)

    def test_budget_stop_has_no_value(self):
        with mock.patch('board_http.evaluate', side_effect=CalculationBudgetExceeded('stop', kind='time')):
            response = self.post(FIVE)
        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.get_json()['pending'])
        self.assertNotIn('win_rates', response.get_json())


if __name__ == '__main__':
    unittest.main()
