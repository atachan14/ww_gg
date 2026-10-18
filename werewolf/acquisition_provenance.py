"""Opt-in uniform acquisition lineage and trusted audited-group bindings.

Receipts attest a trusted generator invocation and exact carrier references.
Root audits remain a trusted adapter obligation; the ledger never infers a root
from marginal roles, endpoint metadata or an arbitrary callback. Receipts do not
alter numerical keys or automatically authorize a merge.
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
    groups:object=None


@dataclass(frozen=True,eq=False)
class AuditedGroupReceipt:
    groups:tuple


class AcquisitionLedger:
    def __init__(self,engine):
        self._engine=ref(engine)
        self._configuration=(engine.rules,engine.strategy)
        self._generations={}
        self._issued=WeakKeyDictionary()
        self._roots=WeakKeyDictionary()
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
        groups=self.groups_for(before.provenance,board,before)
        inherited=self._groups_record(before.provenance) if groups is not None else None
        owner=None if inherited is None else inherited[2]
        receipt=UniformAcquisitionReceipt(before.provenance,groups=groups)
        self._issued[receipt]=(_frame(board,before),_frame(board,after),receipt.parent,receipt.operation,groups,owner)
        self.stats['paired_receipts']+=1
        if groups is not None:self.stats['inherited_groups']+=1
        return receipt

    def validates(self,receipt,board,before,after):
        """Fixed-field identity checks; no state hash/equality or parent replay."""
        self.stats['validation_requests']+=1
        if not self._supported() or type(receipt)is not UniformAcquisitionReceipt:return False
        row=self._issued.get(receipt)
        if row is None:return False
        parent,child,prior,operation,groups,owner=row
        if groups is not None and (owner is None or not self._owner_current(owner)):return False
        return (after.provenance is receipt and before.provenance is prior and receipt.parent is prior and receipt.operation is operation
            and receipt.groups is groups
            and _same_references(parent,_frame(board,before))
            and _same_references(child,_frame(board,after)))

    def _register_audited_root(self,board,payload,groups,owner):
        """Trusted adapter seam AFTER a complete root audit, not an auditor.

        Callers must not expose this internal assertion as an input API.
        owner=(graph, immutable_saved_data) binds later use to the audited game.
        """
        if not self._supported():return None
        if (type(groups)is not tuple or any(type(g)is not tuple or not g or any(type(p)is not int for p in g) for g in groups)
            or tuple(sorted(p for g in groups for p in g))!=tuple(range(1,board.player_count+1))):
            raise ValueError('Audited groups must partition original players')
        graph,data=owner
        if graph.data is not data:raise ValueError('Audited owner changed')
        receipt=AuditedGroupReceipt(groups)
        baseline=graph.engine.baseline
        self._roots[receipt]=(_frame(board,payload),groups,(graph,data,graph.engine,graph.root,graph.origin,baseline,baseline.rules,baseline.strategy))
        self.stats['audited_roots']+=1
        return receipt

    def _groups_record(self,receipt):
        if not self._supported():return None
        if type(receipt)is AuditedGroupReceipt:
            row=self._roots.get(receipt)
            if row is None:return None
            frame,groups,owner=row
            if receipt.groups is not groups or not self._owner_current(owner):return None
            return frame,groups,owner
        if type(receipt)is UniformAcquisitionReceipt:
            row=self._issued.get(receipt)
            if row is None:return None
            parent,child,prior,operation,groups,owner=row
            # Owner was sealed at issue time. No parent walk, full-state
            # equality or replay is needed at consumption.
            if (owner is None or groups is None or receipt.groups is not groups
                or receipt.parent is not prior or receipt.operation is not operation):return None
            if not self._owner_current(owner):return None
            return child,groups,owner
        return None

    @staticmethod
    def _owner_current(owner):
        graph,data,engine,root,origin,baseline,rules,strategy=owner
        return (graph.data is data and graph.engine is engine and graph.root is root and graph.origin is origin
            and engine.baseline is baseline and baseline.rules is rules and baseline.strategy is strategy)

    def groups_for(self,receipt,board,payload):
        """Consume only an exact, owned frame; never compare complete laws."""
        row=self._groups_record(receipt)
        if row is None:return None
        frame,groups,owner=row
        if payload.provenance is not receipt or not _same_references(frame,_frame(board,payload)):
            return None
        self.stats['group_consumptions']+=1
        return groups

    def public_groups_for(self,receipt,board,state,past):
        row=self._groups_record(receipt)
        if row is None:return None
        frame,groups,owner=row
        if not _same_references(frame[:3],(board,state,past)):return None
        return groups
