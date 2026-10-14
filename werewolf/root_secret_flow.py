"""Opt-in complete root secrets under existing uniform acquisition rules.

This API never replaces the fixed-CO entry or an unsupported max with random.
Public Model A role weights and actual branch measures remain distinct.
"""
from dataclasses import dataclass,replace,asdict
from fractions import Fraction as F
from .seer_acquisition import from_board,normalize
from .seer_future_uniform import TrueScanState,FuturePending,acquire_uniform
from .actor_information import condition_actor_state
from .evaluation_branch import ActionInputs,physical_board
from .information_set_forecast import InformationSetForecast,InformationSetActionPolicy,Pending
from .action_flow import resolve_action
from .night_knowledge import WolfAttack
from .calculation_budget import calculation_budget,CalculationBudgetExceeded
from .forecast_result import Forecast
from .exact import legal_targets,Strategy


@dataclass(frozen=True)
class RootSecretBranch:
    public: object
    public_law: TrueScanState
    physical: object
    physical_law: TrueScanState
    past: tuple = ()

    def __post_init__(self):
        if self.public_law.public_roles!=tuple(sorted(self.public.worlds)):
            raise ValueError('Public role prior must remain owned by public Board')
        if self.physical_law.public_roles!=tuple(sorted(self.physical.worlds)):
            raise ValueError('Physical role law must match actual branch Board')
        physical_board(self.public,self.physical_law,self.physical)


@dataclass(frozen=True)
class RootActorView:
    belief: TrueScanState
    physical_law: TrueScanState


def prepare_root_secrets(board,rules,*,max_work=250000):
    if board.day!=1 or board.phase!='day' or board.history or board.alive!=tuple(range(1,board.player_count+1)):
        return FuturePending('root_secret_initial_board_required')
    initial=TrueScanState(from_board(board),initial_rule=rules.initial_seer,tracked=None)
    law=acquire_uniform(initial,board.alive,max_work=max_work)
    if isinstance(law,FuturePending):return law
    return RootSecretBranch(board,law,board,law)


def observe_root_public(branch,public,compatible,*,past=None):
    """Use externally updated Model A Q; condition history within each world.

    The caller supplies an existing public observation predicate, never an
    optimized-action likelihood for public roles. Physical evidence uses P.
    """
    kept=tuple(h for h in branch.public_law.hypotheses if compatible(h))
    totals={}
    for h in kept:totals[h.roles]=totals.get(h.roles,F())+h.mass
    if any(not totals.get(w[:-1]) for w in public.worlds):
        return FuturePending('root_secret_public_history_zero_support')
    weights={w[:-1]:w[-1] for w in public.worlds}
    public_law=replace(branch.public_law,hypotheses=normalize(tuple(
        replace(h,mass=weights[h.roles]*h.mass/totals[h.roles]) for h in kept if h.roles in weights)))
    predicate=lambda h:h.roles in weights and compatible(h)
    if not any(predicate(h) for h in branch.physical_law.hypotheses):
        return FuturePending('root_secret_physical_zero_support')
    physical_law=condition_actor_state(branch.physical_law,predicate)
    physical=physical_board(public,physical_law,branch.physical)
    return RootSecretBranch(public,public_law,physical,physical_law,branch.past if past is None else tuple(past))


def root_actor_view(branch,compatible,*,guards=(),attacks=()):
    if not any(compatible(h) for h in branch.public_law.hypotheses):
        return FuturePending('root_secret_actor_belief_zero_support')
    if not any(compatible(h) for h in branch.physical_law.hypotheses):
        return FuturePending('root_secret_actor_physical_zero_support')
    return RootActorView(condition_actor_state(branch.public_law,compatible,guards=guards,attacks=attacks),
                         condition_actor_state(branch.physical_law,compatible,guards=guards,attacks=attacks))


