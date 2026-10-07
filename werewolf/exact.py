"""Public Board calculations for 3–9 players, wolves and ability-free mediums, using exact fractions."""

from dataclasses import dataclass, replace
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from math import comb
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


ROLES = ('villager', 'medium', 'wolf')


@dataclass(frozen=True)
class ClaimPolicy:
    villager: str | tuple[str, ...] | list[str] = 'filled'
    medium: str | tuple[str, ...] | list[str] = 'filled'
    wolf: str = 'none'

    def __post_init__(self):
        if any(not self.valid_conditions(getattr(self, role)) for role in ('villager', 'medium')) or self.wolf != 'none':
            raise ValueError("Invalid CO calculation condition")
        for role in ('villager', 'medium'):
            if isinstance(getattr(self, role), list):
                object.__setattr__(self, role, tuple(getattr(self, role)))

    @staticmethod
    def valid_conditions(value):
        return (value in ('none', 'counter', 'filled') if isinstance(value, str) else
                isinstance(value, (tuple, list)) and all(v in ('counter', 'filled') for v in value) and len(set(value)) == len(value))

    def conditions(self, role):
        value = getattr(self, role)
        return (() if value == 'none' else (value,)) if isinstance(value, str) else tuple(value)


def default_bluff_roles(present):
    # Role settings, shared by both models; not a special case in inference.
    return {'villager': (), 'medium': (), 'wolf': tuple(r for r in ROLES if r in present)}


def compatible_claim(mask_w, mask_m, player, claim, bluff_roles=None):
    role = 'wolf' if mask_w & (1 << (player - 1)) else 'medium' if mask_m & (1 << (player - 1)) else 'villager'
    settings = default_bluff_roles(ROLES) if bluff_roles is None else bluff_roles
    return claim == 'latent' or role == claim or claim in settings.get(role, ())


def condition_claims(board, claims, policy=ClaimPolicy(), bluff_roles=None):
    if not isinstance(claims, tuple) or len(claims) != board.player_count or any(c not in (*ROLES, 'latent') for c in claims):
        raise ValueError("CO must identify one allowed role per player")
    present = {'latent'}
    for wolf, medium, _ in board.role_belief:
        if wolf: present.add('wolf')
        if medium: present.add('medium')
        if (wolf | medium).bit_count() < board.player_count: present.add('villager')
    if any(c not in present for c in claims):
        raise ValueError("配役にない役職へのCOは指定できません。")
    entries = []
    for wolf, medium, q in board.role_belief:
        if not all(compatible_claim(wolf, medium, i, claim, bluff_roles) for i, claim in enumerate(claims, 1)):
            continue
        allowed = True
        for role in ('villager', 'medium'):
            modes = policy.conditions(role)
            capacity = medium.bit_count() if role == 'medium' else board.player_count - wolf.bit_count() - medium.bit_count()
            claim_count = claims.count(role)
            trigger = ('counter' in modes and claim_count > 0) or ('filled' in modes and capacity > 0 and claim_count >= capacity)
            if trigger:
                for i, claim in enumerate(claims, 1):
                    actual = 'wolf' if wolf & (1 << (i - 1)) else 'medium' if medium & (1 << (i - 1)) else 'villager'
                    # A living true role must have counterclaimed when the
                    # public trigger occurs. Dead players cannot issue a new CO.
                    if i in board.alive and actual == role and claim != role:
                        allowed = False
                        break
        if allowed:
            entries.append((wolf, medium, q))
    mass = sum((q for _, _, q in entries), Fraction(0))
    if not mass:
        raise ValueError("COと配役・騙り・CCO条件が両立しません。CO人数と計算条件を確認してください。")
    return replace(board, wolf_count=None, claims=claims, belief=(),
                   role_belief=tuple((w, m, q / mass) for w, m, q in entries))


