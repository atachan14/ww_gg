"""Explicit comparison engine only; not imported by application factories."""
from collections import Counter
from time import perf_counter
from .general_reuse import GeneralReuseForecast
from .bounded_key_plan import KeyReusePlan,planned_key

class PlannedReuseForecast(GeneralReuseForecast):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.plan_stats=Counter()
        self.key_function=self.planned_constructor

    def planned_constructor(self,*args,**kwargs):
        plan=KeyReusePlan();started=perf_counter()
        try:return planned_key(*args,plan=plan,**kwargs)
        finally:
            self.plan_stats['calls']+=1;self.plan_stats['seconds']+=perf_counter()-started
            self.plan_stats[plan.reason]+=1;self.plan_stats['snapshots']+=plan.snapshots
            self.plan_stats['swaps']+=plan.swaps;self.plan_stats['serialized_cells']+=plan.serialized_cells
            if plan.initial_count>kwargs.get('max_mappings',10000):
                self.plan_stats['over_cap_requests']+=1
                if plan.reason=='complete':self.plan_stats['over_cap_completed']+=1