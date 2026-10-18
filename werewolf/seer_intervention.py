"""Own scan intervention: only the owner's absence cancels a new result.

Targets remain readable as corpses. Test membership in the acquisition roster,
not current morning survival, so already obtained records remain mandatory.
"""
def scan_intervention_matches(h,state,owner,day,target):
    if len(state.rosters)<day or owner not in state.rosters[day-1]:return True
    return any(a.player==owner and a.day==day and a.target==target for a in h.acquisitions)


from dataclasses import dataclass

@dataclass(frozen=True)
class SeerObserver:
    """Serializable own intervention, never another actor's secret information."""
    actor: int
    acquisitions: tuple
    day: int
    target: int

    def __call__(self,h,state):
        return (bool(h.roles[2] & (1 << (self.actor-1)))
                and all(a in h.acquisitions for a in self.acquisitions)
                and scan_intervention_matches(h,state,self.actor,self.day,self.target))
