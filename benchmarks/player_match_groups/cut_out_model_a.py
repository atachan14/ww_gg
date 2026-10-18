"""Constructed initial Model A public prior adapter; no arbitrary-law ingestion.

Only explicit simultaneous Day1 snapshots use this path. Existing reconstruction
and public-prior objects are retained by reference. Group guarantee is for their
joint law, snapshot relations and ONE execution, not future disclosure policies
or equality of the legacy ordered-past cache representation.
"""
from collections import Counter
from dataclasses import dataclass, asdict
import json
from time import perf_counter
from math import comb
from types import SimpleNamespace
from .partitioned_match_groups import SharedContext, Observation, UnsupportedPartition
from .constructive_cut_out import ConstructiveCutOutGroups
from .cut_out_one_step import OneStepExecution
from werewolf.exact import Rules,Strategy,ClaimPolicy
from werewolf.seer_acquisition import SeerReport
from werewolf.seer_future_uniform import FuturePending
from werewolf.board_roles import reconstruct_saved,prepare_joint
from werewolf.public_prior import prepare_public_prior
from werewolf.public_log import migrate
from werewolf.public_log_changes import upgrade


@dataclass(frozen=True)
class InitialModelASpec:
    players: int
    claims: tuple
    simultaneous_snapshot: bool
    mediums: int = 1
    seers: int = 1
    reports: tuple = ()
    rules: Rules = Rules(initial_seer='none')
    strategy: Strategy = Strategy(day='random',night='random',fake_reports='random')
    claim_policy: ClaimPolicy = ClaimPolicy()


def _reason(spec,*,six=False,seven=False,max_trial=False,latent_max=False,terminal_night_max=False,no_read_night_max=False):
    if no_read_night_max and (not latent_max or terminal_night_max):return 'choose the explicit five-player no-read scope'
    if terminal_night_max and not latent_max:return 'terminal night max requires explicit latent max comparison'
    if latent_max and not max_trial:return 'latent max requires the explicit max comparison flag'
    if max_trial and (six or seven):return 'max comparison is 4/5 only'
    if six and seven:return 'choose exactly one comparison scope'
    if type(spec) is not InitialModelASpec:return 'constructed InitialModelASpec only; no Board/law/game/callable input'
    if (type(spec.players) is not int or spec.players not in ((7,) if seven else (6,) if six else (4,5)) or type(spec.mediums) is not int or spec.mediums not in (0,1)
        or type(spec.seers) is not int or spec.seers not in ((1,) if six or seven else (1,2)) or 1+spec.mediums+spec.seers>spec.players):return '7-player minimal comparison only' if seven else '6-player comparison W1 H0 M0/1 S1 only' if six else '4/5 original players W1 H0 M0/1 S1/2 only'
    if spec.simultaneous_snapshot is not True:return 'explicit simultaneous initial snapshot required; no inferred CCO timing'
    if (type(spec.rules) is not Rules or spec.rules.allow_self_bite or type(spec.strategy) is not Strategy
        or (not max_trial and (spec.strategy.day,spec.strategy.night,spec.strategy.fake_reports)!=('random',)*3)
        or (max_trial and (spec.strategy.day!='max' or spec.strategy.night not in ('random','max') or spec.strategy.fake_reports not in ('random','max')))
        or spec.strategy.include_self_bite or spec.strategy.disclosure_for('seer')!='all'
        or spec.strategy.disclosure_for('medium')!='all' or type(spec.claim_policy) is not ClaimPolicy):return 'fixed supported uniform/full-disclosure configuration only'
    if type(spec.claims) is not tuple or len(spec.claims)!=spec.players or any(type(c) is not str or c not in ('latent','villager','seer','medium','wolf') for c in spec.claims):return 'explicit original-player CO snapshot required'
    if max_trial and spec.strategy.fake_reports=='max' and 'medium' in spec.claims:return 'active_medium_report_max_outside_comparison_scope'
    if type(spec.reports) is not tuple or any(type(r) is not SeerReport for r in spec.reports):return 'exact initial SeerReport records only'
    if len({r.player for r in spec.reports})!=len(spec.reports):return 'one initial result per reporter'
    for r in spec.reports:
        if (r.acquired_day!=1 or r.published_day!=1 or not 1<=r.player<=spec.players or not 1<=r.target<=spec.players
            or spec.claims[r.player-1]!='seer'):return 'Day1 same-frame reports by declared seers only'
    if spec.rules.initial_seer=='none' and spec.reports:return 'no initial result when initial acquisition is none'
    if max_trial and not latent_max and (spec.seers!=1 or spec.rules!=Rules(initial_seer='random_white')
        or spec.claim_policy!=ClaimPolicy()
        or spec.strategy!=Strategy(day='max',night=spec.strategy.night,fake_reports=spec.strategy.fake_reports)
        or spec.claims!=('seer',)+('latent',)*(spec.players-1)
        or len(spec.reports)!=1 or spec.reports[0]!=SeerReport(1,1,1,3,'white')):
        return 'max trial requires true seer1 CO, initial white3, other players latent'
    latent_claims=(('latent',)*spec.players,)
    if spec.mediums==1:latent_claims+=(('medium',)+('latent',)*(spec.players-1),)
    if latent_max and (spec.seers!=1 or spec.rules not in (Rules(initial_seer='none'),Rules(initial_seer='random_white'))
        or spec.claim_policy!=ClaimPolicy() or spec.claims not in latent_claims or spec.reports
        or spec.strategy!=Strategy(day='max',night='max' if terminal_night_max or no_read_night_max else 'random',fake_reports=spec.strategy.fake_reports)
        or terminal_night_max and (spec.players!=4 or spec.claims!=('latent',)*4)
        or no_read_night_max and (spec.players!=5 or spec.mediums or spec.rules.initial_seer!='none' or spec.claims!=('latent',)*5)):
        if no_read_night_max:return 'five_player_no_read_requires_M0_initial_none_all_latent'
        if terminal_night_max:return 'terminal_night_max_requires_four_all_latent'
        return 'latent max comparison requires 4/5 W1 S1 H0 M0/1, latent seer/no reports, optional medium1 CO, initial none/white, public day max/random night'
    return None


