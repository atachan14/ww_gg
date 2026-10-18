"""Measurement adapter only: all numerical methods are original inherited ones."""
from werewolf.information_set_forecast import InformationSetForecast

class OriginalForecastAdapter(InformationSetForecast):
    def __init__(self,*args,**kwargs):
        for name in('retirement_proof','future_reuse','physical_reuse','retired_reuse','compact_keys','fast_parts'):
            if kwargs.pop(name,False):raise ValueError('Original reference cannot enable '+name)
        super().__init__(*args,**kwargs)
        self.reuse_stats={};self.mask_stats={};self.retirement_proof_hits=0
