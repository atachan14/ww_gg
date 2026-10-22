"""Supported hand evidence, independent of strategy selection probability.

Q and P are filtered independently. No parent is changed and no initial prior is
reseeded. This adapter adds public observations, not edits to old acquisitions.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from .information_set_forecast import Pending

class ContradictoryPublicInput(ValueError):pass
class UnsupportedPublicInput(Pending):pass

@dataclass(frozen=True)
class PublicInput:
    claims:tuple
    seer_reports:tuple=()
    medium_reports:tuple=()
    def __post_init__(self):
        object.__setattr__(self,'claims',tuple(self.claims));object.__setattr__(self,'seer_reports',tuple(self.seer_reports));object.__setattr__(self,'medium_reports',tuple(self.medium_reports))

@dataclass(frozen=True)
class ConditionedInput:
    public_mass:F
    physical_mass:F
    source:object

def condition_input(source,evidence,rules,claim_policy):
    from .exact import condition_claims
    from .seer_acquisition import publication_support,normalize,SeerReport
    from .evaluation_branch import ContinuationInputs,physical_board
    if source.observer is not None:raise ValueError('Public input requires a public Board')
    b=source.public
    if b.winner:raise ValueError('A finished Board cannot accept new declarations')
    if b.phase!='day':raise UnsupportedPublicInput('manual_public_day_required')
    if evidence.medium_reports:raise UnsupportedPublicInput('manual_medium_input_pending')
    if len(evidence.claims)!=b.player_count:raise ValueError('One claim per player is required')
    if any(p not in b.alive and claim!=b.claims[p-1] for p,claim in enumerate(evidence.claims,1)):raise ValueError('Dead players cannot declare a new role')
    reports=[]
    for r in evidence.seer_reports:
        if type(r)is not SeerReport:raise ValueError('Typed seer reports required')
        if type(r.player)is not int or not 1<=r.player<=b.player_count or type(r.target)is not int or not 1<=r.target<=b.player_count:raise ValueError('Invalid report player')
        old=next((old for old in source.past if (old.acquired_day,old.player)==(r.acquired_day,r.player)),None)
        if old is not None:
            if old!=r:raise UnsupportedPublicInput('historical_report_edit_requires_baseline')
            continue
        if r.acquired_day!=b.day or r.published_day!=b.day:raise UnsupportedPublicInput('manual_report_timing_pending')
        if r.player not in b.alive or evidence.claims[r.player-1]!='seer':raise ValueError('Reporter must be an alive seer claimant')
        roster=source.public_state.rosters[r.acquired_day-1]
        if r.target not in roster or r.target==r.player or r.color not in ('white','black'):raise ValueError('Illegal divination report')
        reports.append(r)
    try:public=condition_claims(b,evidence.claims,claim_policy)
    except ValueError as error:
        # Shape/role eligibility validation belongs to condition_claims. An empty
        # otherwise-valid role support is a contradiction, not a policy zero.
        if not isinstance(evidence.claims,tuple) or any(c not in ('latent','villager','wolf','seer','medium','hunter') for c in evidence.claims):raise
        raise ContradictoryPublicInput(str(error)) from error
    roles={row[:-1] for row in public.worlds}
    def filtered(law):
        kept=tuple(h for h in publication_support(law.hypotheses,tuple(reports)) if h.roles in roles)
        total=sum((h.mass for h in kept),F())
        if not total:raise ContradictoryPublicInput('Public input has zero evidence support')
        return total,replace(law,hypotheses=normalize(kept))
    qmass,q=filtered(source.public_state);pmass,p=filtered(source.private)
    public=physical_board(public,q)
    child=ContinuationInputs(public,q,tuple(sorted((*source.past,*reports))),p,None,physical_board(public,p,source.physical))
    return ConditionedInput(qmass,pmass,child)

@dataclass(frozen=True)
class PublicInputEvidence:
    evidence:PublicInput
    rules:object
    claim_policy:object
    def __call__(self,source):return condition_input(source,self.evidence,self.rules,self.claim_policy).source


def initial_relation_game(root,path,evidence,source):
    """Construct the public incidence/timing colours of initial manual updates."""
    from copy import deepcopy
    game=deepcopy(root);n=game['players'];batches=[]
    prior=list(root.get('claims',['latent']*n));base=[]
    for p,c in enumerate(prior,1):
        if c!='latent':base.append(dict(kind='co',player=p,role=c))
    for r in root.get('seer_inputs',()):base.append(dict(kind='seer',player=r['reporter'],day=r['day'],target=r['target'],color=r['color']))
    if base:batches.append(dict(slot=0,mode='simultaneous',events=base))
    batches.extend(deepcopy(root.get('public_log',{}).get('batches',())))
    seen={(r['day'],r['reporter'],r['target'],r['color']) for r in root.get('seer_inputs',())}
    updates=[step[1] for step in path if step[0]=='public_input']+[evidence]
    for update in updates:
        events=[dict(kind='co',player=p,role=c) for p,c in enumerate(update.claims,1) if c!=prior[p-1]]
        for r in update.seer_reports:
            key=(r.acquired_day,r.player,r.target,r.color)
            if key not in seen:events.append(dict(kind='seer',player=r.player,day=r.acquired_day,target=r.target,color=r.color));seen.add(key)
        if events:batches.append(dict(slot=0,mode='simultaneous',events=events))
        prior=list(update.claims)
    game.update(history=[],claims=list(source.public.claims),seer_inputs=[dict(day=r.acquired_day,reporter=r.player,target=r.target,color=r.color) for r in source.past],public_log=dict(batches=batches))
    return game
