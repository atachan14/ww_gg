"""Development-only DEFAULT MAX decision-order experiments.

Rows are unnormalised joint Q/P masses by complete report and named target.
No production state, cache key, or policy is changed by these experiments.
"""
from collections import defaultdict
from fractions import Fraction as F


def face(scores):
    best = max(scores.values())
    return tuple(t for t, score in scores.items() if score == best)


def moment_value(events):
    """Choose each public Q face first, then sum private P contributions."""
    buckets = defaultdict(lambda: defaultdict(F))
    for public, private in events:
        chosen = face(public)
        for t, mass in private.items():
            buckets[chosen][t] += mass
    return sum((sum((rows[t] for t in chosen), F()) / len(chosen)
                for chosen, rows in buckets.items()), F()), dict(buckets)


def posterior_reference(events):
    """Deliberately normalized, ungrouped independent reconstruction."""
    total = F()
    for q, p in events:
        qm, pm = sum(q.values(), F()), sum(p.values(), F())
        assert qm > 0
        qs = {t: x / qm for t, x in q.items()}
        best = max(qs.values())
        chosen = [t for t in qs if qs[t] == best]
        if pm:
            ps = {t: x / pm for t, x in p.items()}
            total += pm * sum((ps[t] for t in chosen), F()) / len(chosen)
    return total


def oracle_moments(source, rows):
    """Convert independently enumerated final-three reports to raw moments."""
    assert len(source.public.alive) == 3
    events = []
    for event in rows.values():
        q = {t: sum((mass for (roles, *_), mass in event['Q'].items()
                     if roles[0] & (1 << (t-1))), F()) * event['q']
             for t in source.public.alive}
        p = {t: sum((mass for (roles, *_), mass in event['P'].items()
                     if roles[0] & (1 << (t-1))), F()) * event['p']
             for t in source.public.alive}
        assert sum(q.values(), F()) == event['q']
        events.append((q, p))
    return events