def root_scope(branch,rules,strategy):
    if strategy.day!='random' or strategy.night!='random':return 'root_secret_max_unimplemented'
    from .guard_model import scope_reason
    reason=scope_reason(branch.public,rules,strategy,True)
    if reason:return reason
    if rules.allow_self_bite and not strategy.include_self_bite:
        return 'root_secret_self_bite_policy_support_unimplemented'
    # Initial full-disclosure omissions retain the existing fixed-CO contract.
    if strategy.disclosure_for('seer')=='all':
        published={(r.player,r.acquired_day) for r in branch.past}
        if any(a.player in branch.public.alive and branch.public.claims[a.player-1]=='seer' and
               (a.player,a.day) not in published for h in branch.public_law.hypotheses for a in h.acquisitions):
            return 'full_disclosure_truth_not_conditioned'
    if (strategy.disclosure_for('medium')=='all' and strategy.fake_reports=='max' and
        any(branch.public.claims[p-1]=='medium' for p in branch.public.alive)):
        return 'root_secret_max_unimplemented'
    return None


class RootSecretPolicy(InformationSetActionPolicy):
    def project(self,b,payload,outcome,target):
        continuation=super().project(b,payload,outcome,target)
        if b.phase!='night' or b.initial_hunter_count:return continuation
        known=(WolfAttack(b.day,target),)
        # In this non-guard path the corpse publicly identifies the bite.
        return replace(continuation,
            public_state=condition_actor_state(continuation.public_state,lambda h:True,attacks=known),
            private=condition_actor_state(continuation.private,lambda h:True,attacks=known))


class RootSecretEngine(InformationSetForecast):
    retain_joint_guard_history=True
    def __init__(self,rules,strategy,**kwargs):
        super().__init__(rules,strategy,retire_uninformative_scans=False,memoize_flows=False,**kwargs)
        self.action_policy=RootSecretPolicy(self)

    def exchangeable(self,b):return False  # Keep the complete latent acquisition flow.
    def value_law(self,state):return state  # No history compression in this entry.


def step_root_action(branch,target,rules,strategy,*,max_work=250000,max_seconds=20,publish=True):
    """Explicit action intervention through the shared ability/death/report flow."""
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    if branch.public.winner:return FuturePending('root_secret_terminal_action')
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            e=RootSecretEngine(rules,strategy,max_work=max_work)
            own=branch.physical_law;physical=branch.physical
            if branch.public.phase=='night':
                from .exact import forced_action_worlds,replace_worlds
                from .belief_projection import project_private
                physical=replace_worlds(physical,forced_action_worlds(physical,target,rules,strategy))
                own=project_private(own,physical,marginalize_private=False)
            acquired,outcomes=resolve_action(branch.public,ActionInputs(branch.public_law,branch.past,
                own,None,physical),target,e.action_policy)
            result=[]
            for o in outcomes:
                c=e.action_policy.project(branch.public,acquired,o,target)
                if publish and branch.public.phase=='night' and o.board.winner is None:
                    choices=e.push(c.public_state,c.private,e.morning(c.public,c.public_state,c.past))
                else:choices=((F(1),c.public,c.public_state,c.past,c.private),)
                for q,b,s,past,own in choices:
                    result.append((o.probability*q,RootSecretBranch(b,s,physical_board(b,own,c.physical),own,past)))
            return tuple(result)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_secret_value(branch,rules,strategy,*,actor=None,max_work=250000,max_seconds=20):
    if branch.public.winner:return F(branch.public.winner=='village')
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    own=branch.physical_law if actor is None else actor.physical_law
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            e=RootSecretEngine(rules,strategy,max_work=max_work)
            return e.solve(branch.public,branch.public_law,branch.past,own,None,
                           physical=physical_board(branch.public,own,branch.physical))
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_screen_eligible(board,rules,strategy):
    """Existing initial screen subset; no change to fixed-CO/max entrypoints."""
    return (bool(board.initial_seer_count or board.initial_hunter_count) and
            board.initial_hunter_count<=1 and (not board.initial_hunter_count or rules.allow_repeat_guard) and
            board.day==1 and board.phase=='day' and not board.history and
            board.alive==tuple(range(1,board.player_count+1)) and
            strategy.day=='random' and strategy.night=='random' and
            not (rules.allow_self_bite and not strategy.include_self_bite) and
            not any(board.claims[p-1]=='seer' for p in board.alive) and
            not (strategy.disclosure_for('medium')=='all' and strategy.fake_reports=='max' and
                 any(board.claims[p-1]=='medium' for p in board.alive)))


