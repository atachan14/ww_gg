"""Public inputs of the v0.7 core: cast, rules, strategy and the public log.

Definitions are in docs/redesign/calculation.md; the formulas this core computes
are in docs/redesign/core-v07.md. Players are 1..n here and 0..n-1 inside.
"""
from dataclasses import dataclass


class InvalidBoard(ValueError):
    """The input cannot be a board of this core."""


class BoardContradiction(ValueError):
    """No role assignment can produce this public log under the strategy."""


class WorkLimitExceeded(RuntimeError):
    """The calculation hit its work limit; there is no value (未計算)."""


VILLAGER, MEDIUM, WOLF, SEER = range(4)
ROLE_NAMES = ('villager', 'medium', 'wolf', 'seer')
ROLE_OF = {name: i for i, name in enumerate(ROLE_NAMES)}
WHITE, BLACK = 0, 1
COLOR_NAMES = ('white', 'black')
COLOR_OF = {name: i for i, name in enumerate(COLOR_NAMES)}

SEER_TARGET_STAGES = ('undetermined', 'unseen', 'latent', 'half_white', 'uniform')
FAKE_REPORT_STAGES = ('no_contradiction', 'uniform')


@dataclass(frozen=True)
class Cast:
    villager: int = 0
    seer: int = 0
    medium: int = 0
    wolf: int = 1

    @property
    def players(self):
        return self.villager + self.seer + self.medium + self.wolf

    def count(self, role):
        return (self.villager, self.medium, self.wolf, self.seer)[role]


@dataclass(frozen=True)
class Rules:
    self_bite: bool = False
    first_night: str = 'random_white'  # 'divine' | 'random_white' | 'none'


@dataclass(frozen=True)
class Strategy:
    # CO可能性: which roles a wolf may claim. Village claims nothing in v0.7.
    wolf_claims: tuple = ('seer', 'medium')
    # 約束 (read, and generate branches)
    co_on_saturation: bool = True
    co_on_black: bool = True
    disclose_black: bool = True
    # 想定 (generate branches only)
    disclose_all: bool = True
    seer_target: tuple = SEER_TARGET_STAGES
    fake_report: tuple = FAKE_REPORT_STAGES
    bite: str = 'max'  # 'max' | 'uniform'
    execution: str = 'max'  # 'max' | 'uniform'


# Public events, in user labels. A column is one 盤面更新; an empty column is 更新なし.
def co(player, role):
    return ('co', player, ROLE_OF[role])


def report(player, target, color):
    return ('report', player, target, COLOR_OF[color])


def column(*acts):
    return ('col', tuple(sorted(acts, key=repr)))


def execute(player):
    return ('exec', player)


def bite(player):
    return ('bite', player)


@dataclass(frozen=True)
class Board:
    cast: Cast
    log: tuple = ()
    rules: Rules = Rules()
    strategy: Strategy = Strategy()


def validate(board):
    """Check the shape of external input; reading decides everything else."""
    cast, rules, strategy = board.cast, board.rules, board.strategy
    if min(cast.villager, cast.seer, cast.medium, cast.wolf) < 0 or cast.wolf < 1:
        raise InvalidBoard('Cast counts must be non-negative with at least one wolf')
    if cast.seer > 1 or cast.medium > 1:
        raise InvalidBoard('v0.7 supports at most one seer and one medium')
    if cast.players <= 2 * cast.wolf:
        raise InvalidBoard('The game is already decided at the start')
    if rules.first_night not in ('divine', 'random_white', 'none'):
        raise InvalidBoard('Unknown first night rule')
    if not set(strategy.wolf_claims) <= {'seer', 'medium'}:
        raise InvalidBoard('Wolves can claim only seer or medium in v0.7')
    if strategy.bite not in ('max', 'uniform') or strategy.execution not in ('max', 'uniform'):
        raise InvalidBoard('Bite and execution are max or uniform')
    for stages, known in ((strategy.seer_target, SEER_TARGET_STAGES), (strategy.fake_report, FAKE_REPORT_STAGES)):
        if not stages or stages[-1] != 'uniform' or not set(stages) <= set(known):
            raise InvalidBoard('Ordered filters must use known stages and end in uniform')
    players = range(1, cast.players + 1)
    alive, claims, night = set(players), {}, False
    for event in board.log:
        kind = event[0]
        if kind == 'col':
            if night:
                raise InvalidBoard('A column belongs to a day')
            for act in event[1]:
                if act[0] == 'co':
                    _, player, role = act
                    if player not in alive or player in claims or role not in (SEER, MEDIUM):
                        raise InvalidBoard(f'Invalid CO: {act}')
                    claims[player] = role
            for act in event[1]:
                if act[0] == 'report':
                    _, player, target, color = act
                    if player not in claims or player not in alive or target not in players \
                            or target == player or color not in (WHITE, BLACK):
                        raise InvalidBoard(f'Invalid report: {act}')
        elif kind in ('exec', 'bite'):
            if night != (kind == 'bite') or event[1] not in alive:
                raise InvalidBoard(f'Invalid event order or target: {event}')
            alive.discard(event[1])
            night = kind == 'exec'
        else:
            raise InvalidBoard(f'Unknown event: {event}')
