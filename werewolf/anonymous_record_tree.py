"""A public Tree projection of anonymous evaluator-owned transition records.

No private ability stages are reconstructed. A root read evaluates the existing
value once; children use its retained rows or explicitly request that evaluator.
"""
from hashlib import sha256

class AnonymousRecordTree:
    def __init__(self,node):
        self.nodes={'0':node};self.children={}
        self.snapshot=sha256(repr((node.state_identity,node.solver_identity)).encode()).hexdigest()[:24]
    def expand(self,key):
        if key in self.children:return self.children[key]
        node=self.nodes[key];b=node.read().public;rows=[]
        if not b.winner:
            if b.phase=='night':
                rows=[(None,None,row) for row in node.night()]
            else:
                for group in node.groups:
                    living=tuple(p for p in group if p in b.alive)
                    if living:rows.extend((living[0],living,row) for row in node.action(living[0]))
        edges=[]
        for index,(target,group,row) in enumerate(rows):
            child=key+'.'+str(index);self.nodes[child]=row.node
            edges.append(dict(node=child,target=target,targets=group,probability=str(row.probability),
              selection_probability=None if group is None else str(sum(node.selection_probability(p) for p in group))))
        self.children[key]=tuple(edges);return self.children[key]
    def read(self,key='0',expand=False):
        node=self.nodes[key];value=node.forecast().village_win
        if expand:self.expand(key)
        items={}
        for identity,child in self.nodes.items():
            b=child.read().public;items[identity]=dict(day=b.day,phase=b.phase,alive=list(b.alive),winner=b.winner,
              village_win=str(child.forecast().village_win),reduction=child.calculation.evaluator.reductions.get(child.owned.belief))
        return dict(node=key,snapshot=self.snapshot,village_win=str(value),items=items,
          edges=list(self.children.get(key,())),evaluation_trace=dict(owner='evaluator',representation='anonymous-owned',private_stages='not-evaluated'))
