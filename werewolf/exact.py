"""Exact possible-world transitions; action candidates never receive random weights."""

from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import combinations
from typing import Literal

Role = Literal["village", "wolf"]
PLAYERS = (1, 2, 3)  # The existing three-player screen; TOP expansion is separate.


@dataclass(frozen=True)
class World:
    """One possible assignment, never a role assignment selected as the truth."""

    players: tuple[int, ...]
    wolves: frozenset[int]
    alive: tuple[int, ...]

    def __post_init__(self):
        if not isinstance(self.players, tuple) or not self.players:
            raise ValueError("A player roster is required")
        if any(type(player) is not int or player < 1 for player in self.players) or len(set(self.players)) != len(self.players):
            raise ValueError("Player IDs must be distinct positive integers")
        if not isinstance(self.wolves, frozenset) or any(type(player) is not int for player in self.wolves) or not self.wolves <= set(self.players):
            raise ValueError("Wolf IDs must belong to the roster")
        if not isinstance(self.alive, tuple) or any(type(player) is not int or player not in self.players for player in self.alive):
            raise ValueError("Alive players must belong to the roster")
        if len(set(self.alive)) != len(self.alive):
            raise ValueError("Alive players cannot be duplicated")

    def role(self, player: int) -> Role:
        if type(player) is not int or player not in self.players:
            raise ValueError("Unknown player")
        return "wolf" if player in self.wolves else "village"

    @property
    def counts(self) -> tuple[int, int]:
        wolves = len(self.wolves.intersection(self.alive))
        return len(self.alive) - wolves, wolves

    @property
    def winner(self) -> Role | None:
        villagers, wolves = self.counts
        if wolves == 0:
            return "village"
        if wolves >= villagers:
            return "wolf"
        return None

    def remove(self, player: int) -> "World":
        if type(player) is not int or player not in self.alive:
            raise ValueError("Choose a living player")
        if self.winner is not None:
            raise ValueError("A finished world cannot take another action")
        return replace(self, alive=tuple(item for item in self.alive if item != player))


@dataclass(frozen=True)
class WeightedWorld:
    world: World
    probability: Fraction

    def __post_init__(self):
        if not isinstance(self.world, World) or not isinstance(self.probability, Fraction) or self.probability <= 0:
            raise ValueError("A world must have a positive exact probability")


@dataclass(frozen=True)
class Belief:
    """A normalized distribution for one public roster/alive configuration."""

    worlds: tuple[WeightedWorld, ...]

    def __post_init__(self):
        if not isinstance(self.worlds, tuple) or not self.worlds or any(not isinstance(item, WeightedWorld) for item in self.worlds):
            raise ValueError("At least one weighted world is required")
        if sum((item.probability for item in self.worlds), Fraction(0)) != 1:
            raise ValueError("World probabilities must sum to one")
        if len({item.world for item in self.worlds}) != len(self.worlds):
            raise ValueError("Duplicate worlds")
        first = self.worlds[0].world
        if any(item.world.players != first.players or item.world.alive != first.alive or len(item.world.wolves) != len(first.wolves) for item in self.worlds):
            raise ValueError("Possible worlds must share their roster, initial cast, and alive list")

    @property
    def players(self) -> tuple[int, ...]:
        return self.worlds[0].world.players

    @property
    def alive(self) -> tuple[int, ...]:
        return self.worlds[0].world.alive

    @property
    def finished(self) -> bool:
        return all(item.world.winner is not None for item in self.worlds)

    def role_probability(self, player: int, role: Role) -> Fraction:
        if type(player) is not int or player not in self.players or role not in ("village", "wolf"):
            raise ValueError("Unknown player or role")
        return sum((item.probability for item in self.worlds if item.world.role(player) == role), Fraction(0))


@dataclass(frozen=True)
class Outcome:
    removed_role: Role
    probability: Fraction
    posterior: Belief
    winner: Role | None

    @property
    def counts(self) -> tuple[int, int] | None:
        counts = {item.world.counts for item in self.posterior.worlds}
        return next(iter(counts)) if len(counts) == 1 else None


@dataclass(frozen=True)
class ActionEvaluation:
    """Resolved probabilities immediately after one specified action, not a policy."""

    target_id: int
    outcomes: tuple[Outcome, ...]
    village_win: Fraction
    wolf_win: Fraction
    unresolved: Fraction