def group_initial_board(board, claims, policy=ClaimPolicy(), bluff_roles=None):
    """Equal legal joint bluff-role placements, then equal legal completions.

    This is an initial snapshot interpretation, never a transition updater.
    """
    if board.history or board.alive != tuple(range(1, board.player_count+1)) or board.phase != 'day' or board.day != 1:
        raise ValueError('COグループの初期配分は初日昼だけで定義します。')
    present = {r for r in ROLES if any(board.role_probability(i,r)>0 for i in board.alive)}
    settings=default_bluff_roles(present) if bluff_roles is None else bluff_roles
    if set(settings)-set(ROLES) or any(set(options)-present for options in settings.values()):
        raise ValueError('Unknown bluff-role setting')
    filtered=condition_claims(board,claims,policy,settings)
    faker_roles=tuple(r for r in ROLES if any(c!=r and c in present for c in settings.get(r,())))
    full=(1<<board.player_count)-1
    groups={}
    for w,m,_ in filtered.role_belief:
        masks={'wolf':w,'medium':m,'villager':full^(w|m)}
        key=tuple(masks[r] for r in faker_roles)
        groups.setdefault(key,[]).append((w,m))
    entries=tuple((w,m,Fraction(1,len(groups)*len(configs))) for configs in groups.values() for w,m in configs)
    return replace(filtered,belief=(),role_belief=entries)


