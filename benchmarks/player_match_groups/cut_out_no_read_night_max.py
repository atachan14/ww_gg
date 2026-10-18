"""Five-player structural and monitored dependency cut. Comparison only."""
from dataclasses import replace
from fractions import Fraction as F
from .cut_out_latent_max import graph as random_graph,LatentMaxOrigin,scan_values as latent_scans
from .cut_out_model_a import adapt_no_read_night_max_model_a,_reason
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_max_game import CutOutMaxEngine
from .cut_out_uniform_game import evaluate as common_evaluate
from .partitioned_match_groups import UnsupportedPartition
from werewolf.exact import Rules,Strategy
from werewolf.information_set_forecast import Pending
from werewolf.policy_certificates import ProfileSearch,ProfileCertificate,best_response_profile


def guarded_profile_probe(b,s,past,rules,strategy,*,max_seconds=12):
    """Fresh exact evaluators; first actual profile read invalidates ALL rows."""
    from werewolf.actor_information import wolf_information_groups
    from werewolf.policy_choice import uniform_policy
    from werewolf.candidate_policy import CandidateRules
    from werewolf.wolf_profile_certificate import FixedPublicWolfProfile,_PolicyRead
    from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded
    from werewolf.board_future import evidence_reconstruction
    if s.public_roles!=tuple(sorted(b.worlds)):raise ValueError('complete public source required')
    groups=wolf_information_groups(s)
    legal=tuple((i,tuple(p for p in b.alive if not i.initial_roster&(1<<(p-1)))) for i,m,g in groups)
    profile=tuple((i,uniform_policy(actions)) for i,actions in legal)
    total=1
    for i,actions in legal:total*=(1<<len(actions))-1
    diagnostics=dict(profile_reads=0,complete_candidate_scores=0,candidate_engines=0,theoretical_profiles=total)
    scores={}
    try:
        with calculation_budget(100000,max_seconds=max_seconds),evidence_reconstruction():
            candidate_rules=CandidateRules(b,s,past,rules,strategy)
            for info,mass,group in groups:
                row=[]
                for target in dict(legal)[info]:
                    candidate=candidate_rules.candidate(profile,info,target)
                    engine=FixedPublicWolfProfile(b,s,past,rules,strategy,candidate,stop_on_policy_read=True,max_work=100000)
                    diagnostics['candidate_engines']+=1
                    try:value=engine.act(b,s,past,target,group,None)
                    finally:diagnostics['profile_reads']+=engine.policy_reads
                    row.append((target,value));diagnostics['complete_candidate_scores']+=1
                scores[info]=tuple(row)
            chosen,rows=best_response_profile(legal,scores,maximize=False)
        return ProfileSearch('unique',total,1,(ProfileCertificate(chosen,rows),),proof='guarded_no_policy_reads'),diagnostics
    except _PolicyRead:
        return ProfileSearch('dependency_unfinished',total,0,reason='fixed_public_profile_read',proof='read_guard_refusal'),diagnostics
    except (Pending,CalculationBudgetExceeded) as error:
        return ProfileSearch('dependency_unfinished',total,0,reason=getattr(error,'reason',str(error)),proof='no_partial_certificate'),diagnostics


def certify_night(b,s,past,rules,strategy):
    # Exactly one current night; every subsequent 3-player execution terminates.
    # No guardian and no active public abilities can read an anchor kernel.
    if (b.player_count!=5 or len(b.alive)!=4 or b.phase!='night' or b.day!=1 or b.winner
        or b.initial_hunter_count or b.initial_medium_count or b.initial_seer_count!=1
        or b.claims!=('latent',)*5 or b.wolf_count_distribution!={1:F(1)}
        or rules!=Rules(initial_seer='none') or strategy!=Strategy(day='max',night='max',fake_reports=strategy.fake_reports)
        or len(b.history)!=1 or b.history[0].phase!='day' or past or len(s.rosters)!=1):
        return ProfileSearch('dependency_unfinished',0,0,reason='five_player_no_read_structure_unproved'),{}
    return guarded_profile_probe(b,s,past,rules,strategy)


class NoReadNightMaxEngine(CutOutMaxEngine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.no_read_certificates={};self.no_read_diagnostics={}
    def wolf_policy(self,b,s,past,mask,history=()):
        from werewolf.actor_information import WolfInformation
        key=(self.rules,self.strategy,b,s,past)
        if key not in self.no_read_certificates:
            result,diagnostics=certify_night(b,s,past,self.rules,self.strategy)
            self.no_read_diagnostics[key]=(result,diagnostics)
            if result.selected is None:raise Pending('no_read_night_'+str(result.reason))
            self.no_read_certificates[key]=result.selected
        info=WolfInformation(mask,history)
        policy=dict(self.no_read_certificates[key].profile).get(info)
        if policy is None:raise Pending('no_read_night_roster_missing')
        return policy


def graph(fake_reports='random'):
    spec=replace(random_graph(5,0,'none').engine.baseline.spec,strategy=Strategy(day='max',night='max',fake_reports=fake_reports))
    adapter=adapt_no_read_night_max_model_a(spec)
    if isinstance(adapter,UnsupportedPartition):raise ValueError(adapter.reason)
    return SavedCutOutGraph(adapter,origin_factory=LatentMaxOrigin)


def evaluate(source,**kwargs):
    if not isinstance(source,SavedCutOutGraph):return UnsupportedPartition('constructed saved graph required')
    reason=_reason(source.engine.baseline.spec,max_trial=True,latent_max=True,no_read_night_max=True)
    if reason:return UnsupportedPartition(reason)
    if kwargs.get('official_reference'):return common_evaluate(source,**kwargs)
    return common_evaluate(source,engine_class=NoReadNightMaxEngine,**kwargs)


def scan_values(source,view,**kwargs):return latent_scans(source,view,_no_read_night_max=True,**kwargs)
