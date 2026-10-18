"""Explicit minimal initial six-player uniform inheritance; no UI/registry routing."""
from .cut_out_uniform_game import CutOutUniformEngine,evaluate as common_evaluate
from .cut_out_inherited_groups import InheritedGroupRegistry
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_model_a import ModelAInitialGroups,_reason
from .partitioned_match_groups import UnsupportedPartition
from werewolf.information_set_forecast import Pending
from werewolf.exact import Rules
from werewolf.seer_acquisition import SeerReport


def scope_reason(source):
    if type(source)is not SavedCutOutGraph or type(source.engine)is not ModelAInitialGroups:
        return 'six_inherited_initial_saved_root_witness_required'
    spec=source.engine.baseline.spec;reason=_reason(spec,six=True)
    if source.engine.baseline.players!=6 or reason:return 'six_inherited_uniform_scope_unproved:'+str(reason)
    # Only the two existing3240ad1 input shapes. Other uniform6 shapes can
    # have complete data, but have not passed this incremental comparison gate.
    shape=(spec.mediums,spec.claims,spec.reports)
    if spec.rules!=Rules(initial_seer='random_white') or shape not in (
        (0,('seer','latent','latent','latent','latent','latent'),(SeerReport(1,1,1,3,'white'),)),
        (1,('seer','medium','medium','latent','latent','latent'),(SeerReport(1,1,1,4,'white'),))):
        return 'six_inherited_minimal_input_shape_unproved'
    return None


class SixInheritedUniformEngine(CutOutUniformEngine):
    def make_group_registry(self,graph):
        reason=scope_reason(graph)
        if reason:raise Pending(reason)
        return InheritedGroupRegistry(graph,six=True)

    def groups(self,*args,**kwargs):
        if self.inherited_groups is None:raise Pending('six_inherited_witness_required_no_legacy_fallback')
        return super().groups(*args,**kwargs)


def evaluate(source,**kwargs):
    reason=scope_reason(source)
    if reason:return UnsupportedPartition(reason)
    if kwargs.get('official_reference'):return common_evaluate(source,**kwargs)
    return common_evaluate(source,engine_class=SixInheritedUniformEngine,**kwargs)