def co_group_compositions(board):
    groups=[]
    for claim in ('villager','medium','wolf','latent'):
        ids=tuple(i for i in board.alive if board.claims[i-1]==claim)
        if not ids: continue
        bit=sum(1<<(i-1) for i in ids)
        counts={}
        for w,m,q in board.role_belief:
            key=(len(ids)-(w&bit).bit_count()-(m&bit).bit_count(),(m&bit).bit_count(),(w&bit).bit_count())
            counts[key]=counts.get(key,Fraction(0))+q
        groups.append(dict(claim=claim,ids=ids,compositions=tuple((*key,q) for key,q in sorted(counts.items()))))
    return groups


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
    wolf_count: int | None = 1
    day: int = 1
    phase: Phase = "day"
    history: tuple[PublicEvent, ...] = ()

    belief: tuple[tuple[int, Fraction], ...] = ()
    initial_medium_count: int = 0
    claims: tuple[str, ...] = ()
    role_belief: tuple[tuple[int, int, Fraction], ...] = ()

    def __post_init__(self):
        if type(self.player_count) is not int or not 3 <= self.player_count <= 9:
            raise ValueError("v0.2 supports 3–9 players")
        if not isinstance(self.alive, tuple) or len(set(self.alive)) != len(self.alive):
            raise ValueError("Alive IDs must be a distinct tuple")
        if any(type(player) is not int or not 1 <= player <= self.player_count for player in self.alive):
            raise ValueError("Unknown player")
        if self.wolf_count is not None and (type(self.wolf_count) is not int or not 0 <= self.wolf_count <= len(self.alive)):
            raise ValueError("Invalid public wolf-count constraint")
        if type(self.day) is not int or self.day < 1 or self.phase not in ("day", "night"):
            raise ValueError("Invalid Day/Phase")
        if not isinstance(self.history, tuple) or any(not isinstance(event, PublicEvent) for event in self.history):
            raise ValueError("Invalid public history")
        dead = tuple(event.target for event in self.history)
        if len(set(dead)) != len(dead) or set(dead) != set(range(1, self.player_count + 1)) - set(self.alive):
            raise ValueError("History and alive players must agree")

        if type(self.initial_medium_count) is not int or not 0 <= self.initial_medium_count <= self.player_count:
            raise ValueError("Invalid medium count")
        if not self.claims:
            object.__setattr__(self, 'claims', ('latent',) * self.player_count)
        if len(self.claims) != self.player_count or any(c not in (*ROLES, 'latent') for c in self.claims):
            raise ValueError("Invalid public CO")
        if self.role_belief:
            if (len({(w, m) for w, m, _ in self.role_belief}) != len(self.role_belief)
                    or any(type(w) is not int or type(m) is not int or w < 0 or m < 0
                           or w >= 1 << self.player_count or m >= 1 << self.player_count
                           or w & m or m.bit_count() != self.initial_medium_count
                           or not isinstance(q, Fraction) or q <= 0 for w, m, q in self.role_belief)
                    or sum((q for _, _, q in self.role_belief), Fraction(0)) != 1):
                raise ValueError("Use an exact joint wolf/medium distribution")
            marginal = {}
            for wolf, _, q in self.role_belief:
                marginal[wolf] = marginal.get(wolf, Fraction(0)) + q
            object.__setattr__(self, 'belief', tuple(sorted(marginal.items())))
        if not self.belief:
            if self.wolf_count is None:
                raise ValueError("A mixed count needs an exact belief")
            masks = [sum(1 << (i - 1) for i in ids) for ids in combinations(self.alive, self.wolf_count)]
            # Compatibility for direct one-wolf terminal Board construction.
            if self.wolf_count == 0 and self.history:
                masks = [1 << (self.history[-1].target - 1)]
            object.__setattr__(self, 'belief', tuple((mask, Fraction(1, len(masks))) for mask in masks))
        if (len({m for m, _ in self.belief}) != len(self.belief)
                or any(type(m) is not int or not 0 <= m < 1 << self.player_count
                       or not isinstance(q, Fraction) or q <= 0 for m, q in self.belief)
                or sum((q for _, q in self.belief), Fraction(0)) != 1):
            raise ValueError("Belief must be a normalized exact joint distribution")
        if not self.role_belief:
            joint = []
            for wolf, q in self.belief:
                available = tuple(i for i in range(self.player_count) if not wolf & (1 << i))
                if self.initial_medium_count > len(available):
                    raise ValueError("Role counts exceed player count")
                medium_sets = tuple(combinations(available, self.initial_medium_count))
                joint.extend((wolf, sum(1 << i for i in ids), q / len(medium_sets)) for ids in medium_sets)
            object.__setattr__(self, 'role_belief', tuple(joint))
        counts = self.wolf_count_distribution
        exact = next(iter(counts)) if len(counts) == 1 else None
        if self.wolf_count is not None and self.wolf_count != exact:
            raise ValueError("Count and joint distribution disagree")
        object.__setattr__(self, 'wolf_count', exact)

    @property
    def alive_mask(self):
        return sum(1 << (i - 1) for i in self.alive)

    @property
    def wolf_count_distribution(self) -> dict[int, Fraction]:
        result = {}
        for mask, weight in self.belief:
            count = (mask & self.alive_mask).bit_count()
            result[count] = result.get(count, Fraction(0)) + weight
        return dict(sorted(result.items()))

    @property
    def villagers(self) -> int | None:
        return None if self.wolf_count is None else len(self.alive) - self.wolf_count

    @property
    def winner(self) -> Winner | None:
        winners = {winner_for(len(self.alive), w) for w in self.wolf_count_distribution}
        return next(iter(winners)) if len(winners) == 1 else None

    def wolf_probability(self, player: int) -> Fraction:
        if type(player) is not int or not 1 <= player <= self.player_count:
            raise ValueError("Unknown player")
        return sum((q for mask, q in self.belief if mask & (1 << (player - 1))), Fraction(0))

    def role_probability(self, player: int, role: str) -> Fraction:
        if type(player) is not int or not 1 <= player <= self.player_count or role not in ROLES:
            raise ValueError("Unknown player or role")
        bit = 1 << (player - 1)
        return sum((q for wolf, medium, q in self.role_belief
                    if (bool(wolf & bit) if role == 'wolf' else bool(medium & bit) if role == 'medium'
                        else not (wolf | medium) & bit)), Fraction(0))

    def joint_wolf_probability(self, players: tuple[int, ...]) -> Fraction:
        if any(type(i) is not int or not 1 <= i <= self.player_count for i in players):
            raise ValueError("Unknown player")
        required = sum(1 << (i - 1) for i in set(players))
        return sum((q for mask, q in self.belief if mask & required == required), Fraction(0))


