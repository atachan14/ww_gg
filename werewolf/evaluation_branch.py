"""Named public/physical carriers for the existing shared action flow."""
from dataclasses import dataclass
from .exact import replace_worlds


def physical_board(public,law,physical=None):
    """Bootstrap only at an entry; otherwise condition the actual branch base.

    The role mass always comes from the branch law, never public beliefs.
    Observable facts must describe the same point in the game. Report fields
    are updated from the public observation. Existing solver-only role
    projections may change count descriptors, but not the surviving facts.
    """
    if physical is None:return replace_worlds(public,law.public_roles)
    facts=('player_count','alive','day','phase','history')
    if any(getattr(public,k)!=getattr(physical,k) for k in facts):
        raise ValueError('Public and physical branch facts disagree')
    fields=('claims','medium_opportunities','reports','report_resolved','guard_prior_roster',
            'initial_medium_count','initial_seer_count','initial_hunter_count')
    updates={k:getattr(public,k) for k in fields}
    if physical.worlds==law.public_roles and all(getattr(physical,k)==v for k,v in updates.items()):
        return physical
    return replace_worlds(physical,law.public_roles,**updates)


@dataclass(frozen=True)
class ActionInputs:
    public_state: object
    past: tuple
    private: object
    observer: object
    physical: object

    def __iter__(self):
        return iter((self.public_state,self.past,self.private,self.observer,self.physical))

    def __getitem__(self,index):return tuple(self)[index]

    def __len__(self):return 5


@dataclass(frozen=True)
class ContinuationInputs:
    public: object
    public_state: object
    past: tuple
    private: object
    observer: object
    physical: object

    def __iter__(self):
        # Existing five-input evaluation helpers can still inspect a carrier;
        # the common policy explicitly passes the physical field onwards.
        return iter((self.public,self.public_state,self.past,self.private,self.observer))

    def __getitem__(self,index):return tuple(self)[index]

    def __len__(self):return 5
