import json,subprocess,sys,time
from pathlib import Path
rows=[]
for flags in [[],['--enabled'],['--enabled','--audit'],['--enabled'],[],[],['--enabled']]:
 t=time.perf_counter()
 code="import werewolf.match_groups as m; from pathlib import Path; exec(compile(Path(m.__file__).read_text(encoding='utf-8').replace('((5,1),(6,1),(6,2))','((5,1),(6,1),(6,2),(7,1))'),m.__file__,'exec'),m.__dict__); import runpy; runpy.run_path('benchmarks/player_match_groups/run.py',run_name='__main__')"
 p=subprocess.run([sys.executable,'-c',code,'7','1',*flags],capture_output=True,text=True,timeout=30,check=True)
 r=json.loads(p.stdout);r['wall_seconds']=time.perf_counter()-t;rows.append(r)
 Path('benchmarks/player_match_groups/seven-stage1-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
 print(flags,r['complete'],r.get('seconds'),flush=True)
 if not r['complete']:break
if all(r['complete'] for r in rows):
 assert all((r['value'],r['table'])==(rows[0]['value'],rows[0]['table'])for r in rows)
 print('All exact values and full Tables equal',flush=True)
