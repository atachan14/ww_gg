"""Bounded cold cancellation latency, same actual public workload per process.
Baseline intentionally waits for its capped calculation, matching the old queue.
"""
import argparse,io,subprocess,sys,tarfile,tempfile,time,json,copy
from pathlib import Path
from threading import Thread
p=argparse.ArgumentParser();p.add_argument('--baseline');a=p.parse_args();repo=Path.cwd();temp=None
if a.baseline:
 temp=tempfile.TemporaryDirectory();root=Path(temp.name)
 archive=subprocess.check_output(['git','archive',a.baseline,'app.py','werewolf'])
 with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(root,filter='data')
 sys.path.insert(0,str(root))
else:sys.path.insert(0,str(repo))
from app import create_app
from jinja2 import FileSystemLoader
app=create_app({'TESTING':True,'SECRET_KEY':'cancel-benchmark-only','SEER_UNIFORM_FUTURE_PREVIEW':True,'MANUAL_CALC_MAX_SECONDS':2,'MANUAL_CALC_MAX_WORK':4000000})
app.jinja_loader=FileSystemLoader(str(repo/'templates'))
c=app.test_client();r=c.post('/start',data={'citizens':'3','mediums':'1','seers':'1','hunters':'1','wolves':'2','day':'random','night':'random','fake_reports':'random','win_cutoff':'0'})
assert r.status_code in (200,303),r.status_code
c.get('/main',headers={'Sec-Fetch-Dest':'document'})
cookie=c.get_cookie('session').value;result={}
def heavy():
 client=app.test_client();client.set_cookie('session',cookie)
 with client.get('/main',headers={'X-WW-Calculation-ID':'e'*32}) as r:result.update(status=r.status_code,bytes=len(r.data))
start=time.monotonic();worker=Thread(target=heavy);worker.start();time.sleep(.2)
assert worker.is_alive(),'workload completed before cancellation measurement'
cancel_at=time.monotonic()
ack=None
if not a.baseline:
 r=c.post('/calculation-cancel',data={'calculation_id':'e'*32});assert r.status_code==200;ack=time.monotonic()
worker.join(5);assert not worker.is_alive(),'worker did not release'
released=time.monotonic()
r=c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'});assert r.status_code in (200,303)
new_started=time.monotonic()
with c.get('/main') as r:assert r.status_code==200 and b'data-fraction="7/15"' in r.data
print(json.dumps({'baseline':a.baseline,'workload':'8p citizen3 medium1 seer1 hunter1 wolf2 random; cold; 2s exact budget','cancel_requested_seconds':cancel_at-start,'cancel_ack_seconds':None if ack is None else ack-cancel_at,'cancel_to_worker_exit_seconds':released-cancel_at,'cancel_to_next_start_completed_seconds':new_started-cancel_at,'old_result':result,'new_exact':'7/15'}))
if temp:temp.cleanup()
