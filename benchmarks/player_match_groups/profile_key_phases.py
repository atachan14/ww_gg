"""One bounded CURRENT actual-seven phase readout, not a speed trial."""
import time,json,sys,subprocess,ctypes,inspect,textwrap,types,builtins
from collections import Counter,OrderedDict
from pathlib import Path
from .remaining_regression import Counters
BASE=Path('benchmarks/player_match_groups')

def worker(out):
 from .extension_reuse import ExtensionForecast
 from .future_reuse import FutureReuseForecast
 from .fast_key_parts import make_canonical
 import benchmarks.player_match_groups.future_reuse as module
 from .measure_future_reuse import run
 from .extension_cases import prepare_game
 made=[]
 class Measured(ExtensionForecast):
  def __init__(self,*a,**kw):
   super().__init__(*a,**kw);made.append(self);stats=self.phase_stats=Counter()
   def timed(label,fn):
    def call(*args,**kwargs):
     started=time.perf_counter()
     try:return fn(*args,**kwargs)
     finally:stats[label+'_seconds']+=time.perf_counter()-started;stats[label+'_calls']+=1
    return call
   fn,_,self.mask_stats=make_canonical()
   class Groups(dict):
    def setdefault(self,*args):
     start=time.perf_counter()
     try:return super().setdefault(*args)
     finally:stats['group_hash_seconds']+=time.perf_counter()-start;stats['group_hash_calls']+=1
   def equal(left,right,label):
    start=time.perf_counter()
    try:return left==right
    finally:stats[label+'_seconds']+=time.perf_counter()-start;stats[label+'_calls']+=1
   from werewolf.exact_renaming import canonical_key as production_key
   canonical_source=inspect.getsource(production_key)
   old_masks="""        return tuple(sum(1<<(ids[p]-1) for p in range(b.player_count) if m&(1<<p))
                     for m in range(1<<b.player_count))"""
   for before,after in(('    groups={}','    groups=MeasuredGroups()'),(old_masks,'        return completed_mask_map(ids)'),('private==s',"measured_equal(private,s,'private_equal')"),('physical==b',"measured_equal(physical,b,'physical_equal')")):
    assert canonical_source.count(before)==1;canonical_source=canonical_source.replace(before,after)
   ns=fn.__globals__;ns.update(MeasuredGroups=Groups,measured_equal=equal,sorted=timed('group_sort',builtins.sorted))
   ns['record']=timed('past_record',ns['record'])
   ns['completed_mask_map']=timed('mask_map',ns['completed_mask_map'])
   exec(compile(canonical_source,production_key.__code__.co_filename,'exec'),ns);fn=ns['canonical_key']
   for name in('colors','configuration','board_signature','state_signature'):
    fn.__globals__[name]=timed(name,fn.__globals__[name])
   self.key_function=timed('canonical',fn)
   class Sources(OrderedDict):
    def __contains__(self,key):
     start=time.perf_counter()
     try:return super().__contains__(key)
     finally:stats['source_dictionary_seconds']+=time.perf_counter()-start
    def pop(self,*a,**kw):
     start=time.perf_counter()
     try:return super().pop(*a,**kw)
     finally:stats['source_dictionary_seconds']+=time.perf_counter()-start
    def __setitem__(self,key,value):
     start=time.perf_counter()
     try:return super().__setitem__(key,value)
     finally:stats['source_dictionary_seconds']+=time.perf_counter()-start
   self.reuse_sources=Sources()
   def member(engine,key,target):return key in(engine.values if target is None else engine.action_values)
   source=textwrap.dedent(inspect.getsource(FutureReuseForecast.complete_reuse_key))
   before="if key in(self.values if target is None else self.action_values):"
   assert source.count(before)==1
   source=source.replace(before,'if measured_value_membership(self,key,target):')
   ns=dict(vars(module));ns.update(evidence_key=timed('source_hash',module.evidence_key),hash=timed('final_hash',builtins.hash),measured_value_membership=timed('value_key_membership',member))
   exec(compile(source,module.__file__,'exec'),ns);self.complete_reuse_key=types.MethodType(ns['complete_reuse_key'],self)
 game=json.loads((BASE/'corpse-rule-seven-results.json').read_text())['game']
 result=run(prepared=prepare_game(game),enabled=True,physical_reuse=True,retired_reuse=True,compact_keys=True,fast_parts=True,retirement_proof=True,max_work=4000000,max_seconds=115,engine_class=Measured,engine_options=dict(medium_reuse=True,max_reuse=True,combined_reuse=True,extended_retirement=True))
 result['phase_stats']=dict(made[0].phase_stats)
 ref=json.loads((BASE/'corpse-rule-seven-results.json').read_text())['after'];result['complete_value_table_equal']=result.get('complete')and(result['value'],result['table'])==(ref['value'],ref['table'])
 Path(out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in('complete','seconds','value','complete_value_table_equal','phase_stats')}),flush=True)

def controller():
 prior=BASE/'component-seven-results.json';main=json.loads(prior.read_text());remaining=600-main['elapsed']-max(0,time.time()-prior.stat().st_mtime)-1
 if remaining<=0:raise RuntimeError('Combined600s stage exhausted; phase run not started')
 limit=min(120,remaining);out=BASE/'component-seven-key-phases-v2.json';log=Path('.artifacts/component-seven/current-phases-v2.log');started=time.perf_counter();rss=commit=0;stop=None
 memory=ctypes.windll.psapi.GetProcessMemoryInfo;memory.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
 with log.open('w',encoding='utf-8')as f:
  p=subprocess.Popen([sys.executable,'-B','-m','benchmarks.player_match_groups.profile_key_phases','--worker',str(out)],stdout=f,stderr=subprocess.STDOUT)
  while p.poll()is None:
   c=Counters();c.cb=ctypes.sizeof(c)
   if memory(int(p._handle),ctypes.byref(c),c.cb):rss=max(rss,c.PeakWorkingSetSize);commit=max(commit,c.PeakPagefileUsage)
   if max(rss,commit)>=1500000000:stop='memory_limit'
   elif time.perf_counter()-started>=limit:stop='combined_time_limit'
   if stop:p.terminate();p.wait(timeout=10);break
   time.sleep(.1)
 meta=dict(status=stop or('finished'if p.returncode==0 else'failed'),process_seconds=time.perf_counter()-started,peak_rss=rss,peak_commit=commit,remaining_at_start=remaining,limit=limit,log=str(log))
 (BASE/'component-seven-phase-process-v2.json').write_text(json.dumps(meta,indent=2)+'\n')
 print(json.dumps(meta),flush=True)
 if out.exists()and stop is None:
  result=json.loads(out.read_text());print(json.dumps({k:result[k]for k in('complete','seconds','value','complete_value_table_equal','phase_stats')}),flush=True)
if __name__=='__main__':
 if len(sys.argv)>1:worker(sys.argv[2])
 else:controller()