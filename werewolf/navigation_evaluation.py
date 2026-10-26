"""One immutable Current snapshot; adoption and evaluation have separate lifetimes.

The journal/revision owns navigation. Completed forecasts are process-local
projections over the exact same immutable node, never replacement game state.
"""
from dataclasses import dataclass
from fractions import Fraction
from .navigation_current import NavigationCurrent
from .forecast_result import Forecast

@dataclass
class NavigationEvaluation:
 document:object
 current:object
 revision:int
 details:bool=False
 @property
 def occurrence(self):return self.current.occurrence.key
 @property
 def identity(self):
  return dict(occurrence=self.occurrence,revision=self.revision,board_id=self.current.identity)
 def is_current(self):
  return self.document.revision==self.revision and self.document.game.current==self.occurrence
 def forecast(self):
  if hasattr(self,'_forecast'):return self._forecast
  if self.current.roles.progress.finished:self._forecast=None;return None
  node=self.current.navigation.node
  key=(self.current.occurrence.state,self.current.occurrence.names.forward,self.details)
  cache=self.document._evaluation_results
  previous=cache.get(key)
  if previous is not None and previous[0] is node:self._forecast=previous[1];return self._forecast
  if not self.details and node.win_certificate():
   result=Forecast(Fraction(1),(),pending_metrics=('win_cutoff_details',))
  else:result=self.current.roles.forecast()
  # Exceptions/Pending/partial action vectors are never completed cache entries.
  if isinstance(result,Forecast):cache[key]=(node,result)
  self._forecast=result
  return result

def capture(document,*,details=False):
 with document.lock:
  if not hasattr(document,'_evaluation_results'):document._evaluation_results={}
  # Fork only cursor/history containers. Immutable solver nodes and the existing
  # evaluation owner are shared; an advancing cursor cannot mutate this request.
  snapshot=document.game.fork()
  current=NavigationCurrent(snapshot)
  # Preserve the ordinary boundary's existing exact-node/name-map projection
  # cache when the request cursor is forked; no new solver is constructed.
  document.game._current_projection=snapshot._current_projection
  return NavigationEvaluation(document,current,document.revision,details)
