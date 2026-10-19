"""Development-only dead-owner scalar projection experiments.

Never feed projected records to saved/observed Board reconstruction.
"""
from dataclasses import replace,asdict
from collections import Counter
from fractions import Fraction as F
from werewolf.seer_acquisition import Hypothesis,normalize
from werewolf.exact import Strategy
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.evaluation_branch import ContinuationInputs


def projected_state(state,keep):
    tracked=tuple(p for p in (state.rosters[0] if state.tracked is None else state.tracked) if p in keep)
    entries=tuple(Hypothesis(h.roles,tuple(a for a in h.acquisitions if a.player in keep),h.mass,h.guards,h.attacks)
                  for h in state.hypotheses)
    return replace(state,hypotheses=normalize(entries),tracked=tracked)


def project(source,*,protect=True):
    keep=set(source.public.alive)
    if protect and source.observer is not None:keep.add(source.observer.actor)
    public=projected_state(source.public_state,keep)
    private=public if source.private is source.public_state else projected_state(source.private,keep)
    return ContinuationInputs(source.public,public,source.past,private,source.observer,source.physical)


class DeadPublicExperiment(InformationSetForecast):
    """Pure public scalar requests only; private/observer requests stay full."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.projections={};self.visits=Counter()
    def scalar_laws(self,b,s,private,observer):
        # Isolate the development candidate from later production adoption.
        return s,private
    def scalar_inputs(self,b,s,private,observer):
        self.visits['requests']+=1
        if observer is not None or private is not s or b.initial_hunter_count:return s,private
        if not any(a.player not in b.alive for h in s.hypotheses for a in h.acquisitions):return s,private
        key=(b.alive,s)
        if key not in self.projections:self.projections[key]=projected_state(s,set(b.alive))
        q=self.projections[key]
        self.visits['projected_calls']+=1
        self.visits['hypotheses_before']+=len(s.hypotheses);self.visits['hypotheses_after']+=len(q.hypotheses)
        return q,q
    def solve(self,b,s,past,private,observer,*,physical=None):
        s,private=self.scalar_inputs(b,s,private,observer)
        return super().solve(b,s,past,private,observer,physical=physical)
    def act(self,b,s,past,target,private,observer,*,physical=None):
        s,private=self.scalar_inputs(b,s,private,observer)
        return super().act(b,s,past,target,private,observer,physical=physical)


def dead_two_seers():
    from .closed_full_tree_fixture import case
    game=case(6,'single').data.to_game()
    game.update(seers=2,claims=['seer','seer','latent','latent','latent','latent'],
        seer_inputs=[dict(day=1,reporter=p,target=4,color='white') for p in (1,2)],policy=asdict(Strategy()))
    c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_reports=True,max_work=250000,max_seconds=30)
    n=c.root
    for target in (4,1):n=next(r.node for r in n.action(target) if r.node.read().public.winner is None)
    n=next(r.node for r in n.reports() if any(p.player==2 and p.acquired_day==2 and p.target==1 and p.color=='white' for p in r.node.read().past))
    return c,n


from werewolf.grouped_forecast import GroupedForecast
class ModernDeadExperiment(DeadPublicExperiment,GroupedForecast):
    pass


def actual_dead_seer_prefix():
    import json
    from pathlib import Path
    game=json.loads(Path('benchmarks/player_match_groups/actual-seven-max-results.json').read_text(encoding='utf-8'))['game']
    c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_reports=True,max_work=250000,max_seconds=30)
    n=c.root
    for target in (4,1):n=next(r.node for r in n.action(target) if r.node.read().public.winner is None)
    return c,n


class PairedDeadExperiment(ModernDeadExperiment):
    """Development only: align Q/P quotients, preserve all selected evidence."""
    def scalar_inputs(self,b,s,private,observer):
        self.visits['requests']+=1
        if b.initial_hunter_count:return s,private
        keep=frozenset((*b.alive,*((observer.actor,) if observer is not None else ())))
        if not any(a.player not in keep for st in (s,private) for h in st.hypotheses for a in h.acquisitions):return s,private
        # A quotient must not turn an unsupported private record into support.
        # This explicit domain check is development evidence, not an issued
        # frame/owner certificate or a proposed production proof cache.
        from werewolf.information_weights import observer_projection_ratios
        from werewolf.information_set_forecast import Pending
        observer_projection_ratios(s,private,incomplete=lambda:Pending('information_set_report_likelihood_incomplete'))
        def cached(st):
            key=(keep,st)
            if key not in self.projections:self.projections[key]=projected_state(st,keep)
            return self.projections[key]
        q,p=cached(s),cached(private)
        self.visits['projected_calls']+=1
        self.visits['hypotheses_before']+=len(s.hypotheses)+len(private.hypotheses)
        self.visits['hypotheses_after']+=len(q.hypotheses)+len(p.hypotheses)
        return q,p


def terminal_public_payoff_moments(source,events):
    """Independent next-step design: Q-owned payoff numerator by likelihood fiber.

    Not used by production; complete independently enumerated joint events only.
    """
    from collections import defaultdict
    qpi=defaultdict(F);moments=defaultdict(F)
    for h in source.public_state.hypotheses:qpi[h.roles,h.acquisitions]+=h.mass
    for event in events.values():
        scores={t:sum((q for (roles,*rest),q in event['Q'].items() if roles[0]&(1<<(t-1))),F()) for t in source.public.alive}
        chosen=tuple(t for t in scores if scores[t]==max(scores.values()))
        for (roles,acqs,guards,attacks),q in event['Q'].items():
            payoff=F(sum(bool(roles[0]&(1<<(t-1))) for t in chosen),len(chosen))
            moments[roles,acqs]+=event['q']*q*payoff
    return dict(moments),dict(qpi)
