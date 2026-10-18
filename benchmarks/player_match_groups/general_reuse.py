"""Complete-key local extension. No retirement of general/private evidence."""
from .extension_reuse import ExtensionForecast
from werewolf.information_set_forecast import InformationSetForecast

class GeneralReuseForecast(ExtensionForecast):
    structured_seer_observer=True
    def full_renamed_key(self,b,s,past,private,observer,*,target=None,physical=None):
        if (self.future_reuse and self.exact_renaming and self.memoize_flows
            and self.trace is None and b.player_count<=7):
            # Complete constructor rejects unknown records/observers or >120
            # mappings. Private laws, histories, targets and physical bases stay
            # in equality. Labelled actor rankings and ties are never transported.
            key=self.complete_reuse_key(b,s,past,private,observer,target=target,physical=physical)
            if key is not None:return key
        return InformationSetForecast.full_renamed_key(self,b,s,past,private,observer,target=target,physical=physical)
