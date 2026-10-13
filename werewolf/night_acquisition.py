"""Generate separate public/viewer ability histories on one predeath roster."""
from dataclasses import dataclass, replace
from .seer_acquisition import normalize


@dataclass(frozen=True)
class AcquiredLaws:
    public: object
    private: object = None


def acquire_laws(board, public, generate, *, private=None, observer=None, inconsistent=None):
    """generate(state, alive) receives no observer; observer filters own law only.

    Generation/Pending budgets are owned by the caller. This preserves legacy
    generation caching and the information-set engine's distinct work contract.
    """
    if observer is not None and (private is None or inconsistent is None):
        raise ValueError('Observer filtering requires a private law and failure contract')
    public_next = generate(public, board.alive)
    if private is None:
        return AcquiredLaws(public_next)
    own = generate(private, board.alive)
    if observer is not None:
        kept = tuple(h for h in own.hypotheses if observer(h,own))
        if not kept:
            raise inconsistent()
        own = replace(own,hypotheses=normalize(kept))
    return AcquiredLaws(public_next,own)
