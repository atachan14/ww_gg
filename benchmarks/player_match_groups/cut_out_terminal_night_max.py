"""Exact terminal dependency cut, not a general latent night-max entry."""
from dataclasses import replace
from fractions import Fraction as F
from .cut_out_latent_max import graph as uniform_night_graph,LatentMaxOrigin,scan_values as latent_scan_values
from .cut_out_model_a import adapt_terminal_night_max_model_a,_reason
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_max_game import CutOutMaxEngine
from .cut_out_uniform_game import evaluate as evaluate_common
from .partitioned_match_groups import UnsupportedPartition
from werewolf.exact import Strategy
from werewolf.actor_information import WolfInformation
from werewolf.information_set_forecast import Pending


class TerminalNightMaxEngine(CutOutMaxEngine):
    def wolf_policy(self,b,s,past,mask,history=()):
        if (b.phase!='night' or len(b.alive)!=3 or b.initial_hunter_count or
            b.wolf_count_distribution!={1:F(1)} or self.rules.allow_self_bite or self.strategy.include_self_bite):
            raise Pending('terminal_night_max_boundary_unproved')
        # Keep the existing own-information minimization and uniform ties.
        # Every candidate is physically terminal; no later public policy is read.
        group=WolfInformation(mask,history).condition_public(s)
        result=super().wolf_policy(b,s,past,mask,history)
        assert all(self.act(b,s,past,p,group,None)==0 for p,q in result)
        return result


def graph(mediums=0,initial='none',fake_reports='random'):
    spec=replace(uniform_night_graph(4,mediums,initial).engine.baseline.spec,
        strategy=Strategy(day='max',night='max',fake_reports=fake_reports))
    adapter=adapt_terminal_night_max_model_a(spec)
    if isinstance(adapter,UnsupportedPartition):raise ValueError(adapter.reason)
    return SavedCutOutGraph(adapter,origin_factory=LatentMaxOrigin)


def evaluate(source,**kwargs):
    if not isinstance(source,SavedCutOutGraph):return UnsupportedPartition('constructed saved graph required')
    reason=_reason(source.engine.baseline.spec,max_trial=True,latent_max=True,terminal_night_max=True)
    if reason:return UnsupportedPartition(reason)
    if kwargs.get('official_reference'):return evaluate_common(source,**kwargs)
    return evaluate_common(source,engine_class=TerminalNightMaxEngine,**kwargs)


def scan_values(source,view,**kwargs):
    return latent_scan_values(source,view,_terminal_night_max=True,**kwargs)
