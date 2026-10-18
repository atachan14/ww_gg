"""Fresh-process actual-seven component-key comparison, finite and opt-in only."""
import sys,json,time,subprocess,os,ctypes,hashlib
from pathlib import Path
from .remaining_regression import Counters

BASE=Path('benchmarks/player_match_groups')

def worker(mode,out):
 from .extension_cases import prepare_game
 from .measure_future_reuse import run
 from .extension_reuse import ExtensionForecast
 from .component_key import ComponentReuseForecast
 from werewolf.local_reuse import reuse_scope
 game=json.loads((BASE/'corpse-rule-seven-results.json').read_text())['game'];made=[]
 parent=ExtensionForecast if mode=='current'else ComponentReuseForecast
 class Measured(parent):
  def __init__(self,*a,**kw):
   if mode=='audit':kw['component_audit']=True
   super().__init__(*a,**kw);made.append(self)
 started=time.perf_counter();prepared=prepare_game(game)
 with reuse_scope(False):
  result=run(prepared=prepared,enabled=True,physical_reuse=True,retired_reuse=True,compact_keys=True,fast_parts=True,retirement_proof=True,max_work=4000000,max_seconds=115,engine_class=Measured,engine_options=dict(medium_reuse=True,max_reuse=True,combined_reuse=True,extended_retirement=True))
 if made:
  result['component_stats']=dict(getattr(made[0],'component_stats',{}));result['audit_stats']=dict(getattr(made[0],'component_audit_stats',{}))
 result['worker_total_seconds']=time.perf_counter()-started;result['mode']=mode
 Path(out).write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items()if k not in('table','trial_source')}),flush=True)

def controller():
 start=time.perf_counter();out=BASE/'component-seven-results.json';logs=Path('.artifacts/component-seven');logs.mkdir(exist_ok=True)
 rows=[];stops=[];reference=json.loads((BASE/'corpse-rule-seven-results.json').read_text())['after']
 expected=None
 def save():
  out.write_text(json.dumps(dict(scope='actual initial7, identical cold fresh processes; no default/factory change',source_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in(BASE/'component_key.py',BASE/'compare_component_seven.py')},run_limit_seconds=120,stage_limit_seconds=600,memory_limit_bytes=1500000000,elapsed=time.perf_counter()-start,stop=stops,runs=rows),indent=2)+'\n')
 memory=ctypes.windll.psapi.GetProcessMemoryInfo;memory.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
 for i,mode in enumerate(('current','candidate','candidate','current','audit')):
  if time.perf_counter()-start>=600:stops.append('stage_limit');break
  result_file=logs/f'{i:02}-{mode}.json';log=logs/f'{i:02}-{mode}.log';began=time.perf_counter();rss=commit=0;stop=None
  with log.open('w',encoding='utf-8')as f:
   p=subprocess.Popen([sys.executable,'-B','-m','benchmarks.player_match_groups.compare_component_seven','--worker',mode,str(result_file)],stdout=f,stderr=subprocess.STDOUT)
   while p.poll()is None:
    c=Counters();c.cb=ctypes.sizeof(c)
    if memory(int(p._handle),ctypes.byref(c),c.cb):rss=max(rss,c.PeakWorkingSetSize);commit=max(commit,c.PeakPagefileUsage)
    if max(rss,commit)>=1500000000:stop='memory_limit'
    elif time.perf_counter()-began>=120:stop='run_time_limit'
    elif time.perf_counter()-start>=600:stop='stage_time_limit'
    if stop:p.terminate();p.wait(timeout=10);break
    time.sleep(.1)
  row=dict(mode=mode,status=stop or('finished'if p.returncode==0 else'failed'),process_seconds=time.perf_counter()-began,peak_rss=rss,peak_commit=commit,log=str(log))
  if result_file.exists()and stop is None:
   result=json.loads(result_file.read_text());row['result']=result
   if result.get('complete'):
    row['saved_value_and_table_equal']=(result['value'],result['table'])==(reference['value'],reference['table'])
    if expected is None:expected=(result['value'],result['table'])
    row['cold_pair_value_and_table_equal']=(result['value'],result['table'])==expected
    if not row['saved_value_and_table_equal']or not row['cold_pair_value_and_table_equal']:row['status']='numerical_mismatch'
   else:row['status']='incomplete'
  rows.append(row);save()
  print(json.dumps({k:v for k,v in row.items()if k!='result'}|({'seconds':row['result'].get('seconds'),'value':row['result'].get('value'),'component_stats':row['result'].get('component_stats'),'audit_stats':row['result'].get('audit_stats')}if'result'in row else{})),flush=True)
  if row['status']!='finished':stops.append(row['status']);break
 save();print(json.dumps(dict(stage_complete=len(rows)==5 and not stops,elapsed=time.perf_counter()-start)),flush=True)
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--worker':worker(sys.argv[2],sys.argv[3])
 else:controller()