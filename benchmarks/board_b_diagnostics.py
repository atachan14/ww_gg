"""Separate diagnostic entrypoint; normal baseline never imports this module."""
import sys,types
import board_b_benchmark as bench

class ExclusiveDiagnostic(bench.Diagnostic):
    def install(self,new,oracle):
        super().install(new,oracle)
        import gc,time
        self.gc_start=None;self.gc_pause=0.;self.gc_collections={}
        def observe_gc(phase,info):
            if phase=='start':self.gc_start=time.perf_counter() if self.phase is not None else None
            elif self.gc_start is not None:
                self.gc_pause+=time.perf_counter()-self.gc_start
                generation=info['generation'];self.gc_collections[generation]=self.gc_collections.get(generation,0)+1
                self.gc_start=None
        self.gc_callback=observe_gc;gc.callbacks.append(observe_gc)
        from werewolf.information_set_forecast import InformationSetForecast
        # A replay may invoke a future solver. Switch back to 3b there, rather
        # than attributing nested solve time to its outer reconstruction caller.
        if new:
            import werewolf.board_future as flow
            for name in ('register_origin','reconstruct_child','reconstruct_publication','record_publications','record_medium_instruction'):
                self.wrap(flow,name,phase='3a')
        self.wrap(InformationSetForecast,'solve',phase='3b')
        self.wrap(InformationSetForecast,'act',phase='3b')
        from werewolf.root_secret_flow import RootSecretEngine
        self.wrap(RootSecretEngine,'solve',phase='3b')
        self.wrap(RootSecretEngine,'act',phase='3b')
        # Modules bind imported normalize/acquire aliases before wrappers are
        # installed. Wrap identity-equal aliases too, without consuming iterators.
        aliases=[]
        for owner,name,original in list(self.undo):
            if isinstance(owner,types.ModuleType):
                measured=getattr(owner,name)
                for module_name,module in list(sys.modules.items()):
                    if module_name.startswith('werewolf.') and module is not None:
                        for alias,value in list(vars(module).items()):
                            if value is original:
                                setattr(module,alias,measured);aliases.append((module,alias,original))
        self.undo.extend(aliases)
    def close(self):
        import gc
        gc.callbacks.remove(self.gc_callback)
        self.counts['gc.pause_seconds']=self.gc_pause
        for generation,count in self.gc_collections.items():self.counts['gc.collections.gen'+str(generation)]=count
        from werewolf.model_a_public import public_cache_info
        import werewolf.public_prior as prior
        import werewolf.seer_manual as manual
        for label,fn in [('complete_public',public_cache_info),('public_prior',getattr(prior._complete_prior,'cache_info',None)),('seer_replay',getattr(getattr(manual,'_replay',None),'cache_info',None))]:
            if fn:
                info=fn()
                for key in ('hits','misses','currsize'):self.counts['lru.'+label+'.'+key]=getattr(info,key)
        super().close()

def process_memory():
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    value=Counters();value.cb=ctypes.sizeof(value)
    ctypes.windll.kernel32.GetCurrentProcess.restype=ctypes.c_void_p
    handle=ctypes.windll.kernel32.GetCurrentProcess()
    fn=ctypes.windll.psapi.GetProcessMemoryInfo
    fn.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),wintypes.DWORD]
    if not fn(handle,ctypes.byref(value),value.cb):return None
    return {'peak_working_set_bytes':value.PeakWorkingSetSize,'peak_pagefile_bytes':value.PeakPagefileUsage,'working_set_bytes':value.WorkingSetSize}

original_worker=bench.worker
def memory_worker(args):
    original_worker(args)
    import json
    from pathlib import Path
    path=Path(args.output);record=json.loads(path.read_text(encoding='utf-8'))
    record['process_memory']=process_memory()
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
bench.worker=memory_worker
bench.Diagnostic=ExclusiveDiagnostic
# Child workers use this entrypoint as well. ROOT, fixtures and budget stay fixed.
bench.__file__=__file__
if __name__=='__main__':bench.main()