def source_game(spec,*,six=False,seven=False,max_trial=False,latent_max=False,terminal_night_max=False,no_read_night_max=False):
    """Build a NEW narrow snapshot, never reinterpret an existing game/log."""
    reason=_reason(spec,six=six,seven=seven,max_trial=max_trial,latent_max=latent_max,terminal_night_max=terminal_night_max,no_read_night_max=no_read_night_max)
    if reason:raise ValueError(reason)
    game=dict(players=spec.players,wolves=1,mediums=spec.mediums,seers=spec.seers,hunters=0,
        model='group',history=[],claims=list(spec.claims),claim_policy=asdict(spec.claim_policy),
        policy=asdict(spec.strategy),rules=asdict(spec.rules),seer_mode='information-fixed-v1',
        seer_options=dict(initial_rule=spec.rules.initial_seer,likelihood='compatibility'),
        seer_inputs=[dict(day=r.acquired_day,reporter=r.player,target=r.target,color=r.color) for r in spec.reports],
        reports=[],result_disclosure_model='full-observed-v1')
    game['public_log']=upgrade(migrate(game))
    return game


@dataclass(frozen=True,eq=False)
class ModelAReference:
    players: int
    mediums: int
    seers: int
    rules: Rules
    strategy: Strategy
    claim_policy: ClaimPolicy
    board: object
    state: object
    past: tuple
    spec: InitialModelASpec
    game_json: str


