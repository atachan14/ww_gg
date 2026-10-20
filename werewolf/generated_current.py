"""Exact generated Current adapter; no posterior is written into saved evidence.

The durable cursor is a bounded sequence of common generator selectors. Public
rows use Q. The original node/exported recipe retains physical P and all secrets.
The transient Game projection is for existing declaration/history UI only.
"""
from dataclasses import dataclass,asdict,replace
from hashlib import sha256
import json
from .board_flow import BoardData,RoleState
from .board_roles import role_rates,role_summary
from .exact import Progress

@dataclass(frozen=True)
class GeneratedRoleState(RoleState):
    node:object=None
    def forecast(self,**limits):return self.node.forecast()
    def private(self,*args,**kwargs):
        raise ValueError('Choose a generated personal view through its common node generator')

class GeneratedCurrent:
    def __init__(self,tree,key):
        self.tree=tree;self.key=key;self.route=tree.route(key)
        self.identity=sha256(json.dumps([tree.snapshot,self.route],separators=(',',':')).encode()).hexdigest()[:24]
        self.node=tree.nodes[key]['node']
        # Cold reconstruction uses the existing root/evidence generators and
        # never imports a calculated posterior as an authoritative prior.
        self.source=self.node.export_request().roles()
        b=self.source.public;game=tree.data.to_game()
        base={k:game[k] for k in ('policy','claim_policy','seer_options','strategy_ui','result_disclosure_model') if k in game}
        history=[{**base,'target':e.target,'claims':list(b.claims)} for e in b.history]
        view={**game,'history':history,'claims':list(b.claims),'selection':None,
              'seer_inputs':[dict(day=r.published_day,reporter=r.player,target=r.target,color=r.color) for r in self.source.past],
              'reports':[asdict(r) for r in b.reports], '_generated_current_identity':self.identity}
        view.pop('public_log',None);view.pop('public_draft',None)
        data=BoardData.from_game(view,game_data=tree.data.game_data,runtime=tree.data.runtime)
        self.data=replace(data,facts=replace(data.facts,board_id=self.identity))
        progress=Progress.initial(b);groups,counts=role_summary(progress)
        self.roles=GeneratedRoleState(self.data,progress,role_rates(progress),groups,counts,self.node)
        original=tree.data.roles();original_value=original.forecast()
        from .seer_future_uniform import FuturePending
        if isinstance(original_value,FuturePending):
            from .information_set_forecast import Pending
            raise Pending(original_value.reason)
        from .exact import Values
        self.origin_cumulative=original.progress.total_values(Values(original_value.village_win,1-original_value.village_win)) if not original.progress.finished else original.progress.total_values()
    @property
    def metadata(self):return dict(node=self.key,identity=self.identity,snapshot=self.tree.snapshot)
