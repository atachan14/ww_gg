"""Local exact key-construction adapter; no game law or equality is changed."""
from collections import OrderedDict
import inspect
from werewolf import exact_renaming as original


class RecentSerializations(OrderedDict):
    def get(self,key,default=None):
        if key in self:
            value=self.pop(key);self[key]=value;return value
        # The original serializer inserts only while len < 128. Free one old
        # completed entry on a miss instead of permanently retaining the first.
        if len(self)>=128:self.popitem(last=False)
        return default


def make_canonical():
    mappings=OrderedDict();stats=dict(mask_requests=0,mask_hits=0)
    def masks(ids):
        stats['mask_requests']+=1
        if ids in mappings:
            result=mappings.pop(ids);mappings[ids]=result;stats['mask_hits']+=1;return result
        moved=tuple(1<<(p-1)for p in ids);values=[0]*(1<<len(ids))
        # Induction on removed lowest bit is exactly the old sum over set bits.
        for mask in range(1,len(values)):
            bit=mask&-mask;values[mask]=values[mask^bit]+moved[bit.bit_length()-1]
        result=tuple(values);mappings[ids]=result
        if len(mappings)>256:mappings.popitem(last=False)
        return result
    source=inspect.getsource(original.canonical_key)
    old="""        return tuple(sum(1<<(ids[p]-1) for p in range(b.player_count) if m&(1<<p))
                     for m in range(1<<b.player_count))"""
    if source.count(old)!=1:raise RuntimeError('Canonical implementation changed; adapter must be revalidated')
    namespace=dict(vars(original));namespace['completed_mask_map']=masks
    exec(compile(source.replace(old,'        return completed_mask_map(ids)'),original.__file__,'exec'),namespace)
    return namespace['canonical_key'],masks,stats
