"""Complete continuation values shared by public evaluation entrypoints."""
from dataclasses import dataclass
from fractions import Fraction as F


@dataclass(frozen=True)
class Forecast:
    village_win: F
    action_values: tuple
    by_dawn_values: tuple = ()
    pending_metrics: tuple = ()
