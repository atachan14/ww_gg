"""Opt-in lineage for complete uniform acquisition; never a symmetry root.

Receipts attest a trusted generator invocation and exact carrier references.
They do not assert parent invariance, authorize a merge, or alter numerical keys.
Only observer-free, uniform configured acquisition is currently supported.
Unknown cache identities and replay snapshots retain ordinary results unproved.
"""
from collections import Counter
from dataclasses import dataclass
from weakref import ref,WeakKeyDictionary


def _frame(board,payload):
    return (board,payload.public_state,payload.past,payload.private,payload.observer,payload.physical)


def _same_references(left,right):
    return len(left)==len(right) and all(a is b for a,b in zip(left,right))


@dataclass(frozen=True,eq=False)
class UniformAcquisitionReceipt:
    parent:object
    operation:str='unobserved_uniform_acquisition'


class AcquisitionLedger:
    def __init__(self,engine):
        self._engine=ref(engine)
        self._configuration=(engine.rules,engine.strategy)
        self._generations={}
        self._issued=WeakKeyDictionary()
        self.stats=Counter()

    def _supported(self):
        e=self._engine()
        if e is None:return False
        rules,strategy=self._configuration
        return (e.rules is rules and e.strategy is strategy
            and not getattr(e,'_board_evidence_snapshot',False)
            and (strategy.day,strategy.night,strategy.fake_reports)==('random',)*3
            and tuple(strategy.seer_position)==('unvisited','uniform'))

    def _record_uniform(self,board,before,after):
        # Called only at the canonical acquire_uniform cache fill. Equivalent
        # but nonidentical cache keys are intentionally not re-proved here.
        if not self._supported():return
        self._generations[id(board),id(before)]=(board,before,after)
        self.stats['generation_records']+=1

    def _generation(self,board,before,after):
        row=self._generations.get((id(board),id(before)))
        return row is not None and _same_references(row,(board,before,after))

    def _bind(self,board,before,after):
        if not self._supported():
            self.stats['configuration_declines']+=1;return None
        if before.observer is not None:
            # A caller predicate is an observation operation with a separate
            # proof obligation, even if it happens to retain every hypothesis.
            self.stats['observer_declines']+=1;return None
        if board.phase!='night' or board.initial_hunter_count:
            self.stats['scope_declines']+=1;return None
        if not (self._generation(board,before.public_state,after.public_state)
                and self._generation(board,before.private,after.private)):
            self.stats['unknown_generation_declines']+=1;return None
        receipt=UniformAcquisitionReceipt(before.provenance)
        self._issued[receipt]=(_frame(board,before),_frame(board,after),receipt.parent,receipt.operation)
        self.stats['paired_receipts']+=1
        return receipt

    def validates(self,receipt,board,before,after):
        """Fixed-field identity checks; no state hash/equality or parent replay."""
        self.stats['validation_requests']+=1
        if not self._supported() or type(receipt)is not UniformAcquisitionReceipt:return False
        row=self._issued.get(receipt)
        if row is None:return False
        parent,child,prior,operation=row
        return (after.provenance is receipt and before.provenance is prior and receipt.parent is prior and receipt.operation is operation
            and _same_references(parent,_frame(board,before))
            and _same_references(child,_frame(board,after)))
