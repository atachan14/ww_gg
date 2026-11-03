"""Development tests of the v0.7 core against the oracle and the named results."""
import random
import unittest
from fractions import Fraction as F

from wwcore import (Board, BoardContradiction, Cast, InvalidBoard, Rules, Strategy, WorkLimitExceeded,
                    bite, co, column, evaluate, execute, read_roles, report)
from wwcore.core import initial_masses
from wwcore.model import MEDIUM
from tests.wwcore_oracle import Oracle

UNIFORM_BITE = Strategy(bite='uniform')
ROLES = ('villager', 'medium', 'wolf', 'seer')


def groups_of(sizes):
    groups, start = [], 0
    for size in sizes:
        groups.append(tuple(range(start, start + size)))
        start += size
    return tuple(groups)


class NamedResults(unittest.TestCase):
    def test_five_player_village(self):
        self.assertEqual(evaluate(Board(Cast(villager=4, wolf=1))).win_rates['village'], F(7, 15))

    def test_bite_example(self):
        board = Board(Cast(villager=4, medium=1, wolf=2), (column(), execute(1), bite(2)), strategy=UNIFORM_BITE)
        rates = read_roles(board)
        self.assertEqual(rates[1]['wolf'], F(2, 7))
        for player in (3, 4, 5, 6, 7):
            self.assertEqual(rates[player]['wolf'], F(12, 35))
        self.assertEqual(rates[2]['wolf'], 0)

    def test_board_b_c_e(self):
        cast = Cast(villager=4, medium=1, wolf=2)
        log = (column(), execute(1), bite(2))
        result = evaluate(Board(cast, log, strategy=UNIFORM_BITE))
        updated = sum(p for event, p in result.branches if event[1])
        silent = [p for event, p in result.branches if not event[1]]
        self.assertEqual(updated, F(8, 35))
        self.assertEqual(silent, [F(27, 35)])
        board_e = read_roles(Board(cast, log + (column(),), strategy=UNIFORM_BITE))
        self.assertEqual(board_e[1]['wolf'], F(2, 27))
        # With wolves unable to claim, BoardC confirms X and the children average back to 2/7.
        no_claims = Strategy(wolf_claims=(), bite='uniform')
        board_c = read_roles(Board(cast, log + (column(co(3, 'medium'), report(3, 1, 'black')),), strategy=no_claims))
        self.assertEqual(board_c[1]['wolf'], 1)
        self.assertEqual(F(8, 35) * 1 + F(27, 35) * F(2, 27), F(2, 7))

    def test_board_c_when_wolves_may_claim(self):
        # core-v07.md: a free fake CO stays possible, so X is not confirmed.
        cast = Cast(villager=4, medium=1, wolf=2)
        log = (column(), execute(1), bite(2), column(co(3, 'medium'), report(3, 1, 'black')))
        self.assertEqual(read_roles(Board(cast, log, strategy=UNIFORM_BITE))[1]['wolf'], F(1, 3))

    def test_co_group_table(self):
        # archive/20261029/co-group-model.md: five villagers, two mediums, two wolves.
        cast = Cast(villager=5, medium=2, wolf=2)
        for claimers, expected in ((1, F(2, 9)), (2, F(2, 9)), (3, F(8, 21)), (4, F(1, 2))):
            groups = groups_of((claimers, 9 - claimers))
            masses = initial_masses(cast, {MEDIUM}, groups, {0: MEDIUM})
            wolf = sum(m * F(sum(s[0][6:9]), claimers) for s, m in masses.items())
            self.assertEqual(wolf, expected)

    def test_fake_report_leaves_the_true_rate_alone(self):
        # calculation.md: A and B claim seer, C is in a group of two villagers and a wolf.
        cast = Cast(villager=2, seer=1, wolf=2)
        rules = Rules(first_night='divine')
        strategy = Strategy(co_on_black=False, disclose_black=False)
        claimed = (column(co(1, 'seer'), co(2, 'seer')), column())  # the deadline removes a latent seer
        before = read_roles(Board(cast, claimed, rules, strategy))
        self.assertEqual(before[1]['seer'], F(1, 2))
        after = read_roles(Board(cast, claimed + (column(report(1, 3, 'black')),), rules, strategy))
        self.assertEqual(after[1]['seer'], F(1, 2))

    def test_black_report_of_a_lone_seer_claim(self):
        # Without the saturation deadline the claim stays open, and reports do not move it.
        cast = Cast(villager=3, seer=1, wolf=1)
        rules = Rules(first_night='divine')
        strategy = Strategy(co_on_black=False, disclose_black=False, co_on_saturation=False)
        claimed = (column(co(1, 'seer')),)
        base = read_roles(Board(cast, claimed, rules, strategy))[1]['seer']
        for shade in ('white', 'black'):
            rates = read_roles(Board(cast, claimed + (column(report(1, 2, shade)),), rules, strategy))
            self.assertEqual(rates[1]['seer'], base)


