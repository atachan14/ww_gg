"""Current cursor/controller over one Day1-rooted navigational history.

Actions and observations always call existing exact node generators. The cursor
has no effect on solver caching or probabilities of previously generated states.
"""
from fractions import Fraction as F
from .navigation_history import NavigationHistory,NameMap
from .manual_public_input import PublicInput
from .seer_acquisition import SeerReport

class NavigationGame:
    def __init__(self,node,*,names=None):
        self.history=NavigationHistory(node,names=names);self.current=self.history.root
        self._forward={}
    @property
    def occurrence(self):return self.history.occurrence(self.current)
    @property
    def node(self):return self.history.state(self.current).node
    def move(self,key):
        row=self.history.occurrence(key)
        if row.parent is not None:self._forward[row.parent]=key
        self.current=key;return self.occurrence
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
    def action(self,display_target,*,outcome=None,selection_weight=None,names=None,_replay=False,_saved_target=None):
        parent=self.occurrence;requested=parent.names.canonical(display_target)
        target,lift=self.node.representative_action(requested)
        mapping=lift.then(parent.names)
        if _replay and _saved_target is not None:
            # Old journals may explicitly name an action before its orbit was
            # supported. Replay that literal generator, never reinterpret its
            # stored target/map as a different physical history.
            literal=(_saved_target==requested and names==parent.names)
            canonical=(_saved_target==target and names==mapping)
            if not (literal or canonical):raise ValueError('Saved action mapping differs from constructed transport')
            target=_saved_target
        elif names is not None and names!=mapping:raise ValueError('Saved action mapping differs from constructed transport')
        else:names=mapping
        selection_weight=self.node.selection_probability(target) if selection_weight is None else selection_weight
        rows=self.node.action(target)
        if outcome is not None:
            if type(outcome)is not int or not 0<=outcome<len(rows):raise ValueError('Invalid public outcome')
            child=rows[outcome].node;selector=dict(kind='action',target=target,requested=requested,outcome=outcome)
            winner=child.read().public.winner
            settled=(parent.settled_village+parent.active_mass*int(winner=='village'),parent.settled_wolf+parent.active_mass*int(winner=='wolf'))
            if not _replay:
                old=next((r for r in self.history.children(self.current) if r.selector==selector and r.names==names),None)
                if old:return self.move(old.key)
            return self._commit(child,selector,names=names,weight=selection_weight,settled=settled)
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
        selector=dict(kind='advance',target=target,requested=requested)
        if not _replay:
            old=next((r for r in self.history.children(self.current) if r.selector==selector and r.names==names),None)
            if old:return self.move(old.key)
        return self._commit(child,selector,names=names,weight=selection_weight,settled=(village,wolf))
    def fork(self):
        from copy import copy
        game=copy(self);game.history=copy(self.history)
        for name in ('_states','_by_source','_occurrences'):setattr(game.history,name,dict(getattr(self.history,name)))
        game.history._children={key:list(rows) for key,rows in self.history._children.items()}
        game._forward=dict(self._forward);return game

    def generated(self,route):
        """Select public continuation occurrences through common Tree recipes."""
        from .calculation_tree import CalculationTree
        pending=[]
        for step in route:
            pending.append(step);tree=CalculationTree.from_node(self.node);key=tree.restore(pending)
            child=tree.nodes[key]['node'];before=self.node.read();after=child.read()
            visible=((before.public.day,before.public.phase,before.public.alive)!=(after.public.day,after.public.phase,after.public.alive) or before.public.history!=after.public.history or before.past!=after.past or before.public.reports!=after.public.reports or before.public.claims!=after.public.claims)
            if not visible:continue
            if not tree.public_current(key):continue
            arrival=tree.nodes[key].get('day_arrival')
            if arrival and arrival.get('node'):
                night=self.current;before_key=arrival['node'];before=tree.nodes[before_key]['node']
                self.generated(tree.route(before_key))
                self.published(night,tree.route(key));pending=[];continue
            selector=dict(kind='generated',route=tree.route(key))
            old=next((r for r in self.history.children(self.current) if r.selector==selector),None)
            if old:self.move(old.key)
            else:
                parent=self.occurrence;winner=after.public.winner
                settled=(parent.settled_village+parent.active_mass*int(winner=='village'),parent.settled_wolf+parent.active_mass*int(winner=='wolf'))
                self._commit(child,selector,settled=settled)
            pending=[]
        if pending:raise ValueError('Choose a public Board rather than a private stage')
        return self.occurrence

    def replay_generated(self,route):
        """One persisted occurrence; new UI staging never rewrites old history."""
        from .calculation_tree import CalculationTree
        tree=CalculationTree.from_node(self.node);key=tree.restore(route)
        if not tree.public_current(key):raise ValueError('Choose a public Board')
        child=tree.nodes[key]['node'];parent=self.occurrence;winner=child.read().public.winner
        settled=(parent.settled_village+parent.active_mass*int(winner=='village'),parent.settled_wolf+parent.active_mass*int(winner=='wolf'))
        return self._commit(child,dict(kind='generated',route=tree.route(key)),settled=settled)

    def published(self,night,route):
        from .calculation_tree import CalculationTree
        if night not in {r.key for r in self.history.path(self.current)}:raise ValueError('Publication origin must be an ancestor')
        tree=CalculationTree.from_node(self.history.state(night).node);key=tree.restore(route)
        if not tree.public_current(key):raise ValueError('Choose a public update')
        selector=dict(kind='published',night=night,route=tree.route(key))
        old=next((r for r in self.history.children(self.current) if r.selector==selector),None)
        return self.move(old.key) if old else self._commit(tree.nodes[key]['node'],selector)

    def recorded(self,game,events):
        from .board_flow import BoardData
        from .closed_calculation import ClosedCalculation
        root=self.history.state(self.history.root).node.data
        data=BoardData.from_game(game,game_data=root.game_data,runtime=root.runtime)
        if data.game_data!=root.game_data or game.get('history'):raise ValueError('Initial recorded inputs require unchanged game rules')
        child=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True).root
        return self._commit(child,dict(kind='recorded',game=game,events=events),kind='recorded_input',weight=F())

    def observed(self,target,reports=(),medium=()):
        """Replay a supported saved public observation without reseeding its law."""
        mass,child=self.node.observe(target)
        if reports or medium:_,child=child.observe_reports(tuple(reports),tuple(medium))
        return self._commit(child,dict(kind='observed',target=target,reports=[dict(acquired_day=r.acquired_day,published_day=r.published_day,player=r.player,target=r.target,color=r.color) for r in reports],medium=[dict(day=r.day,reporter=r.reporter,target=r.target,color=r.color) for r in medium]))

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
    def restore(cls,node,document,*,names=None):
        game=cls(node,names=names)
        for row in document['rows'][1:]:
            game.move(row['parent']);step=row['selector'];kind=step['kind'];names=game.occurrence.names
            if kind=='public_input':
                claims=tuple(step['claims'][names.canonical(p)-1] for p in range(1,len(names.forward)+1))
                reports=tuple(SeerReport(r['acquired_day'],r['published_day'],names.display(r['player']),names.display(r['target']),r['color']) for r in step['reports'])
                added=game.public_input(claims,reports)
            elif kind=='generated':added=game.replay_generated(step['route'])
            elif kind=='published':added=game.published(step['night'],step['route'])
            elif kind=='recorded':added=game.recorded(step['game'],step['events'])
            elif kind=='observed':
                from .exact import MediumReport
                added=game.observed(step['target'],tuple(SeerReport(**r) for r in step['reports']),tuple(MediumReport(**r) for r in step['medium']))
            else:added=game.action(names.display(step.get('requested',step['target'])),outcome=step.get('outcome') if kind=='action' else None,names=NameMap(tuple(row['names'])),_replay=True,_saved_target=step['target'])
            if added.key!=row['key']:raise ValueError('Invalid history order')
        # Saved files are evidence recipes, not authority to inject weights/maps.
        import json
        if json.dumps(game.history.export(),sort_keys=True)!=json.dumps(document['rows'],sort_keys=True):raise ValueError('Saved navigation differs from exact replay')
        game.current=document['current'];game.history.occurrence(game.current)
        forward=dict(document.get('forward',{}))
        for parent,child in forward.items():
            game.history.occurrence(parent)
            if game.history.occurrence(child).parent!=parent:raise ValueError('Invalid saved forward path')
        game._forward=forward;return game
