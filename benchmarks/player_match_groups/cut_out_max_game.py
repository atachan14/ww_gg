"""Finite max comparison. Policy selection stays in the existing information set flow."""
from .cut_out_model_a import InitialModelASpec,adapt_max_model_a,_reason
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_uniform_game import CutOutUniformEngine,evaluate as evaluate_uniform
from .partitioned_match_groups import UnsupportedPartition
from werewolf.exact import Rules,Strategy
from werewolf.seer_acquisition import SeerReport
from werewolf.information_set_forecast import InformationSetForecast


class CutOutMaxEngine(CutOutUniformEngine):
    # Reuse the original public day policy / wolf own-information policy.
    # Only action evaluation uses cut-out representatives. Never rank per world.
    def solve(self,*args,**kwargs):return InformationSetForecast.solve(self,*args,**kwargs)


def graph(players=5,mediums=0,night='random'):
    spec=InitialModelASpec(players,('seer',)+('latent',)*(players-1),True,
        mediums=mediums,seers=1,reports=(SeerReport(1,1,1,3,'white'),),
        rules=Rules(initial_seer='random_white'),
        strategy=Strategy(day='max',night=night,fake_reports='random'))
    adapter=adapt_max_model_a(spec)
    if isinstance(adapter,UnsupportedPartition):raise ValueError(adapter.reason)
    return SavedCutOutGraph(adapter)


def evaluate(source,**kwargs):
    reason=_reason(source.engine.baseline.spec,max_trial=True)
    if reason:return UnsupportedPartition(reason)
    if kwargs.get('official_reference'):return evaluate_uniform(source,**kwargs)
    return evaluate_uniform(source,engine_class=CutOutMaxEngine,**kwargs)
