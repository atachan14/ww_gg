"""Optional public Tree wire projection; full summaries remain the default API."""
DETAIL_FIELDS=frozenset(('players','rules','policy','method','viewpoint'))

def public_tree_payload(row):
    return {key:value for key,value in row.items() if key not in DETAIL_FIELDS}