def winner_for(n: int, wolves: int) -> Winner | None:
    return "village" if wolves == 0 else "wolf" if wolves >= n - wolves else None


def initial_board(player_count: int = 5, wolf_count: int = 1, medium_count: int = 0) -> Board:
    if type(player_count) is not int or not 3 <= player_count <= 9:
        raise ValueError("Choose 3–9 players")
    if type(wolf_count) is not int or not 1 <= wolf_count <= (player_count - 1) // 2:
        raise ValueError("Choose wolves fewer than villagers")
    if type(medium_count) is not int or not 0 <= medium_count <= player_count - wolf_count:
        raise ValueError("Choose medium count within the village camp")
    return Board(player_count, tuple(range(1, player_count + 1)), wolf_count, initial_medium_count=medium_count)


@dataclass(frozen=True)
class BoardOutcome:
    probability: Fraction
    board: Board


def legal_targets(board: Board, rules: Rules, strategy: Strategy) -> tuple[int, ...]:
    validate_strategy(rules, strategy)
    if board.winner:
        return ()
    if board.phase == 'day' or strategy.include_self_bite:
        return board.alive
    alive_mask = board.alive_mask
    counts = set(board.wolf_count_distribution)
    return tuple(i for i in board.alive if
                 {(w & alive_mask).bit_count() for w, _ in board.belief if not w & (1 << (i - 1))} == counts)


def action_outcomes(board: Board, target: int, rules: Rules, strategy: Strategy) -> tuple[BoardOutcome, ...]:
    validate_strategy(rules, strategy)
    if board.winner is not None:
        raise ValueError("A terminal Board cannot advance")
    if type(target) is not int or target not in legal_targets(board, rules, strategy):
        raise ValueError("Choose a living player")
    alive = tuple(player for player in board.alive if player != target)
    bit = 1 << (target - 1)
    groups = {}
    count_weights = board.wolf_count_distribution
    alive_mask = board.alive_mask
    if board.phase == "night" and not strategy.include_self_bite:
        # A forced legal bite, within each count hypothesis. This is not a
        # globally observed random location (which would reweight the counts).
        normalizers = {}
        for mask, q in board.belief:
            w = (mask & alive_mask).bit_count()
            if not mask & bit:
                normalizers[w] = normalizers.get(w, Fraction(0)) + q
        if set(normalizers) != set(count_weights):
            raise ValueError("Target cannot be legally bitten in every count hypothesis")
    for mask, medium, q in board.role_belief:
        if board.phase == "night" and not strategy.include_self_bite:
            if mask & bit:
                continue
            w = (mask & alive_mask).bit_count()
            q *= count_weights[w] / normalizers[w]
        w = (mask & (alive_mask ^ bit)).bit_count()
        winner = winner_for(len(alive), w)
        groups.setdefault(winner, []).append((mask, medium, q))
    event = PublicEvent(board.day, board.phase, target)
    outcomes = []
    for winner in ('village', 'wolf', None):
        entries = groups.get(winner)
        if not entries:
            continue
        mass = sum((q for _, _, q in entries), Fraction(0))
        phase = board.phase if winner else ('night' if board.phase == 'day' else 'day')
        day = board.day + int(not winner and board.phase == 'night')
        child = Board(board.player_count, alive, None, day, phase, board.history + (event,),
                      initial_medium_count=board.initial_medium_count, claims=board.claims,
                      role_belief=tuple((w, m, q / mass) for w, m, q in entries))
        outcomes.append(BoardOutcome(mass, child))
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
    """Lazy view of every exact action/chance branch; histories are never pruned."""
    board: Board
    rules: Rules = Rules()
    strategy: Strategy = Strategy()

    @property
    def actions(self) -> tuple[Action, ...]:
        if self.board.winner:
            return ()
        return tuple(Action(target, tuple(Chance(o.probability, TreeNode(o.board, self.rules, self.strategy))
                     for o in action_outcomes(self.board, target, self.rules, self.strategy)))
                     for target in legal_targets(self.board, self.rules, self.strategy))


