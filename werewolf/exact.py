"""The agreed V2/W1 example; no sampled role assignment or random outcome."""

from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Literal

Role = Literal["village", "wolf"]
PLAYERS = (1, 2, 3)


@dataclass(frozen=True)
class World:
    """One possible assignment, not an assignment selected as the real game."""

    wolf_id: int
    alive: tuple[int, ...] = PLAYERS

    def __post_init__(self):
        if type(self.wolf_id) is not int or self.wolf_id not in PLAYERS:
            raise ValueError("wolf_id must be one of the three player IDs")
        if not isinstance(self.alive, tuple) or any(type(p) is not int or p not in PLAYERS for p in self.alive):
            raise ValueError("alive must contain valid player IDs")
        if len(set(self.alive)) != len(self.alive):
            raise ValueError("alive cannot contain duplicate players")

    def role(self, player_id: int) -> Role:
        if type(player_id) is not int or player_id not in PLAYERS:
            raise ValueError("Unknown player")
        return "wolf" if player_id == self.wolf_id else "village"

    @property
    def counts(self) -> tuple[int, int]:
        wolves = int(self.wolf_id in self.alive)
        return len(self.alive) - wolves, wolves

    @property
    def winner(self) -> Role | None:
        villagers, wolves = self.counts
        if wolves == 0:
            return "village"
        if wolves >= villagers:
            return "wolf"
        return None


@dataclass(frozen=True)
class WeightedWorld:
    world: World
    probability: Fraction


@dataclass(frozen=True)
class Belief:
    """A normalized distribution over compatible worlds with the same alive list."""

    worlds: tuple[WeightedWorld, ...]

    def __post_init__(self):
        if not isinstance(self.worlds, tuple) or not self.worlds:
            raise ValueError("At least one weighted world is required")
        if any(not isinstance(item, WeightedWorld) or not isinstance(item.world, World) for item in self.worlds):
            raise ValueError("Invalid weighted world")
        if any(not isinstance(item.probability, Fraction) or item.probability <= 0 for item in self.worlds):
            raise ValueError("World probabilities must be positive Fractions")
        if sum((item.probability for item in self.worlds), Fraction(0)) != 1:
            raise ValueError("World probabilities must sum to one")
        if len({item.world for item in self.worlds}) != len(self.worlds):
            raise ValueError("Duplicate worlds")
        if any(item.world.alive != self.worlds[0].world.alive for item in self.worlds):
            raise ValueError("Alive players must agree across possible worlds")

    @property
    def alive(self) -> tuple[int, ...]:
        return self.worlds[0].world.alive

    @property
    def finished(self) -> bool:
        return all(item.world.winner is not None for item in self.worlds)

    def role_probability(self, player_id: int, role: Role) -> Fraction:
        if type(player_id) is not int or player_id not in PLAYERS:
            raise ValueError("Unknown player")
        if role not in ("village", "wolf"):
            raise ValueError("Unknown role")
        return sum((item.probability for item in self.worlds if item.world.role(player_id) == role), Fraction(0))


@dataclass(frozen=True)
class Outcome:
    removed_role: Role
    probability: Fraction
    posterior: Belief
    winner: Role

    @property
    def counts(self) -> tuple[int, int]:
        return self.posterior.worlds[0].world.counts


@dataclass(frozen=True)
class ActionEvaluation:
    target_id: int
    outcomes: tuple[Outcome, ...]
    village_win: Fraction
    wolf_win: Fraction


@dataclass(frozen=True)
class StrategyEvaluation:
    village_win: Fraction
    wolf_win: Fraction


def initial_belief() -> Belief:
    """Uniform prior over all three compatible V2/W1 assignments."""
    return Belief(tuple(WeightedWorld(World(wolf), Fraction(1, 3)) for wolf in PLAYERS))


def evaluate_execution(belief: Belief, target_id: int) -> ActionEvaluation:
    """Condition on the chosen action; preserve and return all role outcomes."""
    if type(target_id) is not int or target_id not in belief.alive:
        raise ValueError("Choose a living player")
    if any(item.world.winner is not None for item in belief.worlds):
        raise ValueError("A finished world cannot take another action")

    outcomes = []
    for role in ("wolf", "village"):
        compatible = tuple(item for item in belief.worlds if item.world.role(target_id) == role)
        probability = sum((item.probability for item in compatible), Fraction(0))
        if not probability:
            continue
        posterior = Belief(tuple(WeightedWorld(
            replace(item.world, alive=tuple(p for p in item.world.alive if p != target_id)),
            item.probability / probability,
        ) for item in compatible))
        winners = {item.world.winner for item in posterior.worlds}
        if len(winners) != 1 or None in winners:
            raise ValueError("This minimal implementation only evaluates terminal V2/W1 outcomes")
        outcomes.append(Outcome(role, probability, posterior, winners.pop()))

    village_win = sum((outcome.probability for outcome in outcomes if outcome.winner == "village"), Fraction(0))
    return ActionEvaluation(target_id, tuple(outcomes), village_win, 1 - village_win)


def evaluate_uniform_strategy(belief: Belief) -> StrategyEvaluation:
    """Average candidate values; a target evaluation is a separate quantity."""
    if not belief.alive:
        raise ValueError("No living players")
    village_win = sum((evaluate_execution(belief, target).village_win for target in belief.alive), Fraction(0)) / len(belief.alive)
    return StrategyEvaluation(village_win, 1 - village_win)
