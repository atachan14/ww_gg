"""Development-only configured-MAX equivariance experiment; no new evaluator."""
from werewolf.grouped_forecast import GroupedForecast
from werewolf.actor_information import WolfInformation,wolf_information_orbits


class ConstructedMaxOrbitExperiment(GroupedForecast):
    def target_orbits(self,targets):
        available=set(targets)
        parts=tuple(tuple(p for p in group if p in available) for group in self.groups)
        parts=tuple(group for group in parts if group)
        covered={p for group in parts for p in group}
        return parts+tuple((p,) for p in targets if p not in covered)

    def equivalent_targets(self,b,s,x,y,past=()):
        if any(x in group and y in group for group in self.groups):return True
        return super().equivalent_targets(b,s,x,y,past)

    def wolf_policy(self,b,s,past,mask,history=()):
        # Stabilise the COMPLETE known roster and own attack targets before
        # reusing the common configured-policy/legal-action scorer.
        with self.actor_scope(WolfInformation(mask,history)):
            return super().wolf_policy(b,s,past,mask,history)

    def wolf_cells(self,state):
        if self.aggregate_wolf and any(len(group)>1 for group in self.groups):
            return wolf_information_orbits(state,self.groups)
        return super().wolf_cells(state)


def calculation(kind,mode,view='public'):
    from .closed_full_tree_fixture import case
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.exact import Strategy
    from dataclasses import asdict
    from werewolf.actor_information import PersonalInformation
    c=ClosedCalculation(case(5,kind).data.updated(policy=asdict(Strategy())),grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)
    if mode=='orbits':c._ClosedCalculation__engine.__class__=RefinedMaxOrbitExperiment
    root=c.root
    if view!='public':
        h=next(h for h in root.read().private.hypotheses if h.roles[2]&1)
        info=(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)) if view=='seer' else WolfInformation.from_hypothesis(h))
        root=root.personal(info)[1]
    return c,root


def mask_map(ids):
    return tuple(sum(1<<(ids[p]-1) for p in range(len(ids)) if mask&(1<<p)) for mask in range(1<<len(ids)))


def frame_signature(source,ids):
    # Development full-joint comparison. Simultaneous report ordering is a
    # canonical set WITH all acquisition/publication-day fields retained.
    from werewolf.exact_renaming import board_signature,state_signature,record
    from dataclasses import fields
    masks=mask_map(ids)
    def board(b):
        return tuple((name,tuple(sorted(value)) if name=='reports' else value) for name,value in board_signature(b,ids,masks))
    observer=source.observer
    own=None if observer is None else (type(observer).__name__,tuple((f.name,ids[getattr(observer,f.name)-1] if f.name in ('actor','target') else tuple(record(a,ids) for a in getattr(observer,f.name)) if f.name=='acquisitions' else getattr(observer,f.name)) for f in fields(observer)))
    return board(source.public),state_signature(source.public_state,ids,masks),tuple(sorted(record(r,ids) for r in source.past)),state_signature(source.private,ids,masks),own,board(source.physical)


def invariant(source,groups):
    n=source.public.player_count;identity=tuple(range(1,n+1));original=frame_signature(source,identity)
    for group in groups:
        for other in group[1:]:
            ids=list(identity);a=group[0]-1;b=other-1;ids[a],ids[b]=ids[b],ids[a]
            if frame_signature(source,tuple(ids))!=original:return False
    return True


def actual_report_frames():
    import json
    from pathlib import Path
    from werewolf.board_flow import BoardData
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.exact import report_actions
    from werewolf.evaluation_branch import ContinuationInputs,physical_board
    from werewolf.board_future import kernel_calculation
    from werewolf.calculation_budget import calculation_budget
    game=json.loads(Path('benchmarks/player_match_groups/actual-seven-max-results.json').read_text(encoding='utf-8'))['game']
    c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_reports=True,aggregate_wolf=True,max_work=250000,max_seconds=30);n=c.root
    for target in (4,5):n=next(r.node for r in n.action(target) if r.node.read().public.winner is None)
    e=c._ClosedCalculation__engine;s=n.read()
    with kernel_calculation(),calculation_budget(250000,max_seconds=30):
        actions=report_actions(s.public);assert len(actions)==1
        o=actions[0].outcomes[0];law=e.project(s.public_state,o.board)
        rows=e.publications(o.board,law,s.past)
        weighted=e.push(s.public_state,s.private,tuple((o.probability*q,b,st,past) for q,b,st,past in rows))
        frames=tuple(ContinuationInputs(b,st,past,p,s.observer,physical_board(b,p,s.physical)) for mass,b,st,past,p in weighted)
    return c,n,frames


class RefinedMaxOrbitExperiment(ConstructedMaxOrbitExperiment):
    def wolf_policy(self,b,s,past,mask,history=()):
        # Horizon queries resolve a named execution directly, outside act().
        # Its public history must refine the inherited stabiliser as well.
        from werewolf.group_partition import _fix
        with self.group_scope(_fix(self.groups,(event.target for event in b.history))):
            return super().wolf_policy(b,s,past,mask,history)
    def scalar(self,b,s,past):
        # Candidate scoring via report_flow calls scalar directly, bypassing
        # GroupedPolicy.morning_value's actual-P report-branch refinement.
        from types import SimpleNamespace
        from werewolf.group_partition import _report_groups
        with self.group_scope(_report_groups(self.groups,SimpleNamespace(public=b,past=past))):
            return super().scalar(b,s,past)


class AuditedRefinedExperiment(RefinedMaxOrbitExperiment):
    """Full-state transposition checks live ONLY in development tests."""
    def audit(self,b,s,past,private,observer,physical):
        from werewolf.evaluation_branch import ContinuationInputs,physical_board
        source=ContinuationInputs(b,s,past,private,observer,physical_board(b,private,physical))
        key=(source,self.groups)
        if not hasattr(self,'audited_frames'):self.audited_frames=set()
        if key not in self.audited_frames:
            assert invariant(source,self.groups),'constructed group does not stabilise full Q/P context'
            self.audited_frames.add(key)
    def solve(self,b,s,past,private,observer,*,physical=None):
        self.audit(b,s,past,private,observer,physical)
        return super().solve(b,s,past,private,observer,physical=physical)
    def act(self,b,s,past,target,private,observer,*,physical=None):
        self.audit(b,s,past,private,observer,physical)
        return super().act(b,s,past,target,private,observer,physical=physical)