def build_tree(board: Board, rules: Rules, strategy: Strategy) -> TreeNode:
    validate_strategy(rules, strategy)
    return TreeNode(board, rules, strategy)


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


def marginal_state(board):
    result = {}
    for mask, q in board.belief:
        compact = sum(1 << j for j, i in enumerate(board.alive) if mask & (1 << (i - 1)))
        result[compact] = result.get(compact, Fraction(0)) + q
    return tuple(sorted(result.items()))


@lru_cache(maxsize=4096)
def solve(n, phase, belief, strategy):
    """Backward induction on exact public states, sharing equivalent histories.

    Exchangeable survivors have identical action subtrees up to relabeling.
    Their count distribution is a sufficient statistic for future values,
    but full correlated location beliefs remain on displayed Boards.
    """
    counts = {}
    for mask, q in belief:
        w = mask.bit_count()
        counts[w] = counts.get(w, Fraction(0)) + q
    winners = {winner_for(n, w) for w in counts}
    if len(winners) == 1 and None not in winners:
        return Values(Fraction(int('village' in winners)), Fraction(int('wolf' in winners)))
    symmetric = all(q == counts[m.bit_count()] / comb(n, m.bit_count()) for m, q in belief)
    symmetric &= len(belief) == sum(comb(n, w) for w in counts)
    if symmetric:
        candidates = (symmetric_action(n, phase, tuple(sorted(counts.items())), strategy),) * n
    else:
        # General joint beliefs: one public optimization after all candidates.
        board = Board(max(3, n), tuple(range(1, n + 1)), None, phase=phase, belief=belief)
        candidates = tuple(value_for_action(board, i, Rules(strategy.include_self_bite), strategy)
                           for i in legal_targets(board, Rules(strategy.include_self_bite), strategy))
    return aggregate_values(phase, candidates, strategy)


@lru_cache(maxsize=4096)
def symmetric_action(n, phase, counts, strategy):
    village, continuing = Fraction(0), {}
    for w, mass in counts:
        hits = ((w - 1, Fraction(w, n)), (w, Fraction(n - w, n))) if phase == 'day' or strategy.include_self_bite else ((w, Fraction(1)),)
        for remaining, probability in hits:
            if not probability:
                continue
            q = mass * probability
            winner = winner_for(n - 1, remaining)
            if winner == 'village':
                village += q
            elif winner is None:
                continuing[remaining] = continuing.get(remaining, Fraction(0)) + q
    mass = sum(continuing.values(), Fraction(0))
    if mass:
        belief = tuple(sorted((sum(1 << i for i in ids), q / mass / comb(n - 1, w))
                       for w, q in continuing.items() for ids in combinations(range(n - 1), w)))
        village += mass * solve(n - 1, 'night' if phase == 'day' else 'day', belief, strategy).village_win
    return Values(village, 1 - village)


def value_for_action(board, target, rules, strategy):
    village = sum((o.probability * solve(len(o.board.alive), o.board.phase, marginal_state(o.board), strategy).village_win
                   for o in action_outcomes(board, target, rules, strategy)), Fraction(0))
    return Values(village, 1 - village)


@dataclass
class Evaluation:
    strategy: Strategy

    def board_value(self, node: TreeNode) -> Values:
        return solve(len(node.board.alive), node.board.phase, marginal_state(node.board), self.strategy)

    def action_value(self, node: TreeNode, target: int) -> Values:
        return value_for_action(node.board, target, node.rules, self.strategy)


def evaluate_tree(root: TreeNode, strategy: Strategy) -> Evaluation:
    validate_strategy(root.rules, strategy)
    result = Evaluation(strategy)
    result.board_value(root)  # Complete terminal-to-root evaluation before rendering.
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
        raise ValueError("Continuing hypotheses must be merged into one public Board")
    return Progress(continuing[0] if continuing else None, village, wolf, progress.board, outcomes)
