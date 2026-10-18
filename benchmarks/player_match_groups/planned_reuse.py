"""Explicit comparison engine only; not imported by application factories."""
from collections import Counter
from time import perf_counter
from .general_reuse import GeneralReuseForecast
from .bounded_key_plan import KeyReusePlan,planned_key

class PlannedReuseForecast(GeneralReuseForecast):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.plan_stats=Counter()
        self.current_key_function=self.key_function
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
class OverCapReuseForecast(PlannedReuseForecast):
    """Comparison-only selector: keep current keys, try proof only for >120."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.selection_stats=Counter()

    def planned_constructor(self,*args,**kwargs):
        self.selection_stats['calls']+=1
        current=self.current_key_function(*args,**kwargs)
        if current is not None:
            self.selection_stats['current_key']+=1;return current
        b,s,past,private,observer,rules,strategy=args
        # For six original IDs a proper colour partition has <=5!=120 maps.
        # This size test avoids extra work for already-distinguished targets.
        if b.player_count!=6 or kwargs.get('target')is not None or kwargs.get('max_mappings')!=120:
            self.selection_stats['declined_without_proof']+=1;return None
        if len(s.hypotheses)>128 or len(private.hypotheses)>128:
            self.selection_stats['declined_without_proof']+=1;return None
        from werewolf.exact_renaming import colors
        from werewolf.guard_model import GuardObserver
        from werewolf.seer_intervention import SeerObserver
        if observer is not None and type(observer)not in(GuardObserver,SeerObserver):
            self.selection_stats['declined_without_proof']+=1;return None
        if len(set(colors(b,s,private,None,marginal_cache=kwargs.get('marginal_cache'))))!=1:
            self.selection_stats['declined_without_proof']+=1;return None
        self.selection_stats['over_cap_proof']+=1
        return super().planned_constructor(*args,**kwargs)