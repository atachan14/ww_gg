"""Complete unattempted tail in-process, with cancellable per-test work."""
import unittest,threading,time,json,sys,ctypes
from pathlib import Path
from werewolf.calculation_budget import cancellation_scope

def main():
 sys.path.insert(0,str(Path('tests').resolve()))
 previous=json.loads(Path('benchmarks/player_match_groups/remaining-regression.json').read_text())
 wanted=set(previous['not_run']);norm=lambda x:x.removeprefix('tests.')
 def flatten(s):
  for t in s:
   if isinstance(t,unittest.TestSuite):yield from flatten(t)
   else:yield t
 tests={norm(t.id()):t for t in flatten(unittest.defaultTestLoader.discover('tests'))}
 rows=[];start=time.perf_counter();out=Path('benchmarks/player_match_groups/regression-tail.json')
 for name in previous['not_run']:
  if time.perf_counter()-start>=280:break
  event=threading.Event();timer=threading.Timer(20,event.set);timer.daemon=True;r=unittest.TestResult();begun=time.perf_counter();timer.start()
  with cancellation_scope(event):tests[name].run(r)
  timer.cancel();status='time_limit'if event.is_set()else('passed'if r.wasSuccessful()else'failed')
  row=dict(test=name,status=status,seconds=time.perf_counter()-begun,failures=[s[-1200:]for _,s in r.failures+r.errors]);rows.append(row)
  if status!='passed':print(json.dumps(row),flush=True)
  out.write_text(json.dumps(dict(per_test_seconds=20,global_seconds_limit=280,planned=len(wanted),attempted=len(rows),results=rows,not_run=previous['not_run'][len(rows):]),indent=2)+'\n')
 print(json.dumps(dict(planned=len(wanted),attempted=len(rows),passed=sum(r['status']=='passed'for r in rows),seconds=time.perf_counter()-start)),flush=True)
if __name__=='__main__':main()
