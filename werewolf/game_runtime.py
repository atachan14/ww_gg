"""Bounded, process-local completed evaluations owned by one immutable Game.

Common cast/rules are captured once on Game creation. No Board cache key contains
or compares rule values. A new setup creates a new Game runtime; there is no
in-place common-settings update in the current application.
"""
from collections import OrderedDict
from copy import deepcopy
from threading import RLock

_MISSING=object()

class GameRuntime:
    def __init__(self,data,*,max_entries=32):
        self._data=data;self.max_entries=max_entries;self._values=OrderedDict();self._lock=RLock()
        self.hits=0;self.misses=0;self.stores=0
    @property
    def data(self):return self._data
    @classmethod
    def from_game(cls,game,**kwargs):
        from .board_flow import GameData
        return cls(GameData.from_game(game),**kwargs)
    def get(self,key,*,private=False):
        from .board_future import reconstruction_reuse_enabled
        if not reconstruction_reuse_enabled():return False,None
        with self._lock:
            value=self._values.get(key,_MISSING)
            if value is _MISSING:self.misses+=1;return False,None
            self._values.move_to_end(key);self.hits+=1
        from .calculation_budget import tick
        tick()
        result=deepcopy(value) if private else value
        tick(0)
        return True,result
    def put(self,key,value,*,private=False,require_dawn=False):
        from .board_future import reconstruction_reuse_enabled
        if not reconstruction_reuse_enabled():return
        from .seer_future_uniform import FuturePending
        if isinstance(value,FuturePending) or getattr(value,'pending_metrics',()):return
        if private:
            # Unsupported dawn is separate from the requested final scan rows.
            if any(p['legal'] and (p['final'] is None or require_dawn and p.get('dawn') is None) for p in value.get('players',())):return
            value=deepcopy(value)
        with self._lock:
            self._values[key]=value;self._values.move_to_end(key);self.stores+=1
            while len(self._values)>self.max_entries:self._values.popitem(last=False)
    def clear(self):
        with self._lock:self._values.clear()
    def info(self):
        with self._lock:return dict(hits=self.hits,misses=self.misses,stores=self.stores,entries=len(self._values))

class GameRuntimes:
    """App-local registry keyed by the existing co_display_game identity."""
    def __init__(self,*,max_games=16,max_entries=32):
        self.max_games=max_games;self.max_entries=max_entries;self._games=OrderedDict();self._lock=RLock()
    def get(self,game_id,game):
        with self._lock:
            runtime=self._games.get(game_id)
            if runtime is None:
                runtime=GameRuntime.from_game(game,max_entries=self.max_entries);self._games[game_id]=runtime
            self._games.move_to_end(game_id)
            while len(self._games)>self.max_games:self._games.popitem(last=False)[1].clear()
            return runtime
    def discard(self,game_id):
        with self._lock:
            old=self._games.pop(game_id,None)
            if old is not None:old.clear()
