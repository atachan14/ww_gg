"""OFF-only experiment retaining validated public evidence after retirement."""
from .future_reuse import FutureReuseForecast


class RetirementProofForecast(FutureReuseForecast):
    def __init__(self,*args,retirement_proof=False,**kwargs):
        super().__init__(*args,**kwargs)
        self.retirement_proof=retirement_proof
        self.retirement_proof_hits=0

    def retirement_policy_supported(self,b):
        return(not b.initial_medium_count and self.strategy.day=='random'
               and self.strategy.night=='random' and self.strategy.fake_reports=='random')

    def continuation_context(self,b,s,past,private,observer):
        result=super().continuation_context(b,s,past,private,observer)
        if (self.retirement_proof and self.reuse_public_entry and observer is None
            and self.trace is None and self.memoize_flows
            and b.initial_seer_count==1 and not b.initial_hunter_count
            and self.retirement_policy_supported(b)
            and tuple(self.strategy.seer_position)==('unvisited','uniform')
            and tuple(self.strategy.fake_seer_policy) in (('uniform',),('noncontradictory','uniform'))
            and result[0].initial_seer_count==0 and self.can_retire_scans(b,s,past)):
            # Keep ACTUAL observed public reports, never synthesize an initial
            # fake law. The original retirement predicate validates them again.
            self.retirement_proof_hits+=1
            return result[0],result[1],past,result[3],result[4]
        return result