def initial_belief(player_count: int = 3, wolf_count: int = 1) -> Belief:
    """Equal role-assignment weights; no probability is assigned to an action."""
    if type(player_count) is not int or not 3 <= player_count <= 9:
        raise ValueError("The calculation roster must have 3 to 9 players")
    if type(wolf_count) is not int or not 1 <= wolf_count < player_count - wolf_count:
        raise ValueError("Choose a nonterminal village/wolf initial cast")
    players = tuple(range(1, player_count + 1))
    assignments = tuple(frozenset(wolves) for wolves in combinations(players, wolf_count))
    probability = Fraction(1, len(assignments))
    return Belief(tuple(WeightedWorld(World(players, wolves, players), probability) for wolves in assignments))


def evaluate_execution(belief: Belief, target_id: int) -> ActionEvaluation:
    """Evaluate this target alone, retaining all of its possible role outcomes."""
    if type(target_id) is not int or target_id not in belief.alive:
        raise ValueError("Choose a living player")
    if any(item.world.winner is not None for item in belief.worlds):
        raise ValueError("A finished world cannot take another action")
    groups = {}
    for item in belief.worlds:
        child = item.world.remove(target_id)
        key = (item.world.role(target_id), child.winner)
        groups.setdefault(key, []).append(WeightedWorld(child, item.probability))
    outcomes = []
    for (role, winner), worlds in groups.items():
        probability = sum((item.probability for item in worlds), Fraction(0))
        posterior = Belief(tuple(WeightedWorld(item.world, item.probability / probability) for item in worlds))
        outcomes.append(Outcome(role, probability, posterior, winner))
    village_win = sum((outcome.probability for outcome in outcomes if outcome.winner == "village"), Fraction(0))
    wolf_win = sum((outcome.probability for outcome in outcomes if outcome.winner == "wolf"), Fraction(0))
    return ActionEvaluation(target_id, tuple(outcomes), village_win, wolf_win, 1 - village_win - wolf_win)


@dataclass(frozen=True)
class AnalysisState:
    """The unresolved distribution plus stopped worlds with absolute weights."""

    active: Belief | None
    settled: tuple[WeightedWorld, ...] = ()

    def __post_init__(self):
        if not isinstance(self.settled, tuple) or any(not isinstance(item, WeightedWorld) or item.world.winner is None for item in self.settled):
            raise ValueError("Only terminal worlds can be settled")
        mass = sum((item.probability for item in self.settled), Fraction(0))
        if mass > 1 or (self.active is None and mass != 1) or (self.active is not None and mass >= 1):
            raise ValueError("Active and settled probabilities must conserve one")
        if self.active is not None:
            if not isinstance(self.active, Belief) or any(item.world.winner is not None for item in self.active.worlds):
                raise ValueError("Active worlds must be nonterminal")
        worlds = self.all_worlds
        first = worlds[0].world
        if any(item.world.players != first.players or len(item.world.wolves) != len(first.wolves) for item in worlds):
            raise ValueError("All worlds must share their initial cast")
        if len({item.world for item in worlds}) != len(worlds):
            raise ValueError("Duplicate worlds in a fixed-action history")

    @property
    def village_win(self) -> Fraction:
        return sum((item.probability for item in self.settled if item.world.winner == "village"), Fraction(0))

    @property
    def wolf_win(self) -> Fraction:
        return sum((item.probability for item in self.settled if item.world.winner == "wolf"), Fraction(0))

    @property
    def active_mass(self) -> Fraction:
        return 1 - self.village_win - self.wolf_win

    @property
    def all_worlds(self) -> tuple[WeightedWorld, ...]:
        active = tuple(WeightedWorld(item.world, item.probability * self.active_mass) for item in self.active.worlds) if self.active else ()
        return self.settled + active

    @property
    def finished(self) -> bool:
        return self.active is None


def apply_execution(state: AnalysisState, target_id: int) -> AnalysisState:
    """Advance only the unresolved worlds; preserve every already finished world."""
    if state.active is None:
        raise ValueError("This analysis has already finished")
    if type(target_id) is not int or target_id not in state.active.alive:
        raise ValueError("Choose a living player")
    settled = list(state.settled)
    active = []
    for item in state.active.worlds:
        child = item.world.remove(target_id)
        weighted = WeightedWorld(child, item.probability * state.active_mass)
        (settled if child.winner else active).append(weighted)
    mass = sum((item.probability for item in active), Fraction(0))
    belief = Belief(tuple(WeightedWorld(item.world, item.probability / mass) for item in active)) if active else None
    return AnalysisState(belief, tuple(settled))


def legal_attacks(world: World) -> tuple[int, ...]:
    """Legal candidates in one possible world; this does not choose or weight them."""
    if world.winner is not None:
        return ()
    return tuple(player for player in world.alive if world.role(player) == "village")


def attack_world(world: World, target_id: int) -> World:
    if type(target_id) is not int or target_id not in legal_attacks(world):
        raise ValueError("Wolves may attack a living villager in a nonterminal world")
    return world.remove(target_id)