def root_screen_forecast(board,rules,strategy,*,max_work=250000,max_seconds=20):
    """Full initial screen metrics from one complete latent secret law."""
    if not root_screen_eligible(board,rules,strategy):
        return FuturePending('root_secret_screen_scope_unimplemented')
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            branch=prepare_root_secrets(board,rules,max_work=max_work)
            if isinstance(branch,FuturePending):return branch
            e=RootSecretEngine(rules,strategy,max_work=max_work)
            value=e.solve(board,branch.public_law,(),branch.physical_law,None,physical=branch.physical)
            targets=legal_targets(board,rules,strategy)
            actions=tuple((t,e.act(board,branch.public_law,(),t,branch.physical_law,None,
                                  physical=branch.physical)) for t in targets)
            from .model_a_public import horizon_for_action
            horizons=tuple((t,horizon_for_action(e,board,branch.public_law,(),t,branch.physical_law))
                           for t in targets)
            return Forecast(value,actions,horizons)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_replay_eligible(game,board,rules,strategy):
    """Saved uniform history with observed publications; no invented CO law."""
    if (not game.get('history') or not (board.initial_seer_count or board.initial_hunter_count) or
            board.initial_hunter_count>1 or board.initial_hunter_count and not rules.allow_repeat_guard):
        return False
    snapshots=(*game['history'],game)
    return (strategy.day==strategy.night=='random' and
            not (rules.allow_self_bite and not strategy.include_self_bite) and
            all(Strategy(**step.get('policy',{})).day==Strategy(**step.get('policy',{})).night=='random'
                for step in snapshots))


