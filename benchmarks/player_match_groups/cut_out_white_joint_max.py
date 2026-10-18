"""M1/initial-white entry requires all source support and every candidate proof."""
from dataclasses import replace
from .cut_out_model_a import adapt_white_joint_night_max_model_a,_reason
from .cut_out_latent_max import graph as random_graph,LatentMaxOrigin,scan_values as common_scans
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_no_read_night_max import WhiteJointNightMaxEngine
from .cut_out_uniform_game import evaluate as common_evaluate
from .partitioned_match_groups import UnsupportedPartition
from werewolf.exact import Strategy


def graph(fake_reports='max'):
    spec=replace(random_graph(5,1,'random_white').engine.baseline.spec,
        strategy=Strategy(day='max',night='max',fake_reports=fake_reports))
    adapter=adapt_white_joint_night_max_model_a(spec)
    if isinstance(adapter,UnsupportedPartition):raise ValueError(adapter.reason)
    return SavedCutOutGraph(adapter,origin_factory=LatentMaxOrigin)


def evaluate(source,**kwargs):
    if not isinstance(source,SavedCutOutGraph):return UnsupportedPartition('constructed saved graph required')
    reason=_reason(source.engine.baseline.spec,max_trial=True,latent_max=True,no_read_night_max=True,white_joint=True)
    if reason:return UnsupportedPartition(reason)
    if kwargs.get('official_reference'):return common_evaluate(source,**kwargs)
    return common_evaluate(source,engine_class=WhiteJointNightMaxEngine,**kwargs)


def scan_values(source,view,**kwargs):return common_scans(source,view,_no_read_night_max=True,_white_joint=True,**kwargs)
