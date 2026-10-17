"""Explicit separate OFF scalar-key experiments; no rank-vector transport."""
from .retirement_proof import RetirementProofForecast


class ExtensionForecast(RetirementProofForecast):
    def __init__(self,*args,medium_reuse=False,max_reuse=False,combined_reuse=False,extended_retirement=False,**kwargs):
        super().__init__(*args,**kwargs)
        self.medium_reuse=medium_reuse;self.max_reuse=max_reuse;self.combined_reuse=combined_reuse;self.extended_retirement=extended_retirement

    def full_renamed_key(self,b,s,past,private,observer,*,target=None,physical=None):
        random=self.strategy.day==self.strategy.night==self.strategy.fake_reports=='random'
        scope=((self.medium_reuse and b.initial_medium_count==1 and random)
               or(self.max_reuse and not b.initial_medium_count and not random)
               or(self.combined_reuse and b.initial_medium_count==1 and not random))
        if (self.future_reuse and scope and self.exact_renaming and self.memoize_flows
            and self.reuse_public_entry and self.trace is None and observer is None
            and not b.initial_hunter_count and b.initial_seer_count in (0,1)
            and sum(b.claims[p-1]=='seer'for p in b.alive)<=2
            and tuple(self.strategy.seer_position)==('unvisited','uniform')
            and tuple(self.strategy.fake_seer_policy)in(('uniform',),('noncontradictory','uniform'))):
            return self.complete_reuse_key(b,s,past,private,observer,target=target,physical=physical)
        return super().full_renamed_key(b,s,past,private,observer,target=target,physical=physical)

    def retirement_policy_supported(self,b):
        # Separate opt-in: only the ORIGINAL retirement predicate may establish
        # no informative seer. Keep actual public evidence; never invent a law.
        if self.extended_retirement and b.initial_medium_count in (0,1):
            return True
        return super().retirement_policy_supported(b)
