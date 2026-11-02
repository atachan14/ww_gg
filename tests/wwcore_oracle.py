"""Independent oracle for wwcore: every role assignment named, player by player.

No count groups, no splitting and no shared code with wwcore except the Board
input. It computes the definitions in docs/redesign/core-v07.md directly.
Boards are memoized only under renaming players by first appearance in the log.
"""
from fractions import Fraction as F
from itertools import permutations

V, M, W, S = 'villager', 'medium', 'wolf', 'seer'
ROLE_INDEX = {0: V, 1: M, 2: W, 3: S}  # the numeric roles of wwcore.model
WHITE, BLACK = 0, 1


class Contradiction(Exception):
    pass


def color(role):
    return BLACK if role == W else WHITE


def rename_by_appearance(log, n):
    order = []
    for event in log:
        if event[0] == 'col':
            for act in event[1]:
                for p in (act[1:3] if act[0] == 'report' else act[1:2]):
                    if p not in order:
                        order.append(p)
        elif event[1] not in order:
            order.append(event[1])
    order += [p for p in range(n) if p not in order]
    return {old: new for new, old in enumerate(order)}


def apply_names(log, names):
    result = []
    for event in log:
        if event[0] == 'col':
            acts = [('co', names[a[1]], a[2]) if a[0] == 'co' else ('report', names[a[1]], names[a[2]], a[3])
                    for a in event[1]]
            result.append(('col', tuple(sorted(acts, key=repr))))
        else:
            result.append((event[0], names[event[1]]))
    return tuple(result)


