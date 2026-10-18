"""Root/hunter opt-in only accelerates EXISTING full certificate construction.

Candidate profiles, actor mask, proof namespace and private/physical histories
remain owned by the original RootSecretEngine. No noise retirement is enabled.
"""
from time import perf_counter
from werewolf.root_secret_flow import RootSecretEngine
from .fast_key_parts import make_canonical

class LocalRootEngine(RootSecretEngine):
    structured_seer_observer=True
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.local_canonical,_,self.local_mask_stats=make_canonical()
        self.local_key_calls=0;self.local_key_seconds=0.
    def canonical_payoff_key(self,*args,**kwargs):
        started=perf_counter();self.local_key_calls+=1
        try:return self.local_canonical(*args,**kwargs)
        finally:self.local_key_seconds+=perf_counter()-started
