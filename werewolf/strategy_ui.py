"""Thin CO editor adapter. Numerical policies remain ClaimPolicy values."""
from werewolf.exact import ClaimPolicy, VILLAGE_ROLES

def co_editor(policy):
    p = ClaimPolicy(**policy)
    common = ['filled']
    return {'common': common, 'roles': {r: {'local': [x for x in p.conditions(r) if x not in common], 'disabled': [x for x in common if x not in p.conditions(r)]} for r in VILLAGE_ROLES}}

def resolve_co_editor(data):
    if not isinstance(data, dict) or set(data) != {'common', 'roles'}:
        raise ValueError('CO設定の入力を確認してください。')
    def items(v):
        if not isinstance(v, list) or not ClaimPolicy.valid_conditions(v):
            raise ValueError('CO設定の入力を確認してください。')
        return sorted(v)
    common = items(data['common'])
    if not isinstance(data['roles'], dict) or set(data['roles']) != set(VILLAGE_ROLES):
        raise ValueError('CO設定の役職を確認してください。')
    result = {'wolf': 'none'}
    normalized = {'common': common, 'roles': {}}
    for role in VILLAGE_ROLES:
        row = data['roles'][role]
        if not isinstance(row, dict) or set(row) != {'local', 'disabled'}:
            raise ValueError('CO設定の入力を確認してください。')
        local, disabled = items(row['local']), items(row['disabled'])
        if set(local) & set(common) or not set(disabled) <= set(common):
            raise ValueError('CO設定の継承を確認してください。')
        result[role] = sorted((set(common) - set(disabled)) | set(local))
        normalized['roles'][role] = {'local': local, 'disabled': disabled}
    return normalized, result