def observe_root_snapshot(branch,game,index,rules):
    """Replay the existing public observations, then condition the joint ledger.

    Hand reports remain truth-support filters. Their target frequencies never
    replace Model A role weights or introduce a fake-report selection law.
    """
    from .seer_manual import replay,migrate_game
    from .report_publication import publication_slot
    from .seer_acquisition import SeerReport,condition_publications
    snapshot=game['history'][index] if index<len(game['history']) else game
    slot=2*(branch.public.day-1)+(branch.public.phase=='night')
    prefix={**game,'history':game['history'][:index],
            'claims':snapshot.get('claims',['latent']*branch.public.player_count),
            'claim_policy':snapshot.get('claim_policy',{}),'policy':snapshot.get('policy',{}),
            'result_disclosure_model':snapshot.get('result_disclosure_model'),
            'rules':asdict(rules),'seer_mode':'information-fixed-v1',
            'seer_options':{'initial_rule':rules.initial_seer,'likelihood':'compatibility'},
            'seer_inputs':[r for r in game.get('seer_inputs',()) if publication_slot(game,'seer',r)<=slot],
            'reports':[r for r in game.get('reports',()) if publication_slot(game,'medium',r)<=slot]}
    _,progress=replay(migrate_game(prefix))
    observed=progress.board
    reports=tuple(SeerReport(r['day'],max(r['day'],1+publication_slot(game,'seer',r)//2),
                            r['reporter'],r['target'],r['color'])
                  for r in prefix['seer_inputs'] if r['target'] is not None and r['color'] is not None)
    try:kept=condition_publications(branch.public_law.hypotheses,reports)
    except ValueError:return FuturePending('root_secret_public_history_zero_support')
    signatures={(h.roles,h.acquisitions,h.guards,h.attacks) for h in kept}
    return observe_root_public(branch,observed,
        lambda h:(h.roles,h.acquisitions,h.guards,h.attacks) in signatures,past=reports)


def replay_root_secrets(game,board,rules,strategy,*,max_work=250000,max_seconds=20):
    """Recreate actual joint histories; observed bites use the configured policy.

    Q is restored from the existing public replay only after P is conditioned.
    Actions recorded in history are observations, not target-row interventions.
    """
    from .exact import initial_board,condition_claims,group_initial_board,ClaimPolicy
    if not root_replay_eligible(game,board,rules,strategy):
        return FuturePending('root_secret_replay_scope_unimplemented')
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            seed=initial_board(board.player_count,game.get('wolves',1),game.get('mediums',0),
                               game.get('seers',0),game.get('hunters',0),experimental_cast=True)
            first=game['history'][0]
            claims=tuple(first.get('claims',('latent',)*board.player_count))
            cp=ClaimPolicy(**first.get('claim_policy',{}))
            seed=(group_initial_board(seed,claims,cp) if game.get('model')=='group'
                  else condition_claims(seed,claims,cp))
            branch=prepare_root_secrets(seed,rules,max_work=max_work)
            if isinstance(branch,FuturePending):return branch
            for index,step in enumerate(game['history']):
                branch=observe_root_snapshot(branch,game,index,rules)
                if isinstance(branch,FuturePending):return branch
                policy=Strategy(**step['policy']);target=step['target']
                candidates=branch.public.alive if branch.public.phase=='night' and target is None else (target,)
                selected=[]
                for action in candidates:
                    active=branch;mass=F(1)
                    if branch.public.phase=='night':
                        legal=lambda h:policy.include_self_bite or not h.roles[0]&(1<<(action-1))
                        hs=tuple(replace(h,mass=h.mass/F(len(branch.public.alive) if policy.include_self_bite else
                            len(branch.public.alive)-(h.roles[0]&branch.public.alive_mask).bit_count()))
                            for h in branch.physical_law.hypotheses if legal(h))
                        if not hs:continue
                        mass=sum((h.mass for h in hs),F())
                        own=replace(branch.physical_law,hypotheses=normalize(hs))
                        active=replace(branch,physical_law=own,
                                       physical=physical_board(branch.public,own,branch.physical))
                    children=step_root_action(active,action,rules,policy,max_work=max_work,
                                              max_seconds=max_seconds,publish=False)
                    if isinstance(children,FuturePending):return children
                    expected=branch.public.alive if target is None else tuple(p for p in branch.public.alive if p!=target)
                    selected.extend((mass*q,c) for q,c in children if not c.public.winner and c.public.alive==expected)
                if not selected:return FuturePending('root_secret_replay_observation_zero_support')
                template=selected[0][1]
                entries=normalize(tuple(replace(h,mass=q*h.mass) for q,c in selected for h in c.physical_law.hypotheses))
                own=replace(template.physical_law,hypotheses=entries)
                physical=physical_board(template.public,own,template.physical)
                # Uniform saved policies depend only on roles and owned records.
                # Restore Q per world, retaining the observed guard/bite mixture.
                branch=observe_root_public(RootSecretBranch(physical,own,physical,own,template.past),
                                           template.public,lambda h:True)
                if isinstance(branch,FuturePending):return branch
            branch=observe_root_snapshot(branch,game,len(game['history']),rules)
            if isinstance(branch,FuturePending):return branch
            facts=('alive','day','phase','history')
            if any(getattr(branch.public,k)!=getattr(board,k) for k in facts):
                return FuturePending('root_secret_replay_board_mismatch')
            return observe_root_public(branch,board,lambda h:True)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_branch_forecast(branch,rules,strategy,*,max_work=250000,max_seconds=20):
    """One retained joint law supplies overview, target rows and dawn values."""
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            e=RootSecretEngine(rules,strategy,max_work=max_work)
            b=branch.public;s=branch.public_law;past=branch.past;own=branch.physical_law
            value=e.solve(b,s,past,own,None,physical=branch.physical)
            from .belief_projection import project_private
            from .exact import forced_action_worlds,replace_worlds
            from .model_a_public import horizon_for_action
            targets=legal_targets(b,rules,strategy)
            laws={t:project_private(own,replace_worlds(branch.physical,
                forced_action_worlds(branch.physical,t,rules,strategy)),marginalize_private=False)
                if b.phase=='night' else own for t in targets}
            actions=tuple((t,e.act(b,s,past,t,laws[t],None,
                physical=physical_board(b,laws[t],branch.physical))) for t in targets)
            horizons=tuple((t,horizon_for_action(e,b,s,past,t,laws[t])) for t in targets)
            return Forecast(value,actions,horizons)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)



