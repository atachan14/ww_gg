"""Marginal-only experiment on an independent initial board."""
from fractions import Fraction as F
from .exact import ClaimPolicy, condition_claims, initial_board, Values, Rules, Strategy, group_initial_board, co_group_compositions, ROLES, ROLE_LABELS, default_bluff_roles


def compare_initial(citizens, mediums, wolves, claims, policy=ClaimPolicy(), mode='trial', seers=0, hunters=0):
    board = initial_board(citizens + mediums + seers + hunters + wolves, wolves, mediums, seers, hunters)
    if len(claims) != board.player_count or any(c not in ('latent',*ROLES) for c in claims):
        raise ValueError('CO入力を確認してください。')
    if mode not in ('current','trial','group'):
        raise ValueError('比較モードを確認してください。')
    counts = {'villager': citizens, 'medium': mediums, 'wolf': wolves}
    if seers:counts['seer']=seers
    if hunters:counts['hunter']=hunters
    if mode=='trial' and (seers or hunters):
        return dict(mode=mode,issues=['2段階試作は市民・霊能・人狼の定義を維持します。占い師・狩人を含む残差配分は未定義です。'],rows=[],totals={},rates=None,valid=False)
    roles=('villager','wolf','medium')+tuple(r for r in ('seer','hunter') if r in counts)
    def compatible(role, claim):
        return claim == 'latent' or role == claim or role == 'wolf'
    issues = []
    filtered = None
    try:
        filtered = (group_initial_board(board,tuple(claims),policy) if mode=='group' else condition_claims(board,tuple(claims),policy))
    except ValueError as exc:
        issues.append(str(exc))
    if mode in ('current','group'):
        if filtered is None:
            return dict(mode=mode, issues=issues, rows=[], totals={}, rates=None, valid=False)
        # This independent experiment explicitly has no seer ability. Its
        # continuation still uses model A, never the historical public solver.
        from .model_a_public import evaluate_public_game
        from .seer_future_uniform import FuturePending
        result = evaluate_public_game({}, filtered, Rules(), Strategy(seer_disclosure='none'))
        rates = None if isinstance(result, FuturePending) else Values(result.village_win,1-result.village_win)
        if rates is None:issues.append('モデルAの計算予算に達したため勝率はPendingです。')
        rows = [dict(id=i, values={r:filtered.role_probability(i,r) for r in counts}, total=F(1)) for i in board.alive]
    else:
        rates = None
        if not mediums:
            issues.append('後段に霊能を置く試案です。霊能0人への適用は未定義です。')
        values = [{r:F(0) for r in counts} for _ in claims]
        for role in ('villager','wolf'):
            eligible = [i for i,c in enumerate(claims) if compatible(role,c)]
            if not eligible and counts[role]:
                issues.append(('市民' if role=='villager' else '人狼') + 'の前段配分候補がありません。')
            for i in eligible:
                values[i][role] = F(counts[role], len(eligible))
        rows = []
        for i, (claim, row) in enumerate(zip(claims, values),1):
            row['medium'] = 1-row['villager']-row['wolf']
            for role,q in row.items():
                label=ROLE_LABELS[role]
                if q < 0 or q > 1:
                    issues.append(f'Player {i}：{label}の配分 {q} は0〜1の範囲外です。')
                if q and not compatible(role,claim):
                    issues.append(f'Player {i}：COと両立しない{label}へ {q} が入っています。')
                if q > 0 and filtered is not None and filtered.role_probability(i,role) == 0:
                    issues.append(f'Player {i}：人数・CO・CCO制約で候補がない{label}へ {q} が入っています。')
                cco=policy.conditions(role)
                trigger='counter' in cco and role in claims or 'filled' in cco and counts[role]>0 and claims.count(role)>=counts[role]
                if q and trigger and claim!=role:
                    issues.append(f'Player {i}：CCO条件で禁止される非COの{label}へ {q} が入っています。')
            rows.append(dict(id=i,values=row,total=sum(row.values(),F(0))))
    totals={r:sum((row['values'][r] for row in rows),F(0)) for r in counts}
    for role,expected in counts.items():
        if totals.get(role,F(0)) != expected:
            issues.append(f'{role}の人数合計が配役人数と一致しません。')
    return dict(mode=mode,roles=roles,issues=issues,rows=rows,totals=totals,rates=rates,valid=not issues, co_groups=co_group_compositions(filtered) if mode=='group' and filtered else [])
