"""Marginal-only experiment on an independent initial board."""
from fractions import Fraction as F
from .exact import ClaimPolicy, condition_claims, initial_board, build_tree, evaluate_tree, Rules, Strategy


def compare_initial(citizens, mediums, wolves, claims, policy=ClaimPolicy(), mode='trial'):
    board = initial_board(citizens + mediums + wolves, wolves, mediums)
    if len(claims) != board.player_count or any(c not in ('latent','villager','medium','wolf') for c in claims):
        raise ValueError('CO入力を確認してください。')
    if mode not in ('current','trial'):
        raise ValueError('比較モードを確認してください。')
    counts = {'villager': citizens, 'medium': mediums, 'wolf': wolves}
    def compatible(role, claim):
        return claim == 'latent' or role == claim or role == 'wolf'
    issues = []
    filtered = None
    try:
        filtered = condition_claims(board, tuple(claims), policy)
    except ValueError as exc:
        issues.append(str(exc))
    if mode == 'current':
        if filtered is None:
            return dict(mode=mode, issues=issues, rows=[], totals={}, rates=None, valid=False)
        root = build_tree(filtered, Rules(), Strategy())
        rates = evaluate_tree(root, Strategy()).board_value(root)
        rows = [dict(id=i, values={r:filtered.role_probability(i,r) for r in counts}, total=F(1)) for i in board.alive]
    else:
        rates = None
        if not mediums:
            issues.append('後段に霊能を置く試案です。霊能0人への適用は未定義です。')
        values = [{r:F(0) for r in counts} for _ in claims]
        for role in ('villager','wolf'):
            eligible = [i for i,c in enumerate(claims) if compatible(role,c)]
            if not eligible and counts[role]:
                issues.append(('市民' if role=='villager' else '狼') + 'の前段配分候補がありません。')
            for i in eligible:
                values[i][role] = F(counts[role], len(eligible))
        rows = []
        for i, (claim, row) in enumerate(zip(claims, values),1):
            row['medium'] = 1-row['villager']-row['wolf']
            for role,q in row.items():
                label={'villager':'市民','medium':'霊能','wolf':'狼'}[role]
                if q < 0 or q > 1:
                    issues.append(f'Player {i}：{label}の配分 {q} は0〜1の範囲外です。')
                if q and not compatible(role,claim):
                    issues.append(f'Player {i}：COと両立しない{label}へ {q} が入っています。')
                if q > 0 and filtered is not None and filtered.role_probability(i,role) == 0:
                    issues.append(f'Player {i}：人数・CO・CCO制約で候補がない{label}へ {q} が入っています。')
                cco=getattr(policy,role)
                trigger=cco=='counter' and role in claims or cco=='filled' and counts[role]>0 and claims.count(role)>=counts[role]
                if q and trigger and claim!=role:
                    issues.append(f'Player {i}：CCO条件で禁止される非COの{label}へ {q} が入っています。')
            rows.append(dict(id=i,values=row,total=sum(row.values(),F(0))))
    totals={r:sum((row['values'][r] for row in rows),F(0)) for r in counts}
    for role,expected in counts.items():
        if totals.get(role,F(0)) != expected:
            issues.append(f'{role}の人数合計が配役人数と一致しません。')
    return dict(mode=mode,issues=issues,rows=rows,totals=totals,rates=rates,valid=not issues)