def root_seer_forecast(branch,player,acquisitions,rules,strategy,*,max_work=250000,max_seconds=20):
    """Own scan interventions over the unchanged public joint policy law."""
    from .seer_future_uniform import candidates
    compatible=lambda h:bool(h.roles[2]&(1<<(player-1))) and all(a in h.acquisitions for a in acquisitions)
    actor=root_actor_view(branch,compatible)
    if isinstance(actor,FuturePending):return actor
    histories={tuple(a for a in h.acquisitions if a.player==player) for h in actor.physical_law.hypotheses}
    if len(histories)!=1:return FuturePending('seer_view_past_private_history_unresolved')
    choices={candidates(h,player,branch.public.alive) for h in actor.physical_law.hypotheses}
    if len(choices)!=1:return FuturePending('seer_view_target_generation_support_unresolved')
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    day=branch.public.day+1;values=[]
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            engine=RootSecretEngine(rules,strategy,max_work=max_work)
            for target in next(iter(choices)):
                def observer(h,state,target=target):
                    return compatible(h) and (len(state.rosters)<day or
                        player not in state.rosters[day-1] or target not in state.rosters[day-1] or
                        any(a.player==player and a.day==day and a.target==target for a in h.acquisitions))
                value=engine.solve(branch.public,branch.public_law,branch.past,actor.physical_law,
                    observer,physical=physical_board(branch.public,actor.physical_law,branch.physical))
                values.append((target,value))
            return tuple(values)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_guard_forecast(branch,player,guards,rules,strategy,*,max_work=250000,max_seconds=20):
    """Owner guard records condition P; public policy continues using Q."""
    from .guard_view_forecast import guard_forecast
    compatible=lambda h:bool(h.roles[3]&(1<<(player-1))) and all(g in h.guards for g in guards)
    actor=root_actor_view(branch,compatible)
    if isinstance(actor,FuturePending):return actor
    from .exact import replace_worlds
    private=replace_worlds(branch.public,actor.belief.public_roles)
    return guard_forecast(branch.public,player,private,branch.public_law,branch.past,rules,strategy,
        guards=guards,private_state=actor.physical_law,engine_factory=RootSecretEngine,
        max_work=max_work,max_seconds=max_seconds)


def root_wolf_forecast(branch,players,attacks,rules,strategy,*,max_work=250000,max_seconds=20):
    """Aggregate unknown other roles and their secrets before each wolf action."""
    mask=sum(1<<(p-1) for p in players)
    actor=root_actor_view(branch,lambda h:h.roles[0]==mask and all(a in h.attacks for a in attacks))
    if isinstance(actor,FuturePending):return actor
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            from .model_a_public import horizon_for_action
            engine=RootSecretEngine(rules,strategy,max_work=max_work)
            own=actor.physical_law;b=branch.public;state=branch.public_law;past=branch.past
            physical=physical_board(b,own,branch.physical)
            targets=legal_targets(physical,rules,strategy)
            values=tuple((t,engine.act(b,state,past,t,own,None,physical=physical)) for t in targets)
            dawn={t:horizon_for_action(engine,b,state,past,t,own) for t in targets}
            return values,dawn,actor.belief
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)
