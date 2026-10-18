"""Event-constructed cut-out proof; no generator/whole-law matching on updates.

Only the closed, validated Observation language and constructed symmetric law
of the small prototype are admitted. This is a conservative product-subgroup
restriction, never an arbitrary colour/refinement claim.
"""
from .partitioned_match_groups import PartitionedMatchGroups


class ConstructiveCutOutGroups(PartitionedMatchGroups):
    def _refine_groups(self, context, event):
        # Each label describes a sufficient subgroup of this event's stabilizer.
        # Intersecting inherited blocks retains all previous proofs, without
        # checking any old event or permuting a law. No blocks are ever merged.
        n = self.baseline.players
        self.stats['constructive_events'] += 1
        self.stats['event_rows_read'] += len(event.rows)
        untouched = ('untouched',)
        labels = {p:untouched for p in range(1,n+1)}
        if event.kind == 'co':
            # A simultaneous batch assigns one role per owner. Permutations
            # within each same-role subset preserve the assignment map.
            for p, role in event.rows:labels[p] = ('co',role)
        elif event.kind == 'report':
            # Point-fix EVERY target, including any target which is also a
            # reporter. Other reporters may move only with identical fixed
            # target, colour and acquisition slot. The batch is a multiset of
            # commuting support predicates; never infer report-order semantics.
            targets = {row[1] for row in event.rows}
            for p, target, colour, slot in event.rows:
                labels[p] = ('report',target,colour,slot)
            for p in targets:labels[p] = ('fixed-target',p)
        elif event.kind == 'death':
            # A set of removed players has S_removed x S_remaining stabilizer.
            # No death likelihood/physical transition is supplied by this step.
            for p, in event.rows:labels[p] = ('removed',)
        elif event.kind == 'private_role':
            for p, role in event.rows:labels[p] = ('fixed-owner',p)
        elif event.kind in ('private_result','select'):
            # Conservative point stabilizer of all referenced positions. This
            # can under-share simultaneous patterns; it cannot invent symmetry.
            for row in event.rows:
                for p in row[:2]:labels[p] = ('fixed-position',p)
        else:
            # The base validator rejects unknown kinds BEFORE reaching this.
            raise ValueError('No construction proof for this event kind')
        groups = []
        for parent in context.groups:
            children = {}
            for p in parent:
                self.stats['partition_positions_read'] += 1
                children.setdefault(labels[p],[]).append(p)
            groups.extend(tuple(group) for group in children.values())
        return tuple(groups)