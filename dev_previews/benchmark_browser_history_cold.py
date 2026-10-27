"""Cold independent-worker browser recipe benchmark; local synthetic public fixture only."""
import json,re,hashlib,time,ctypes
from ctypes import wintypes
from unittest.mock import patch
from urllib.parse import urlencode
from app import create_app
from werewolf.navigation_evaluation import NavigationEvaluation
from werewolf.public_convergence import state_key
KEY='browser-history-benchmark-fixture-only'
def app():return create_app(dict(TESTING=True,SECRET_KEY=KEY,BROWSER_HISTORY_PREVIEW=True,GAME_TREE_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True))
def wire(c,token,url,body='',method='GET',content_type=''):
 return c.post('/browser-history/request',json=dict(url=url,method=method,body=body,content_type=content_type,token=token,routes={}),headers={'X-WW-Staged':'1','Accept':'application/x-ndjson'})
a=app();c=a.test_client();c.post('/start',data=dict(citizens=3,mediums=1,seers=1,wolves=2,day='max',night='max',fake_reports='max',win_cutoff=1))
h=c.get('/main',headers={'X-WW-Staged':'1'}).get_data(as_text=True);seed=json.loads(re.search(r'id="browser-history-seed">(.*?)</script>',h).group(1))
payload=dict(claims=['seer','seer','medium',*['latent']*4],seers=[dict(day=1,reporter=p,target=3,color='white') for p in (1,2)],mediums=[])
t=time.perf_counter();r=wire(c,seed['token'],'/table-publish',urlencode(dict(revision=0,payload=json.dumps(payload))),'POST','application/x-www-form-urlencoded');assert r.status_code==200,r.get_json();adopt=time.perf_counter()-t;doc=r.get_json();token=doc['browser_history']
# A new app/client means no in-memory evaluator or Tree cache survives.
fresh=app().test_client();fresh.set_cookie('session',c.get_cookie('session').value)
original=NavigationEvaluation.forecast;seen=[]
def record(self,*a,**kw):
 value=original(self,*a,**kw);seen.append((self,value));return value
start=time.perf_counter();cpu=time.process_time();roles=None;complete=None
with patch.object(NavigationEvaluation,'forecast',record):
 response=wire(fresh,token,'/navigation/calculation?occurrence=h1&revision=1&request_id=1')
 for raw in response.response:
  row=json.loads(raw)
  if row['event']=='roles':roles=time.perf_counter()-start
  if row['event']=='complete':complete=row
  if row['event']=='error':raise RuntimeError(row)
wall=time.perf_counter()-start;cpu=time.process_time()-cpu;assert complete and complete['value_complete']
evaluation,value=seen[-1];fingerprint=hashlib.sha256(repr(state_key(evaluation.current.navigation.node.read())).encode()).hexdigest()
class Memory(ctypes.Structure):_fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),*[(k,ctypes.c_size_t) for k in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]]
m=Memory();m.cb=ctypes.sizeof(m);ctypes.windll.kernel32.GetCurrentProcess.restype=wintypes.HANDLE
ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
assert ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(m),m.cb),ctypes.get_last_error()
result=dict(adoption_wall=adopt,cold_restore_roles_wall=roles,cold_restore_calculation_wall=wall,cold_restore_calculation_cpu=cpu,process_peak_working_set_mb=m.PeakWorkingSetSize/1048576,village_win=str(value.village_win),action_values=[(p,str(v)) for p,v in value.action_values],source_fingerprint=fingerprint)
assert str(value.village_win)=='89/224',result
assert result['action_values']==[(1,'5/16'),(2,'5/16'),(3,'4/15'),*[(p,'89/224') for p in range(4,8)]]
assert fingerprint=='c94710df19129901d4e0c811d0b202b4c39fdf0a53746c56bfc16613064c6d6d'
from pathlib import Path
Path('.artifacts/browser-history-heavy-cold.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
