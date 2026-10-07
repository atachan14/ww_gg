"""Public Board calculations for 3–5 players and one wolf, using exact fractions."""

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

Phase = Literal["day", "night"]
Winner = Literal["village", "wolf"]


@dataclass(frozen=True)
class Rules:
    allow_self_bite: bool = False

    def __post_init__(self):
        if type(self.allow_self_bite) is not bool:
            raise ValueError("Self-bite permission must be a boolean")


@dataclass(frozen=True)
class Strategy:
    day: str = "max"
    night: str = "max"
    include_self_bite: bool = False

    def __post_init__(self):
        if self.day not in ("max", "random") or self.night not in ("max", "random"):
            raise ValueError("Choose max or random")
        if type(self.include_self_bite) is not bool:
            raise ValueError("Self-bite inclusion must be a boolean")


def validate_strategy(rules: Rules, strategy: Strategy):
    if strategy.include_self_bite and not rules.allow_self_bite:
        raise ValueError("The game rule does not permit self-bite")


@dataclass(frozen=True)
class PublicEvent:
    day: int
    phase: Phase
    target: int


@dataclass(frozen=True)
class Board:
    """Public history and count constraints; no player has an assigned true role."""

    player_count: int
    alive: tuple[int, ...]
    wolf_count: int = 1
    day: int = 1
    phase: Phase = "day"
    history: tuple[PublicEvent, ...] = ()

    def __post_init__(self):
        if type(self.player_count) is not int or self.player_count not in (3, 4, 5):
            raise ValueError("v0.1 supports 3–5 players and one initial wolf")
        if not isinstance(self.alive, tuple) or len(set(self.alive)) != len(self.alive):
            raise ValueError("Alive IDs must be a distinct tuple")
        if any(type(player) is not int or not 1 <= player <= self.player_count for player in self.alive):
            raise ValueError("Unknown player")
        if type(self.wolf_count) is not int or self.wolf_count not in (0, 1) or self.wolf_count > len(self.alive):
            raise ValueError("Invalid public wolf-count constraint")
        if type(self.day) is not int or self.day < 1 or self.phase not in ("day", "night"):
            raise ValueError("Invalid Day/Phase")
        if not isinstance(self.history, tuple) or any(not isinstance(event, PublicEvent) for event in self.history):
            raise ValueError("Invalid public history")
        dead = tuple(event.target for event in self.history)
        if len(set(dead)) != len(dead) or set(dead) != set(range(1, self.player_count + 1)) - set(self.alive):
            raise ValueError("History and alive players must agree")

    @property
    def villagers(self) -> int:
        return len(self.alive) - self.wolf_count

    @property
    def winner(self) -> Winner | None:
        if self.wolf_count == 0:
            return "village"
        if self.wolf_count >= self.villagers:
            return "wolf"
        return None

    def wolf_probability(self, player: int) -> Fraction:
        if type(player) is not int or not 1 <= player <= self.player_count:
            raise ValueError("Unknown player")
        if player in self.alive:
            return Fraction(self.wolf_count, len(self.alive))
        # In this one-wolf scope, continuation proves earlier victims non-wolf.
        # A village-win announcement identifies the final victim as that wolf.
        return Fraction(int(self.wolf_count == 0 and self.history[-1].target == player))


def initial_board(player_count: int = 5) -> Board:
    if type(player_count) is not int or player_count not in (3, 4, 5):
        raise ValueError("Choose 3, 4, or 5 players")
    return Board(player_count, tuple(range(1, player_count + 1)))


@dataclass(frozen=True)
class BoardOutcome:
    probability: Fraction
    board: Board


def action_outcomes(board: Board, target: int, rules: Rules, strategy: Strategy) -> tuple[BoardOutcome, ...]:
    validate_strategy(rules, strategy)
    if board.winner is not None:
        raise ValueError("A terminal Board cannot advance")
    if type(target) is not int or target not in board.alive:
        raise ValueError("Choose a living player")
    # This scope is exchangeable: no CO, private information, or role locations.
    # If bite excludes wolves, the resulting public bite conditions the victim
    # to non-wolf. Otherwise the current Board's role probabilities apply.
    wolf_probability = board.wolf_probability(target) if board.phase == "day" or strategy.include_self_bite else Fraction(0)
    alive = tuple(player for player in board.alive if player != target)
    event = PublicEvent(board.day, board.phase, target)
    outcomes = []
    for hit_wolf, probability in ((True, wolf_probability), (False, 1 - wolf_probability)):
        if not probability:
            continue
        wolves = board.wolf_count - int(hit_wolf)
        terminal = wolves == 0 or wolves >= len(alive) - wolves
        phase = board.phase if terminal else ("night" if board.phase == "day" else "day")
        day = board.day + int(not terminal and board.phase == "night")
        child = Board(board.player_count, alive, wolves, day, phase, board.history + (event,))
        outcomes.append(BoardOutcome(probability, child))
    return tuple(outcomes)


