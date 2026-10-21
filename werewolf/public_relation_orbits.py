"""Initial public action orbits of a coloured relational forest.

These are rooted *action* orbits, not independently exchangeable populations.
A rooted tree code retains directed reporter/target incidence and publication
batch order. Equal codes construct an isomorphism by matching equal child codes;
no labelled assignments, permutation search or payoff comparisons are needed.
Cyclic public relations conservatively keep their component's named actions.
Only the immutable initial saved law may register these orbits. Descendants use
their existing refined population groups; they never inherit these action orbits.
"""

def initial_orbits(game):
    n=game['players'];single=tuple((p,) for p in range(1,n+1))
    if game.get('history') or game.get('mediums') or game.get('hunters'):return single
    claims=game.get('claims',['latent']*n)
    marks=[[] for _ in claims];edges={};times={}
    for order,batch in enumerate(game.get('public_log',{}).get('batches',())):
        stamp=(batch.get('slot',0),batch.get('mode','single'),order)
        for event in batch.get('events',()):
            player=event['player']
            if event['kind']=='co':marks[player-1].append((stamp,event['role']))
            else:times[(event['kind'],player,event['day'],event['target'])]=stamp
    for row in game.get('seer_inputs',()):
        a,b=row['reporter'],row['target']
        if a==b:return single
        pair=tuple(sorted((a,b)))
        edges.setdefault(pair,[]).append((a,b,('seer',row['day'],row['color'],times.get(('seer',a,row['day'],b),(-1,'legacy',0)))))
    adjacency={p:[] for p in range(1,n+1)}
    for (a,b),records in edges.items():
        adjacency[a].append((b,tuple(sorted((('out' if reporter==a else 'in',label) for reporter,target,label in records),key=repr))))
        adjacency[b].append((a,tuple(sorted((('out' if reporter==b else 'in',label) for reporter,target,label in records),key=repr))))
    cyclic=set();seen=set()
    for root in adjacency:
        if root in seen:continue
        component=set();stack=[root];degree=0
        while stack:
            p=stack.pop()
            if p in component:continue
            component.add(p);degree+=len(adjacency[p]);stack.extend(q for q,label in adjacency[p])
        seen.update(component)
        if degree//2>=len(component):cyclic.update(component)
    def code(p,parent=None):
        return (claims[p-1],tuple(marks[p-1]),tuple(sorted(((label,code(q,p)) for q,label in adjacency[p] if q!=parent),key=repr)))
    groups={}
    for p in adjacency:groups.setdefault(('fixed',p) if p in cyclic else ('tree',code(p)),[]).append(p)
    return tuple(tuple(group) for group in groups.values())
