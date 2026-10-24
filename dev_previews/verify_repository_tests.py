"""Sequential bounded unittest coverage, preserving exact unattempted IDs.

Uses the standard discovery manifest, deduplicates repeated IDs/import aliases,
and isolates each module. It is not the monolithic discovery-order command.
"""
import argparse,ast,json,os,subprocess,sys,time,traceback,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT));os.chdir(ROOT)
def emit(path,row):
 with Path(path).open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
def detail(err):return ''.join(traceback.format_tb(err[2],limit=5))+'\n'+type(err[1]).__name__+': '+str(err[1])[:5000]
class Result(unittest.TestResult):
 def __init__(self,path):super().__init__();self.path=path;self.current=None;self.started=0;self.status='success'
 def startTest(self,test):super().startTest(test);self.current=test;self.started=time.monotonic();self.status='success';emit(self.path,dict(event='start',id=test.id(),time=time.time()))
 def stopTest(self,test):emit(self.path,dict(event='end',id=test.id(),status=self.status,seconds=round(time.monotonic()-self.started,4)));super().stopTest(test);self.current=None
 def addError(self,test,err):self.status='error';text=detail(err);self.errors.append((test,text));emit(self.path,dict(event='error',id=test.id(),detail=text))
 def addFailure(self,test,err):self.status='failure';text=detail(err);self.failures.append((test,text));emit(self.path,dict(event='failure',id=test.id(),detail=text))
 def addSkip(self,test,reason):super().addSkip(test,reason);self.status='skipped';emit(self.path,dict(event='skip',id=test.id(),reason=reason))
 def addExpectedFailure(self,test,err):self.expectedFailures.append((test,detail(err)));self.status='expected_failure';emit(self.path,dict(event='expected_failure',id=test.id()))
 def addUnexpectedSuccess(self,test):super().addUnexpectedSuccess(test);self.status='unexpected_success'
 def addSubTest(self,test,subtest,err):
  if err is not None:
   self.status='failure' if issubclass(err[0],test.failureException) else 'error';text=detail(err)
   (self.failures if self.status=='failure' else self.errors).append((subtest,text))
   emit(self.path,dict(event=self.status,id=test.id(),detail=text,subtest=str(subtest)[:300]))
def events(path):
 rows=[]
 if Path(path).exists():
  for line in Path(path).read_text(encoding='utf-8',errors='replace').splitlines():
   try:rows.append(json.loads(line))
   except json.JSONDecodeError:pass
 return rows
parser=argparse.ArgumentParser();parser.add_argument('--child');parser.add_argument('--events');parser.add_argument('--seconds',type=int,default=540);parser.add_argument('--kinds',default='fast,integration,exact');parser.add_argument('--modules');parser.add_argument('--output',default='.artifacts/repository-bounded');args=parser.parse_args()
if args.child:
 ids=json.loads(Path(args.child).read_text(encoding='utf-8'));suite=unittest.defaultTestLoader.loadTestsFromNames(ids)
 emit(args.events,dict(event='ready',cases=suite.countTestCases()));result=Result(args.events);suite.run(result)
 emit(args.events,dict(event='finished',run=result.testsRun,successful=result.wasSuccessful()));raise SystemExit(0 if result.wasSuccessful() else 1)
loader=unittest.TestLoader();discovered=loader.discover('tests')
def identities(suite):
 for test in suite:
  if isinstance(test,unittest.TestSuite):yield from identities(test)
  else:yield test.id()
manifest=dict(ids=list(identities(discovered)),loader_errors=[error[:6000] for error in loader.errors])
Path('.artifacts/repository-test-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
groups={}
for identity in manifest['ids']:
 identity='tests.'+identity if identity.startswith('test_') else identity
 groups.setdefault(identity.rsplit('.',2)[0],set()).add(identity)
plan=[]
for name,ids in groups.items():
 file=ROOT.joinpath(*name.split('.')).with_suffix('.py');source=file.read_text(encoding='utf-8') if file.exists() else '';tree=ast.parse(source)
 expensive=any(isinstance(n,ast.keyword) and n.arg in ('max_seconds','timeout') and isinstance(n.value,ast.Constant) and isinstance(n.value.value,(int,float)) and n.value.value>=40 for n in ast.walk(tree))
 kind='exact' if expensive else 'integration' if 'create_app' in source else 'fast'
 plan.append(dict(module=name,ids=sorted(ids),kind=kind))
plan=[r for r in plan if r['kind'] in args.kinds.split(',') and (not args.modules or r['module'] in args.modules.split(','))]
plan.sort(key=lambda r:({'fast':0,'integration':1,'exact':2}[r['kind']],r['module']))
output=Path(args.output);output.mkdir(parents=True,exist_ok=True);(output/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
started=time.monotonic();runs=[]
for number,row in enumerate(plan):
 if time.monotonic()-started>=args.seconds:break
 idsfile=output/(str(number)+'.ids.json');eventfile=output/(str(number)+'.events.jsonl');logfile=output/(str(number)+'.log')
 idsfile.write_text(json.dumps(row['ids']),encoding='utf-8');eventfile.write_text('',encoding='utf-8')
 begin=time.monotonic();last_count=0;activity=begin;active=None;reason=None
 with logfile.open('w',encoding='utf-8') as log:
  proc=subprocess.Popen([sys.executable,'-X','utf8',__file__,'--child',str(idsfile),'--events',str(eventfile)],stdout=log,stderr=log,cwd=ROOT)
  while proc.poll() is None:
   rows=events(eventfile)
   if len(rows)!=last_count:
    last_count=len(rows);activity=time.monotonic()
    for event in rows:
     if event['event']=='start':active=event['id']
     elif event['event']=='end':active=None
   limit={'fast':15,'integration':20,'exact':40}[row['kind']]
   if time.monotonic()-started>=args.seconds:reason='global_time_limit'
   elif time.monotonic()-activity>limit:reason='case_or_setup_time_limit'
   elif time.monotonic()-begin>{'fast':60,'integration':90,'exact':120}[row['kind']]:reason='module_time_limit'
   elif logfile.stat().st_size>3000000:reason='bounded_log_limit'
   if reason:
    subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10);proc.wait(timeout=10);break
   time.sleep(.3)
 rows=events(eventfile);completed={e['id']:e['status'] for e in rows if e['event']=='end'}
 record=dict(module=row['module'],kind=row['kind'],seconds=round(time.monotonic()-begin,3),returncode=proc.returncode,reason=reason,active=active,outcomes=completed,diagnostics=[e for e in rows if e['event']in('error','failure','skip')],unattempted=[id for id in row['ids'] if id not in completed])
 runs.append(record);(output/'progress.json').write_text(json.dumps(dict(seconds=round(time.monotonic()-started,2),runs=runs),ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(dict(module=row['module'],kind=row['kind'],completed=len(completed),statuses={s:list(completed.values()).count(s)for s in set(completed.values())},reason=reason,seconds=record['seconds'])),flush=True)
completed={id:status for r in runs for id,status in r['outcomes'].items()};all_ids={id for row in plan for id in row['ids']}
summary=dict(seconds=round(time.monotonic()-started,2),raw_discovered=len(manifest['ids']),unique=len(all_ids),completed=len(completed),statuses={s:list(completed.values()).count(s)for s in set(completed.values())},unattempted=sorted(all_ids-set(completed)),runs=runs,loader_errors=manifest['loader_errors'])
(output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in summary.items()if k not in ('runs','unattempted','loader_errors')}),flush=True)
