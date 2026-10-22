"""Append-only navigational occurrences over immutable exact solver inputs.

The history is not an evaluator: adding manual edges cannot change a solver's
policy or expectation. A repeated state may have several different parents,
selectors and display bijections. Only occurrences own those navigation facts.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import json

@dataclass(frozen=True)
class NameMap:
    """Canonical -> displayed names; all fields use this one bijection."""
    forward:tuple
    def __post_init__(self):
        object.__setattr__(self,'forward',tuple(self.forward))
        if any(type(p)is not int for p in self.forward) or tuple(sorted(self.forward))!=tuple(range(1,len(self.forward)+1)):raise ValueError('Player mapping must be a bijection')
    @classmethod
    def identity(cls,n):return cls(tuple(range(1,n+1)))
    def display(self,canonical):
        if type(canonical)is not int or not 1<=canonical<=len(self.forward):raise ValueError('Invalid player')
        return self.forward[canonical-1]
    def canonical(self,displayed):
        if type(displayed)is not int or not 1<=displayed<=len(self.forward):raise ValueError('Invalid player')
        return self.forward.index(displayed)+1
    def then(self,other):
        if len(self.forward)!=len(other.forward):raise ValueError('Player mapping size mismatch')
        return NameMap(tuple(other.display(p) for p in self.forward))

@dataclass(frozen=True)
class SolverState:
    key:str
    node:object
    @property
    def source(self):return self.node.read()
    def cold(self):return self.node.export_request().roles()

@dataclass(frozen=True)
class Occurrence:
    key:str
    parent:str|None
    state:str
    _selector:str
    names:NameMap
    edge_kind:str
    selection_weight:F
    settled_village:F=F()
    settled_wolf:F=F()
    @property
    def active_mass(self):return 1-self.settled_village-self.settled_wolf
    @property
    def selector(self):return json.loads(self._selector)

class NavigationHistory:
    def __init__(self,node):
        self._states={};self._by_source={};self._occurrences={};self._children={}
        state=self._intern(node)
        self.root=self._append(None,state,None,NameMap.identity(node.read().public.player_count),'root',F(1)).key
    def _intern(self,node):
        from .public_convergence import state_key
        source=(state_key(node.read()),node.solver_identity)
        if source in self._by_source:return self._by_source[source]
        key='s'+str(len(self._states));self._states[key]=SolverState(key,node);self._by_source[source]=key;return key
    def _append(self,parent,state,selector,names,kind,weight,settled=(F(),F())):
        key='h'+str(len(self._occurrences));row=Occurrence(key,parent,state,json.dumps(selector,sort_keys=True,separators=(',',':'),allow_nan=False),names,kind,F(weight),*settled)
        self._occurrences[key]=row;self._children[key]=[]
        if parent is not None:self._children[parent].append(key)
        return row
    def append(self,parent,node,selector,*,names=None,kind='strategy',selection_weight=F(1),settled=None):
        owner=self.occurrence(parent)
        if kind not in ('strategy','manual_public','recorded_input'):raise ValueError('Unknown navigation edge kind')
        weight=F(selection_weight)
        if not 0<=weight<=1 or kind in ('manual_public','recorded_input') and weight!=0:raise ValueError('Manual input must have zero strategy selection weight')
        mapping=owner.names if names is None else names
        if len(mapping.forward)!=node.read().public.player_count:raise ValueError('Player mapping size mismatch')
        # Append only after the caller's common generator accepted the input.
        totals=(owner.settled_village,owner.settled_wolf) if settled is None else tuple(F(p) for p in settled)
        if len(totals)!=2 or any(p<0 for p in totals) or sum(totals)>1:raise ValueError('Invalid settled mass')
        return self._append(parent,self._intern(node),selector,mapping,kind,weight,totals)
    def occurrence(self,key):return self._occurrences[key]
    def state(self,key):return self._states[self.occurrence(key).state]
    def children(self,key):return tuple(self._occurrences[k] for k in self._children[key])
    def path(self,key):
        result=[]
        while key is not None:
            row=self.occurrence(key);result.append(row);key=row.parent
        return tuple(reversed(result))
    def recipe(self,key):return tuple(row.selector for row in self.path(key)[1:])
    def export(self):
        return tuple(dict(key=row.key,parent=row.parent,selector=row.selector,names=list(row.names.forward),edge_kind=row.edge_kind,selection_weight=str(row.selection_weight),settled=[str(row.settled_village),str(row.settled_wolf)]) for row in self._occurrences.values())
    @classmethod
    def restore(cls,node,rows,resolve):
        history=cls(node)
        if not rows or rows[0]['key']!=history.root or rows[0]['parent'] is not None:raise ValueError('Invalid history root')
        for row in rows[1:]:
            parent=history.occurrence(row['parent']);child=resolve(history.state(parent.key).node,row['selector'])
            added=history.append(parent.key,child,row['selector'],names=NameMap(tuple(row['names'])),kind=row['edge_kind'],selection_weight=F(row['selection_weight']),settled=row.get('settled'))
            if added.key!=row['key']:raise ValueError('Invalid occurrence order')
        return history
