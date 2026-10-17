"""Cold public/private Flask-stream comparison against an exported Git baseline.

Usage: python -B benchmarks/exploration_position_web_benchmark.py TREE OUTPUT [private]
Run baseline/new/new/baseline in separate processes. No tracemalloc or UI polling.
"""
from pathlib import Path
import sys,json,time,hashlib
source=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve()
sys.path.insert(0,str(source));sys.path.insert(0,str(source/'benchmarks'))
from app import create_app
from board_b_benchmark import process_memory_peak
case=json.loads((source/'benchmarks/board_b_extended_cases.json').read_text(encoding='utf-8'))['seven-observed']['game']
private=len(sys.argv)>3 and sys.argv[3]=='private'
app=create_app({'TESTING':True,'SECRET_KEY':'normal-position-fixture','HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True})
c=app.test_client()
with c.session_transaction() as session:session['game']=case;session['co_display_game']='normal-position-fixture'
if private:
 with c.session_transaction() as session:revision=session['game']['revision']
 advanced=c.post('/advance',data={'revision':revision,'target':'4','day':'max','night':'max'})
 assert advanced.status_code==303
 with c.session_transaction() as session:state=dict(session['game'])
 form={'revision':state['revision'],'board_id':state['public_log']['board_id'],'payload':json.dumps({'role':'wolf','players':[6,7],'results':[]})}
start=time.perf_counter();cpu=time.process_time();first=None;events=[];size=0
response=c.post('/private-view',data=form,headers={'Accept':'application/x-ndjson'},buffered=False) if private else c.get('/main',headers={'Accept':'application/x-ndjson'},buffered=False)
for chunk in response.response:
 size+=len(chunk);event=json.loads(chunk);events.append(event)
 if event['event']=='roles':first=time.perf_counter()-start
response.close();seconds=time.perf_counter()-start;cpu=time.process_time()-cpu
assert events[-1]['event']=='complete'
final=json.dumps({key:value for key,value in events[-1].items() if key not in ('event','run_id','view')},sort_keys=True) if private else events[-1]['html']
if not private:assert '113/504' in final
else:assert all(row['final'] is not None for row in events[-1]['players'] if row['legal'])
result={'source':str(source),'first_roles_seconds':first,'seconds':seconds,'cpu_seconds':cpu,
 'final_payload_sha256':hashlib.sha256(final.encode()).hexdigest(),'memory':process_memory_peak(),
 'body_bytes':size,'event_types':[event['event'] for event in events],
 'positions':sum(event['event']=='position' for event in events),
 'max_position_path':max([len(event.get('path',[])) for event in events] or [0])}
result['memory']['scope']='Whole worker high-water: startup + one cold request; not per-request allocation.'
result['scope']='Flask endpoint including worker, sampling, JSON and cleanup; excludes network and browser.'
output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
