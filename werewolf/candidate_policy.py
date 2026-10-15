"""Candidate rules from exact automorphisms of the complete shared input.

A private focal information key is not announced to other actors. The SAME
candidate rule applies to every exactly renamed information/action pair, and
uniform ties retain all equivalent targets. No marginal-only equality is used.
"""
from .actor_information import wolf_information_groups
from .exact_renaming import canonical_key
from .policy_choice import uniform_policy

class CandidateRules:
    def __init__(self,board,state,past,rules,strategy):
        self.actions={};self.classes={}
        pairs={};marginal_cache={};serialization_cache={}
        for info,mass,group in wolf_information_groups(state):
            actions=tuple(t for t in board.alive if strategy.include_self_bite or not info.initial_roster&(1<<(t-1)))
            self.actions[info]=actions
            for target in actions:
                key=canonical_key(board,state,past,group,None,rules,strategy,target=target,marginal_cache=marginal_cache,serialization_cache=serialization_cache)
                key=('exact',key) if key is not None else ('identity-action',info,target)
                self.classes[info,target]=pairs.setdefault(key,len(pairs))
        # Compile pure row replacements once for this complete public source.
        self.replacements={};self.replacement_masks={}
        for candidate_class in set(self.classes.values()):
            rows={}
            for owned,actions in self.actions.items():
                matches=tuple(t for t in actions if self.classes[owned,t]==candidate_class)
                if matches:rows[owned]=uniform_policy(matches)
            self.replacements[candidate_class]=rows
            self.replacement_masks[candidate_class]={owned:sum(1<<(t-1) for t,q in policy)
                                                     for owned,policy in rows.items()}

    def candidate(self,profile,info,target):
        if target not in self.actions[info]:raise ValueError('Legal candidate required')
        rows=self.replacements[self.classes[info,target]]
        return tuple((owned,rows.get(owned,policy)) for owned,policy in profile)
