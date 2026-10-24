"""Same canonical history inputs, old/full-validation vs mass-only reuse."""
import ast,json,statistics,subprocess,time
from fractions import Fraction as F
import werewolf.seer_acquisition as acquisition
from werewolf.guard_effect import GuardIntent
from werewolf.night_knowledge import WolfAttack
source=subprocess.check_output(['git','show','f282369:werewolf/seer_acquisition.py'],text=True,encoding='utf-8')
function=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='normalize')
namespace=dict(acquisition.__dict__);exec(compile(ast.Module(body=[function],type_ignores=[]),'old-normalization','exec'),namespace)
old=namespace['normalize'];rows=[]
for pack in ((4,5),(4,6),(5,6)):
 wolves=sum(1<<(p-1) for p in pack)
 for target in (2,3,4,5,6):
  for guarded in (1,3,4):
   records=(acquisition.Acquisition(2,1,target,'black' if target in pack else 'white'),)
   rows.append(acquisition.Hypothesis((wolves,0,1,2),records,F(target+guarded), (GuardIntent(1,2,guarded),),(WolfAttack(1,3),)))
rows=tuple(rows);expected=old(rows);assert acquisition.normalize(rows)==expected
results=[]
for name,fn in [('full-validation',old),('mass-only-reuse',acquisition.normalize)]:
 times=[]
 for _ in range(5):
  start=time.perf_counter()
  for _ in range(200):actual=fn(rows)
  times.append(time.perf_counter()-start);assert actual==expected
 results.append(dict(mode=name,median_200_calls_s=round(statistics.median(times),4),entries=len(rows),mass=str(sum(h.mass for h in actual))))
print(json.dumps(results))