@dataclass(frozen=True)
class Action:
    target: int
    outcomes: tuple["Chance", ...]


@dataclass(frozen=True)
class Chance:
    probability: Fraction
    child: "TreeNode"


@dataclass(frozen=True)
class TreeNode:
    board: Board
    actions: tuple[Action, ...] = ()


def build_tree(board: Board, rules: Rules, strategy: Strategy) -> TreeNode:
    """Build all action candidates to terminal leaves before evaluating values."""
    validate_strategy(rules, strategy)
    if board.winner is not None:
        return TreeNode(board)
    return TreeNode(board, tuple(Action(target, tuple(
        Chance(outcome.probability, build_tree(outcome.board, rules, strategy))
        for outcome in action_outcomes(board, target, rules, strategy)
    )) for target in board.alive))


@dataclass(frozen=True)
class Values:
    village_win: Fraction
    wolf_win: Fraction

    def __post_init__(self):
        if not isinstance(self.village_win, Fraction) or not isinstance(self.wolf_win, Fraction):
            raise ValueError("Use exact Fractions")
        if self.village_win < 0 or self.wolf_win < 0 or self.village_win + self.wolf_win != 1:
            raise ValueError("Win probabilities must conserve one")


def aggregate_values(phase: Phase, candidates: tuple[Values, ...], strategy: Strategy) -> Values:
    """A public Board aggregation, without selecting or weighting maximum ties."""
    if not candidates or phase not in ("day", "night"):
        raise ValueError("A valid phase and action candidates are required")
    mode = strategy.day if phase == "day" else strategy.night
    if mode == "random":
        village = sum((value.village_win for value in candidates), Fraction(0)) / len(candidates)
    elif phase == "day":
        village = max(value.village_win for value in candidates)
    else:
        village = 1 - max(value.wolf_win for value in candidates)
    return Values(village, 1 - village)


@dataclass
class Evaluation:
    boards: dict[int, Values]
    actions: dict[tuple[int, int], Values]

    def board_value(self, node: TreeNode) -> Values:
        return self.boards[id(node)]

    def action_value(self, node: TreeNode, target: int) -> Values:
        return self.actions[(id(node), target)]


def evaluate_tree(root: TreeNode, strategy: Strategy) -> Evaluation:
    result = Evaluation({}, {})

    def visit(node):
        winner = node.board.winner
        if winner:
            value = Values(Fraction(int(winner == "village")), Fraction(int(winner == "wolf")))
        else:
            candidates = []
            for action in node.actions:
                village = sum((chance.probability * visit(chance.child).village_win for chance in action.outcomes), Fraction(0))
                value = Values(village, 1 - village)
                result.actions[(id(node), action.target)] = value
                candidates.append(value)
            value = aggregate_values(node.board.phase, tuple(candidates), strategy)
        result.boards[id(node)] = value
        return value

    visit(root)
    return result


@dataclass(frozen=True)
class Progress:
    board: Board | None
    settled_village: Fraction = Fraction(0)
    settled_wolf: Fraction = Fraction(0)
    last_board: Board | None = None
    last_outcomes: tuple[BoardOutcome, ...] = ()

    def __post_init__(self):
        if any(not isinstance(value, Fraction) or value < 0 for value in (self.settled_village, self.settled_wolf)):
            raise ValueError("Settled mass must be exact and nonnegative")
        settled = self.settled_village + self.settled_wolf
        if settled > 1 or (self.board is None and settled != 1) or (self.board is not None and settled >= 1):
            raise ValueError("Resolved and ongoing probabilities must conserve one")
        if self.board is not None and self.board.winner is not None:
            raise ValueError("Only a continuing Board can be active")

    @property
    def active_mass(self) -> Fraction:
        return 1 - self.settled_village - self.settled_wolf

    @property
    def finished(self) -> bool:
        return self.board is None

    def total_values(self, continuation: Values | None = None) -> Values:
        if self.board is not None and continuation is None:
            raise ValueError("A continuing Board needs its evaluated value")
        village = self.settled_village + (self.active_mass * continuation.village_win if continuation else 0)
        return Values(village, 1 - village)


def advance(progress: Progress, target: int, rules: Rules, strategy: Strategy) -> Progress:
    if progress.finished:
        raise ValueError("The analysis has finished")
    outcomes = action_outcomes(progress.board, target, rules, strategy)
    village, wolf = progress.settled_village, progress.settled_wolf
    continuing = []
    for outcome in outcomes:
        if outcome.board.winner == "village":
            village += progress.active_mass * outcome.probability
        elif outcome.board.winner == "wolf":
            wolf += progress.active_mass * outcome.probability
        else:
            continuing.append(outcome.board)
    if len(continuing) > 1:
        raise ValueError("Multiple continuing Boards need a broader public-information model")
    return Progress(continuing[0] if continuing else None, village, wolf, progress.board, outcomes)