class ModelAInitialGroups(ConstructiveCutOutGroups):
    def __init__(self,spec,*,six=False,seven=False,max_trial=False,latent_max=False,terminal_night_max=False,no_read_night_max=False):
        reason=_reason(spec,six=six,seven=seven,max_trial=max_trial,latent_max=latent_max,terminal_night_max=terminal_night_max,no_read_night_max=no_read_night_max)
        if reason:raise ValueError(reason)
        self.stats=Counter(generator_checks=0,symmetry_history_rows_read=0,full_permutation_searches=0,
                           upstream_permutation_checks=0,comparisons=0,official_board_builds=1,official_prior_builds=0,official_root_checks=1)
        started=perf_counter();game=source_game(spec,six=six,seven=seven,max_trial=max_trial,latent_max=latent_max,terminal_night_max=terminal_night_max,no_read_night_max=no_read_night_max)
        rules,progress=reconstruct_saved(game)
        self.stats['official_board_seconds']=perf_counter()-started
        if progress.finished:raise ValueError('terminal snapshot outside initial one-step scope')
        started=perf_counter()
        # Match the official entry selector BEFORE considering the fixed-CO
        # public prior. A no-seer-CO root owns latent initial acquisitions;
        # the fixed-CO prior intentionally omits those records.
        if latent_max:
            # Initial hidden acquisition law has no action-policy dependency.
            # Keep max in the snapshot: never relabel its continuation uniform.
            from werewolf.root_secret_flow import prepare_root_secrets
            root=prepare_root_secrets(progress.board,rules,max_work=100000)
        else:root=prepare_joint(game,progress.board,rules,spec.strategy,max_work=100000)
        if isinstance(root,FuturePending):raise ValueError(root.reason)
        self.stats['official_root_entry']=int(root is not None)
        if root is not None:
            if root.public!=progress.board or root.physical!=progress.board or root.public_law!=root.physical_law:
                raise ValueError('initial public/physical root mismatch')
            prior=(root.public_law,root.past)
        else:
            self.stats['official_prior_builds']=1
            prior=prepare_public_prior(game,progress.board,rules,max_work=100000)
        self.stats['official_prior_seconds']=perf_counter()-started
        if isinstance(prior,FuturePending):raise ValueError(prior.reason)
        state,past=prior
        if state.public_roles!=tuple(sorted(progress.board.worlds)):raise ValueError('official public role/joint prior mismatch')
        self.baseline=ModelAReference(spec.players,spec.mediums,spec.seers,rules,spec.strategy,spec.claim_policy,
            progress.board,state,past,spec,json.dumps(game,sort_keys=True,separators=(',',':')))
        self.stats['nominal_initial_worlds']=spec.players*comb(spec.players-1,spec.mediums)*comb(spec.players-1-spec.mediums,spec.seers)
        self.stats['public_worlds']=len(progress.board.worlds)
        self.stats['public_hypotheses']=len(state.hypotheses)
        # Proof-only partition construction: initial S_n is restricted by the
        # final CO map then fixed-target report relations. No law is conditioned
        # here; the COMPLETE official weighted law above is used unchanged.
        events=[]
        co=tuple((p,c) for p,c in enumerate(spec.claims,1) if c!='latent')
        if co:events.append(Observation('co',co))
        if spec.reports:events.append(Observation('report',tuple((r.player,r.target,r.color,r.acquired_day) for r in spec.reports)))
        started=perf_counter();groups=(tuple(range(1,spec.players+1)),)
        for event in events:groups=self._refine_groups(SimpleNamespace(groups=groups),event)
        self.stats['partition_seconds']=perf_counter()-started
        self._context=SharedContext(self.baseline,state,state,spec.claims,progress.board.alive,tuple(events),groups)

    def start(self):return self._context

    def update(self,*args,**kwargs):
        return UnsupportedPartition('Model A adapter is initial-snapshot only; reconstruct a new explicit spec, never use prototype filtering')

    def rebuild(self,*args,**kwargs):
        return UnsupportedPartition('reconstruct a new InitialModelASpec; no inferred temporal/CCO changes')


def adapt_model_a(spec):
    reason=_reason(spec)
    if reason:return UnsupportedPartition(reason)
    try:return ModelAInitialGroups(spec)
    except ValueError as error:return UnsupportedPartition('official initial Model A unavailable: '+str(error))


