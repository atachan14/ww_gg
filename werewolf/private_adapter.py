"""Private table projection. Public policy evaluation never receives private worlds.

Only the immediate night horizon is supported for wolf actions. Final values,
seer information value and hunter mechanics need a joint information-set solver.
"""
from .exact import actual_role, legal_targets
from .private_view import condition_private
from .by_dawn import immediate


LABELS = {'seer': '占い視点', 'hunter': '狩人視点', 'wolf': '狼視点'}


def viewpoint_roles(board):
    result = {}
    for role, label in LABELS.items():
        if not board.initial_role_counts[role]:
            continue
        if role == 'wolf':
            combinations = {tuple(p for p in range(1, board.player_count + 1)
                                  if w[0] & (1 << (p - 1))) for w in board.worlds}
        else:
            combinations = {(p,) for p in board.alive for w in board.worlds
                            if actual_role(board, w, p) == role}
        result[role] = {'label': label, 'required': board.initial_role_counts['wolf'] if role == 'wolf' else 1,
                        'combinations': sorted(combinations)}
    return result


def private_slots(board, player, rules):
    slots = []
    for day in range(1, board.day + 1):
        if day == 1 and rules.initial_seer == 'none':
            continue
        dead = {e.target for e in board.history
                if e.day < day - 1 or e.day == day - 1 and e.phase == 'day'}
        slots.append({'day': day, 'targets': [p for p in range(1, board.player_count + 1)
                                            if p != player and p not in dead]})
    return slots


def evaluate_private_table(public, role, players, results, rules, strategy):
    view = condition_private(public, role, players, results, rules=rules)
    private = view.board
    reason = {'seer': '占い先の取得履歴と将来の公開判断を分離した勝率評価は未対応です。',
              'hunter': '護衛能力の計算と秘密の護衛履歴は未対応です。',
              'wolf': '最終勝率は公開方針と私的分布を分離した継続評価が未対応です。'}[role]
    targets = legal_targets(private, rules, strategy) if role == 'wolf' else ()
    rows = []
    for p in range(1, public.player_count + 1):
        probabilities = {r: str(private.role_probability(p, r)) for r in ('villager', 'medium', 'seer', 'hunter', 'wolf')}
        probabilities['citizen'] = probabilities.pop('villager')
        probabilities['village'] = str(1 - private.wolf_probability(p))
        dawn = immediate(private, p, rules, strategy) if p in targets else None
        rows.append({'id': p, 'probabilities': probabilities,
                     'dawn': {'village': str(dawn.village_win), 'wolf': str(dawn.wolf_win)} if dawn else None,
                     'final': None, 'legal': p in targets})
    return {'players': rows, 'reason': reason,
            'acquisitions': [{'day': a.day, 'player': a.player, 'target': a.target, 'color': a.color}
                             for a in view.acquisitions]}
