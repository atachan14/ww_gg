"""Own scan intervention: only the owner's absence cancels a new result.

Targets remain readable as corpses. Test membership in the acquisition roster,
not current morning survival, so already obtained records remain mandatory.
"""
def scan_intervention_matches(h,state,owner,day,target):
    if len(state.rosters)<day or owner not in state.rosters[day-1]:return True
    return any(a.player==owner and a.day==day and a.target==target for a in h.acquisitions)