class Boundaries(unittest.TestCase):
    def test_contradictions_have_no_value(self):
        cast = Cast(villager=4, seer=1, wolf=1)
        with self.assertRaises(BoardContradiction):
            read_roles(Board(cast, (column(co(1, 'seer'), co(2, 'seer'), co(3, 'seer')),)))
        with self.assertRaises(BoardContradiction):
            read_roles(Board(cast, (column(co(1, 'medium')),), strategy=Strategy(wolf_claims=())))

    def test_invalid_input(self):
        with self.assertRaises(InvalidBoard):
            evaluate(Board(Cast(villager=1, wolf=1)))
        with self.assertRaises(InvalidBoard):
            evaluate(Board(Cast(villager=4, wolf=1), (execute(9),)))
        with self.assertRaises(InvalidBoard):
            evaluate(Board(Cast(villager=4, wolf=1), (bite(1),)))
        with self.assertRaises(InvalidBoard):
            evaluate(Board(Cast(villager=4, wolf=1), (column(report(1, 2, 'white')),)))

    def test_work_limit_gives_no_value(self):
        with self.assertRaises(WorkLimitExceeded):
            evaluate(Board(Cast(villager=4, wolf=1)), max_work=1)


CASTS = (
    Cast(villager=4, wolf=1),
    Cast(villager=3, seer=1, wolf=1),
    Cast(villager=3, medium=1, wolf=1),
    Cast(villager=2, seer=1, medium=1, wolf=1),
    Cast(villager=3, seer=1, medium=1, wolf=1),
    Cast(villager=2, seer=1, medium=1, wolf=2),
)
SETTINGS = (
    (Rules(), Strategy()),
    (Rules(first_night='divine'), Strategy()),
    (Rules(first_night='none'), Strategy()),
    (Rules(self_bite=True), Strategy()),
    (Rules(first_night='divine'), Strategy(bite='uniform', execution='uniform')),
    (Rules(), Strategy(wolf_claims=())),
    (Rules(), Strategy(seer_target=('uniform',), fake_report=('uniform',))),
    (Rules(first_night='divine'), Strategy(co_on_black=False, disclose_black=False, disclose_all=False)),
    (Rules(), Strategy(seer_target=('half_white', 'latent', 'unseen', 'uniform'))),
)


def claim_boards(cast):
    """Boards with public COs and reports, with the cast's roles only."""
    boards = [()]
    if cast.seer:
        boards.append((column(co(1, 'seer')),))
        boards.append((column(co(1, 'seer'), report(1, 2, 'white')),))
        boards.append((column(co(1, 'seer'), co(2, 'seer'), report(1, 3, 'white'), report(2, 3, 'white')),))
        boards.append((column(co(1, 'seer'), co(2, 'seer')), column(report(1, 3, 'white')),))
    if cast.medium:
        boards.append((column(co(1, 'medium')),))
    if cast.seer and cast.medium:
        boards.append((column(co(1, 'seer'), co(2, 'medium')),))
    boards.append((column(), execute(1)))
    boards.append((column(), execute(1), bite(2)))
    return boards


