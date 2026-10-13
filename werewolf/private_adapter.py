"""Private table projection. Public policy evaluation never receives private worlds.

Wolf finals and supported CO/all seer scan comparisons use a
separate public-policy continuation. Other seer scopes and hunter mechanics
remain explicit unsupported values.
"""
from .exact import actual_role, legal_targets
from .private_view import condition_private
from .by_dawn import immediate
from .phase_updates import acquisition_roster
from .information_set_forecast import information_forecast
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
        slots.append({'day': day, 'targets': [p for p in acquisition_roster(board.player_count,board.history,day)
                                            if p != player]})
    return slots


def evaluate_private_table(public, role, players, results, rules, strategy, *, game_state=None,
                           max_work=250000, max_seconds=20):
    view = condition_private(public, role, players, results, rules=rules)
    private = view.board
    reason = {'seer': '占い先の取得履歴と将来の公開判断を分離した勝率評価は未対応です。',
              'hunter': '護衛能力の計算と秘密の護衛履歴は未対応です。',
              'wolf': '仲間の情報集合で設定済みの襲撃戦略を評価した最終勝率です。同値の最適候補は均等、仲間への襲撃は除外します。'}[role]
    targets = legal_targets(private, rules, strategy) if role == 'wolf' else ()
    final_values = {}
    if role == 'seer':
        targets = tuple(p for p in public.alive if p != players[0])
        from .seer_future_bridge import prepare_game
        from .seer_view_forecast import seer_forecast
        if strategy.disclosure_for('seer') != 'all':
            result = FuturePending('seer_view_unpublished_own_action_unimplemented')
        elif public.claims[players[0]-1] != 'seer':
            result = FuturePending('seer_view_latent_future_co_unimplemented')
        else:
            prepared = prepare_game(game_state, public, max_work=max_work) if game_state else FuturePending('seer_view_public_prior_missing')
            if isinstance(prepared, FuturePending): result = prepared
            else:
                state, past = prepared
                result = seer_forecast(public, players[0], view.acquisitions, rules, strategy,
                                       scan_state=state, past=past, max_work=max_work, max_seconds=max_seconds)
        reasons = {'seer_view_unpublished_own_action_unimplemented': 'なし開示：未公開結果を本人の後続行動へ使う評価は未対応です。',
                   'information_set_budget_exceeded': '狼情報集合の評価が計算予算を超えたため最終勝率は未計算です。',
                   'multiple_fake_report_correlation_unselected': '複数偽占いの共同報告モデルが未対応のため最終勝率は未計算です。',
                   'seer_view_latent_future_co_unimplemented': '潜伏中の将来COと秘密結果利用は未対応です。占いCO済み・すべて開示の範囲に対応します。'}
        if isinstance(result, FuturePending):
            reason = reasons.get(result.reason, '占いの公開取得履歴・未来報告モデルまたは計算予算が未対応のため未計算です。')
        else:
            final_values = dict(result); targets = tuple(final_values)
            reason = '占い先別の最終勝率です。狼は仲間を知って行動し、公開推理は死体との矛盾除外を維持します。すべて開示・CO固定・未訪問先優先。次の朝までの勝率は未対応です。'
        if public.initial_hunter_count: reason += ' 狩人の護衛能力はこの計算に含まれません。'
    if role == 'wolf':
        state = None; past = ()
        if strategy.disclosure_for('seer') == 'all' and any(public.claims[p-1] == 'seer' for p in public.alive):
            from .seer_future_bridge import prepare_game
            prepared = prepare_game(game_state, public, max_work=max_work) if game_state else FuturePending('wolf_view_public_acquisition_prior_missing')
            if isinstance(prepared, FuturePending):
                result = prepared
            else:
                state, past = prepared
                result = information_forecast(public, state, past, rules, strategy,
                                              mask=sum(1 << (p-1) for p in players), max_work=max_work, max_seconds=max_seconds)
        else:
            from .seer_acquisition import from_board
            from .seer_future_uniform import TrueScanState
            from .phase_updates import acquisition_rosters
            rosters=acquisition_rosters(public)
            state=TrueScanState(from_board(public),rosters,rules.initial_seer,tracked=(),observed_prefix=public.day)
            result = information_forecast(public, state, past, rules, strategy,
                                          mask=sum(1 << (p-1) for p in players), max_work=max_work, max_seconds=max_seconds)
        if isinstance(result, FuturePending):
            reasons = {'information_set_budget_exceeded': '最終勝率が計算予算を超えたため未計算です。',
                       'future_public_continuation_budget_exceeded': '公開側の未来計算が計算予算を超えたため未計算です。',
                       'multiple_fake_report_correlation_unselected': '複数偽占いの共同報告モデルが未対応のため最終勝率は未計算です。',
                       'full_disclosure_truth_not_conditioned': '公開側の占い取得履歴が不足するため最終勝率は未計算です。',
                       'wolf_view_public_acquisition_prior_missing': '公開側の占い取得履歴が不足するため最終勝率は未計算です。'}
            reason = reasons.get(result.reason, '現在の公開継続モデルでは最終勝率を計算できません。')
        else:
            final_values = dict(result)
            reason += ' 狼は仲間の情報集合内で期待値を比較し、公開推理は死体との矛盾除外を維持します。'
            if set(targets) - set(final_values): reason += ' 公開側の全仮説で合法にならない襲撃先は未対応です。'
        if public.initial_hunter_count: reason += ' 狩人の護衛能力はこの計算に含まれません。'
    rows = []
    for p in range(1, public.player_count + 1):
        probabilities = {r: str(private.role_probability(p, r)) for r in ('villager', 'medium', 'seer', 'hunter', 'wolf')}
        probabilities['citizen'] = probabilities.pop('villager')
        probabilities['village'] = str(1 - private.wolf_probability(p))
        dawn = immediate(private, p, rules, strategy) if role == 'wolf' and p in targets else None
        rows.append({'id': p, 'probabilities': probabilities,
                     'dawn': {'village': str(dawn.village_win), 'wolf': str(dawn.wolf_win)} if dawn else None,
                     'final': {'village': str(final_values[p]), 'wolf': str(1-final_values[p])} if p in final_values else None,
                     'legal': p in targets})
    return {'players': rows, 'reason': reason,
            'acquisitions': [{'day': a.day, 'player': a.player, 'target': a.target, 'color': a.color}
                             for a in view.acquisitions]}
