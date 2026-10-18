"""Bounded isolated follow-up for tests not passed in the first full pass."""
import unittest,subprocess,time,json,os,sys,re,ctypes
from pathlib import Path
class Counters(ctypes.Structure):
 _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
def main():
 sys.path.insert(0,str(Path('tests').resolve()))
 passed=set();current=None
 norm=lambda s:s.removeprefix('tests.')
 for line in Path('.artifacts/general-full-regression.log').read_text(encoding='utf-8').splitlines():
  if line.startswith('test_')and' ... 'in line:
   current=norm(line.split(' (',1)[1].split(') ... ',1)[0])
   if line.endswith(' ... ok'):passed.add(current)
  elif line.strip()=='ok'and current:passed.add(current)
 def flatten(s):
  for t in s:
   if isinstance(t,unittest.TestSuite):yield from flatten(t)
   else:yield t.id()
 ids=list(dict.fromkeys(norm(t)for t in flatten(unittest.defaultTestLoader.discover('tests'))if norm(t)not in passed))
 rows=[];start=time.perf_counter();out=Path('benchmarks/player_match_groups/remaining-regression.json');logs=Path('.artifacts/remaining-tests');logs.mkdir(exist_ok=True)
 env={**os.environ,'PYTHONPATH':str(Path('tests').resolve())+os.pathsep+str(Path.cwd())}
 for i,name in enumerate(ids):
  if time.perf_counter()-start>=300:break
  began=time.perf_counter();peak=0;stop=None;limit=45 if "saved_seven_player"in name else 20
  with(logs/f'{i:04}.log').open('w',encoding='utf-8')as f:
   p=subprocess.Popen([sys.executable,'-B','-m','unittest',name],stdout=f,stderr=subprocess.STDOUT,env=env)
   while p.poll()is None:
    c=Counters();c.cb=ctypes.sizeof(c)
    if ctypes.windll.psapi.GetProcessMemoryInfo(int(p._handle),ctypes.byref(c),c.cb):peak=max(peak,c.PeakWorkingSetSize,c.PeakPagefileUsage)
    if peak>=1500000000:stop='memory_limit'
    elif time.perf_counter()-began>=limit or time.perf_counter()-start>=300:stop='time_limit'
    if stop:p.terminate();p.wait(timeout=10);break
    time.sleep(.1)
  row=dict(test=name,status=stop or('passed'if p.returncode==0 else'failed'),seconds=time.perf_counter()-began,peak_bytes=peak,log=str(logs/f'{i:04}.log'));rows.append(row)
  if row['status']!='passed':print(json.dumps(row),flush=True)
  out.write_text(json.dumps(dict(per_test_seconds=20,saved_seven_player_seconds=45,total_seconds_limit=300,previously_passed=len(passed),planned=len(ids),attempted=len(rows),results=rows,not_run=ids[len(rows):]),indent=2)+'\n')
 print(json.dumps(dict(planned=len(ids),attempted=len(rows),passed=sum(x['status']=='passed'for x in rows),seconds=time.perf_counter()-start)),flush=True)
if __name__=='__main__':main()
