"""Current cursor/controller over one Day1-rooted navigational history.

Actions and observations always call existing exact node generators. The cursor
has no effect on solver caching or probabilities of previously generated states.
"""
from fractions import Fraction as F
from .navigation_history import NavigationHistory,NameMap
from .manual_public_input import PublicInput
from .seer_acquisition import SeerReport

class NavigationGame:
    def __init__(self,node):
        self.history=NavigationHistory(node);self.current=self.history.root
        self._forward={}
    @property
    def occurrence(self):return self.history.occurrence(self.current)
    @property
    def node(self):return self.history.state(self.current).node
    def move(self,key):
        self.history.occurrence(key);self.current=key;return self.occurrence
    def back(self):
        parent=self.occurrence.parent
        if parent is not None:self._forward[parent]=self.current;self.current=parent
        return self.occurrence
    def forward(self,key=None):
        target=key or self._forward.get(self.current)
        if target is not None:
            if self.history.occurrence(target).parent!=self.current:raise ValueError('Forward occurrence must be a child')
            self.current=target
        return self.occurrence
    def _commit(self,node,selector,*,names=None,kind='strategy',weight=F(1),settled=None):
        parent=self.current
        row=self.history.append(parent,node,selector,names=names,kind=kind,selection_weight=weight,settled=settled)
        self._forward[parent]=row.key;self.current=row.key;return row
    def action(self,display_target,*,outcome=None,selection_weight=None,names=None):
        parent=self.occurrence;requested=parent.names.canonical(display_target)
        target,lift=self.node.representative_action(requested)
        mapping=lift.then(parent.names)
        if names is not None and names!=mapping:raise ValueError('Saved action mapping differs from constructed transport')
        names=mapping
        selection_weight=self.node.selection_probability(target) if selection_weight is None else selection_weight
        rows=self.node.action(target)
        if outcome is not None:
            if type(outcome)is not int or not 0<=outcome<len(rows):raise ValueError('Invalid public outcome')
            child=rows[outcome].node;selector=dict(kind='action',target=target,requested=requested,outcome=outcome)
            return self._commit(child,selector,names=names,weight=selection_weight)
        # Ordinary Footer accumulates settled probability while exposing the one
        # ongoing public Board, exactly as Progress.advance does.
        village,wolf=parent.settled_village,parent.settled_wolf;ongoing=[]
        for index,row in enumerate(rows):
            winner=row.node.read().public.winner
            if winner=='village':village+=parent.active_mass*row.probability
            elif winner=='wolf':wolf+=parent.active_mass*row.probability
            else:ongoing.append((index,row.node))
        if len(ongoing)>1:raise ValueError('Footer requires a public observation to distinguish ongoing Boards')
        index,child=ongoing[0] if ongoing else (0,rows[0].node)
        return self._commit(child,dict(kind='advance',target=target,requested=requested),names=names,weight=selection_weight,settled=(village,wolf))
    def public_input(self,claims,reports=()):
        parent=self.occurrence;names=parent.names
        canonical_claims=tuple(claims[names.display(p)-1] for p in range(1,len(names.forward)+1))
        canonical_reports=tuple(SeerReport(r.acquired_day,r.published_day,names.canonical(r.player),names.canonical(r.target),r.color) for r in reports)
        evidence=PublicInput(canonical_claims,canonical_reports)
        q,p,child=self.node.observe_public_input(evidence)
        selector=dict(kind='public_input',claims=list(canonical_claims),reports=[dict(acquired_day=r.acquired_day,published_day=r.published_day,player=r.player,target=r.target,color=r.color) for r in canonical_reports])
        return self._commit(child,selector,kind='manual_public',weight=F())
    def export(self):return dict(rows=self.history.export(),current=self.current,forward=dict(self._forward))
    @classmethod
    def restore(cls,node,document):
        game=cls(node)
        for row in document['rows'][1:]:
            game.move(row['parent']);step=row['selector'];kind=step['kind'];names=game.occurrence.names
            if kind=='public_input':
                claims=tuple(step['claims'][names.canonical(p)-1] for p in range(1,len(names.forward)+1))
                reports=tuple(SeerReport(r['acquired_day'],r['published_day'],names.display(r['player']),names.display(r['target']),r['color']) for r in step['reports'])
                added=game.public_input(claims,reports)
            else:added=game.action(names.display(step.get('requested',step['target'])),outcome=step.get('outcome') if kind=='action' else None,names=NameMap(tuple(row['names'])))
            if added.key!=row['key']:raise ValueError('Invalid history order')
        game.current=document['current'];game.history.occurrence(game.current);game._forward=dict(document.get('forward',{}));return game
