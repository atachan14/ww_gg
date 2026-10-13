"""Private table projection. Public policy evaluation never receives private worlds.

Wolf final values use a separate public-policy continuation. Seer information
value and hunter mechanics remain unsupported.
"""
from .exact import actual_role, legal_targets
from .private_view import condition_private
from .by_dawn import immediate
from .wolf_view_forecast import wolf_forecast
from .seer_future_uniform import FuturePending


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


def evaluate_private_table(public, role, players, results, rules, strategy, *, game_state=None,
                           max_work=250000, max_seconds=20):
    view = condition_private(public, role, players, results, rules=rules)
    private = view.board
    reason = {'seer': '占い先の取得履歴と将来の公開判断を分離した勝率評価は未対応です。',
              'hunter': '護衛能力の計算と秘密の護衛履歴は未対応です。',
              'wolf': '公開戦略の候補順に従う狼条件付き最終勝率です。同率は番号順、仲間への襲撃は除外します。'}[role]
    targets = legal_targets(private, rules, strategy) if role == 'wolf' else ()
    final_values = {}
    if role == 'wolf':
        state = None; past = ()
        if strategy.disclosure_for('seer') == 'all' and any(public.claims[p-1] == 'seer' for p in public.alive):
            from .seer_future_bridge import prepare_game
            prepared = prepare_game(game_state, public, max_work=max_work) if game_state else FuturePending('wolf_view_public_acquisition_prior_missing')
            if isinstance(prepared, FuturePending):
                result = prepared
            else:
                state, past = prepared
                result = wolf_forecast(public, sum(1 << (p-1) for p in players), rules, strategy,
                                       scan_state=state, past=past, max_work=max_work, max_seconds=max_seconds)
        else:
            result = wolf_forecast(public, sum(1 << (p-1) for p in players), rules, strategy,
                                   max_work=max_work, max_seconds=max_seconds)
        if isinstance(result, FuturePending):
            reasons = {'wolf_view_continuation_budget_exceeded': '最終勝率が計算予算を超えたため未計算です。',
                       'future_public_continuation_budget_exceeded': '公開側の未来計算が計算予算を超えたため未計算です。',
                       'multiple_fake_report_correlation_unselected': '複数偽占いの共同報告モデルが未対応のため最終勝率は未計算です。',
                       'full_disclosure_truth_not_conditioned': '公開側の占い取得履歴が不足するため最終勝率は未計算です。',
                       'wolf_view_public_acquisition_prior_missing': '公開側の占い取得履歴が不足するため最終勝率は未計算です。'}
            reason = reasons.get(result.reason, '現在の公開継続モデルでは最終勝率を計算できません。')
        else:
            final_values = dict(result)
            if state is not None: reason += ' 未来占いは既存の未訪問先優先・均等報告モデルを使用します。'
            if set(targets) - set(final_values): reason += ' 公開側の全仮説で合法にならない襲撃先は未対応です。'
        if public.initial_hunter_count: reason += ' 狩人の護衛能力はこの計算に含まれません。'
    rows = []
    for p in range(1, public.player_count + 1):
        probabilities = {r: str(private.role_probability(p, r)) for r in ('villager', 'medium', 'seer', 'hunter', 'wolf')}
        probabilities['citizen'] = probabilities.pop('villager')
        probabilities['village'] = str(1 - private.wolf_probability(p))
        dawn = immediate(private, p, rules, strategy) if p in targets else None
        rows.append({'id': p, 'probabilities': probabilities,
                     'dawn': {'village': str(dawn.village_win), 'wolf': str(dawn.wolf_win)} if dawn else None,
                     'final': {'village': str(final_values[p]), 'wolf': str(1-final_values[p])} if p in final_values else None,
                     'legal': p in targets})
    return {'players': rows, 'reason': reason,
            'acquisitions': [{'day': a.day, 'player': a.player, 'target': a.target, 'color': a.color}
                             for a in view.acquisitions]}
