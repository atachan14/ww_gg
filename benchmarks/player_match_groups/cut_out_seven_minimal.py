"""Seven-player minimal input; unrestricted seven/max/guard stays out."""
from .cut_out_model_a import InitialModelASpec,adapt_seven_model_a
from .cut_out_saved_recipes import SavedCutOutGraph
from .partitioned_match_groups import UnsupportedPartition
from werewolf.exact import Rules


def spec(*,latent=False):
    return InitialModelASpec(7,('latent' if latent else 'seer','wolf','latent','latent','latent','latent','latent'),True,
        mediums=0,rules=Rules(initial_seer='none'))


def graph(*,latent=False):
    engine=adapt_seven_model_a(spec(latent=latent))
    return engine if isinstance(engine,UnsupportedPartition) else SavedCutOutGraph(engine)
