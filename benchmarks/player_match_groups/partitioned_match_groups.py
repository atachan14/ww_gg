"""Independent cut-out grouping prototype (internal PartitionedMatchGroups); never an application factory.

Construct a known symmetric law, then retain only proven within-block swaps
which preserve the ordered observation program. No law/permutation search in
comparison. This is joint-support conditioning, NOT Model A/report generation,
physical transitions, action optimization or a game-value evaluator.
"""
from collections import Counter
from dataclasses import dataclass, field, replace
from fractions import Fraction as F
from werewolf.exact import (Rules, Strategy, ClaimPolicy, initial_board,
                            replace_worlds, condition_claims)
from werewolf.seer_acquisition import from_board, normalize, condition_publications, SeerReport
from werewolf.seer_future_uniform import TrueScanState, acquire_uniform, FuturePending


def _unsupported_baseline(players, mediums, rules, strategy, claim_policy):
    return (type(players) is not int or players not in (4, 5) or type(mediums) is not int or mediums not in (0, 1)
        or type(rules) is not Rules or rules.allow_self_bite or rules.initial_seer not in ('none', 'normal', 'random_white')
        or type(strategy) is not Strategy or (strategy.day, strategy.night, strategy.fake_reports) != ('random',)*3
        or strategy.include_self_bite or type(claim_policy) is not ClaimPolicy)


@dataclass(frozen=True)
class UnsupportedPartition:
    reason: str


@dataclass(frozen=True)
class Observation:
    # rows within ONE explicit simultaneous batch are an unordered multiset.
    # Separate batches are ordered, even when their day/phase is identical.
    kind: str
    rows: tuple
    day: int = 1
    phase: str = 'day'


@dataclass(frozen=True, eq=False)
class SharedContext:
    baseline: object = field(repr=False)
    public: TrueScanState = field(repr=False)
    private: TrueScanState = field(repr=False)
    claims: tuple
    alive: tuple
    events: tuple
    groups: tuple
    scope: str = 'public'
    public_support_mass: F = F(1)
    private_support_mass: F = F(1)


@dataclass(frozen=True)
class PlayerComparisonInfo:
    # A read-only companion to PlayerData, not a replacement of saved UI rows.
    # Every row shares the SAME complete immutable context by reference.
    player: int
    context: SharedContext = field(repr=False)
    block: int
    role_rates: tuple

    @property
    def token(self):
        # Context equality is identity: no accidental cross-history/policy merge.
        return self.context, self.block


@dataclass(frozen=True)
class RoleCell:
    composition: tuple
    world_multiplicity: int
    secret_multiplicity: int
    mass: F


@dataclass(frozen=True)
class ChoiceClass:
    targets: tuple
    multiplicity: int
    mass: F


@dataclass(frozen=True, eq=False)
class SymmetricBaseline:
    players: int
    rules: Rules
    strategy: Strategy
    claim_policy: ClaimPolicy
    mediums: int
    board: object = field(init=False, repr=False)
    state: TrueScanState = field(init=False, repr=False)

    def __post_init__(self):
        if _unsupported_baseline(self.players, self.mediums, self.rules, self.strategy, self.claim_policy):
            raise ValueError('Unsupported constructed baseline')
        board = initial_board(self.players, 1, self.mediums, 1)
        state = TrueScanState(from_board(board), initial_rule=self.rules.initial_seer)
        state = acquire_uniform(state, board.alive)
        if isinstance(state, FuturePending):raise ValueError(state.reason)
        object.__setattr__(self, "board", board)
        object.__setattr__(self, "state", state)


def make_baseline(players=5, *, mediums=0, rules=None, strategy=None, claim_policy=None):
    rules = Rules() if rules is None else rules
    strategy = Strategy(day='random', night='random', fake_reports='random') if strategy is None else strategy
    claim_policy = ClaimPolicy() if claim_policy is None else claim_policy
    # No arbitrary incoming distribution or per-position policy is accepted.
    if _unsupported_baseline(players, mediums, rules, strategy, claim_policy):
        return UnsupportedPartition('only constructed symmetric 4/5-player W1 S1 H0 uniform-policy baselines')

    # Construction theorem: all labelled allocations are uniform; acquisition
    # uses the original roster with equivariant uniform target rules. S_n acts
    # on the complete roles+acquisition law, not independent player marginals.
    return SymmetricBaseline(players, rules, strategy, claim_policy, mediums)


def _map_event(event, ids):
    rows = []
    for row in event.rows:
        if event.kind in ('co', 'private_role'):
            rows.append((ids[row[0]-1], row[1]))
        elif event.kind in ('report', 'private_result', 'select'):
            rows.append((ids[row[0]-1], ids[row[1]-1], *row[2:]))
        elif event.kind == 'death':
            rows.append((ids[row[0]-1],))
        else:
            raise ValueError('Unvalidated observation')
    return event.kind, event.day, event.phase, tuple(sorted(rows))


