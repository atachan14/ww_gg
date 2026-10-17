"""Opt-in numerical prototype: complete continuation keys for two seer CO.

Not wired to the app. No audit oracle or approximate/player-marginal key.
"""
from collections import OrderedDict
from time import perf_counter
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.exact_renaming import canonical_key
from werewolf.board_future import EvidenceKey,evidence_key


class FutureReuseForecast(InformationSetForecast):
    def __init__(self,*args,future_reuse=False,physical_reuse=False,retired_reuse=False,compact_keys=False,fast_parts=False,**kwargs):
        super().__init__(*args,**kwargs);self.future_reuse=future_reuse;self.reuse_public_entry=True
        self.fast_parts=fast_parts;self.key_function=canonical_key;self.mask_stats={}
        if fast_parts:
            from .fast_key_parts import make_canonical
            self.key_function,_,self.mask_stats=make_canonical()
        self.compact_keys=compact_keys;self.retired_reuse=retired_reuse;self.physical_reuse=physical_reuse;self.physical_kernels=OrderedDict()
        self.reuse_sources=OrderedDict();self.reuse_serialization={};self.reuse_marginals={}
        if fast_parts:
            from .fast_key_parts import RecentSerializations
            self.reuse_serialization={'boards':RecentSerializations(),'states':RecentSerializations()}
        self.reuse_stats=dict(key_seconds=0.,key_requests=0,key_source_hits=0,key_supported=0,key_value_hits=0,key_action_hits=0,generated_publication_branches=0,acquisition_states=0,kernel_requests=0,kernel_hits=0,kernel_computations=0,kernel_key_seconds=0.)

    def full_renamed_key(self,b,s,past,private,observer,*,target=None,physical=None):
        live=sum(b.claims[p-1]=='seer'for p in b.alive)
        gap=(b.initial_seer_count==1 and(live==2 or live==1 and b.claims.count('latent')>4)
             or self.retired_reuse and b.initial_seer_count==0 and len(b.alive)<=5)
        if(not self.future_reuse or not self.exact_renaming or not self.memoize_flows or not self.reuse_public_entry or self.trace is not None or b.initial_hunter_count or b.initial_medium_count
            or observer is not None or self.strategy.day!='random'or self.strategy.night!='random'
            or self.strategy.fake_reports!='random'
            or tuple(self.strategy.seer_position)!=('unvisited','uniform')
            or tuple(self.strategy.fake_seer_policy)not in(('uniform',),('noncontradictory','uniform'))
            or not gap):
            return super().full_renamed_key(b,s,past,private,observer,target=target,physical=physical)
        return self.complete_reuse_key(b,s,past,private,observer,target=target,physical=physical)

    def complete_reuse_key(self,b,s,past,private,observer,*,target=None,physical=None):
        started=perf_counter();stats=self.reuse_stats;stats['key_requests']+=1
        values=(self.rules,self.strategy,b,s,past,private,observer,target,physical)
        source=evidence_key(self,values)if self.compact_keys else values
        if source in self.reuse_sources:
            key=self.reuse_sources.pop(source);self.reuse_sources[source]=key;stats['key_source_hits']+=1
        else:
            if len(self.reuse_marginals)>128:self.reuse_marginals.clear()
            key=self.key_function(b,s,past,private,observer,self.rules,self.strategy,target=target,physical=physical,
                max_mappings=120,marginal_cache=self.reuse_marginals,serialization_cache=self.reuse_serialization)
            if key is not None and self.compact_keys:key=EvidenceKey(key,(hash(key),))
            self.reuse_sources[source]=key
            if len(self.reuse_sources)>2048:self.reuse_sources.popitem(last=False)
        if key is not None:
            stats['key_supported']+=1
            if key in(self.values if target is None else self.action_values):stats['key_value_hits'if target is None else'key_action_hits']+=1
        stats['key_seconds']+=perf_counter()-started
        return key

    def generate_publications(self,*args):
        result=super().generate_publications(*args)
        self.reuse_stats['generated_publication_branches']+=len(result)
        return result

    def acquire(self,b,state):
        missing=(b,state)not in self.acquired
        result=super().acquire(b,state)
        if missing:self.reuse_stats['acquisition_states']+=1
        return result

    def evaluate(self,*args,**kwargs):
        previous=self.reuse_public_entry;self.reuse_public_entry=False
        try:return super().evaluate(*args,**kwargs)
        finally:self.reuse_public_entry=previous

    def physical_children(self,b,target):
        stats=self.reuse_stats;stats['kernel_requests']+=1
        if not self.physical_reuse or not self.memoize_flows or b.initial_hunter_count:
            stats['kernel_computations']+=1
            return super().physical_children(b,target)
        started=perf_counter();key=(b,target,self.rules,self.strategy)
        if key in self.physical_kernels:
            result=self.physical_kernels.pop(key);self.physical_kernels[key]=result
            stats['kernel_hits']+=1;stats['kernel_key_seconds']+=perf_counter()-started
            return result
        stats['kernel_key_seconds']+=perf_counter()-started
        stats['kernel_computations']+=1
        result=super().physical_children(b,target)
        self.physical_kernels[key]=result
        if len(self.physical_kernels)>4096:self.physical_kernels.popitem(last=False)
        return result

    def public_children(self,b,target,guard_state=None):
        # Daytime raw casualties use this exact Board. Night public observation
        # has a different count-conditioning law and stays on its original path.
        if b.phase=='day'and not b.initial_hunter_count:return self.physical_children(b,target)
        return super().public_children(b,target,guard_state)
