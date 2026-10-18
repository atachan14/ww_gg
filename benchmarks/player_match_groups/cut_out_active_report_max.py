"""Existing medium report max on complete joint laws. No new CO/report rule."""
from fractions import Fraction as F
from .cut_out_model_a import InitialModelASpec,adapt_active_report_max_model_a,_reason
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_max_game import CutOutMaxEngine
from .cut_out_uniform_game import evaluate as common_evaluate
from .cut_out_no_read_night_max import guarded_profile_probe
from .partitioned_match_groups import UnsupportedPartition
from werewolf.exact import Rules,Strategy
from werewolf.board_future import SavedOrigin
from werewolf.evaluation_branch import ContinuationInputs
from werewolf.information_set_forecast import Pending


class ActiveReportOrigin(SavedOrigin):
    def _reconstruct(self):
        from werewolf.root_secret_flow import prepare_root_secrets
        from werewolf.seer_future_uniform import FuturePending
        b=self.board_data.roles().board
        if (b.player_count not in (4,5) or b.day!=1 or b.phase!='day' or b.history
            or b.initial_hunter_count or b.initial_seer_count!=1 or b.initial_medium_count!=1
            or b.claims!=('medium','medium')+('latent',)*(b.player_count-2)
            or self.strategy!=Strategy() or self.rules not in (Rules(initial_seer='none'),Rules(initial_seer='random_white'))):
            raise Pending('active_report_initial_scope_unproved')
        root=prepare_root_secrets(b,self.rules,max_work=100000)
        if isinstance(root,FuturePending):raise Pending(root.reason)
        return ContinuationInputs(root.public,root.public_law,root.past,root.physical_law,None,root.physical)


class ActiveReportMaxEngine(CutOutMaxEngine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.report_decisions={};self.report_certificates={};self.report_diagnostics={}

    def wolf_policy(self,b,s,past,mask,history=()):
        from werewolf.actor_information import WolfInformation
        key=(self.rules,self.strategy,b,s,past)
        if key not in self.report_certificates:
            if (b.player_count not in (4,5) or len(b.alive)!=b.player_count-1 or b.phase!='night' or b.day!=1
                or b.initial_hunter_count or b.initial_medium_count!=1 or b.initial_seer_count!=1
                or b.claims!=('medium','medium')+('latent',)*(b.player_count-2)
                or b.wolf_count_distribution!={1:F(1)} or len(b.history)!=1 or past or len(s.rosters)!=1):
                raise Pending('active_report_night_structure_unproved')
            result,diagnostics=guarded_profile_probe(b,s,past,self.rules,self.strategy)
            self.report_diagnostics[key]=(result,diagnostics)
            if result.selected is None:raise Pending('active_report_night_'+str(result.reason))
            self.report_certificates[key]=result.selected
        policy=dict(self.report_certificates[key].profile).get(WolfInformation(mask,history))
        if policy is None:raise Pending('active_report_owned_roster_missing')
        return policy

    def record_report_choices(self,b,s,past,scored,chosen):
        # The production common flow owns selection and merge; this hook only
        # retains exact candidate identities and weights for finite comparisons.
        if not getattr(self,'_board_evidence_snapshot',False):self.report_decisions[b,s,past]=(scored,chosen)


def graph(players=5,initial='none'):
    spec=InitialModelASpec(players,('medium','medium')+('latent',)*(players-2),True,mediums=1,seers=1,
        rules=Rules(initial_seer=initial),strategy=Strategy())
    adapter=adapt_active_report_max_model_a(spec)
    if isinstance(adapter,UnsupportedPartition):raise ValueError(adapter.reason)
    return SavedCutOutGraph(adapter,origin_factory=ActiveReportOrigin)


def evaluate(source,**kwargs):
    if not isinstance(source,SavedCutOutGraph):return UnsupportedPartition('constructed saved graph required')
    reason=_reason(source.engine.baseline.spec,max_trial=True,latent_max=True,active_report_max=True)
    if reason:return UnsupportedPartition(reason)
    if kwargs.get('official_reference'):return common_evaluate(source,**kwargs)
    return common_evaluate(source,engine_class=ActiveReportMaxEngine,**kwargs)


def scan_values(source,view,**kwargs):
    from .cut_out_latent_max import scan_values as common_scans
    return common_scans(source,view,_active_report_max=True,**kwargs)
