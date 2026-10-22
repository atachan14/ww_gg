"""Persistent presentation occurrences over cached exact CalculationTree views.

A view owns a branch-local name bijection. Math nodes remain canonical and shared;
manual input adds a zero selection edge, never an evaluator child or payoff term.
"""
from copy import deepcopy
from .calculation_tree import CalculationTree,input_snapshot
from .public_convergence import transport_source
from .anonymous_night import Symbol,SymbolStep
from .ability_labels import marked
from .tree_public_updates import event_label,publication_label

class NavigationTree:
    def __init__(self,document,role_order=None):
        self.document=document;self.role_order=role_order;self.views={};self.board_numbers={};self.origins={};self.origin_owners={}
        self.snapshot=input_snapshot(document.data)
    def owner(self,key):return key.split('@',1)[0]
    def view(self,owner):
        if '@' in owner and owner not in self.views:
            base,chosen=owner.split('@',1)
            tree,_=self.view(base);row=self.document.game.history.occurrence(chosen)
            if row.parent!=base:raise ValueError('Invalid representative view')
            self.views[owner]=(tree,row.names)
        if owner not in self.views:
            row=self.document.game.history.occurrence(owner)
            self.views[owner]=(CalculationTree.from_node(self.document.game.history.state(owner).node,role_order=self.role_order),row.names)
            if row.parent is not None and row.selector.get('kind') in ('generated','published'):
                origin=row.selector.get('night',row.parent)
                previous,_=self.view(origin);local=previous.restore(row.selector['route'])
                self.origins[owner]=(previous,local);self.origin_owners[owner]=origin
                self.views[owner][0].nodes['0']['value']=previous.value(local)
                if previous.nodes[local].get('public_bundle'):self.views[owner][0].nodes[self.views[owner][0].root]['public_bundle']=True
                if previous.nodes[local].get('day_start'):self.views[owner][0].nodes[self.views[owner][0].root]['day_start']=True
        return self.views[owner]
    def parse(self,key):
        owner,local=key.split('~',1)
        tree,names=self.view(owner)
        if local not in tree.nodes:tree.read(tree.root,True)
        if local not in tree.nodes:raise KeyError(key)
        return owner,local,tree,names
    def key(self,owner,local):return owner+'~'+local
    def current_key(self):return self.key(self.document.game.current,self.view(self.document.game.current)[0].root)
    def _binding(self,owner,local):
        tree,names=self.view(owner);source=tree.nodes[local]['node'].read()
        start=bool(tree.nodes[local].get('day_start'))
        candidates=list(self.document.game.history.children(self.owner(owner)))
        for row in tuple(candidates):
            step=row.selector
            if step.get('kind')=='generated' and any(isinstance(s,dict) and 'public_arrival' in s for s in step['route']):
                candidates.extend(c for c in self.document.game.history.children(row.key) if c.selector.get('kind')=='published')
        for child in reversed(candidates):
            step=child.selector
            is_start=step.get('kind')=='generated' and any(isinstance(s,dict) and 'public_arrival' in s for s in step['route'])
            if start!=is_start or child.names!=names:continue
            if child.edge_kind!='manual_public' and self.document.game.history.state(child.key).source==source and self.document.game.history.state(child.key).node.solver_identity==tree.nodes[local]['node'].solver_identity:return child.key
        return None
    def _id(self,owner,local):
        if local is None:return None
        if local not in self.view(owner)[0].nodes:return self.key(owner,local)
        child=self._binding(owner,local)
        if child:
            tree,names=self.view(owner)
            if tree.nodes[local].get('public_bundle'):
                # Binding preserves the complete source and name map. Keep the
                # presentation sharing marker on this same history occurrence.
                bound,_=self.view(child)
                bound.nodes[bound.root]['public_bundle']=True
            return self.key(child,'0')
        return self.key(owner,local)
    def _stage(self,stage,owner,names):
        if not stage:return stage
        out=deepcopy(stage)
        def symbol(s):return None if s is None else Symbol(s['index'],tuple(sorted(names.display(p) for p in s['members'])))
        def walk(s):
            for leaf in s.get('leaves',()):
                leaf['node']=self._id(owner,leaf['node']);leaf['context_node']=self._id(owner,leaf.get('context_node'))
                for v in leaf.get('variants',()):v['node']=self._id(owner,v['node'])
            for b in s.get('branches',()):
                if b.get('symbols'):
                    sy=b['symbols'];target=symbol(sy['target']) if sy['target'] else b['value']
                    step=SymbolStep(b['kind'],symbol(sy['actor']),target,tuple(symbol(a) for a in sy['actors']))
                    from dataclasses import asdict
                    b['symbols']=dict(actor=None if step.actor is None else asdict(step.actor),target=asdict(step.target) if hasattr(step.target,'members') else None,actors=[asdict(a) for a in step.actors])
                    b['label']=step.label()
                    if b['kind']=='death_notice':b['label']='襲撃死：'+marked(tuple(names.display(p) for p in sy['target']['members']),(names.display(sy['target']['members'][0]),))
                elif b['kind'] in ('seer_target','guard_target','wolf_target'):
                    groups=b.get('actor_groups',[])
                    for g in groups:g['members']=[names.display(p) for p in g['members']];g['representatives']=[names.display(p) for p in g['representatives']]
                    owner_label='と'.join(marked(g['members'],g['representatives'])+(f"（{g['count']}人）" if g['count']>1 else '') for g in groups)
                    targets=[names.display(p) for p in b['targets']] or [names.display(b['value'])]
                    b['label']=owner_label+'が'+marked(targets,(names.display(b['value']),))+('から占い' if b['kind']=='seer_target' and len(targets)>1 else 'を占い' if b['kind']=='seer_target' else 'を護衛' if b['kind']=='guard_target' else 'を襲撃')
                if not b.get('symbols') and b['kind']=='medium_result':
                    target,color=b['value'];b['value']=(names.display(target),color)
                    b['label']=str(names.display(b['actor']))+'：'+str(names.display(target))+('黒' if color=='black' else '白')
                if not b.get('symbols') and b['kind']=='death_notice':
                    b['value']=None if b['value'] is None else names.display(b['value'])
                    b['label']='襲撃死：'+('なし' if b['value'] is None else str(b['value']))
                if not b.get('symbols'):
                    if b.get('actor') is not None:b['actor']=names.display(b['actor'])
                    b['actors']=[names.display(p) for p in b.get('actors',())]
                    b['targets']=[names.display(p) for p in b.get('targets',())]
                    b['visible_to']=[names.display(p) for p in b.get('visible_to',())]
                    if b['kind'].endswith('_target'):b['value']=names.display(b['value'])
                    for choice in b.get('joint_choices',()):
                        choice['actors']=[names.display(p) for p in choice['actors']];choice['target']=names.display(choice['target'])
                walk(b['children'])
                for image in b.get('images',()):
                    image['nodes']=[self._id(owner,n) for n in image['nodes']]
                    if image.get('children'):walk(image['children'])
        walk(out);return out
    def _raw_summary(self,tree,local):
        from .information_set_forecast import Pending
        try:return tree.summary(local,True)
        except Pending as exc:
            from .tree_public_updates import state_summary
            source=tree.nodes[local]['node'].read()
            result=state_summary(source.public,source.private,local,tree.data.game_data,tree.role_order,past=source.past)
            result.update(snapshot_only=False,public_current=True,actions=None,compositions=[],pending=exc.reason,stage_roles=dict(seers=tree.data.game_data.seers))
            return result

    def _summary(self,owner,local,raw):
        tree,names=self.view(owner);row=self.document.game.history.occurrence(self.owner(owner))
        # A recorded action is an explicit detail request. Restore its real
        # edges before presenting a certificate-only stop, so Current stays
        # reachable and its parent is not mistaken for the pruned endpoint.
        if local==tree.root and raw.get('actions') is None and any(c.selector.get('requested') is not None for c in self.document.game.history.children(self.owner(owner))):
            tree.expand(local);raw=tree.summary(local,True)
        out=deepcopy(raw);out.pop('items',None);out['node']=self.key(owner,local)
        out['board_number']=self.board_numbers.setdefault(out['node'],len(self.board_numbers))
        s=transport_source(tree.nodes[local]['node'].read(),names.forward);b=s.public
        from dataclasses import asdict
        out.update(alive=list(b.alive),public_claims=list(b.claims),history=[asdict(e) for e in b.history],reports=[asdict(r) for r in s.past],navigation_owner=owner,navigation_depth=self.depth(owner,out['column_day'],out['column_phase']),navigation_phase_updates=self.phase_updates())
        for player in out['players']:player['player']=names.display(player['player'])
        for part in out.get('compositions',()):part['node']=self._id(owner,part['node'])
        for action in out.get('actions') or ():
            action['targets']=[names.display(p) for p in action['targets']]
            for m in action['members']:m['target']=names.display(m['target'])
            for branch in action['branches']:
                branch['node']=self._id(owner,branch['node'])
                for v in branch.get('variants',()):v['node']=self._id(owner,v['node']);v['target']=names.display(v['target'])
        out['night_stages']=self._stage(out.get('night_stages'),owner,names)
        if out.get('day_arrival'):
            arrival=out['day_arrival'];arrival['id']=self._id(owner,arrival.get('node',arrival['id']));arrival['state']['node']=arrival['id']
            arrival['state']['alive']=[names.display(p) for p in arrival['state']['alive']]
            for update in arrival['updates']:update['node']=self._id(owner,update['node'])
        if out.get('public_updates'):
            for update in out['public_updates']:update['node']=self._id(owner,update['node'])
        if local==tree.root and owner in self.origins:
            previous,previous_local=self.origins[owner]
            if previous.nodes[previous_local].get('public_updates'):
                out['day_start']=True;out['actions']=[]
                out['public_updates']=[{**u,'node':self._id(self.origin_owners[owner],u['node'])} for u in previous.nodes[previous_local]['public_updates']]
        if local==tree.root and owner in self.origins and not out.get('day_arrival'):
            previous,previous_local=self.origins[owner]
            if previous.nodes[previous_local].get('day_arrival'):
                original=self._summary(self.origin_owners[owner],previous_local,previous.summary(previous_local,True))
                out['day_arrival']=original.get('day_arrival')
        if local==tree.root and '@' not in owner:
            out['navigation_occurrence']=owner
            if row.edge_kind in ('manual_public','recorded_input'):
                before=self.document.game.history.state(row.parent).source
                out['navigation_label']=event_label(row.selector['events']) if row.edge_kind=='recorded_input' else publication_label(transport_source(before,names.forward),s)
            out['manual_updates']=[dict(node=self.key(c.key,'0'),probability=None if c.edge_kind=='recorded_input' else '0') for c in self.document.game.history.children(self.owner(owner)) if c.edge_kind in ('manual_public','recorded_input')]
            for child in reversed(self.document.game.history.children(self.owner(owner))):
                step=child.selector
                if step.get('requested') is None:continue
                requested=names.display(step['requested'])
                for action in out.get('actions') or ():
                    if requested in action['targets']:
                        action['representative']=requested
                        branch_owner=owner+'@'+child.key;self.views[branch_owner]=(tree,child.names)
                        original=next(a for a in raw['actions'] if step['target'] in a['targets'])
                        for branch,canonical in zip(action['branches'],original['branches']):
                            branch['node']=self._id(branch_owner,canonical['node'])
                            for v,cv in zip(branch.get('variants',()),canonical.get('variants',())):v['node']=self._id(branch_owner,cv['node'])
                break
        return out
    def depth(self,owner,day=None,phase=None):
        owner=self.owner(owner);rows=self.document.game.history.path(owner)
        current=self.document.game.history.state(owner).source.public
        day=current.day if day is None else day;phase=current.phase if phase is None else phase
        total=0
        for row in rows:
            board=self.document.game.history.state(row.key).source.public
            update=row.edge_kind in ('manual_public','recorded_input') or row.selector is not None and row.selector.get('kind')=='published'
            if update and (board.day,board.phase)==(day,phase):total+=1
        return total
    def phase_updates(self):
        totals={}
        for row in self.document.game.history.export():
            b=self.document.game.history.state(row['key']).source.public
            phase=(b.day-1)*2+(b.phase=='night');totals[str(phase)]=max(totals.get(str(phase),0),self.depth(row['key']))
        return totals
    def read(self,key=None,expand=False,analysis=False):
        owner,local,tree,names=self.parse(key or self.key(self.document.game.history.root,'0'))
        from .information_set_forecast import Pending
        try:raw=tree.read(local,expand)
        except Pending:
            raw=self._raw_summary(tree,local);raw['items']={}
        out=self._summary(owner,local,raw);items={}
        for id,r in raw['items'].items():items[self.key(owner,id)]=self._summary(owner,id,r)
        for alternate in tuple(self.views):
            if alternate.startswith(self.owner(owner)+'@'):
                for id,r in raw['items'].items():items[self.key(alternate,id)]=self._summary(alternate,id,r)
        # Include every explicitly navigated occurrence, without calculating its
        # descendants or opening hidden composition accordions.
        for row in self.document.game.history.export():
            anchor=row['key'];view,_=self.view(anchor)
            k=self.key(anchor,view.root);items[k]=self._summary(anchor,view.root,self._raw_summary(view,view.root))
        out['items']=items;out.update(snapshot=self.snapshot,current_node=self.current_key(),navigation_revision=self.document.revision,display_path=[self.key(r.key,'0') for r in self.document.game.history.path(self.document.game.current)])
        if analysis:
            origin=self.origins.get(owner) if local==tree.root else None
            out['distribution']=(origin[0].distribution(origin[1],names=names) if origin else tree.distribution(local,names=names))
        return out
    def select(self,key):
        owner,local,tree,names=self.parse(key)
        if not tree.public_current(local):raise ValueError('Choose a public Board')
        game=self.document.game;game.move(self.owner(owner));route=tree.route(local)
        if '@' in owner:
            chosen=self.document.game.history.occurrence(owner.split('@',1)[1]);step=chosen.selector
            if not route or not isinstance(route[0],(tuple,list)):raise ValueError('Representative route requires its initial action')
            first=route.pop(0)
            game.action(game.occurrence.names.display(step['requested']),outcome=first[2])
        if route:game.generated(route)
        return game.occurrence
