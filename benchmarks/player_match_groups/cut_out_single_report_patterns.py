"""Primitive single-report adapters feeding a shared vector/state reducer."""
from dataclasses import replace
from fractions import Fraction as F
from werewolf.information_set_forecast import Pending
from werewolf.seer_fake_uniform import fake_uniform_options
from werewolf.seer_future_uniform import FuturePending


def report_patterns(state,past,groups,*,truth,fake_policy):
    seen={(r.player,r.acquired_day) for r in past}
    if truth:
        patterns={}
        for h in state.hypotheses:
            scans=tuple(a for a in h.acquisitions if a.player==2 and (2,a.day) not in seen)
            if len(scans)!=1 or scans[0].day!=2:
                raise Pending('live_medium_one_unpublished_scan_required')
            a=scans[0];block=next(g for g in groups if a.target in g)
            patterns.setdefault((block,a.color),[]).append((h,a.target))
        for (block,color),entries in patterns.items():
            selected=tuple(h for h,target in entries if target==block[0])
            if not selected:raise Pending('live_medium_orbit_representative_missing')
            yield block,color,selected,sum((h.mass for h,_ in entries),F())
    else:
        # Exposed fake P2 has no possible truth history after medium white.
        # Keep the existing noise law, including targets now dead or publicly
        # white. Actual role/scan secrets never filter these legal reports.
        if tuple(fake_policy) not in (('uniform',),('noncontradictory','uniform')):
            raise Pending('live_medium_fake_policy_unproved')
        pending=tuple(day for day,roster in enumerate(state.rosters,1) if 2 in roster and (2,day) not in seen)
        if pending!=(2,):raise Pending('live_medium_fake_backlog_not_implemented')
        options=fake_uniform_options(state.rosters[0],2,past)
        if isinstance(options,FuturePending):raise Pending(options.reason)
        patterns={}
        for (target,color),q in options:
            block=next(g for g in groups if target in g)
            patterns.setdefault((block,color),{})[target]=q
        for (block,color),weights in patterns.items():
            if set(weights)!=set(block) or len(set(weights.values()))!=1:
                raise Pending('live_medium_fake_target_orbit_not_uniform')
            q=weights[block[0]]
            selected=tuple(replace(h,mass=h.mass*q) for h in state.hypotheses)
            yield block,color,selected,sum(weights.values(),F())