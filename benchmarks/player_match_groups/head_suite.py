"""Fresh-HEAD unittest discovery, isolated per-test process and finite limits."""
import unittest,subprocess,time,json,os,sys,ctypes
from pathlib import Path
from .remaining_regression import Counters

def main():
 sys.path.insert(0,str(Path('tests').resolve()))
 def flatten(s):
  for t in s:
   if isinstance(t,unittest.TestSuite):yield from flatten(t)
   else:yield t.id()
 ids=list(dict.fromkeys(flatten(unittest.defaultTestLoader.discover('tests'))))
 head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 out=Path(sys.argv[1])if len(sys.argv)>1 else Path('benchmarks/player_match_groups/head-suite-results.json')
 logs=Path('.artifacts')/out.stem;logs.mkdir(exist_ok=True)
 rows=[];started=time.perf_counter()
 env={**os.environ,'PYTHONPATH':str(Path('tests').resolve())+os.pathsep+str(Path.cwd())}
 memory=ctypes.windll.psapi.GetProcessMemoryInfo
 memory.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
 def save():
  out.write_text(json.dumps(dict(head=head,discovery='unittest discover tests; fresh process per test',per_test_seconds=60,total_seconds_limit=1200,memory_limit_bytes=1500000000,planned=len(ids),attempted=len(rows),elapsed_seconds=time.perf_counter()-started,results=rows,not_run=ids[len(rows):]),indent=2)+'\n')
 save()
 for i,name in enumerate(ids):
  if time.perf_counter()-started>=1200:break
  began=time.perf_counter();rss=commit=0;stop=None
  with(logs/f'{i:04}.log').open('w',encoding='utf-8')as f:
   p=subprocess.Popen([sys.executable,'-B','-m','unittest',name],stdout=f,stderr=subprocess.STDOUT,env=env)
   while p.poll()is None:
    c=Counters();c.cb=ctypes.sizeof(c)
    if memory(int(p._handle),ctypes.byref(c),c.cb):rss=max(rss,c.PeakWorkingSetSize);commit=max(commit,c.PeakPagefileUsage)
    if max(rss,commit)>=1500000000:stop='memory_limit'
    elif time.perf_counter()-began>=60:stop='time_limit'
    elif time.perf_counter()-started>=1200:stop='global_time_limit'
    if stop:p.terminate();p.wait(timeout=10);break
    time.sleep(.05)
  row=dict(test=name,status=stop or('passed'if p.returncode==0 else'failed'),exit=p.returncode,seconds=time.perf_counter()-began,peak_rss_bytes=rss,peak_commit_bytes=commit,log=str(logs/f'{i:04}.log'))
  rows.append(row);save()
  if row['status']!='passed' or len(rows)%50==0:print(json.dumps(dict(completed=len(rows),planned=len(ids),last=row,elapsed=time.perf_counter()-started)),flush=True)
 print(json.dumps(dict(completed=len(rows),planned=len(ids),counts={s:sum(r['status']==s for r in rows)for s in set(r['status']for r in rows)},elapsed=time.perf_counter()-started)),flush=True)
if __name__=='__main__':main()