def _validate(event, n):
    if (type(event) is not Observation or type(event.rows) is not tuple or not event.rows
        or type(event.kind) is not str or type(event.day) is not int or event.day != 1 or type(event.phase) is not str or event.phase not in ('day', 'night')):
        return 'only nonempty explicit day1 observation batches; no physical phase transition'
    if event.kind in ('co', 'report') and event.phase != 'day':
        return 'day1 public declaration/report fixtures only'
    arity = dict(co=2, report=4, death=1, select=2, private_role=2, private_result=4)
    if event.kind not in arity:
        return 'unknown observation kind'
    if any(type(row) is not tuple or len(row) != arity[event.kind] for row in event.rows):
        return 'observation row schema'
    for row in event.rows:
        labels = row[:2] if event.kind in ('report', 'select', 'private_result') else row[:1]
        if any(type(p) is not int or not 1 <= p <= n for p in labels):
            return 'player IDs outside original roster'
        if len(labels) == 2 and labels[0] == labels[1]:
            return 'self target outside supported fixture'
        if event.kind in ('co', 'private_role') and (type(row[1]) is not str or row[1] not in ('latent', 'villager', 'medium', 'seer', 'wolf')):
            return 'unknown role'
        if event.kind == 'private_role' and row[1] == 'latent':
            return 'private role must be explicit'
        if event.kind in ('report', 'private_result') and (type(row[2]) is not str or row[2] not in ('white', 'black') or type(row[3]) is not int or row[3] != 1):
            return 'only acquired-slot1 seer results'
    if len(set(event.rows)) != len(event.rows):
        return 'duplicate observation row'
    if event.kind in ('co', 'report', 'private_role', 'private_result') and len({r[0] for r in event.rows}) != len(event.rows):
        return 'one observation per owner per batch'
    if event.kind.startswith('private') and len(event.rows) != 1:
        return 'single explicit private owner only'
    return None


