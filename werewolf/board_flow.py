"""Board-owned stage boundaries; saved cookie format remains compatible.

GameData is shared. Board inputs contain evidence, never a calculated parent
prior. roles() is the uncached reference reconstruction for stage 3a; ordinary
updates and corrections use exactly that same entry.
"""
from .calculation_budget import DEFAULT_MAX_WORK, DEFAULT_MAX_SECONDS
from dataclasses import dataclass, field
from fractions import Fraction
import json
from .exact import Rules,Strategy,ROLES
from .setup import complete_rules

_COMMON=('players','wolves','mediums','seers','hunters','rules')

def _text(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def validate_budget(max_work,max_seconds):
    if max_work is not None and (type(max_work)is not int or max_work<1):raise ValueError('Positive calculation budget required')
    if max_seconds is not None and (type(max_seconds) not in (int,float) or max_seconds<=0):raise ValueError('Positive calculation time budget required')

@dataclass(frozen=True)
class GameData:
    players:int
    wolves:int
    mediums:int
    seers:int
    hunters:int
    rules:Rules

    @classmethod
    def from_game(cls,game):
        return cls(game['players'],game.get('wolves',1),game.get('mediums',0),
                   game.get('seers',0),game.get('hunters',0),complete_rules(game['rules']))

    def fields(self):
        from dataclasses import asdict
        return {name:getattr(self,name) for name in _COMMON if name!='rules'}|{'rules':asdict(self.rules)}

@dataclass(frozen=True)
class BoardFacts:
    board_id:object
    parent_id:object
    slot:int
    day:int
    phase:str
    alive:tuple

    @classmethod
    def from_inputs(cls,game_data,inputs):
        history=inputs.get('history',())
        alive=set(range(1,game_data.players+1))
        for step in history:
            deaths=step.get('deaths') if 'observation' in step else [step.get('target')]
            for player in deaths or ():alive.discard(player)
        slot=len(history);day=1+slot//2;phase='day' if slot%2==0 else 'night'
        graph=inputs.get('public_log',{}).get('board_graph',{})
        node=graph.get('nodes',{}).get(graph.get('current'),{})
        same=node.get('slot')==slot
        return cls(node.get('id') if same else None,node.get('parent') if same else None,
                   slot,node.get('day',day) if same else day,node.get('phase',phase) if same else phase,
                   tuple(sorted(alive)))

@dataclass(frozen=True)
class RoleState:
    owner:object=field(repr=False)
    progress:object
    rates:tuple
    groups:object
    counts:object

    @property
    def rules(self):return self.owner.game_data.rules
    @property
    def board(self):return self.progress.last_board if self.progress.finished else self.progress.board
    @property
    def replay_result(self):return self.rules,self.progress

    def probabilities(self,player):return dict(self.rates[player-1])

    def forecast(self,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
        # Joint preparation belongs to 3a, before stage 3b starts evaluation.
        from .board_roles import prepare_evaluation
        from .model_a_public import evaluate_prepared_public
        if self.progress.finished:
            from .forecast_result import Forecast
            value=sum((o.probability*int(o.board.winner=='village')
                       for o in self.progress.last_outcomes),Fraction())
            return Forecast(value,())
        validate_budget(max_work,max_seconds)
        key=('public',self.owner.inputs,max_work,max_seconds)
        from .calculation_budget import CalculationBudgetExceeded
        try:hit,value=self.owner.runtime.get(key)
        except CalculationBudgetExceeded:
            from .seer_future_uniform import FuturePending
            return FuturePending('information_set_budget_exceeded')
        if hit:return value
        game=self.owner.to_game();strategy=Strategy(**game['policy'])
        prepared=prepare_evaluation(game,self.board,self.rules,strategy,
                                    max_work=max_work,max_seconds=max_seconds)
        from .board_future import calculation_origin
        with calculation_origin(self.owner):
            result=evaluate_prepared_public(prepared,self.board,self.rules,strategy,
                                            max_work=max_work,max_seconds=max_seconds)
        self.owner.runtime.put(key,result)
        return result

    def private(self,role,players,results,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS,_prepared=None):
        from .board_roles import prepare_private
        from .private_adapter import evaluate_private_table
        validate_budget(max_work,max_seconds)
        key=('private',self.owner.inputs,_text(dict(role=role,players=players,results=results)),max_work,max_seconds)
        hit,value=self.owner.runtime.get(key,private=True)
        if hit:return value
        game=self.owner.to_game();strategy=Strategy(**game['policy'])
        prepared=_prepared if _prepared is not None else prepare_private(self.board,role,players,results,self.rules,strategy,
                                 game_state=game,max_work=max_work,max_seconds=max_seconds)
        from .board_future import calculation_origin
        with calculation_origin(self.owner):
            result=evaluate_private_table(self.board,role,players,results,self.rules,strategy,
                                          game_state=game,max_work=max_work,max_seconds=max_seconds,
                                          _prepared=prepared)
        self.owner.runtime.put(key,result,private=True,require_dawn=role in ('wolf','hunter'))
        return result

@dataclass(frozen=True)
class BoardData:
    game_data:GameData
    inputs:str=field(repr=False)
    facts:BoardFacts
    runtime:object=field(compare=False,hash=False,repr=False)

    @classmethod
    def from_game(cls,game,*,game_data=None,runtime=None):
        from .game_runtime import GameRuntime
        if runtime is None:runtime=GameRuntime(game_data) if game_data is not None else GameRuntime.from_game(game)
        common=runtime.data
        if game_data is not None and common is not game_data:raise ValueError('Different Game runtime')
        # Snapshot ONLY board evidence. Common cast/rules are held once above.
        inputs={k:v for k,v in game.items() if k not in _COMMON}
        text=_text(inputs)
        return cls(common,text,BoardFacts.from_inputs(common,inputs),runtime)

    def to_game(self):
        # A transient adapter for existing kernels, never a second saved truth.
        return self.game_data.fields()|json.loads(self.inputs)

    def updated(self,**changes):
        if set(changes)&set(_COMMON):raise ValueError('GameData changes require a new game version')
        game=self.to_game();game.update(changes)
        return BoardData.from_game(game,game_data=self.game_data,runtime=self.runtime)

    def child(self,step,**changes):
        game=self.to_game();game['history']=[*game.get('history',()),step]
        game.update(changes)
        return BoardData.from_game(game,game_data=self.game_data,runtime=self.runtime)

    def roles(self):
        from .board_roles import reconstruct_roles,role_rates,role_summary
        rules,progress=reconstruct_roles(self)
        groups,counts=role_summary(progress)
        return RoleState(self,progress,role_rates(progress),groups,counts)
