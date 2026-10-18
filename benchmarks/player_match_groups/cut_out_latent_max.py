"""Opt-in latent initial-law bridge; ordinary max eligibility is unchanged."""
from .cut_out_model_a import InitialModelASpec,adapt_latent_max_model_a,_reason
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_max_game import CutOutMaxEngine
from .cut_out_uniform_game import evaluate as evaluate_common
from .partitioned_match_groups import UnsupportedPartition
from werewolf.board_future import SavedOrigin
from werewolf.evaluation_branch import ContinuationInputs
from werewolf.exact import Rules,Strategy


class LatentMaxOrigin(SavedOrigin):
    def _reconstruct(self):
        from werewolf.root_secret_flow import prepare_root_secrets
        from werewolf.seer_future_uniform import FuturePending
        from werewolf.information_set_forecast import Pending
        game=self.board_data.to_game();b=self.board_data.roles().board
        if (game.get('history') or b.history or b.day!=1 or b.phase!='day'
            or b.player_count not in (4,5) or b.initial_hunter_count or b.initial_seer_count!=1
            or b.initial_medium_count not in (0,1) or b.claims not in (('latent',)*b.player_count,('medium',)+('latent',)*(b.player_count-1))
            or self.strategy.fake_reports=='max' and 'medium' in b.claims
            or not (self.strategy==Strategy(day='max',night='random',fake_reports=self.strategy.fake_reports) or
                (b.player_count==4 and b.claims==('latent',)*4 or b.player_count==5 and (b.initial_medium_count,self.rules.initial_seer) in ((0,'none'),(1,'random_white')) and b.claims==('latent',)*5) and self.strategy==Strategy(day='max',night='max',fake_reports=self.strategy.fake_reports))
            or self.rules not in (Rules(initial_seer='none'),Rules(initial_seer='random_white'))):
            raise Pending('latent_max_initial_comparison_scope')
        root=prepare_root_secrets(b,self.rules,max_work=100000)
        if isinstance(root,FuturePending):raise Pending(root.reason)
        return ContinuationInputs(root.public,root.public_law,root.past,root.physical_law,None,root.physical)


def graph(players=5,mediums=1,initial='random_white',medium_co=False,fake_reports='random'):
    claims=('medium',)+('latent',)*(players-1) if medium_co else ('latent',)*players
    spec=InitialModelASpec(players,claims,True,mediums=mediums,seers=1,
        rules=Rules(initial_seer=initial),strategy=Strategy(day='max',night='random',fake_reports=fake_reports))
    adapter=adapt_latent_max_model_a(spec)
    if isinstance(adapter,UnsupportedPartition):raise ValueError(adapter.reason)
    return SavedCutOutGraph(adapter,origin_factory=LatentMaxOrigin)


def evaluate(source,**kwargs):
    if not isinstance(source,SavedCutOutGraph):return UnsupportedPartition('constructed saved graph required')
    reason=_reason(source.engine.baseline.spec,max_trial=True,latent_max=True)
    if reason:return UnsupportedPartition(reason)
    if kwargs.get('official_reference'):return evaluate_common(source,**kwargs)
    return evaluate_common(source,engine_class=CutOutMaxEngine,**kwargs)


def scan_values(source,view,*,official_reference=False,max_seconds=25,_terminal_night_max=False,_no_read_night_max=False,_active_report_max=False,_white_joint=False):
    """Existing configured scan interventions; no new max scan/CO strategy."""
    from .cut_out_uniform_game import OwnView,OfficialLabelledEngine
    from werewolf.actor_information import condition_actor_state
    from werewolf.seer_future_uniform import candidates,scan_target_players
    from werewolf.seer_intervention import SeerObserver
    from werewolf.evaluation_branch import physical_board
    from werewolf.board_future import calculation_origin,remember,condition_recipe
    from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded
    from werewolf.information_set_forecast import Pending
    if not isinstance(source,SavedCutOutGraph) or type(view) is not OwnView or view.role!='seer':
        return UnsupportedPartition('explicit latent own seer history required')
    reason=_reason(source.engine.baseline.spec,max_trial=True,latent_max=True,terminal_night_max=_terminal_night_max,no_read_night_max=_no_read_night_max,active_report_max=_active_report_max,white_joint=_white_joint)
    if reason:return UnsupportedPartition(reason)
    if type(max_seconds) not in (int,float) or not 0<max_seconds<=25:
        return UnsupportedPartition('positive <=25s comparison budget required')
    if any(a.player!=view.player for a in view.acquisitions):return UnsupportedPartition('another owner secret is not an own observation')
    root=source.origin()
    if not any(view.accepts(h) for h in root.private.hypotheses):return UnsupportedPartition('own evidence has zero support')
    own=condition_actor_state(root.private,view.accepts)
    histories={tuple(a for a in h.acquisitions if a.player==view.player) for h in own.hypotheses}
    if len(histories)!=1:return UnsupportedPartition('seer_view_past_private_history_unresolved')
    choices={candidates(h,view.player,scan_target_players(root.public_state,root.public.alive)) for h in own.hypotheses}
    if len(choices)!=1:return UnsupportedPartition('seer_view_target_generation_support_unresolved')
    from .cut_out_terminal_night_max import TerminalNightMaxEngine
    from .cut_out_no_read_night_max import NoReadNightMaxEngine,WhiteJointNightMaxEngine
    from .cut_out_active_report_max import ActiveReportMaxEngine
    engine=(OfficialLabelledEngine if official_reference else ActiveReportMaxEngine if _active_report_max else WhiteJointNightMaxEngine if _white_joint else NoReadNightMaxEngine if _no_read_night_max else TerminalNightMaxEngine if _terminal_night_max else CutOutMaxEngine)(source,view=view)
    values=[]
    try:
        with calculation_budget(1000000,max_seconds=max_seconds),calculation_origin(source.data):
            for target in next(iter(choices)):
                observer=SeerObserver(view.player,next(iter(histories)),root.public.day+1,target)
                context=ContinuationInputs(root.public,root.public_state,root.past,own,observer,physical_board(root.public,own,root.physical))
                recipe=condition_recipe(root,context)
                if recipe is None:return UnsupportedPartition('own scan recipe unavailable')
                request=source.root.child(recipe,source.root.facts);remember(engine,request,context)
                values.append((target,engine.solve(*context,physical=context.physical)))
        return tuple(values),engine
    except Pending as error:return UnsupportedPartition(error.reason)
    except CalculationBudgetExceeded:return UnsupportedPartition('comparison evaluation budget exhausted')
