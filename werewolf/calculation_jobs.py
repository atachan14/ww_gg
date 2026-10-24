"""Process-local, request-owned cooperative cancellation for read computations.

No result/cache ownership lives here. Session owner plus an unpredictable request
ID scopes cancellation; bounded short-lived tombstones close the arrival race.
"""
from collections import OrderedDict
from threading import Event,Lock
from time import monotonic
import re

class CalculationJobs:
    def __init__(self):
        self.lock=Lock();self.active={};self.cancelled=OrderedDict()
    @staticmethod
    def valid(token):return isinstance(token,str) and re.fullmatch(r'[a-f0-9]{32}',token) is not None
    def _prune(self):
        now=monotonic()
        while self.cancelled and (next(iter(self.cancelled.values()))<now-330 or len(self.cancelled)>1024):
            self.cancelled.popitem(last=False)
    def begin(self,owner,token):
        event=Event();key=(owner,token)
        with self.lock:
            self._prune()
            if key in self.active:raise ValueError('Calculation request ID already active')
            if key in self.cancelled:event.set()
            self.active[key]=event
        return event
    def cancel(self,owner,token):
        key=(owner,token)
        with self.lock:
            event=self.active.get(key)
            if event is not None:event.set()
            self.cancelled[key]=monotonic();self.cancelled.move_to_end(key);self._prune()
            return event is not None
    def finish(self,owner,token,event):
        with self.lock:
            if self.active.get((owner,token)) is event:self.active.pop((owner,token))