class Oracle:
    def __init__(self, board):
        self.board = board
        self.cast = board.cast
        self.n = board.cast.players
        self.rules, self.strategy = board.rules, board.strategy
        self.can_claim = {('seer' if r == 'seer' else 'medium') for r in board.strategy.wolf_claims}
        self.assignments = sorted(set(permutations(
            [V] * self.cast.villager + [M] * self.cast.medium + [W] * self.cast.wolf + [S] * self.cast.seer)))
        self.memo_weights = {}
        self.memo_exec, self.memo_bite = {}, {}
        self.memo_value = {}
        self.memo_fake = {}

    # --- public log --------------------------------------------------------------

    def alive(self, log):
        dead = {e[1] for e in log if e[0] != 'col'}
        return [p for p in range(self.n) if p not in dead]

    def claims(self, log):
        return {a[1]: ROLE_INDEX[a[2]] for e in log if e[0] == 'col' for a in e[1] if a[0] == 'co'}

    def saturated(self, log, role):
        count = {S: self.cast.seer, M: self.cast.medium}[role]
        return count > 0 and sum(r == role for r in self.claims(log).values()) >= count

    def first_column(self, log):
        return not log or log[-1][0] == 'bite'

    def last_of(self, log, kind):
        return next((e[1] for e in reversed(log) if e[0] == kind), None)

    def game_end(self, roles, alive):
        wolves = sum(roles[p] == W for p in alive)
        if wolves == 0:
            return F(1)
        return F(0) if wolves >= len(alive) - wolves else None

    # --- reading ------------------------------------------------------------------

    def prior(self, claimers):
        def legal(roles):
            return all(roles[p] == c or (roles[p] == W and c in self.can_claim) for p, c in claimers.items())
        by_wolves = {}
        for roles in self.assignments:
            if legal(roles):
                by_wolves.setdefault(frozenset(p for p in range(self.n) if roles[p] == W), []).append(roles)
        if not by_wolves:
            raise Contradiction
        weights = {}
        for rows in by_wolves.values():
            for roles in rows:
                weights[roles] = F(1, len(by_wolves) * len(rows))
        return weights

    def night_zero(self, prior):
        result = {}
        for roles, w in prior.items():
            if S not in roles or self.rules.first_night == 'none':
                result[(roles, frozenset(), None)] = w
                continue
            seer = roles.index(S)
            pool = [p for p in range(self.n) if p != seer
                    and (self.rules.first_night == 'divine' or roles[p] != W)]
            for t in pool:
                key = (roles, frozenset(), t)
                result[key] = result.get(key, F()) + w / len(pool)
        return result

    def weights(self, log):
        found = self.memo_weights.get(log)
        if found is not None:
            return found
        if not log:
            result = self.night_zero(self.prior({}))
        else:
            event = log[-1]
            if event[0] == 'col':
                result = self.read_column(log[:-1], event[1])
            elif event[0] == 'exec':
                result = self.read_execution(log[:-1], event[1])
            else:
                result = self.read_bite(log[:-1], event[1])
        total = sum(result.values(), F())
        if not total:
            raise Contradiction
        result = {k: w / total for k, w in result.items()}
        self.memo_weights[log] = result
        return result

    def true_report_ok(self, log, world, reporter, target, shade):
        roles, seen, pending = world
        if color(roles[target]) != shade:
            return False
        if self.claims_with(log, reporter) == M:
            return any(e[0] == 'exec' and e[1] == target for e in log)
        return target in seen or target == pending

    def claims_with(self, log, player):
        return self.current_claims[player]

    def read_column(self, log, acts):
        cos = {a[1]: ROLE_INDEX[a[2]] for a in acts if a[0] == 'co'}
        if not log and cos:
            start = self.night_zero(self.prior(cos))
        else:
            start = self.weights(log)
        self.current_claims = {**self.claims(log), **cos}
        kept = {}
        for world, w in start.items():
            roles = world[0]
            if all(roles[p] == c or (roles[p] == W and c in self.can_claim) for p, c in cos.items()):
                kept[world] = w
        laws = {}
        for act in acts:
            if act[0] != 'report':
                continue
            _, reporter, target, shade = act
            role = self.current_claims[reporter]
            true_mass = sum((w for k, w in kept.items() if k[0][reporter] == role), F())
            hit = sum((w for k, w in kept.items() if k[0][reporter] == role
                       and self.true_report_ok(log, k, reporter, target, shade)), F())
            laws[act] = hit / true_mass if hit else F(1)
        result = {}
        first = self.first_column(log)
        for world, w in kept.items():
            roles, seen, pending = world
            for act, law in laws.items():
                _, reporter, target, shade = act
                if roles[reporter] == self.current_claims[reporter]:
                    if not self.true_report_ok(log, world, reporter, target, shade):
                        w = F()
                else:
                    w *= law
            if not w or not self.promises(log, world, acts):
                continue
            key = (roles, seen | {pending}, None) if first and pending is not None else world
            result[key] = result.get(key, F()) + w
        return result

    def promises(self, log, world, acts):
        roles, _, pending = world
        alive = self.alive(log)
        first = self.first_column(log)
        for role in (S, M):
            holder = next((p for p in alive if roles[p] == role), None)
            if holder is None:
                continue
            claimed = self.current_claims.get(holder) == role
            if not claimed and self.strategy.co_on_saturation and self.saturated(log, role):
                return False
            if not first:
                continue
            if role == S:
                result = pending
            else:
                result = self.last_of(log, 'exec')
            if result is None or roles[result] != W:
                continue
            told = any(a[0] == 'report' and a[1] == holder and a[2] == result and a[3] == BLACK for a in acts)
            if claimed and self.strategy.disclose_black and not told:
                return False
            if not claimed and self.strategy.co_on_black:
                return False
        return True

    def read_execution(self, log, player):
        alive = [p for p in self.alive(log) if p != player]
        result = {}
        for world, w in self.weights(log).items():
            if self.game_end(world[0], alive) is None:
                key = self.dead_seer_clean(world, alive)
                result[key] = result.get(key, F()) + w
        return result

    @staticmethod
    def dead_seer_clean(world, alive):
        roles = world[0]
        if not any(roles[p] == S for p in alive):
            return (roles, frozenset(), None)
        return world

    def read_bite(self, log, player):
        before = self.alive(log)
        after = [p for p in before if p != player]
        result = {}
        for (roles, seen, pending), w in self.weights(log).items():
            if roles[player] == W and not self.rules.self_bite:
                continue
            pool = len(before) if self.rules.self_bite else sum(roles[p] != W for p in before)
            if self.game_end(roles, after) is not None:
                continue
            w = w / pool
            if any(roles[p] == S for p in after):
                seer = roles.index(S)
                others = [p for p in before if p != seer]
                for t in others:
                    key = (roles, seen, t)
                    result[key] = result.get(key, F()) + w / len(others)
            else:
                key = (roles, frozenset(), None)
                result[key] = result.get(key, F()) + w
        return result

    def role_rates(self, log):
        rates = [{r: F() for r in (V, M, W, S)} for _ in range(self.n)]
        for (roles, _, _), w in self.weights(log).items():
            for p, role in enumerate(roles):
                rates[p][role] += w
        return rates

    # --- forward ------------------------------------------------------------------

    def stage(self, log):
        if log and log[-1][0] == 'exec':
            return 'night'
        if log and log[-1][0] == 'col' and not log[-1][1]:
            return 'closed'
        return 'open'

    def value(self, log, world):
        """Village win probability; `log` is already renamed by appearance."""
        key = (log, world)
        found = self.memo_value.get(key)
        if found is not None:
            return found
        stage = self.stage(log)
        if stage == 'open':
            result = F()
            settled = world
            if self.first_column(log) and world[2] is not None:
                settled = (world[0], world[1] | {world[2]}, None)
            for acts, p in self.column_choices(log, world).items():
                result += p * self.step(log, ('col', acts), settled)
        elif stage == 'closed':
            result = F()
            for player, p in self.execution_choice(log).items():
                result += p * self.after_execution(log, world, player)
        else:
            wolves = frozenset(q for q in self.alive(log) if world[0][q] == W)
            result = F()
            for target, p in self.bite_choice(log)[wolves].items():
                result += p * self.after_bite(log, world, target)
        self.memo_value[key] = result
        return result

    def step(self, log, event, world):
        longer = log + (event,)
        names = rename_by_appearance(longer, self.n)
        roles, seen, pending = world
        new_roles = [None] * self.n
        for old, new in names.items():
            new_roles[new] = roles[old]
        renamed = (tuple(new_roles), frozenset(names[p] for p in seen), None if pending is None else names[pending])
        return self.value(apply_names(longer, names), renamed)

    def after_execution(self, log, world, player):
        key = (log, world, player)
        found = self.memo_exec.get(key)
        if found is not None:
            return found
        alive = [p for p in self.alive(log) if p != player]
        end = self.game_end(world[0], alive)
        if end is not None:
            result = end
        else:
            result = self.step(log, ('exec', player), self.dead_seer_clean(world, alive))
        self.memo_exec[key] = result
        return result

    def execution_choice(self, log):
        alive = self.alive(log)
        rates = self.weights(log)
        values = {p: sum((w * self.after_execution(log, k, p) for k, w in rates.items()), F()) for p in alive}
        if self.strategy.execution == 'uniform':
            return {p: F(1, len(alive)) for p in alive}
        best = max(values.values())
        chosen = [p for p, v in values.items() if v == best]
        return {p: F(1, len(chosen)) for p in chosen}

    def after_bite(self, log, world, target):
        key = (log, world, target)
        found = self.memo_bite.get(key)
        if found is not None:
            return found
        roles, seen, _ = world
        before = self.alive(log)
        after = [p for p in before if p != target]
        end = self.game_end(roles, after)
        if end is not None:
            result = end
        elif not any(roles[p] == S for p in after):
            result = self.step(log, ('bite', target), (roles, frozenset(), None))
        else:
            result = F()
            for t, p in self.seer_targets(log, world).items():
                result += p * self.step(log, ('bite', target), (roles, seen, t))
        self.memo_bite[key] = result
        return result

    def seer_targets(self, log, world):
        roles, seen, _ = world
        before = self.alive(log)
        seer = roles.index(S)
        pool = [p for p in before if p != seer]
        rates = self.role_rates(log)
        claims = self.claims(log)
        whites, blacks = [0] * self.n, [0] * self.n
        for e in log:
            if e[0] == 'col':
                for a in e[1]:
                    if a[0] == 'report':
                        (blacks if a[3] == BLACK else whites)[a[2]] += 1
        tests = {
            'undetermined': lambda p: 0 < rates[p][W] < 1,
            'unseen': lambda p: p not in seen,
            'latent': lambda p: p not in claims,
            'half_white': lambda p: whites[p] == 1 and blacks[p] == 0,
        }
        for stage in self.strategy.seer_target:
            if stage == 'uniform':
                break
            narrowed = [p for p in pool if tests[stage](p)]
            if narrowed:
                pool = narrowed
        return {p: F(1, len(pool)) for p in pool}

    def bite_choice(self, log):
        key = log
        found = self.memo_bite.get(key)
        if found is not None:
            return found
        alive = self.alive(log)
        by_wolves = {}
        for world, w in self.weights(log).items():
            wolves = frozenset(q for q in alive if world[0][q] == W)
            by_wolves.setdefault(wolves, []).append((world, w))
        policy = {}
        for wolves, rows in by_wolves.items():
            pool = alive if self.rules.self_bite else [p for p in alive if p not in wolves]
            if self.strategy.bite == 'uniform':
                policy[wolves] = {p: F(1, len(pool)) for p in pool}
                continue
            values = {p: sum((w * self.after_bite(log, k, p) for k, w in rows), F()) for p in pool}
            best = min(values.values())
            chosen = [p for p, v in values.items() if v == best]
            policy[wolves] = {p: F(1, len(chosen)) for p in chosen}
        self.memo_bite[key] = policy
        return policy

    def fake_law(self, log, player):
        key = (log, player)
        found = self.memo_fake.get(key)
        if found is not None:
            return found
        claims = self.claims(log)
        role = claims[player]
        alive = self.alive(log)
        if role == S:
            start = sorted(set(alive) | {self.last_of(log, 'bite')})
            start = [p for p in start if p != player]
            told = {a[2] for e in log if e[0] == 'col' for a in e[1] if a[0] == 'report' and a[1] == player}
            pool = [p for p in start if p not in told] or start
        else:
            pool = [self.last_of(log, 'exec')]
        options = [(t, c) for t in pool for c in (WHITE, BLACK)]
        if self.strategy.fake_report[0] == 'no_contradiction':
            rates = self.weights(log)

            def possible(t, c):
                for (roles, _, pending), w in rates.items():
                    if w and roles[player] == role and color(roles[t]) == c and (role == M or pending == t):
                        return True
                return False
            options = [o for o in options if possible(*o)] or options
        result = {o: F(1, len(options)) for o in options}
        self.memo_fake[key] = result
        return result

    def column_choices(self, log, world):
        roles, _, pending = world
        strategy = self.strategy
        alive = self.alive(log)
        claims = self.claims(log)
        first = self.first_column(log)
        fixed = []
        true_holders = set()
        for role in (S, M):
            holder = next((p for p in alive if roles[p] == role), None)
            if holder is None:
                continue
            true_holders.add(holder)
            claimed = claims.get(holder) == role
            result = None
            if first:
                result = pending if role == S else self.last_of(log, 'exec')
            black = result is not None and roles[result] == W
            if claimed:
                if result is not None and (strategy.disclose_all or (black and strategy.disclose_black)):
                    fixed.append(('report', holder, result, color(roles[result])))
            else:
                if (black and strategy.co_on_black) or (strategy.co_on_saturation and self.saturated(log, role)):
                    fixed.append(('co', holder, 3 if role == S else 1))
                    if black and strategy.disclose_black:
                        fixed.append(('report', holder, result, BLACK))
        columns = {tuple(fixed): F(1)}
        if first and self.last_of(log, 'bite') is not None and strategy.disclose_all:
            for player in claims:
                if player in alive and player not in true_holders:
                    grown = {}
                    for acts, p in columns.items():
                        for (t, c), q in self.fake_law(log, player).items():
                            longer = acts + (('report', player, t, c),)
                            grown[longer] = grown.get(longer, F()) + p * q
                    columns = grown
        return {tuple(sorted(acts, key=repr)): p for acts, p in columns.items()}

    # --- entry ------------------------------------------------------------------

    def normal_log(self):
        """Input log in 0-based names with the implied 更新なし before each execution."""
        log = []
        for event in self.board.log:
            if event[0] == 'col':
                acts = [('co', a[1] - 1, a[2]) if a[0] == 'co' else ('report', a[1] - 1, a[2] - 1, a[3])
                        for a in event[1]]
                log.append(('col', tuple(sorted(acts, key=repr))))
            else:
                if event[0] == 'exec' and not (log and log[-1][0] == 'col' and not log[-1][1]):
                    log.append(('col', ()))
                log.append((event[0], event[1] - 1))
        return tuple(log)

    def evaluate(self):
        raw = self.normal_log()
        names = rename_by_appearance(raw, self.n)
        log = apply_names(raw, names)
        rates = self.role_rates(log)
        weights = self.weights(log)
        village = sum((w * self.value(log, k) for k, w in weights.items()), F())
        role_rates = {user + 1: rates[names[user]] for user in range(self.n)}
        return {'role_rates': role_rates, 'village': village, 'actions': self.actions(log, names)}

    def actions(self, log, names):
        back = {new: old + 1 for old, new in names.items()}
        stage = self.stage(log)
        if stage == 'open':
            worlds = self.weights(log)
            if any(acts for k in worlds for acts in self.column_choices(log, k)):
                return {}
            log = log + (('col', ()),)
            stage = 'closed'
        weights = self.weights(log)
        actions = {}
        for p in self.alive(log):
            if stage == 'closed':
                actions[back[p]] = sum((w * self.after_execution(log, k, p) for k, w in weights.items()), F())
            else:
                legal = [(k, w) for k, w in weights.items() if self.rules.self_bite or k[0][p] != W]
                total = sum((w for _, w in legal), F())
                if total:
                    actions[back[p]] = sum((w * self.after_bite(log, k, p) for k, w in legal), F()) / total
        return actions
