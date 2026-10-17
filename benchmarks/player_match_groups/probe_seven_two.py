"""Separate bounded cast probe; runtime seven/two-wolf gate remains disabled."""
import json,subprocess,sys,time
from pathlib import Path
rows=[]
stage_started=time.perf_counter()
for enabled,audit,budget in ((False,False,300),(True,False,300),(True,True,300)):
    code="""import json
from dataclasses import asdict,is_dataclass
from pathlib import Path
import werewolf.match_groups as m
source=Path(m.__file__).read_text(encoding='utf-8')
assert 'and (n,board.wolf_count)in(' in source
exec(compile(source.replace('((5,1),(6,1),(6,2),(7,1))','((5,1),(6,1),(6,2),(7,1),(7,2))'),m.__file__,'exec'),m.__dict__)
from benchmarks.player_match_groups.run import run
result=run(7,2,ENABLED,AUDIT,max_seconds=BUDGET,max_work=4000000)
print(json.dumps(result,default=lambda x:asdict(x)if is_dataclass(x)else str(x)))
""".replace('ENABLED',repr(enabled)).replace('AUDIT',repr(audit)).replace('BUDGET',repr(budget))
    budget=min(budget,max(1,300-(time.perf_counter()-stage_started)))
    code=code.replace("max_seconds=300",f"max_seconds={budget!r}")
    started=time.perf_counter()
    process=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=budget+10,check=True)
    row=json.loads(process.stdout);row['wall_seconds']=time.perf_counter()-started;rows.append(row)
    Path('benchmarks/player_match_groups/seven-two-probe.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(json.dumps({k:row.get(k)for k in ('complete','seconds','value','stats','memory')}),flush=True)
    if not row['complete']:break
    assert (row['value'],row['table'])==(rows[0]['value'],rows[0]['table'])
