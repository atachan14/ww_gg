"""Comparison-only lossless component hash memoization; no factory integration.

Existing key shape, full equality, ordering, mapping search and cache admission
remain unchanged. Cached hash accelerates a tuple; it never decides equality.
"""
from collections import Counter
import inspect
from werewolf import exact_renaming as original
from .fast_key_parts import make_canonical


def component_tuple_type(stats):
    class ComponentTuple(tuple):
        def __new__(cls,values):
            value=tuple.__new__(cls,values)
            object.__setattr__(value,'_component_hash',None)
            stats['components_created']+=1
            return value
        def __hash__(self):
            stats['component_hash_requests']+=1
            value=self._component_hash
            if value is None:
                value=tuple.__hash__(self)
                object.__setattr__(self,'_component_hash',value)
                stats['component_hash_computations']+=1
            else:stats['component_hash_hits']+=1
            return value
        def __setattr__(self,name,value):raise AttributeError('Immutable component tuple')
        def __delattr__(self,name):raise AttributeError('Immutable component tuple')
    return ComponentTuple


def make_component_canonical():
    # Reuse the SAME fast masks, not an unoptimized substitute constructor.
    unused,masks,mask_stats=make_canonical()
    stats=Counter();component_tuple=component_tuple_type(stats)
    source=inspect.getsource(original.canonical_key)
    changes=(
      ("""        return tuple(sum(1<<(ids[p]-1) for p in range(b.player_count) if m&(1<<p))
                     for m in range(1<<b.player_count))""",'        return completed_mask_map(ids)'),
      ('        result=compute(obj,ids,masks,record_cache)',
       '        result=component_tuple(compute(obj,ids,masks,record_cache))'),
    )
    for before,after in changes:
        if source.count(before)!=1:raise RuntimeError('Canonical source changed; revalidate component adapter')
        source=source.replace(before,after)
    namespace=dict(vars(original));namespace.update(completed_mask_map=masks,component_tuple=component_tuple)
    exec(compile(source,original.__file__,'exec'),namespace)
    return namespace['canonical_key'],stats,mask_stats
# Explicit comparison engine; existing app factories still instantiate ExtensionForecast.
from .extension_reuse import ExtensionForecast
from .fast_key_parts import RecentSerializations

class ComponentReuseForecast(ExtensionForecast):
    def __init__(self,*args,component_audit=False,**kwargs):
        super().__init__(*args,**kwargs)
        fn,self.component_stats,self.mask_stats=make_component_canonical()
        self.component_audit_stats=Counter()
        if component_audit:
            oracle,_,_=make_canonical()
            oracle_cache={'boards':RecentSerializations(),'states':RecentSerializations()}
            oracle_marginals={}
            def checked(*values,**options):
                actual=fn(*values,**options)
                if len(oracle_marginals)>128:oracle_marginals.clear()
                independent=dict(options,serialization_cache=oracle_cache,marginal_cache=oracle_marginals)
                expected=oracle(*values,**independent)
                if actual!=expected or hash(actual)!=hash(expected):raise AssertionError('Complete component key differs from current constructor')
                self.component_audit_stats['keys_compared']+=1
                return actual
            self.key_function=checked
        else:self.key_function=fn