class AgainstOracle(unittest.TestCase):
    def assert_same(self, board):
        try:
            oracle = Oracle(board).evaluate()
        except Exception as error:
            if type(error).__name__ != 'Contradiction':
                raise
            with self.assertRaises(BoardContradiction):
                evaluate(board)
            return None
        result = evaluate(board)
        for player in oracle['role_rates']:
            for role in ROLES:
                self.assertEqual(result.role_rates[player][role], oracle['role_rates'][player][role],
                                 (board, player, role))
        self.assertEqual(result.win_rates['village'], oracle['village'], board)
        for player, value in oracle['actions'].items():
            self.assertEqual(result.action_rates[player], value, (board, player))
        return result

    def test_grid(self):
        checked = 0
        for cast in CASTS:
            for rules, strategy in SETTINGS:
                for log in claim_boards(cast):
                    self.assert_same(Board(cast, log, rules, strategy))
                    checked += 1
        self.assertGreater(checked, 300)

    def test_every_branch_walk(self):
        """Follow the expected branches from the root and compare each board, cold."""
        rng = random.Random(20261102)
        for cast in CASTS[1:]:
            for rules, strategy in SETTINGS[:4] + SETTINGS[6:7]:
                for start in claim_boards(cast)[:4]:
                    log = start
                    for _ in range(10):
                        result = self.assert_same(Board(cast, log, rules, strategy))
                        if result is None or not result.branches:
                            break
                        total = sum(p for _, p in result.branches)
                        self.assertEqual(total, 1, (cast, log))
                        event, _ = rng.choice(result.branches)
                        extended = log + (event,)
                        if event[0] == 'exec' and log and not (log[-1][0] == 'col' and not log[-1][1]):
                            extended = log + (('col', ()), event)
                        if event[0] != 'col' and self.game_over(cast, extended, rules, strategy):
                            break
                        log = extended

    @staticmethod
    def game_over(cast, log, rules, strategy):
        try:
            read_roles(Board(cast, log, rules, strategy))
        except BoardContradiction:
            return True
        return False


class SevenPlayers(unittest.TestCase):
    def test_performance_case_matches_the_oracle(self):
        # PERFORMANCE.md's case under the new definitions; the value comes from the oracle.
        cast = Cast(villager=3, medium=1, seer=1, wolf=2)
        board = Board(cast, (column(co(1, 'seer'), co(2, 'seer'), report(1, 3, 'white'), report(2, 3, 'white'),
                                    co(3, 'medium')),))
        oracle = Oracle(board).evaluate()
        result = evaluate(board)
        self.assertEqual(oracle['village'], F(123, 308))
        self.assertEqual(result.win_rates['village'], F(123, 308))
        self.assertEqual({p: r['seer'] for p, r in result.role_rates.items()},
                         {p: r['seer'] for p, r in oracle['role_rates'].items()})
        self.assertEqual(result.role_rates[1]['seer'], F(5, 11))
        self.assertEqual(result.role_rates[3]['medium'], 1)


class Structure(unittest.TestCase):
    def test_uniform_future_averages_to_the_parent(self):
        # calculation.md: with uniform secret actions and no free claims, children average to the parent.
        for cast in (Cast(villager=4, medium=1, wolf=2),
                     Cast(villager=3, seer=1, medium=1, wolf=1)):
            strategy = Strategy(wolf_claims=(), bite='uniform', execution='uniform', seer_target=('uniform',))
            log = (column(), execute(1), bite(2))
            parent = evaluate(Board(cast, log, strategy=strategy))
            average, wolf_rate = F(), F()
            for event, p in parent.branches:
                child = evaluate(Board(cast, log + (event,), strategy=strategy))
                average += p * child.win_rates['village']
                wolf_rate += p * child.role_rates[1]['wolf']
            self.assertEqual(average, parent.win_rates['village'])
            self.assertEqual(wolf_rate, parent.role_rates[1]['wolf'])

    def test_renaming_players_renames_the_answer(self):
        cast = Cast(villager=3, seer=1, medium=1, wolf=2)
        rng = random.Random(7)
        def log_for(name):
            return (column(co(name[1], 'seer'), co(name[2], 'seer'), report(name[1], name[3], 'white'),
                           report(name[2], name[3], 'black')),
                    execute(name[4]), bite(name[5]))
        base = evaluate(Board(cast, log_for({i: i for i in range(1, 8)})))
        for _ in range(4):
            order = list(range(1, 8))
            rng.shuffle(order)
            name = {i + 1: order[i] for i in range(7)}
            renamed = evaluate(Board(cast, log_for(name)))
            self.assertEqual(renamed.win_rates, base.win_rates)
            for i in range(1, 8):
                self.assertEqual(renamed.role_rates[name[i]], base.role_rates[i])
            for player, value in base.action_rates.items():
                self.assertEqual(renamed.action_rates[name[player]], value)

    def test_board_reads_the_same_however_it_is_reached(self):
        # A cold read equals the rate met along the way (no hidden state in the calculation).
        cast = Cast(villager=3, seer=1, wolf=1)
        first = Board(cast, (column(co(1, 'seer'), report(1, 2, 'white')), execute(3), bite(4)))
        self.assertEqual(read_roles(first), evaluate(first).role_rates)


if __name__ == '__main__':
    unittest.main()
