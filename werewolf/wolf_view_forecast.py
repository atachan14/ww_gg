"""Wolf-conditional payoffs of a separately evaluated public continuation.

Public target/report rankings never receive the viewer's mask. Equally optimal
targets and report instructions are mixed uniformly, without player-ID priority.
Future bites filter that common ranking only for actual legal non-teammates;
this does not optimize public executions inside the known wolf assignment.
Public updates retain the engine's chosen-action law, not an additional action
selection likelihood. No equilibrium or new reporting strategy is introduced.
"""
from fractions import Fraction as F
from dataclasses import replace
from .seer_acquisition import Hypothesis, normalize
from .night_acquisition import acquire_laws
from .information_weights import observer_report_weights
from .exact import (action_outcomes, legal_targets, value_for_action, report_actions,
                    random_report_outcomes, joint_value, replace_worlds)
from .seer_future_uniform import FuturePending, acquire_uniform
from .seer_future_forecast import forecast, project_private, future_publications
from .calculation_budget import calculation_budget, tick, CalculationBudgetExceeded


class Unresolved(Exception):
    def __init__(self, reason): self.reason = reason


def wolf_forecast(public, mask, rules, strategy, *, scan_state=None, past=(),
                  max_work=250000, max_seconds=20, trace=None, observer=None):
    """Return forced-bite village values; exact Fractions, or a complete Pending.

scan_state is the PUBLIC role/acquisition prior. Conditioning applies only to
branch weights and payoffs; each child public Board keeps all public worlds.
"""
    if public.phase != 'night' or public.winner is not None:
        raise ValueError('Wolf comparison requires a continuing night Board')
    if scan_state is not None and scan_state.public_roles != tuple(sorted(public.worlds)):
        raise ValueError('Public acquisition prior must match public worlds')
    public_memo = {}; conditional_memo = {}; action_memo = {}; acquisition_memo = {}

    def checked(result):
        if isinstance(result, FuturePending): raise Unresolved(result.reason)
        return result

    def mass(b, s):
        if observer is not None:
            return sum((h.mass for h in s.hypotheses if observer(h, s)), F())
        return (sum((h.mass for h in s.hypotheses if h.roles[0] == mask), F()) if s is not None
                else sum((w[-1] for w in b.worlds if w[0] == mask), F()))

    def public_values(b, s, published):
        key = (b, s, published)
        if key not in public_memo:
            tick(len(b.worlds))
            if not legal_targets(b, rules, strategy):
                raise Unresolved('wolf_view_no_legal_public_continuation')
            if s is None:
                values = tuple((p, value_for_action(b, p, rules, strategy).village_win)
                               for p in legal_targets(b, rules, strategy))
                value = (sum((v for _, v in values), F()) / len(values) if getattr(strategy, b.phase) == 'random'
                         else (max if b.phase == 'day' else min)(v for _, v in values))
            else:
                result = checked(forecast(b, s, published, rules, strategy, max_work=max_work,
                                          marginalize_known_fake=False))
                value, values = result.village_win, result.action_values
            public_memo[key] = (value, values)
            if trace is not None:
                trace.setdefault('public_rankings', []).append({'day': b.day, 'phase': b.phase,
                    'history': tuple((e.day, e.phase, e.target) for e in b.history),
                    'values': values})
        return public_memo[key]

    def project(s, child):
        return project_private(s, child, marginalize_private=observer is None) if s is not None else None

    def weighted(parent, state, branches):
        # Chosen bites normalize within counts in the existing public engine.
        # The observer's full initial mask fixes its count on this history;
        # normalize its conditional branch law without changing public Boards.
        prior = mass(parent, state)
        if not prior: raise Unresolved('wolf_view_no_compatible_public_branch')
        terms = [(q * mass(child, s) / prior, child, s, published)
                 for q, child, s, published in branches if mass(child, s)]
        total = sum((q for q, _, _, _ in terms), F())
        if not total: raise Unresolved('wolf_view_no_compatible_public_branch')
        return sum((q / total * solve(child, s, published) for q, child, s, published in terms), F())

    def publications(b, s, published):
        if s is None:
            return ((F(1), b, None, published),)
        generated = checked(future_publications(s, published, b.alive, b.claims,
                                                fake_policy=strategy.fake_seer_policy))
        return tuple((branch.probability, replace_worlds(b, branch.state.public_roles),
                      branch.state, published + branch.reports) for branch in generated)

    def morning_branches(b, s, published):
        actions = report_actions(b) if strategy.disclosure_for('medium') == 'all' else ()
        if not actions:
            return publications(b, s, published)
        if strategy.fake_reports == 'random':
            outcomes = random_report_outcomes(b)
        else:
            # Choose the medium fake instruction once from PUBLIC expectations,
            # including future seer vectors, before applying the viewer's mask.
            candidates = []
            for action in actions:
                value = F()
                for o in action.outcomes:
                    next_s = project(s, o.board)
                    if o.board.winner is not None:
                        continuation = F(o.board.winner == 'village')
                    elif next_s is None:
                        continuation = joint_value(o.board, rules, strategy).village_win
                    else:
                        continuation = sum((q * public_values(child, st, reports)[0]
                                            for q, child, st, reports in publications(o.board, next_s, published)), F())
                    value += o.probability * continuation
                candidates.append((value, action))
            best = min(value for value, _ in candidates)
            tied = tuple(action for value, action in candidates if value == best)
            # The randomly selected tie instruction is not public information.
            # Merge equal public vectors before any subsequent public decision,
            # as in the existing random-report law.
            from .exact import BoardOutcome, merge_report_outcomes
            outcomes = merge_report_outcomes(BoardOutcome(o.probability / len(tied), o.board)
                                             for instruction in tied for o in instruction.outcomes)
        branches = []
        for o in outcomes:
            next_s = project(s, o.board)
            for q, child, st, reports in publications(o.board, next_s, published):
                branches.append((o.probability * q, child, st, reports))
        return tuple(branches)

    def morning(b, s, published):
        return weighted(b, s, morning_branches(b, s, published))

    def push_private(source, private, branches):
        """Apply PUBLIC report likelihoods to the separately carried private law."""
        return observer_report_weights(source,private,branches,
            incomplete=lambda:Unresolved('seer_view_report_likelihood_incomplete'))

    def private_action(b, s, published, target, private):
        # Both laws use the same fixed PUBLIC instruction, but each law retains
        # its own count prior and count-wise legal-bite normalizers.
        key = (b, s, published, target, private)
        if key in action_memo: return action_memo[key]
        tick(len(s.hypotheses) + len(private.hypotheses))
        private_board = replace_worlds(b, private.public_roles)
        if target not in legal_targets(private_board, rules, strategy):
            raise Unresolved('seer_view_public_instruction_private_illegal')
        pub_acquired, priv_acquired = s, private
        if b.phase == 'night':
            laws = acquire_laws(b,s,
                lambda source,alive:checked(acquire_uniform(source,alive,max_work=max_work,position=strategy.seer_position)),
                private=private,observer=observer,inconsistent=lambda:Unresolved('seer_view_scan_outside_public_support'))
            pub_acquired,priv_acquired = laws.public,laws.private
        public_children = {o.board.winner: o.board for o in action_outcomes(b, target, rules, strategy)}
        private_outcomes = action_outcomes(private_board, target, rules, strategy)
        if trace is not None:
            trace.setdefault('private_transitions', []).append({'history': tuple((e.day,e.phase,e.target) for e in b.history),
                'phase': b.phase, 'target': target, 'prior_counts': private_board.wolf_count_distribution,
                'child_counts': tuple((o.probability, o.board.wolf_count_distribution) for o in private_outcomes),
                'public_child_counts': tuple(child.wolf_count_distribution for child in public_children.values())})
        total = F()
        for o in private_outcomes:
            if o.board.winner is not None:
                value = F(o.board.winner == 'village')
            else:
                child = public_children[None]
                pub_next = project(pub_acquired, child)
                priv_next = project_private(priv_acquired, o.board, marginalize_private=False)
                if b.phase == 'night':
                    branches = push_private(pub_next, priv_next, morning_branches(child, pub_next, published))
                    value = sum((q * private_solve(c, st, reports, priv)
                                 for q, c, st, reports, priv in branches), F())
                else:
                    value = private_solve(child, pub_next, published, priv_next)
            total += o.probability * value
        action_memo[key] = total
        return total

    def private_solve(b, s, published, private):
        if b.winner is not None: return F(b.winner == 'village')
        key = (b, s, published, private)
        if key in conditional_memo: return conditional_memo[key]
        _, scores = public_values(b, s, published)
        if getattr(strategy, b.phase) == 'random': chosen = tuple(p for p, _ in scores)
        else:
            best = (max if b.phase == 'day' else min)(v for _, v in scores)
            chosen = tuple(p for p, v in scores if v == best)
        if not chosen: raise Unresolved('seer_view_no_public_continuation')
        value = sum((private_action(b, s, published, p, private) for p in chosen), F()) / len(chosen)
        conditional_memo[key] = value
        return value

    def action(b, s, published, target):
        key = (b, s, published, target)
        if key in action_memo: return action_memo[key]
        tick(len(b.worlds))
        prepared = s
        if b.phase == 'night' and s is not None:
            acquisition_key = (b, s)
            if acquisition_key not in acquisition_memo:
                acquisition_memo[acquisition_key] = checked(acquire_uniform(s, b.alive, max_work=max_work,
                                                                           position=strategy.seer_position))
            prepared = acquisition_memo[acquisition_key]
        prior = mass(b, s); terms = []
        for o in action_outcomes(b, target, rules, strategy):
            next_s = project(prepared, o.board)
            q = o.probability * mass(o.board, next_s) / prior
            if not q: continue
            value = (F(o.board.winner == 'village') if o.board.winner is not None else
                     morning(o.board, next_s, published) if b.phase == 'night' else solve(o.board, next_s, published))
            terms.append((q, value))
        total = sum((q for q, _ in terms), F())
        if not total: raise Unresolved('wolf_view_no_compatible_public_branch')
        value = sum((q * v for q, v in terms), F()) / total
        action_memo[key] = value
        return value

    def solve(b, s, published):
        tick(len(b.worlds))
        if b.winner is not None: return F(b.winner == 'village')
        key = (b, s, published)
        if key in conditional_memo: return conditional_memo[key]
        _, scores = public_values(b, s, published)
        available = tuple((p, v) for p, v in scores if b.phase == 'day' or strategy.include_self_bite
                          or observer is not None or not mask & (1 << (p - 1)))
        if not available: raise Unresolved('wolf_view_no_legal_continuation')
        if getattr(strategy, b.phase) == 'random':
            chosen = tuple(p for p, _ in available)
        else:
            best = (max if b.phase == 'day' else min)(v for _, v in available)
            chosen = tuple(p for p, v in available if v == best)
        if trace is not None:
            trace.setdefault('choices', []).append({'day': b.day, 'phase': b.phase,
                'history': tuple((e.day, e.phase, e.target) for e in b.history), 'targets': chosen})
        value = sum((action(b, s, published, p) for p in chosen), F()) / len(chosen)
        conditional_memo[key] = value
        return value

    try:
        with calculation_budget(max_work, max_seconds=max_seconds):
            if not mass(public, scan_state): raise ValueError('Inconsistent wolf roster')
            if observer is not None:
                private = replace(scan_state, hypotheses=normalize(tuple(h for h in scan_state.hypotheses if observer(h, scan_state))))
                return private_solve(public, scan_state, past, private)
            targets = tuple(p for p in legal_targets(public, rules, strategy)
                            if strategy.include_self_bite or not mask & (1 << (p - 1)))
            return tuple((p, action(public, scan_state, past, p)) for p in targets)
    except CalculationBudgetExceeded:
        return FuturePending('wolf_view_continuation_budget_exceeded')
    except Unresolved as exc:
        return FuturePending(exc.reason)
