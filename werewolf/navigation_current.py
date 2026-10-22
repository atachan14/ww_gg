"""Ordinary Board projection of an occurrence; never a reconstructed prior.

The immutable node supplies Q/P and values. Transient Game fields exist only for
existing Board widgets, and are inverse-mapped by NavigationGame on submission.
"""
from dataclasses import dataclass,asdict,replace
from fractions import Fraction as F
from .board_flow import BoardData,RoleState
from .board_roles import role_rates,role_summary
from .exact import Progress,BoardOutcome
from .forecast_result import Forecast
from .public_convergence import transport_source

@dataclass(frozen=True)
class NavigationRoleState(RoleState):
    navigation:object=None
    def forecast(self,**limits):
        row=self.navigation.occurrence
        from .information_set_forecast import Pending
        from .seer_future_uniform import FuturePending
        try:value=self.navigation.node.forecast()
        except Pending as exc:return FuturePending(exc.reason)
        return Forecast(value.village_win,tuple((row.names.display(p),v) for p,v in value.action_values),value.by_dawn_values,value.pending_metrics)
    def private(self,*args,**kwargs):
        raise ValueError('Personal views require the exact occurrence owner')

class NavigationCurrent:
    def __init__(self,navigation):
        self.navigation=navigation;self.occurrence=navigation.occurrence
        row=self.occurrence;self.source=transport_source(navigation.node.read(),row.names.forward)
        b=self.source.public;root=navigation.history.state(navigation.history.root).node.data
        game=root.to_game();base={k:game[k] for k in ('policy','claim_policy','seer_options','strategy_ui','result_disclosure_model') if k in game}
        history=[{**base,'target':e.target,'claims':list(b.claims)} for e in b.history]
        view={**game,'history':history,'claims':list(b.claims),'selection':None,
              'seer_inputs':[dict(day=r.published_day,reporter=r.player,target=r.target,color=r.color) for r in self.source.past],
              'reports':[asdict(r) for r in b.reports]}
        view.pop('public_log',None);view.pop('public_draft',None)
        self.prefilled_selection=False
        next_key=navigation._forward.get(row.key)
        if next_key:
            step=navigation.history.occurrence(next_key).selector
            if step.get('requested') is not None:view['selection']=row.names.display(step['requested']);self.prefilled_selection=True
        self.identity='navigation-'+row.key
        data=BoardData.from_game(view,game_data=root.game_data,runtime=root.runtime)
        self.data=replace(data,facts=replace(data.facts,board_id=self.identity))
        if row.active_mass:
            progress=Progress(b,row.settled_village,row.settled_wolf)
        else:
            # A Footer may settle a mixture of winners. Keep every public outcome
            # for ordinary terminal rows instead of treating one as known truth.
            parent=navigation.history.occurrence(row.parent) if row.parent else None
            if parent is not None and row.selector['kind']=='advance':
                node=navigation.history.state(parent.key).node
                outcomes=tuple(BoardOutcome(r.probability,transport_source(r.node.read(),row.names.forward).public) for r in node.action(row.selector['target']))
                prior=transport_source(node.read(),row.names.forward).public
            else:outcomes=(BoardOutcome(F(1),b),);prior=b
            progress=Progress(None,row.settled_village,row.settled_wolf,prior,outcomes)
        groups,counts=role_summary(progress)
        self.roles=NavigationRoleState(self.data,progress,role_rates(progress),groups,counts,navigation)
    def automatic_update(self):
        row=self.occurrence;step=row.selector
        if step is None or step.get('kind')!='generated' or not any(isinstance(s,dict) and 'public_arrival' in s for s in step['route']):return None
        from .calculation_tree import CalculationTree
        tree=CalculationTree.from_node(self.navigation.history.state(row.parent).node)
        key=tree.restore(step['route']);updates=tree.nodes[key].get('public_updates') or ()
        if len(updates)!=1:return None
        return dict(night=row.parent,route=tree.route(updates[0]['node']))

    @property
    def metadata(self):
        parent=None
        if self.occurrence.parent is not None:
            row=self.navigation.history.occurrence(self.occurrence.parent);b=self.navigation.history.state(row.key).source.public
            parent=dict(key=row.key,day=b.day,phase=b.phase)
        forward=None;key=self.navigation._forward.get(self.occurrence.key)
        if key is not None:
            b=self.navigation.history.state(key).source.public;forward=dict(key=key,day=b.day,phase=b.phase)
        if forward is None and self.automatic_update() is not None:
            forward=dict(key=None,day=self.source.public.day,phase=self.source.public.phase,automatic=True)
        return dict(occurrence=self.occurrence.key,state=self.occurrence.state,identity=self.identity,parent=parent,forward=forward,prefilled=self.prefilled_selection)