class ModelAOneStepExecution(OneStepExecution):
    supported_law='model_a_initial_public'

    def __init__(self,engine):
        if type(engine) is not ModelAInitialGroups:raise TypeError('constructed initial Model A adapter required')
        self.engine=engine
        self.stats=Counter(candidate_evaluations=0,legal_candidates=0,hypotheses_scanned=0,
                           posterior_normalizations=0,materialized_targets=0,
                           materialization_hypotheses=0,generator_checks=0)

    def evaluate(self,context,*,view='public',law_semantics='model_a_initial_public',representatives=True):
        if context is not self.engine.start() or view!='public':
            return UnsupportedPartition('issued formal initial public context only; no arbitrary or private law')
        return super().evaluate(context,view=view,law_semantics=law_semantics,representatives=representatives)

def adapt_six_model_a(spec):
    """Explicit six-player two-night comparison; default adapter stays 4/5."""
    reason=_reason(spec,six=True)
    if reason:return UnsupportedPartition('six-player comparison: '+reason)
    try:return ModelAInitialGroups(spec,six=True)
    except ValueError as error:return UnsupportedPartition('official six-player prior: '+str(error))


def adapt_seven_model_a(spec):
    """Explicit tiny-support seven-player uniform comparison, not a UI entry."""
    reason=_reason(spec,seven=True)
    if reason:return UnsupportedPartition('seven-player comparison: '+reason)
    if (spec.mediums!=0 or spec.rules.initial_seer!='none' or spec.claims.count('wolf')!=1
        or spec.claims.count('seer')>1 or any(c not in ('latent','villager','seer','wolf') for c in spec.claims)):
        return UnsupportedPartition('seven comparison requires M0/S1/H0, initial none, one known wolf, <=1 seer CO')
    try:
        engine=ModelAInitialGroups(spec,seven=True)
        if len(engine.baseline.state.hypotheses)>6:return UnsupportedPartition('seven initial public joint support limit6')
        return engine
    except ValueError as error:return UnsupportedPartition('official seven-player prior: '+str(error))


def adapt_max_model_a(spec):
    """Sealed 4/5 public-day-max comparison; existing sequential night convention."""
    reason=_reason(spec,max_trial=True)
    if reason:return UnsupportedPartition(reason)
    try:
        engine=ModelAInitialGroups(spec,max_trial=True)
        if engine.baseline.board.role_probability(1,'seer')!=1 or len(engine.baseline.state.hypotheses)>9:
            return UnsupportedPartition('true seer/support gate')
        return engine
    except ValueError as error:return UnsupportedPartition(str(error))


def adapt_latent_max_model_a(spec):
    """Initial latent secrets with existing public day max/random night, comparison only."""
    reason=_reason(spec,max_trial=True,latent_max=True)
    if reason:return UnsupportedPartition(reason)
    try:return ModelAInitialGroups(spec,max_trial=True,latent_max=True)
    except ValueError as error:return UnsupportedPartition(str(error))


def adapt_terminal_night_max_model_a(spec):
    """Four-player latent no-hunter terminal-night boundary only."""
    reason=_reason(spec,max_trial=True,latent_max=True,terminal_night_max=True)
    if reason:return UnsupportedPartition(reason)
    try:return ModelAInitialGroups(spec,max_trial=True,latent_max=True,terminal_night_max=True)
    except ValueError as error:return UnsupportedPartition(str(error))


def adapt_no_read_night_max_model_a(spec):
    """Five-player no-CO W1 S1 H0 M0 initial-none comparison only."""
    reason=_reason(spec,max_trial=True,latent_max=True,no_read_night_max=True)
    if reason:return UnsupportedPartition(reason)
    try:return ModelAInitialGroups(spec,max_trial=True,latent_max=True,no_read_night_max=True)
    except ValueError as error:return UnsupportedPartition(str(error))