class PartitionedMatchGroups:
    def __init__(self, baseline):
        if type(baseline) is not SymmetricBaseline:
            raise TypeError('Use make_baseline; arbitrary laws have no construction proof')
        self.baseline = baseline
        self.stats = Counter(baseline_constructions=1, joint_normalizations=0,
                             generator_checks=0, full_permutation_searches=0,
                             comparisons=0, rebuilds=0, updates=0)

    def start(self):
        b = self.baseline
        return SharedContext(b, b.state, b.state, ('latent',)*b.players,
                             tuple(range(1, b.players+1)), (), (tuple(range(1, b.players+1)),))

    def _condition(self, law, predicate):
        self.stats['joint_normalizations'] += 1
        return replace(law, hypotheses=normalize(tuple(h for h in law.hypotheses if predicate(h))))

    def _support_mass(self, law):
        # These are support-only filters: retain exact mass under the original
        # joint law. This is not a fake-report likelihood or physical branch mass.
        self.stats['support_mass_scans'] += 1
        keys = {(h.roles, h.acquisitions, h.guards, h.attacks) for h in law.hypotheses}
        return sum((h.mass for h in self.baseline.state.hypotheses if (h.roles, h.acquisitions, h.guards, h.attacks) in keys), F())

    def update(self, context, event):
        if type(context) is not SharedContext or context.baseline is not self.baseline:
            return UnsupportedPartition('context belongs to a different baseline/configuration')
        reason = _validate(event, self.baseline.players)
        if reason:
            return UnsupportedPartition(reason)
        b = self.baseline
        public, private, claims, alive, scope = context.public, context.private, context.claims, context.alive, context.scope
        try:
            if event.kind == 'co':
                if alive != tuple(range(1, b.players+1)) or scope != 'public':
                    return UnsupportedPartition('CO conditioning only before death/private view; rebuild the active ledger')
                if any(claims[p-1] != 'latent' or role == 'latent' for p, role in event.rows):
                    return UnsupportedPartition('CO replacement/withdrawal requires baseline rebuild')
                claims = tuple(dict(event.rows).get(p, claims[p-1]) for p in range(1, b.players+1))
                board = replace_worlds(b.board, public.public_roles)
                allowed = {tuple(w[:-1]) for w in condition_claims(board, claims, b.claim_policy).worlds}
                public = self._condition(public, lambda h: h.roles in allowed)
                private = public
            elif event.kind == 'report':
                if b.rules.initial_seer == 'none':
                    return UnsupportedPartition('no initial acquisition; slot1 reporting eligibility is unsupported')
                if any(p not in alive or claims[p-1] != 'seer' for p, t, c, d in event.rows):
                    return UnsupportedPartition('public report requires living declared seer')
                previous = {(r[0], r[3]) for e in context.events if e.kind == 'report' for r in e.rows}
                if any((p, d) in previous for p, t, c, d in event.rows):
                    return UnsupportedPartition('report correction requires baseline rebuild')
                reports = tuple(SeerReport(d, event.day, p, t, c) for p, t, c, d in event.rows)
                self.stats['joint_normalizations'] += 1
                public = replace(public, hypotheses=condition_publications(public.hypotheses, reports))
                if private is context.public:
                    private = public
                else:
                    self.stats['joint_normalizations'] += 1
                    private = replace(private, hypotheses=condition_publications(private.hypotheses, reports))
            elif event.kind == 'death':
                if any(p not in alive for p, in event.rows):
                    return UnsupportedPartition('death observation must remove a living original player')
                # Exogenous recorded facts only: no bite/execution likelihood or
                # night transition is inferred. Complete secret law is retained.
                alive = tuple(p for p in alive if p not in {r[0] for r in event.rows})
            elif event.kind == 'select':
                if any(p not in alive or t not in alive for p, t in event.rows):
                    return UnsupportedPartition('selection requires living actor and target')
                # Labelled selected instruction, NOT an optimized/generated policy.
            elif event.kind == 'private_role':
                if scope != 'public':
                    return UnsupportedPartition('rebuild for a different private observer')
                p, role = event.rows[0]
                index = dict(wolf=0, medium=1, seer=2).get(role)
                private = self._condition(public, lambda h: bool((h.roles[index] if index is not None else ((1<<b.players)-1)^sum(h.roles)) & (1<<(p-1))))
                scope = f'private:{p}:{role}'
            elif event.kind == 'private_result':
                p, t, c, d = event.rows[0]
                if scope != f'private:{p}:seer':
                    return UnsupportedPartition('own result requires the matching seer private scope')
                private = self._condition(private, lambda h: any((a.player, a.target, a.color, a.day) == (p, t, c, d) for a in h.acquisitions))
        except ValueError as error:
            return UnsupportedPartition('zero/invalid joint support: '+str(error))
        events = context.events+(event,)
        identity = tuple(range(1, b.players+1))
        reference = tuple(_map_event(e, identity) for e in events)
        groups = []
        # Only inherited within-block swaps are eligible. No merging, arbitrary
        # permutations, role-world scan or old canonical-key fallback here.
        # A swap preserving the entire ordered program commutes with every
        # supported equivariant filter. Hence it preserves both complete laws.
        # Leader swaps generate S_block, giving a proven product subgroup.
        for parent in context.groups:
            children = []
            for p in parent:
                for group in children:
                    ids = list(identity); q = group[0]
                    ids[p-1], ids[q-1] = ids[q-1], ids[p-1]
                    self.stats['generator_checks'] += 1
                    if tuple(_map_event(e, ids) for e in events) == reference:
                        group.append(p)
                        break
                else:
                    children.append([p])
            groups.extend(tuple(g) for g in children)
        self.stats['updates'] += 1
        mass = self._support_mass(public)
        own_mass = mass if private is public else self._support_mass(private)
        return SharedContext(b, public, private, claims, alive, events, tuple(groups), scope, mass, own_mass)

    def rebuild(self, active_program):
        self.stats['rebuilds'] += 1
        context = self.start()
        for event in active_program:
            context = self.update(context, event)
            if isinstance(context, UnsupportedPartition):
                break
        return context

    def rows(self, context):
        if context.baseline is not self.baseline:
            raise ValueError('Different baseline')
        self.stats['role_rate_builds'] += 1
        law = context.private
        rates = [[F() for _ in range(5)] for p in range(self.baseline.players)]
        for h in law.hypotheses:
            for p in range(self.baseline.players):
                r = next((r for r, mask in enumerate(h.roles) if mask & (1<<p)), 4)
                rates[p][r] += h.mass
        return tuple(PlayerComparisonInfo(p, context, i, tuple(rates[p-1]))
                     for i, group in enumerate(context.groups) for p in group)

    def equivalent(self, left, right):
        self.stats['comparisons'] += 1
        return left.token == right.token

    def role_cells(self, context):
        # Role-only count summary, NEVER a replacement for the secret joint law.
        cells = {}
        for h in context.private.hypotheses:
            masks = h.roles+(((1<<self.baseline.players)-1)^sum(h.roles),)
            key = tuple(tuple((mask & sum(1<<(p-1) for p in group)).bit_count() for mask in masks) for group in context.groups)
            worlds, count, mass = cells.get(key, (set(), 0, F()))
            worlds.add(h.roles)
            cells[key] = worlds, count+1, mass+h.mass
        return tuple(RoleCell(k, len(w), count, mass) for k, (w, count, mass) in sorted(cells.items()))

    def uniform_choices(self, context, legal):
        if type(context) is not SharedContext or context.baseline is not self.baseline:
            return UnsupportedPartition('context belongs to a different baseline/configuration')
        if type(legal) is not tuple or not legal or any(type(p) is not int for p in legal) or len(set(legal)) != len(legal) or not set(legal) <= set(context.alive):
            return UnsupportedPartition('explicit nonempty unique living legal target set required')
        if any(set(group) & set(legal) and not set(group) <= set(legal) for group in context.groups):
            return UnsupportedPartition('legal choices split a block; record selection/view constraints first')
        return tuple(ChoiceClass(group, len(group), F(len(group), len(legal)))
                     for group in context.groups if set(group) <= set(legal))