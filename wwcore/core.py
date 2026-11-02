"""The v0.7 calculation: reading (蠖ｹ閨ｷ邇・ and forward outcomes (蜍晉紫), board by board.

A state counts, per 荳閾ｴ繧ｰ繝ｫ繝ｼ繝・ how many members have each kind (role plus what
the seer knows about them). `Node.rate` is the reading of a board; `outcome` is
the village win probability of one state when the future follows the strategy.
The formulas and the reasons for the symmetry are in docs/redesign/core-v07.md.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import product
from math import comb

from .model import (BLACK, MEDIUM, ROLE_NAMES, ROLE_OF, SEER, VILLAGER, WHITE, WOLF, BoardContradiction,
                    WorkLimitExceeded, validate)

# Kinds: villager/medium/wolf times the seer's flag (0 unseen, 1 seen, 2 acquired
# last night and not yet past the first column), then the seer.
UNSEEN, SEEN, PENDING = 0, 1, 2
S = 9
KINDS = 10
ROLE = (VILLAGER, VILLAGER, VILLAGER, MEDIUM, MEDIUM, MEDIUM, WOLF, WOLF, WOLF, SEER)
FLAG = (0, 1, 2, 0, 1, 2, 0, 1, 2, 0)
W0, W2 = 6, 8
UNIT = tuple(tuple(int(i == k) for i in range(KINDS)) for k in range(KINDS))
ONE = F(1)


def color_of(kind):
    return BLACK if ROLE[kind] == WOLF else WHITE


def flagged(kind, flag):
    return kind if kind == S else kind - FLAG[kind] + flag


def single(vector):
    return vector.index(1)


def wolves_in(vector):
    return vector[6] + vector[7] + vector[8]


def settle_flags(state):
    """Results stop being pending once the first column of the day has passed."""
    return tuple((v[0], v[1] + v[2], 0, v[3], v[4] + v[5], 0, v[6], v[7] + v[8], 0, v[9]) for v in state)


def initial_masses(cast, wolf_claims, groups, claimed_role):
    """CO繧ｰ繝ｫ繝ｼ繝玲婿蠑・ legal wolf placements are equal, then the rest is equal.

    claimed_role maps a group index to the role its members claim. Every
    non-wolf claimer is truthful, so one wolf placement fixes the counts.
    """
    ranges = []
    for i, group in enumerate(groups):
        role = claimed_role.get(i)
        ranges.append(range((len(group) if role is None or role in wolf_claims else 0) + 1))
    free = [i for i in range(len(groups)) if i not in claimed_role]
    masses, total = {}, 0
    for wolves in product(*ranges):
        if sum(wolves) != cast.wolf:
            continue
        seers, mediums = cast.seer, cast.medium
        for i, group in enumerate(groups):
            role = claimed_role.get(i)
            if role == SEER:
                seers -= len(group) - wolves[i]
            elif role == MEDIUM:
                mediums -= len(group) - wolves[i]
        if seers < 0 or mediums < 0 or seers + mediums > sum(len(groups[i]) - wolves[i] for i in free):
            continue
        ways = 1
        for group, w in zip(groups, wolves):
            ways *= comb(len(group), w)
        total += ways
        for rest_mass, placed in place_rest(groups, free, wolves, seers, mediums):
            state = []
            for i, group in enumerate(groups):
                role = claimed_role.get(i)
                v = [0] * KINDS
                v[W0] = wolves[i]
                remaining = len(group) - wolves[i]
                if role == SEER:
                    v[S] = remaining
                elif role == MEDIUM:
                    v[3] = remaining
                else:
                    v[S], v[3] = placed[i]
                    v[0] = remaining - v[S] - v[3]
                state.append(tuple(v))
            state = tuple(state)
            masses[state] = masses.get(state, F()) + ways * rest_mass
    if not total:
        raise BoardContradiction('No role assignment fits the cast and the CO possibility')
    return {state: mass / total for state, mass in masses.items()}


def place_rest(groups, free, wolves, seers, mediums):
    """Seers and mediums over the free non-wolf seats, as (probability, per group)."""
    seats = [len(groups[i]) - wolves[i] for i in free]
    room = sum(seats)
    denominator = comb(room, seers) * comb(room - seers, mediums)
    results = []

    def walk(position, s_left, m_left, ways, chosen):
        if position == len(free):
            if not s_left and not m_left:
                results.append((F(ways, denominator), dict(chosen)))
            return
        seat = seats[position]
        for s_here in range(min(s_left, seat) + 1):
            for m_here in range(min(m_left, seat - s_here) + 1):
                walk(position + 1, s_left - s_here, m_left - m_here,
                     ways * comb(seat, s_here) * comb(seat - s_here, m_here),
                     chosen + [(free[position], (s_here, m_here))])
    walk(0, seers, mediums, 1, [])
    return results


class Layout:
    """Groups after singling out named players; plan maps each old group to its parts."""

    def __init__(self, groups, named):
        new, plan = [], []
        for group in groups:
            singles = [p for p in group if p in named]
            indices = []
            for player in singles:
                indices.append(len(new))
                new.append((player,))
            rest = tuple(p for p in group if p not in named)
            rest_index = None
            if rest:
                rest_index = len(new)
                new.append(rest)
            plan.append((tuple(indices), rest_index))
        self.groups = tuple(new)
        self.plan = tuple(plan)
        self.where = {p: i for i, group in enumerate(new) for p in group}


def relabel(log, perm):
    result = []
    for event in log:
        if event[0] == 'col':
            acts = []
            for act in event[1]:
                if act[0] == 'co':
                    acts.append(('co', perm[act[1]], act[2]))
                else:
                    acts.append(('report', perm[act[1]], perm[act[2]], act[3]))
            result.append(('col', tuple(sorted(acts, key=repr))))
        else:
            result.append((event[0], perm[event[1]]))
    return tuple(result)


def event_players(event):
    if event[0] != 'col':
        return {event[1]}
    named = set()
    for act in event[1]:
        named.update(act[1:3] if act[0] == 'report' else act[1:2])
    return named


def canonical_order(log, n):
    """Players sorted by what the log says about them; equal logs mean the same board."""
    marks = [[] for _ in range(n)]
    links = []
    for i, event in enumerate(log):
        if event[0] == 'col':
            for act in event[1]:
                if act[0] == 'co':
                    marks[act[1]].append((i, 0, act[2]))
                else:
                    marks[act[1]].append((i, 1, act[3]))
                    marks[act[2]].append((i, 2, act[3]))
                    links.append((i, act[1], act[2]))
        else:
            marks[event[1]].append((i, 3 if event[0] == 'exec' else 4, 0))
    color = [tuple(m) for m in marks]
    for _ in range(2):
        rank = {c: r for r, c in enumerate(sorted(set(color)))}
        added = [[] for _ in range(n)]
        for i, a, b in links:
            added[a].append((i, 0, rank[color[b]]))
            added[b].append((i, 1, rank[color[a]]))
        color = [(rank[color[p]], tuple(sorted(added[p]))) for p in range(n)]
    return sorted(range(n), key=lambda p: (color[p], p)), color


class Node:
    """One public board, in canonical labels."""

    def __init__(self, calc, log, groups):
        self.calc, self.log, self.groups = calc, log, groups
        self.index = {p: i for i, group in enumerate(groups) for p in group}
        self.alive = set(range(calc.n))
        self.claims, self.executed, self.reported, self.last_exec, self.last_bite = {}, set(), {}, None, None
        self.whites, self.blacks = [0] * calc.n, [0] * calc.n
        for event in log:
            if event[0] == 'col':
                for act in event[1]:
                    if act[0] == 'co':
                        self.claims[act[1]] = act[2]
                    else:
                        self.reported.setdefault(act[1], set()).add(act[2])
                        (self.blacks if act[3] == BLACK else self.whites)[act[2]] += 1
            else:
                self.alive.discard(event[1])
                if event[0] == 'exec':
                    self.executed.add(event[1])
                    self.last_exec = event[1]
                else:
                    self.last_bite = event[1]
        last = log[-1] if log else None
        self.first_column = last is None or last[0] == 'bite'
        self.stage = 'night' if last and last[0] == 'exec' else (
            'closed' if last and last[0] == 'col' and not last[1] else 'open')
        self.alive_groups = tuple(i for i, group in enumerate(groups) if group[0] in self.alive)
        self.edges = {}
        self.source = None
        self._rate = None
        self.outcomes = {}
        self.policy = None
        self.action_values = None
        self._fakes = {}
        self._wolf_rates = {}

    def representative(self, acts, needs):
        """Rename inside groups so that symmetric columns coincide; any renaming is exact."""
        marks = {}
        for act in acts:
            if act[0] == 'co':
                marks.setdefault(act[1], []).append((0, act[2]))
            else:
                marks.setdefault(act[1], []).append((1, act[3], self.index[act[2]]))
                marks.setdefault(act[2], []).append((2, act[3], self.index[act[1]]))
        for need in needs:
            marks.setdefault(need[1], []).append((3, need[0], need[2]))
        names = {}
        for player in marks:
            names.setdefault(self.index[player], []).append(player)
        rename = {}
        for index, players in names.items():
            players.sort(key=lambda p: sorted(marks[p]))
            rename.update(zip(players, self.groups[index]))
        renamed = [('co', rename[a[1]], a[2]) if a[0] == 'co' else ('report', rename[a[1]], rename[a[2]], a[3])
                   for a in acts]
        return (tuple(sorted(renamed, key=repr)),
                tuple(sorted(((n[0], rename[n[1]], n[2]) for n in needs), key=repr)))

    def saturated(self, role):
        count = self.calc.board.cast.count(role)
        return count > 0 and sum(r == role for r in self.claims.values()) >= count

    @property
    def rate(self):
        if self._rate is None:
            self._rate = self.calc.read(*self.source)
        return self._rate

    def wolf_rate(self, player):
        group = self.index[player]
        found = self._wolf_rates.get(group)
        if found is None:
            size = len(self.groups[group])
            found = sum((m * F(wolves_in(s[group]), size) for s, m in self.rate.items()), F())
            self._wolf_rates[group] = found
        return found


class Edge:
    __slots__ = ('child', 'perm', 'parts', 'layout')

    def __init__(self, child, perm, parts, layout):
        self.child, self.perm, self.parts, self.layout = child, perm, parts, layout


@dataclass(frozen=True)
class Evaluation:
    stage: str
    role_rates: dict  # player -> role name -> Fraction
    win_rates: dict  # 'village' | 'wolf' -> Fraction
    action_rates: dict  # player -> village win rate if this player is executed / bitten
    branches: tuple  # (event, probability), in user labels; a column stands for its renamings in a group
    stats: dict


class Calculation:
    """Immutable input and caches of one calculation; nothing is shared between boards."""

    def __init__(self, board, max_work=None):
        validate(board)
        self.board = board
        self.cast, self.rules, self.strategy = board.cast, board.rules, board.strategy
        self.n = board.cast.players
        self.wolf_claims = {ROLE_OF[name] for name in board.strategy.wolf_claims}
        self.max_work, self.work = max_work, 0
        self.nodes = {}
        self.layouts = {}
        self.splits = {}
        self.exec_values, self.bite_values = {}, {}
        root_groups = (tuple(range(self.n)),)
        self.root = self.node_for((), root_groups)
        self.root._rate = self.first_night(initial_masses(self.cast, self.wolf_claims, root_groups, {}))

    # --- structure -------------------------------------------------------------

    def tick(self):
        self.work += 1
        if self.max_work is not None and self.work > self.max_work:
            raise WorkLimitExceeded(f'Work limit {self.max_work} reached')

    def node_for(self, log, groups=None):
        node = self.nodes.get(log)
        if node is None:
            node = Node(self, log, groups if groups is not None else self.symmetry_groups(log))
            self.nodes[log] = node
        return node

    def symmetry_groups(self, log):
        """Maximal sets where every transposition leaves the log unchanged."""
        _, color = canonical_order(log, self.n)
        groups, placed = [], set()
        for p in range(self.n):
            if p in placed:
                continue
            group = [p]
            for q in range(p + 1, self.n):
                if q not in placed and color[q] == color[p]:
                    perm = list(range(self.n))
                    perm[p], perm[q] = q, p
                    if relabel(log, perm) == log:
                        group.append(q)
            placed.update(group)
            groups.append(tuple(group))
        return tuple(groups)

    def layout(self, groups, named):
        key = (groups, frozenset(named))
        found = self.layouts.get(key)
        if found is None:
            found = self.layouts[key] = Layout(groups, named)
        return found

    def edge(self, node, event):
        found = node.edges.get(event)
        if found is not None:
            return found
        log = node.log + (event,)
        order, _ = canonical_order(log, self.n)
        perm = [0] * self.n
        for new, old in enumerate(order):
            perm[old] = new
        child_log = relabel(log, perm)
        known = child_log in self.nodes
        child = self.node_for(child_log)
        layout = self.layout(node.groups, event_players(event))
        parts = [[] for _ in child.groups]
        for i, group in enumerate(layout.groups):
            parts[child.index[perm[group[0]]]].append(i)
        found = Edge(child, tuple(perm), tuple(tuple(p) for p in parts), layout)
        node.edges[event] = found
        if not known:
            child.source = (node, event)
        return found

    def project(self, edge, state):
        """Move a split state to the child's groups: same-position parts add up."""
        vectors = []
        for part in edge.parts:
            if len(part) == 1:
                vectors.append(state[part[0]])
            else:
                vectors.append(tuple(map(sum, zip(*(state[i] for i in part)))))
        child = edge.child
        if not any(vectors[i][S] for i in child.alive_groups):
            vectors = [(v[0] + v[1] + v[2], 0, 0, v[3] + v[4] + v[5], 0, 0, v[6] + v[7] + v[8], 0, 0, v[9])
                       for v in vectors]  # a dead seer's memory changes nothing
        return tuple(vectors)

    def split_vector(self, vector, singles):
        key = (vector, singles)
        found = self.splits.get(key)
        if found is None:
            found = [((), vector, ONE)]
            for _ in range(singles):
                grown = []
                for kinds, rest, q in found:
                    total = sum(rest)
                    for k, c in enumerate(rest):
                        if c:
                            grown.append((kinds + (k,), rest[:k] + (c - 1,) + rest[k + 1:], q * F(c, total)))
                found = grown
            self.splits[key] = found
        return found

    def split(self, state, layout):
        """All ways the named players take kinds, with their probability."""
        size = len(layout.groups)
        choices = []
        for vector, (singles, rest_index) in zip(state, layout.plan):
            options = []
            for kinds, rest, q in self.split_vector(vector, len(singles)):
                options.append((tuple(zip(singles, kinds)), rest_index, rest, q))
            choices.append(options)
        result = []
        for combination in product(*choices):
            slots = [None] * size
            mass = ONE
            for pairs, rest_index, rest, q in combination:
                mass *= q
                for index, kind in pairs:
                    slots[index] = UNIT[kind]
                if rest_index is not None:
                    slots[rest_index] = rest
            result.append((tuple(slots), mass))
        return result

    def decided(self, state, groups, alive):
        wolves = humans = 0
        for vector, group in zip(state, groups):
            if group[0] in alive:
                w = wolves_in(vector)
                wolves += w
                humans += len(group) - w
        if wolves == 0:
            return ONE
        if wolves >= humans:
            return F(0)
        return None

    # --- reading (蠖ｹ閨ｷ邇・ ----------------------------------------------------------

    def first_night(self, masses):
        """Night 0: the seer's result is uniform in the rule's range."""
        rule = self.rules.first_night
        if rule == 'none' or not self.cast.seer:
            return masses
        result = {}
        for state, mass in masses.items():
            if not any(v[S] for v in state):
                result[state] = result.get(state, F()) + mass
                continue
            pool = [(i, k, c) for i, v in enumerate(state) for k, c in enumerate(v)
                    if c and k != S and (rule == 'divine' or ROLE[k] != WOLF)]
            total = sum(c for _, _, c in pool)
            for i, k, c in pool:
                new = self.flag_target(state, i, k)
                result[new] = result.get(new, F()) + mass * F(c, total)
        return result

    @staticmethod
    def flag_target(state, group, kind):
        vector = list(state[group])
        vector[kind] -= 1
        vector[flagged(kind, PENDING)] += 1
        return state[:group] + (tuple(vector),) + state[group + 1:]

    def read(self, node, event):
        """Rate of the child of `node` through `event`: the only reading step."""
        edge = node.edges[event]
        if event[0] == 'col':
            masses = self.read_column(node, event[1], edge)
        elif event[0] == 'exec':
            masses = self.read_execution(node, event[1], edge)
        else:
            masses = self.read_bite(node, event[1], edge)
        total = sum(masses.values(), F())
        if not total:
            raise BoardContradiction('The board contradicts the rules, the CO possibility or the promises')
        return {state: mass / total for state, mass in masses.items()}

    def start_masses(self, node, acts):
        """Masses before a column. Day 1's first column fixes the CO snapshot."""
        claimed = {}
        for act in acts:
            if act[0] == 'co':
                claimed.setdefault(act[2], []).append(act[1])
        if node.log or not claimed:
            return node.groups, node.rate
        in_claim = {p for players in claimed.values() for p in players}
        groups, roles = [], {}
        for role, players in claimed.items():
            roles[len(groups)] = role
            groups.append(tuple(sorted(players)))
        rest = tuple(p for p in range(self.n) if p not in in_claim)
        if rest:
            groups.append(rest)
        groups = tuple(groups)
        return groups, self.first_night(initial_masses(self.cast, self.wolf_claims, groups, roles))

    def read_column(self, node, acts, edge):
        named = event_players(('col', acts))
        groups, start = self.start_masses(node, acts)
        layout = self.layout(groups, named)
        where = layout.where
        claims = dict(node.claims)
        for act in acts:
            if act[0] == 'co':
                claims[act[1]] = act[2]
        split = {}
        for state, mass in start.items():
            for new, q in self.split(state, layout):
                keep = True
                for act in acts:
                    if act[0] == 'co':
                        role = ROLE[single(new[where[act[1]]])]
                        keep = keep and (role == act[2] or (role == WOLF and act[2] in self.wolf_claims))
                if keep:
                    split[new] = split.get(new, F()) + mass * q
        reports = [act for act in acts if act[0] == 'report']
        laws = []
        for act in reports:
            role = claims[act[1]]
            truthful = matching = F()
            for state, mass in split.items():
                if ROLE[single(state[where[act[1]]])] == role:
                    truthful += mass
                    if self.report_law(node, state, where, act, role):
                        matching += mass
            # Fake reports follow the distribution a true holder would produce.
            laws.append(matching / truthful if matching else ONE)
        result = {}
        for state, mass in split.items():
            for act, law in zip(reports, laws):
                role = claims[act[1]]
                if ROLE[single(state[where[act[1]]])] == role:
                    if not self.report_law(node, state, where, act, role):
                        mass = F()
                        break
                else:
                    mass *= law
            if mass and self.promises_kept(node, state, layout, acts, claims):
                if layout is not edge.layout:  # the snapshot splits the same players in another order
                    state = tuple(state[where[group[0]]] for group in edge.layout.groups)
                new = self.project(edge, settle_flags(state) if node.first_column else state)
                result[new] = result.get(new, F()) + mass
        return result

    def report_law(self, node, state, where, act, role):
        _, _, target, color = act
        kind = single(state[where[target]])
        if color_of(kind) != color:
            return False
        return target in node.executed if role == MEDIUM else FLAG[kind] >= SEEN

    def promises_kept(self, node, state, layout, acts, claims):
        strategy, where = self.strategy, layout.where
        for role, code in ((SEER, S), (MEDIUM, None)):
            holder = None
            for group, vector in zip(layout.groups, state):
                if group[0] in node.alive and (vector[S] if code is not None else vector[3] + vector[4] + vector[5]):
                    holder = group
                    break
            if holder is None:
                continue
            claimed = holder[0] in claims and claims[holder[0]] == role
            if not claimed and strategy.co_on_saturation and node.saturated(role):
                return False
            if not node.first_column:
                continue
            if role == SEER:
                black = any(v[W2] for v in state)
            else:
                exec_group = node.last_exec
                black = exec_group is not None and ROLE[single(state[where[exec_group]])] == WOLF
            if not black:
                continue
            told = len(holder) == 1 and any(
                act[0] == 'report' and act[1] == holder[0] and act[3] == BLACK
                and (act[2] == node.last_exec if role == MEDIUM else single(state[where[act[2]]]) == W2)
                for act in acts)
            if claimed and strategy.disclose_black and not told:
                return False
            if not claimed and strategy.co_on_black:
                return False
        return True

    def read_execution(self, node, player, edge):
        layout = edge.layout
        alive = node.alive - {player}
        result = {}
        for state, mass in node.rate.items():
            for new, q in self.split(state, layout):
                if self.decided(new, layout.groups, alive) is None:
                    projected = self.project(edge, new)
                    result[projected] = result.get(projected, F()) + mass * q
        return result

    def read_bite(self, node, player, edge):
        """Bite and divination are both read as uniform in the rule's range."""
        layout = edge.layout
        alive = node.alive - {player}
        where = layout.where[player]
        result = {}
        for state, mass in node.rate.items():
            for new, q in self.split(state, layout):
                wolves = sum(wolves_in(v) for g, v in zip(layout.groups, new) if g[0] in node.alive)
                if ROLE[single(new[where])] == WOLF and not self.rules.self_bite:
                    continue
                pool = len(node.alive) if self.rules.self_bite else len(node.alive) - wolves
                if self.decided(new, layout.groups, alive) is not None:
                    continue
                weight = mass * q / pool
                for final, r in self.divine_uniform(node, new, layout, alive):
                    projected = self.project(edge, final)
                    result[projected] = result.get(projected, F()) + weight * r
        return result

    def divine_uniform(self, node, state, layout, alive):
        if not any(v[S] for g, v in zip(layout.groups, state) if g[0] in alive):
            return [(state, ONE)]
        pool = [(i, k, c) for i, (g, v) in enumerate(zip(layout.groups, state)) if g[0] in node.alive
                for k, c in enumerate(v) if c and k != S]
        total = sum(c for _, _, c in pool)
        return [(self.flag_target(state, i, k), F(c, total)) for i, k, c in pool]

    # --- forward (蜍晉紫) -----------------------------------------------------------

    def outcome(self, node, state):
        """Village win probability of this state when the future follows the strategy."""
        found = node.outcomes.get(state)
        if found is not None:
            return found
        self.tick()
        if node.stage == 'open':
            value = F()
            for act_key, items in self.column_law(node, state).items():
                child = self.edge(node, ('col', act_key)).child
                for child_state, mass in items.items():
                    value += mass * self.outcome(child, child_state)
        elif node.stage == 'closed':
            value = F()
            for rep, p in self.execution_policy(node).items():
                value += p * self.execution_outcome(node, state, rep)
        else:
            value = F()
            for group, wolf_target, p in self.bite_policy(node)[self.wolf_key(state)]:
                value += p * self.bite_outcome(node, state, group, wolf_target)
        node.outcomes[state] = value
        return value

    def value(self, node):
        return sum((mass * self.outcome(node, state) for state, mass in node.rate.items()), F())

    def execution_outcome(self, node, state, player):
        key = (id(node), state, player)
        found = self.exec_values.get(key)
        if found is not None:
            return found
        edge = self.edge(node, ('exec', player))
        layout = edge.layout
        alive = node.alive - {player}
        value = F()
        for new, q in self.split(state, layout):
            end = self.decided(new, layout.groups, alive)
            value += q * (end if end is not None else self.outcome(edge.child, self.project(edge, new)))
        self.exec_values[key] = value
        return value

    def execution_policy(self, node):
        if node.policy is None:
            reps = [g[0] for g in node.groups if g[0] in node.alive]
            size = {g[0]: len(g) for g in node.groups}
            values = {rep: sum((m * self.execution_outcome(node, s, rep) for s, m in node.rate.items()), F())
                      for rep in reps}
            node.action_values = values
            if self.strategy.execution == 'max':
                best = max(values.values())
                reps = [rep for rep in reps if values[rep] == best]
            total = sum(size[rep] for rep in reps)
            node.policy = {rep: F(size[rep], total) for rep in reps}
        return node.policy

    def wolf_key(self, state):
        return tuple(wolves_in(v) for v in state)

    def bite_outcome(self, node, state, group, wolf_target):
        """Wolves bite a member of `group`, knowing which members are wolves."""
        key = (id(node), state, group, wolf_target)
        found = self.bite_values.get(key)
        if found is not None:
            return found
        player = node.groups[group][0]
        edge = self.edge(node, ('bite', player))
        layout = edge.layout
        alive = node.alive - {player}
        where = layout.where[player]
        rows, kept = [], F()
        for new, q in self.split(state, layout):
            if (ROLE[single(new[where])] == WOLF) == wolf_target:
                rows.append((new, q))
                kept += q
        value = F()
        for new, q in rows:
            end = self.decided(new, layout.groups, alive)
            if end is not None:
                value += q / kept * end
                continue
            for final, r in self.divine_expected(node, new, layout, alive):
                value += q / kept * r * self.outcome(edge.child, self.project(edge, final))
        self.bite_values[key] = value
        return value

    def bite_targets(self, node, wolves):
        """(group, is wolf, how many players) for one wolf placement."""
        targets = []
        for i in node.alive_groups:
            others = len(node.groups[i]) - wolves[i]
            if others:
                targets.append((i, False, others))
            if wolves[i] and self.rules.self_bite:
                targets.append((i, True, wolves[i]))
        return targets

    def bite_policy(self, node):
        if node.policy is None:
            sets = {}
            for state, mass in node.rate.items():
                sets.setdefault(self.wolf_key(state), []).append((state, mass))
            policy = {}
            for wolves, rows in sets.items():
                targets = self.bite_targets(node, wolves)
                if self.strategy.bite == 'max':
                    # Wolves pick the lowest village win over what they cannot see.
                    values = [sum((m * self.bite_outcome(node, s, g, w) for s, m in rows), F())
                              for g, w, _ in targets]
                    best = min(values)
                    targets = [t for t, v in zip(targets, values) if v == best]
                total = sum(c for _, _, c in targets)
                policy[wolves] = [(g, w, F(c, total)) for g, w, c in targets]
            node.policy = policy
        return node.policy

    def divine_expected(self, node, state, layout, alive):
        """諠ｳ螳・ the seer's ordered filter over who was alive when the night began."""
        if not any(v[S] for g, v in zip(layout.groups, state) if g[0] in alive):
            return [(state, ONE)]
        pool = [(i, k, c) for i, (g, v) in enumerate(zip(layout.groups, state)) if g[0] in node.alive
                for k, c in enumerate(v) if c and k != S]
        for stage in self.strategy.seer_target:
            if stage == 'uniform':
                break
            kept = [x for x in pool if self.target_stage(node, layout.groups[x[0]][0], x[1], stage)]
            if kept:
                pool = kept
        total = sum(c for _, _, c in pool)
        return [(self.flag_target(state, i, k), F(c, total)) for i, k, c in pool]

    def target_stage(self, node, player, kind, stage):
        if stage == 'unseen':
            return FLAG[kind] == UNSEEN
        if stage == 'latent':
            return player not in node.claims
        if stage == 'half_white':
            return node.whites[player] == 1 and not node.blacks[player]
        return 0 < node.wolf_rate(player) < 1  # undetermined

    def fake_options(self, node, player):
        """諠ｳ螳・ a fake report as (target, color, probability); same shape as a true one."""
        found = node._fakes.get(player)
        if found is not None:
            return found
        role = node.claims[player]
        if role == SEER:
            morning = (node.alive | {node.last_bite}) - {player}
            pool = sorted(morning - node.reported.get(player, set())) or sorted(morning)
        else:
            pool = [node.last_exec]
        options = [(t, c) for t in pool for c in (WHITE, BLACK)]
        if self.strategy.fake_report[0] == 'no_contradiction':
            kept = [o for o in options if self.could_be_true(node, player, role, *o)]
            options = kept or options
        result = [(t, c, F(1, len(options))) for t, c in options]
        node._fakes[player] = result
        return result

    def could_be_true(self, node, player, role, target, color):
        """Some supported state has the reporter true and this very result."""
        own, other = node.index[player], node.index[target]
        for state in node.rate:
            holder = state[own]
            if not (holder[S] if role == SEER else holder[3] + holder[4] + holder[5]):
                continue
            vector = state[other]
            if role == SEER:
                if any(c and FLAG[k] == PENDING and color_of(k) == color for k, c in enumerate(vector)):
                    return True
            elif any(c and color_of(k) == color for k, c in enumerate(vector)):
                return True
        return False

    def true_options(self, node, state, role):
        """邏・據 and 諠ｳ螳・of the true holder: (acts, required kinds, holder) per way to name them."""
        kinds = range(3, 6) if role == MEDIUM else (S,)
        owner = next((i for i in node.alive_groups if any(state[i][k] for k in kinds)), None)
        if owner is None:
            return [((), (), None)]
        strategy = self.strategy
        result = None
        if node.first_column:
            if role == MEDIUM:
                if node.last_exec is not None:
                    group = node.index[node.last_exec]
                    result = (group, single(state[group]))
            else:
                result = next(((i, k) for i, v in enumerate(state) for k, c in enumerate(v)
                               if c and FLAG[k] == PENDING), None)
        black = result is not None and color_of(result[1]) == BLACK
        claimed = node.claims.get(node.groups[owner][0]) == role
        if claimed:
            opens = False
            tell = result is not None and (strategy.disclose_all or (black and strategy.disclose_black))
        else:
            opens = (black and strategy.co_on_black) or (strategy.co_on_saturation and node.saturated(role))
            tell = opens and black and strategy.disclose_black
        if not opens and not tell:
            return [((), (), None)]  # silent, and silence names nobody
        options = []
        for player in node.groups[owner]:
            acts = (('co', player, role),) if opens else ()
            need = (('role', player, role),)
            if not tell:
                options.append((acts, need, player))
                continue
            for target in node.groups[result[0]]:
                if target != player:
                    options.append((acts + (('report', player, target, color_of(result[1])),),
                                    need + (('kind', target, result[1]),), player))
        return options

    def column_law(self, node, state):
        """Every column this state can produce, with the child states and masses.

        Columns that differ by renaming players inside a group give the same child
        (the state does not change under that renaming), so one stands for them all.
        """
        plans = {}
        fakes_report = node.first_column and node.last_bite is not None and self.strategy.disclose_all
        for seer_acts, seer_need, seer_player in self.true_options(node, state, SEER):
            for medium_acts, medium_need, medium_player in self.true_options(node, state, MEDIUM):
                fakes = []
                if fakes_report:
                    for player in node.claims:
                        if player in node.alive and player not in (seer_player, medium_player):
                            fakes.append([(player, *option) for option in self.fake_options(node, player)])
                for chosen in product(*fakes):
                    acts = seer_acts + medium_acts + tuple(('report', p, t, c) for p, t, c, _ in chosen)
                    weight = ONE
                    for *_, q in chosen:
                        weight *= q
                    plan = node.representative(acts, seer_need + medium_need)
                    plans[plan] = plans.get(plan, F()) + weight
        result = {}
        for (key, needs), weight in plans.items():
            self.add_column(node, state, key, needs, weight, result)
        return result

    def add_column(self, node, state, key, needs, weight, result):
        edge = self.edge(node, ('col', key))
        where = edge.layout.where
        for new, q in self.split(state, edge.layout):
            if all(self.need_met(new, where, need) for need in needs):
                child_state = self.project(edge, settle_flags(new) if node.first_column else new)
                bucket = result.setdefault(key, {})
                bucket[child_state] = bucket.get(child_state, F()) + q * weight

    @staticmethod
    def need_met(state, where, need):
        kind = single(state[where[need[1]]])
        return ROLE[kind] == need[2] if need[0] == 'role' else kind == need[2]

    # --- entry ------------------------------------------------------------------

    def locate(self):
        """Walk the input log from the root; returns the node and user -> node labels."""
        node, labels = self.root, list(range(self.n))
        log = self.board.log
        for position, event in enumerate(log):
            if event[0] == 'exec' and not (position and log[position - 1][0] == 'col' and not log[position - 1][1]):
                edge = self.edge(node, ('col', ()))  # a day always closes with 譖ｴ譁ｰ縺ｪ縺・before the execution
                node, labels = edge.child, [edge.perm[p] for p in labels]
            inner = self.to_inner(event, labels)
            edge = self.edge(node, inner)
            node, labels = edge.child, [edge.perm[p] for p in labels]
        return node, labels

    @staticmethod
    def to_inner(event, labels):
        if event[0] == 'col':
            acts = []
            for act in event[1]:
                if act[0] == 'co':
                    acts.append(('co', labels[act[1] - 1], act[2]))
                else:
                    acts.append(('report', labels[act[1] - 1], labels[act[2] - 1], act[3]))
            return ('col', tuple(sorted(acts, key=repr)))
        return (event[0], labels[event[1] - 1])

    @staticmethod
    def to_user(event, labels):
        back = {inner: user + 1 for user, inner in enumerate(labels)}
        if event[0] == 'col':
            acts = []
            for act in event[1]:
                if act[0] == 'co':
                    acts.append(('co', back[act[1]], act[2]))
                else:
                    acts.append(('report', back[act[1]], back[act[2]], act[3]))
            return ('col', tuple(sorted(acts, key=repr)))
        return (event[0], back[event[1]])

    def role_rates(self, node, labels):
        rates = {}
        for user, inner in enumerate(labels):
            group = node.index[inner]
            size = len(node.groups[group])
            row = {name: F() for name in ROLE_NAMES}
            for state, mass in node.rate.items():
                for k, c in enumerate(state[group]):
                    if c:
                        row[ROLE_NAMES[ROLE[k]]] += mass * F(c, size)
            rates[user + 1] = row
        return rates

    def evaluate(self):
        node, labels = self.locate()
        role_rates = self.role_rates(node, labels)
        stage_node, stage_labels = node, labels
        branches = []
        if node.stage == 'open':
            masses = {}
            for state, mass in node.rate.items():
                for key, items in self.column_law(node, state).items():
                    masses[key] = masses.get(key, F()) + mass * sum(items.values(), F())
            if set(masses) == {()}:  # no update can happen: the same board, closed
                edge = self.edge(node, ('col', ()))
                stage_node, stage_labels = edge.child, [edge.perm[p] for p in labels]
            else:
                branches = [(('col', key), p) for key, p in masses.items()]
        action_rates = {}
        if stage_node.stage == 'closed':
            policy = self.execution_policy(stage_node)
            for group in stage_node.groups:
                if group[0] in stage_node.alive:
                    share = policy.get(group[0], F()) / len(group)
                    if share:
                        branches.extend((('exec', player), share) for player in group)
                    for player in group:
                        action_rates[player] = stage_node.action_values[group[0]]
        elif stage_node.stage == 'night':
            self.bite_policy(stage_node)
            for i in stage_node.alive_groups:
                action_rates.update(self.bite_action(stage_node, i))
                share = F()
                for state, mass in stage_node.rate.items():
                    for group, _, p in stage_node.policy[self.wolf_key(state)]:
                        if group == i:
                            share += mass * p
                share /= len(stage_node.groups[i])
                if share:
                    branches.extend((('bite', player), share) for player in stage_node.groups[i])
        village = self.value(node)
        back = {inner: user + 1 for user, inner in enumerate(stage_labels)}
        return Evaluation(
            stage=stage_node.stage,
            role_rates=role_rates,
            win_rates={'village': village, 'wolf': 1 - village},
            action_rates={back[p]: v for p, v in action_rates.items()},
            branches=tuple((self.to_user(event, stage_labels), p) for event, p in branches),
            stats={'boards': len(self.nodes), 'states': sum(len(n.outcomes) for n in self.nodes.values()),
                   'work': self.work})

    def bite_action(self, node, i):
        """Village win rate if this player is bitten, over the states where that is legal."""
        size = len(node.groups[i])
        weight, value = F(), F()
        for state, mass in node.rate.items():
            wolves = wolves_in(state[i])
            if size - wolves:
                share = mass * F(size - wolves, size)
                weight += share
                value += share * self.bite_outcome(node, state, i, False)
            if wolves and self.rules.self_bite:
                share = mass * F(wolves, size)
                weight += share
                value += share * self.bite_outcome(node, state, i, True)
        return {player: value / weight for player in node.groups[i]} if weight else {}


def evaluate(board, max_work=None):
    """Board (public information and strategy) -> role rates, win rates, action rates."""
    return Calculation(board, max_work).evaluate()


def read_roles(board):
    """Role rates alone; no future is computed."""
    calculation = Calculation(board)
    node, labels = calculation.locate()
    return calculation.role_rates(node, labels)
