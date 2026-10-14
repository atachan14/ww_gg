"""Private table projection. Public policy evaluation never receives private worlds.

All owner tables keep the public-policy continuation separate from evidence.
Supported uniform entries retain the shared joint history; legacy CO/max entries
keep their existing contracts and explicit Pending for unsupported histories.
"""
from .exact import actual_role, legal_targets
from .private_view import condition_private
from .by_dawn import immediate
from .phase_updates import acquisition_roster
from .information_set_forecast import information_forecast
from .seer_future_uniform import FuturePending
from .public_prior import prepare_public_prior


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


def private_slots(board, player, rules,role="seer"):
    if role in ("hunter","wolf"):
        return [{"day":night,"targets":[p for p in acquisition_roster(board.player_count,board.history,night+1) if role=="wolf" or p!=player]} for night in range(1,board.day)]
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
    from .root_secret_flow import prepare_root_entry
    branch=prepare_root_entry(game_state or {},public,rules,strategy,
                              max_work=max_work,max_seconds=max_seconds)
    root_entry=branch is not None
    reason = {'seer': '占い先の取得履歴と将来の公開判断を分離した勝率評価は未対応です。',
              'hunter': '護衛能力の計算と秘密の護衛履歴は未対応です。',
              'wolf': '仲間の情報集合で設定済みの襲撃戦略を評価した最終勝率です。同値の最適候補は均等、仲間への襲撃は除外します。'}[role]
    targets = legal_targets(private, rules, strategy) if role == 'wolf' else ()
    final_values = {};guard_dawn={}
    if role=="hunter":
        from .guard_view_forecast import guard_forecast
        targets=tuple(p for p in public.alive if p!=players[0])
        from .root_secret_flow import root_guard_forecast
        if root_entry:
            result=branch if isinstance(branch,FuturePending) else root_guard_forecast(branch,players[0],view.guards,rules,strategy,max_work=max_work,max_seconds=max_seconds)
            if not isinstance(branch,FuturePending):
                from .root_secret_flow import root_actor_view
                actor=root_actor_view(branch,lambda h:bool(h.roles[3]&(1<<(players[0]-1))) and all(g in h.guards for g in view.guards))
                if not isinstance(actor,FuturePending):
                    from .exact import replace_worlds
                    private=replace_worlds(public,actor.belief.public_roles)
        else:
            prepared=prepare_public_prior(game_state or {},public,rules,track_live_seers=strategy.disclosure_for("seer")=="all" and bool(public.initial_seer_count),max_work=max_work)
            result=prepared if isinstance(prepared,FuturePending) else guard_forecast(public,players[0],private,prepared[0],prepared[1],rules,strategy,guards=view.guards,max_work=max_work,max_seconds=max_seconds)
        if isinstance(result,FuturePending):
            reason={"guard_hidden_attack_max_unimplemented":"狩人未確定の襲撃最大化は未対応です。襲撃位置「均等化」に対応しています。","guard_multiple_hunters_unimplemented":"複数狩人の能力計算は未対応です。","guard_no_repeat_max_unimplemented":"連続護衛なしのmaxは未対応です。","guard_no_repeat_history_missing":"前夜の護衛履歴を共同分布から再構成できません。","guard_view_target_generation_support_unresolved":"本人の前夜護衛による合法候補が未確定です。"}.get(result.reason,"護衛の能力計算は未対応または計算予算に達しました。")
        else:
            final_values,guard_dawn=result
            targets=tuple(final_values)
            reason="各行を今夜の固定護衛先として比較します。後続の護衛は均等化です。公開情報だけで他者の方針を選び、秘密の護衛先や成功通知は公開しません。"
    if role == 'seer':
        targets = tuple(p for p in public.alive if p != players[0])
        from .seer_view_forecast import seer_forecast
        from .root_secret_flow import root_seer_forecast,root_actor_view
        if root_entry:
            result=branch if isinstance(branch,FuturePending) else root_seer_forecast(
                branch,players[0],view.acquisitions,rules,strategy,max_work=max_work,max_seconds=max_seconds)
            if not isinstance(branch,FuturePending):
                actor=root_actor_view(branch,lambda h:bool(h.roles[2]&(1<<(players[0]-1))) and
                    all(a in h.acquisitions for a in view.acquisitions))
                if not isinstance(actor,FuturePending):
                    from .exact import replace_worlds
                    private=replace_worlds(public,actor.belief.public_roles)
        elif strategy.disclosure_for('seer') != 'all':
            result = FuturePending('seer_view_unpublished_own_action_unimplemented')
        elif public.claims[players[0]-1] != 'seer':
            result = FuturePending('seer_view_latent_future_co_unimplemented')
        else:
            prepared = prepare_public_prior(game_state, public, rules, max_work=max_work) if game_state else FuturePending('seer_view_public_prior_missing')
            if isinstance(prepared, FuturePending): result = prepared
            else:
                state, past = prepared
                from .guard_history_prior import seed_history
                if strategy.night=='max' and public.initial_hunter_count:state=seed_history(public,state)
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
        if root_entry and not isinstance(result,FuturePending):
            reason = '本人の役職・取得結果・行動履歴で共同分布を条件付け、同じ公開方針の下で次の占い先を比較します。'
        if public.initial_hunter_count: reason += ' 護衛位置は均等化です。公開分布と本人の私的分布を分離しています。'
    if role == 'wolf':
        state = None; past = ()
        from .root_secret_flow import root_wolf_forecast
        if root_entry:
            result=branch if isinstance(branch,FuturePending) else root_wolf_forecast(branch,players,view.attacks,rules,strategy,max_work=max_work,max_seconds=max_seconds)
            if not isinstance(result,FuturePending):
                result,guard_dawn,belief=result
                from .exact import replace_worlds
                private=replace_worlds(public,belief.public_roles)
        elif strategy.disclosure_for('seer') == 'all' and any(public.claims[p-1] == 'seer' for p in public.alive):
            prepared = prepare_public_prior(game_state, public, rules, max_work=max_work) if game_state else FuturePending('wolf_view_public_acquisition_prior_missing')
            if isinstance(prepared, FuturePending):
                result = prepared
            else:
                state, past = prepared
                from .guard_history_prior import seed_history
                if strategy.night=='max' and public.initial_hunter_count:state=seed_history(public,state)
                result = information_forecast(public, state, past, rules, strategy,
                                              mask=sum(1 << (p-1) for p in players), private_board=private if public.initial_hunter_count else None, private_attacks=view.attacks, max_work=max_work, max_seconds=max_seconds)
        else:
            state,past=prepare_public_prior(game_state or {},public,rules,track_live_seers=False,max_work=max_work)
            from .guard_history_prior import seed_history
            if strategy.night=='max' and public.initial_hunter_count:state=seed_history(public,state)
            result = information_forecast(public, state, past, rules, strategy,
                                          mask=sum(1 << (p-1) for p in players), private_board=private if public.initial_hunter_count else None, private_attacks=view.attacks, max_work=max_work, max_seconds=max_seconds)
        missing_attacks={night for night in range(1,public.day) if not any(e.day==night and e.phase=='night' for e in public.history)}-{a.night for a in view.attacks}
        from .guard_history_prior import hero_deducible
        if not root_entry and public.initial_hunter_count and missing_attacks and not hero_deducible(public):result=FuturePending('wolf_guard_attack_history_missing')
        if isinstance(result, FuturePending):
            reasons = {'information_set_budget_exceeded': '最終勝率が計算予算を超えたため未計算です。',
                       'future_public_continuation_budget_exceeded': '公開側の未来計算が計算予算を超えたため未計算です。',
                       'multiple_fake_report_correlation_unselected': '複数偽占いの共同報告モデルが未対応のため最終勝率は未計算です。',
                       'full_disclosure_truth_not_conditioned': '公開側の占い取得履歴が不足するため最終勝率は未計算です。',
                       'guard_hidden_attack_max_unimplemented':'狩人未確定の襲撃最大化は未対応です。襲撃位置「均等化」に対応しています。',
                       'wolf_guard_attack_history_missing':'無死亡となった夜の本人の秘密襲撃先を入力してください。',
                       'wolf_view_public_acquisition_prior_missing': '公開側の占い取得履歴が不足するため最終勝率は未計算です。'}
            reason = reasons.get(result.reason, '現在の公開継続モデルでは最終勝率を計算できません。')
        else:
            final_values = dict(result)
            if public.initial_hunter_count and state is not None:
                from .model_a_public import horizon_for_action
                from .information_set_forecast import InformationSetForecast
                from .calculation_budget import calculation_budget,CalculationBudgetExceeded
                from .actor_information import condition_actor_state
                mask=sum(1<<(p-1) for p in players)
                try:
                    with calculation_budget(max_work,max_seconds=max_seconds):
                        engine=InformationSetForecast(rules,strategy,max_work=max_work)
                        from .guard_history_prior import matches
                        own=condition_actor_state(state,lambda h:h.roles[0]==mask and h.roles in {w[:-1] for w in private.worlds} and matches(h.attacks,view.attacks),attacks=view.attacks)
                        guard_dawn={p:horizon_for_action(engine,public,state,past,p,own) for p in final_values}
                except CalculationBudgetExceeded:guard_dawn={}
            reason += ' 狼は仲間の情報集合内で期待値を比較し、公開推理は死体との矛盾除外を維持します。'
            if set(targets) - set(final_values): reason += ' 公開側の全仮説で合法にならない襲撃先は未対応です。'

        if public.initial_hunter_count: reason += ' 護衛位置は均等化です。公開分布と本人の私的分布を分離しています。'
    rows = []
    for p in range(1, public.player_count + 1):
        probabilities = {r: str(private.role_probability(p, r)) for r in ('villager', 'medium', 'seer', 'hunter', 'wolf')}
        probabilities['citizen'] = probabilities.pop('villager')
        probabilities['village'] = str(1 - private.wolf_probability(p))
        dawn = immediate(private, p, rules, strategy) if role == 'wolf' and p in targets and not public.initial_hunter_count else guard_dawn.get(p)
        rows.append({'id': p, 'probabilities': probabilities,
                     'dawn': {'village': str(dawn.village_win), 'wolf': str(dawn.wolf_win)} if dawn else None,
                     'final': {'village': str(final_values[p]), 'wolf': str(1-final_values[p])} if p in final_values else None,
                     'legal': p in targets})
    return {'players': rows, 'reason': reason,
            'acquisitions': [{'day': a.day, 'player': a.player, 'target': a.target, 'color': a.color}
                             for a in view.acquisitions]}
