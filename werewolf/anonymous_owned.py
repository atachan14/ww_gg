"""Anonymous-owned public nodes with explicit, deferred secret acquisitions."""
from dataclasses import dataclass,replace,field
from .anonymous_belief import Belief,winner
from .anonymous_value import Evaluator,alive
from .closed_calculation import ActionBranch

@dataclass(frozen=True)
class AcquisitionRecipe:
    origin:Belief
    steps:tuple=()
    def append(self,step):return replace(self,steps=(*self.steps,step))
    def resolve(self,evaluator):
        belief=self.origin
        for kind,target,observation in self.steps:
            if kind=='day':belief=next(child for mass,result,child in belief.execute(target) if result==observation)
            else:
                flow=evaluator.night_flow(belief,acquire=True) if target is None else evaluator.forced_night_flow(belief,target,acquire=True)
                _,belief=flow.branch(observation)
        return belief

@dataclass(frozen=True)
class PublicFacts:
    player_count:int
    alive:tuple
    day:int
    phase:str
    history:tuple
    winner:str|None
    claims:tuple

@dataclass(frozen=True)
class OwnedState:
    belief:Belief
    recipe:AcquisitionRecipe
    @property
    def public(self):
        b=self.belief;terminal={winner(atom.population) for mass,atom in b.p.rows}
        result=next(iter(terminal)) if len(terminal)==1 else None;n=sum(map(len,b.groups))
        return PublicFacts(n,alive(b),b.day,b.phase,b.history,result,('latent',)*n)

@dataclass(frozen=True)
class AnonymousNode:
    calculation:object=field(compare=False,repr=False)
    owned:OwnedState
    def read(self):return self.owned
    @property
    def data(self):return self.calculation.data
    @property
    def groups(self):return self.owned.belief.groups
    @property
    def state_identity(self):return ('anonymous-owned-v1',self.owned)
    @property
    def solver_identity(self):return self.calculation.identity
    def forecast(self):return self.calculation.evaluator.forecast(self.owned.belief)
    def action(self,target):
        b=self.owned.belief;e=self.calculation.evaluator
        if type(target)is not int or target not in alive(b) or self.read().public.winner:raise ValueError('Illegal anonymous action')
        rows=e.day_children(b,target) if b.phase=='day' else e.night_children(b,target)
        return tuple(ActionBranch(mass,self.calculation.node(child,self.owned.recipe.append((b.phase,target,observation)))) for mass,observation,child in rows)
    def night(self):
        b=self.owned.belief
        if b.phase!='night' or self.read().public.winner:raise ValueError('Ongoing anonymous night required')
        return tuple(ActionBranch(mass,self.calculation.node(child,self.owned.recipe.append(('night',None,observation)))) for mass,observation,child in self.calculation.evaluator.night_children(b))
    def representative_action(self,target):
        from .navigation_history import NameMap
        b=self.owned.belief;group=next(g for g in b.groups if target in g);eligible=tuple(p for p in group if p in alive(b))
        if target not in eligible:raise ValueError('Dead anonymous target')
        representative=eligible[0];mapping=list(range(1,self.read().public.player_count+1));mapping[target-1],mapping[representative-1]=representative,target
        return representative,NameMap(tuple(mapping))
    def full_belief(self):return self.owned.recipe.resolve(self.calculation.evaluator)

class AnonymousCalculation:
    @staticmethod
    def supports(data):
        g=data.to_game();p=g['policy']
        return (g.get('model')=='group' and not g.get('mediums') and not g.get('hunters')
          and not data.game_data.rules.allow_self_bite and not p.get('include_self_bite')
          and all(p[k]=='random' for k in ('day','night','fake_reports'))
          and not g.get('history') and not g.get('seer_inputs') and not g.get('reports')
          and all(c=='latent' for c in g.get('claims',())) and not g.get('public_log',{}).get('batches')
          and (not g.get('seers') or g.get('seer_mode')=='information-fixed-v1'
            and g.get('seer_options',{}).get('likelihood')=='compatibility'
            and g.get('seer_options',{}).get('initial_rule')=='random_white'))
    def __init__(self,data):
        if not self.supports(data):raise ValueError('Anonymous owned slice does not support this entry')
        from .exact import Strategy
        g=data.to_game();strategy=Strategy(**g['policy'])
        if any(strategy.disclosure_for(role)!='all' for role in ('seer','medium')):raise ValueError('Anonymous owned slice requires full disclosure setting')
        self.data=data;self.identity=('anonymous-owned-random-v1',data.inputs);self.evaluator=Evaluator('random','random',False)
        origin=Belief.initial((tuple(range(1,g['players']+1)),),dict(wolf=g['wolves'],seer=g.get('seers',0),villager=g['players']-g['wolves']-g.get('seers',0)),data.game_data.rules.initial_seer)
        self.root=self.node(origin,AcquisitionRecipe(origin))
    def node(self,belief,recipe):return AnonymousNode(self,OwnedState(self.evaluator.scalar(belief),recipe))
