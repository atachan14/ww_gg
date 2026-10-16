"""Board-owned stage boundaries; saved cookie format remains compatible.

GameData is shared. Board inputs contain evidence, never a calculated parent
prior. roles() is the uncached reference reconstruction for stage 3a; ordinary
updates and corrections use exactly that same entry.
"""
from dataclasses import dataclass, field
from fractions import Fraction
import json
from .exact import Rules,Strategy,ROLES
from .setup import complete_rules

_COMMON=('players','wolves','mediums','seers','hunters','rules')

def _text(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

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

    def forecast(self,*,max_work=250000,max_seconds=20):
        # Joint preparation belongs to 3a, before stage 3b starts evaluation.
        from .board_roles import prepare_evaluation
        from .model_a_public import evaluate_prepared_public
        if self.progress.finished:
            from .forecast_result import Forecast
            value=sum((o.probability*int(o.board.winner=='village')
                       for o in self.progress.last_outcomes),Fraction())
            return Forecast(value,())
        game=self.owner.to_game();strategy=Strategy(**game['policy'])
        prepared=prepare_evaluation(game,self.board,self.rules,strategy,
                                    max_work=max_work,max_seconds=max_seconds)
        from .board_future import calculation_origin
        with calculation_origin(self.owner):
            return evaluate_prepared_public(prepared,self.board,self.rules,strategy,
                                            max_work=max_work,max_seconds=max_seconds)

    def private(self,role,players,results,*,max_work=250000,max_seconds=20):
        from .board_roles import prepare_private
        from .private_adapter import evaluate_private_table
        game=self.owner.to_game();strategy=Strategy(**game['policy'])
        prepared=prepare_private(self.board,role,players,results,self.rules,strategy,
                                 game_state=game,max_work=max_work,max_seconds=max_seconds)
        from .board_future import calculation_origin
        with calculation_origin(self.owner):
            return evaluate_private_table(self.board,role,players,results,self.rules,strategy,
                                          game_state=game,max_work=max_work,max_seconds=max_seconds,
                                          _prepared=prepared)

@dataclass(frozen=True)
class BoardData:
    game_data:GameData
    inputs:str=field(repr=False)
    facts:BoardFacts

    @classmethod
    def from_game(cls,game,*,game_data=None):
        common=game_data or GameData.from_game(game)
        if common!=GameData.from_game(game):raise ValueError('GameData version mismatch')
        # Snapshot ONLY board evidence. Common cast/rules are held once above.
        inputs={k:v for k,v in game.items() if k not in _COMMON}
        text=_text(inputs)
        return cls(common,text,BoardFacts.from_inputs(common,inputs))

    def to_game(self):
        # A transient adapter for existing kernels, never a second saved truth.
        return self.game_data.fields()|json.loads(self.inputs)

    def updated(self,**changes):
        if set(changes)&set(_COMMON):raise ValueError('GameData changes require a new game version')
        game=self.to_game();game.update(changes)
        return BoardData.from_game(game,game_data=self.game_data)

    def child(self,step,**changes):
        game=self.to_game();game['history']=[*game.get('history',()),step]
        game.update(changes)
        return BoardData.from_game(game,game_data=self.game_data)

    def roles(self):
        from .board_roles import reconstruct_roles,role_rates,role_summary
        rules,progress=reconstruct_roles(self)
        if rules!=self.game_data.rules:raise ValueError('Reconstruction changed GameData rules')
        groups,counts=role_summary(progress)
        return RoleState(self,progress,role_rates(progress),groups,counts)
