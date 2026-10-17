"""Reproducible old/B evaluation benchmark; diagnostics never run in timed baseline.

Use --help. Workers run serially in isolated Git snapshots, with fixed budgets.
Outputs include exact semantic results, censored runs, environment and raw trials.
"""
from __future__ import annotations
import argparse, contextlib, dataclasses, fractions, hashlib, importlib.util
import json, os, platform, statistics, subprocess, sys, time
from pathlib import Path

OLD='ec513c2eb60bd20d5dbfbbe6c29bceb5648ff049'
NEW='c6dd47539644c65e83c708b824b7792410c62130'
ROOT=Path(__file__).resolve().parents[1]
BUDGET=dict(max_work=250000,max_seconds=20)


def canonical(value):
    if isinstance(value,fractions.Fraction):return {'fraction':f'{value.numerator}/{value.denominator}'}
    if dataclasses.is_dataclass(value):return {f.name:canonical(getattr(value,f.name)) for f in dataclasses.fields(value) if f.compare}
    if isinstance(value,dict):return {str(k):canonical(v) for k,v in sorted(value.items(),key=lambda p:str(p[0]))}
    if isinstance(value,(tuple,list)):return [canonical(v) for v in value]
    if isinstance(value,(str,int,float,bool)) or value is None:return value
    raise TypeError(type(value).__name__)


def digest(value):return hashlib.sha256(json.dumps(canonical(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def summarize(rows):
    completed=[r['seconds'] for r in rows if r['complete']]
    quiet=[r['seconds'] for r in rows if r['complete'] and not r.get('high_background_load',False)]
    ordered=sorted(completed)
    q=statistics.quantiles(ordered,n=4,method='inclusive') if len(ordered)>1 else ordered*3
    return {'trials':len(rows),'completed':sum(r['complete'] for r in rows),
            'censored':sum(not r['complete'] for r in rows),'eligible_completed':len(ordered),
            'median_seconds':statistics.median(ordered) if ordered else None,
            'min_seconds':min(ordered) if ordered else None,'max_seconds':max(ordered) if ordered else None,
            'iqr_seconds':q[2]-q[0] if q else None,'raw_seconds':completed,'low_background_completed_seconds':quiet,'low_background_median_seconds':statistics.median(quiet) if quiet else None}


def census_pending(value):
    found=[]
    if dataclasses.is_dataclass(value):
        if type(value).__name__.endswith('Pending'):found.append(getattr(value,'reason',repr(value)))
        else:
            for f in dataclasses.fields(value):
                item=getattr(value,f.name)
                if f.name=='pending_metrics' and item:found.append('pending_metrics:'+str(item))
                else:found.extend(census_pending(item))
    elif isinstance(value,dict):
        for k,v in value.items():
            if k in ('pending','pending_metrics') and v:found.append(str(v))
            else:found.extend(census_pending(v))
    elif isinstance(value,(tuple,list)):
        for v in value:found.extend(census_pending(v))
    return found


def resolution_status(before,after,result):
    return 'ineligible' if after==before else 'hit' if result is not None else 'miss'


class Diagnostic:
    """Exclusive phase wall time; nested phases never double-count elapsed time.

    Counters wrap pure constructors/functions only in a separate diagnostic run.
    Diagnostic time includes instrumentation overhead; never a baseline estimate.
    """
    def __init__(self):self.phase=None;self.last=time.perf_counter();self.seconds={};self.counts={};self.elements={};self.undo=[]
    def switch(self,phase):
        now=time.perf_counter()
        if self.phase:self.seconds[self.phase]=self.seconds.get(self.phase,0)+now-self.last
        old=self.phase;self.phase=phase;self.last=now;return old
    @contextlib.contextmanager
    def scope(self,phase):
        old=self.switch(phase)
        try:yield
        finally:self.switch(old)
    def wrap(self,obj,name,*,phase=None,elements=None):
        original=getattr(obj,name,None)
        if original is None:return
        label=getattr(obj,'__name__',type(obj).__name__)+'.'+name
        def measured(*args,**kwargs):
            self.counts[label]=self.counts.get(label,0)+1
            if elements is not None:
                n=elements(args,kwargs)
                self.elements[label]=self.elements.get(label,0)+n
            with self.scope(phase) if phase else contextlib.nullcontext():return original(*args,**kwargs)
        # Preserve cache APIs/explicit unwrapped behavior; no altered bypass target.
        measured.__dict__.update(getattr(original,'__dict__',{}))
        if hasattr(original,'__wrapped__'):measured.__wrapped__=original.__wrapped__
        setattr(obj,name,measured);self.undo.append((obj,name,original))
    def install(self,new,oracle):
        import werewolf.exact as exact
        import werewolf.seer_acquisition as acquisition
        import werewolf.seer_future_uniform as future
        from werewolf.information_set_forecast import InformationSetForecast
        self.wrap(exact.Board,'__post_init__')
        self.wrap(acquisition.Hypothesis,'__post_init__')
        self.wrap(future.TrueScanState,'__post_init__',elements=lambda a,k:len(a[0].hypotheses))
        self.wrap(acquisition,'normalize',elements=lambda a,k:len(a[0]) if isinstance(a[0],(list,tuple)) else 0)
        self.wrap(acquisition,'acquire',elements=lambda a,k:len(a[0]) if isinstance(a[0],(list,tuple)) else 0)
        # Solver caches: count calls and hits without changing keys or values.
        original=InformationSetForecast.cached_flow
        def cached(engine,cache,key,generate,kind):
            label='cached_flow.'+kind;self.counts[label]=self.counts.get(label,0)+1
            status='disabled' if not engine.memoize_flows else 'hit' if key in cache else 'miss'
            self.counts[label+'.'+status]=self.counts.get(label+'.'+status,0)+1
            return original(engine,cache,key,generate,kind)
        InformationSetForecast.cached_flow=cached
        self.undo.append((InformationSetForecast,'cached_flow',original))
        if new:
            import werewolf.board_roles as roles
            import werewolf.board_future as flow
            for name in ('reconstruct_roles','prepare_evaluation','prepare_private','prepare_compat_prior'):
                self.wrap(roles,name,phase='3a')
            self.wrap(flow,'kernel_snapshot');self.wrap(flow,'evidence_key');self.wrap(flow,'condition_recipe')
            self.wrap(flow.GeneratedBoard,'_reconstruct',elements=lambda a,k:len(a[0].history))
            original_reuse=flow.reuse_resolution
            def reuse(*a,**k):
                stats=getattr(a[0].engine,'board_replay_stats',{});before=stats.get('requests',0)
                result=original_reuse(*a,**k)
                label='resolution_replay.'+resolution_status(before,stats.get('requests',0),result)
                self.counts[label]=self.counts.get(label,0)+1;return result
            flow.reuse_resolution=reuse;self.undo.append((flow,'reuse_resolution',original_reuse))
        else:
            self.wrap(oracle,'reconstruct_saved',phase='3a')
            import werewolf.seer_manual as manual
            self.wrap(manual,'replay',phase='3a')
    def close(self):
        self.switch(None)
        for obj,name,original in reversed(self.undo):setattr(obj,name,original)


@contextlib.contextmanager
def experiment_bypass_generated_replay(enabled):
    """Diagnostic ablation ONLY: remove generated 3a orchestration, retain kernels.

    Not a product optimization: it weakens the B responsibility contract. Exact
    result equality is checked by the runner, never assumed from this shortcut.
    """
    if not enabled:yield;return
    from unittest.mock import patch
    from werewolf.evaluation_branch import ContinuationInputs
    import werewolf.board_future as flow
    with contextlib.ExitStack() as stack:
        patches={'before_action':lambda *a,**k:None,
          'reconstruct_child':lambda e,b,p,o,t,legacy:legacy(),
          'reconstruct_publication':lambda e,p,c,s,past,own,physical,**k:ContinuationInputs(c,s,past,own,p.observer,physical),
          'record_publications':lambda e,b,s,p,rows,**k:rows,
          'record_medium_instruction':lambda *a,**k:None,
          'reuse_resolution':lambda *a,**k:None,'remember_resolution':lambda *a,**k:None}
        for name,value in patches.items():stack.enter_context(patch.object(flow,name,value))
        yield


def cache_counters(runtime=None):
    from werewolf.model_a_public import public_cache_info
    import werewolf.public_prior as prior
    import werewolf.seer_manual as manual
    result={}
    for label,fn in [('complete_public',public_cache_info),('public_prior',getattr(prior._complete_prior,'cache_info',None)),('seer_replay',getattr(getattr(manual,'_replay',None),'cache_info',None))]:
        if fn:
            info=fn();result[label]={k:getattr(info,k) for k in ('hits','misses','currsize')}
    if runtime is not None:result['game_completed']=runtime.info()
    return result


def worker(args):
    began=time.perf_counter();sys.path.insert(0,str(Path(args.tree).resolve()))
    import pkgutil,importlib,werewolf
    for module in pkgutil.iter_modules(werewolf.__path__):importlib.import_module('werewolf.'+module.name)
    from werewolf.exact import Strategy,ROLES,legal_targets,co_group_compositions
    spec=importlib.util.spec_from_file_location('frozen_replay',ROOT/'tests/fixtures/board_replay_v051.py')
    oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    case=json.loads(Path(args.cases).read_text(encoding='utf-8'))[args.case]
    new=args.version!='old';runtime=None;diagnostic=Diagnostic() if args.diagnostic=='counts' else None
    if diagnostic:diagnostic.install(new,oracle)
    profile=None
    if args.diagnostic=='profile':
        import cProfile
        profile=cProfile.Profile()
    if new:
        from werewolf.board_flow import BoardData
        if importlib.util.find_spec('werewolf.game_runtime') is not None:
            from werewolf.game_runtime import GameRuntime
            runtime=GameRuntime.from_game(case['game'])
    else:
        from werewolf.model_a_public import evaluate_public_game
        from werewolf.private_adapter import evaluate_private_table
        from werewolf.seer_manual import replay
    rows=[];ready=time.perf_counter()-began
    for index in range(args.iterations):
        scope=diagnostic.scope if diagnostic else lambda p:contextlib.nullcontext()
        caches_before=cache_counters(runtime)
        if profile:profile.enable()
        start=time.perf_counter();cpu=time.process_time()
        with experiment_bypass_generated_replay(args.experiment=='bypass-generated'):
            with scope('3a'):
                if new:
                    state=(BoardData.from_game(case['game'],runtime=runtime) if runtime is not None else BoardData.from_game(case['game'])).roles();rules,progress=state.replay_result
                else:
                    rules,progress=(replay(case['game']) if case['game'].get('seer_mode')=='information-fixed-v1' else oracle.reconstruct_saved(case['game']))
                board=progress.last_board if progress.finished else progress.board
                if new:rates,groups,counts=state.rates,state.groups,state.counts
                else:
                    rates=tuple({r:board.role_probability(p,r) for r in ROLES} for p in range(1,board.player_count+1))
                    groups=[] if progress.finished else co_group_compositions(board)
                    counts=board.wolf_count_distribution
            with scope('3b'):
                strategy=Strategy(**case['game']['policy'])
                if case['view']=='public':
                    result=state.forecast(**BUDGET) if new else evaluate_public_game(case['game'],board,rules,strategy,**BUDGET)
                else:
                    view=case['private']
                    result=state.private(view['role'],view['players'],view['results'],**BUDGET) if new else evaluate_private_table(board,view['role'],view['players'],view['results'],rules,strategy,game_state=case['game'],**BUDGET)
        seconds=time.perf_counter()-start;cpu_seconds=time.process_time()-cpu
        if profile:profile.disable()
        caches_after=cache_counters(runtime)
        pending=census_pending(result)
        if case['view']!='public' and any(r['legal'] and r['final'] is None for r in result.get('players',())):
            pending.append(result.get('reason','private_numeric_result_missing'))
        actions=getattr(result,'action_values',())
        tie_groups={}
        for target,value in actions:tie_groups.setdefault(str(value),[]).append(target)
        selected=None
        if board.phase=='day' and actions:
            maximum=max(v for _,v in actions);ties=[p for p,v in actions if v==maximum]
            selected=tuple((p,fractions.Fraction(1,len(ties))) for p in ties) if strategy.day=='max' else tuple((p,fractions.Fraction(1,len(actions))) for p,v in actions)
        semantic=canonical({'public_worlds':tuple(sorted(board.worlds)),'public_roles':tuple(dict(player) for player in rates),'co_groups':groups,'wolf_counts':counts,
            'legal_targets':legal_targets(board,rules,strategy),'result':result,'pending':pending,
            'public_row_tie_groups':tie_groups,'public_day_policy':selected})
        rows.append({'cache':'cold' if index==0 else 'warm','seconds':seconds,'cpu_seconds':cpu_seconds,
                     'complete':not pending,'pending':pending,'cache_before':caches_before,'cache_after':caches_after,'semantic_digest':digest(semantic),'semantic':semantic})
    if diagnostic:diagnostic.close()
    record={'case':args.case,'view':case['view'],'version':args.version,'input_digest':digest(case),
            'budget':BUDGET,'diagnostic':args.diagnostic,'experiment':args.experiment,
            'harness_sha256':hashlib.sha256((ROOT/'benchmarks/board_b_benchmark.py').read_bytes()).hexdigest(),'oracle_sha256':hashlib.sha256((ROOT/'tests/fixtures/board_replay_v051.py').read_bytes()).hexdigest(),'setup_seconds':ready,'worker_cpu_total':time.process_time(),'rows':rows}
    if diagnostic:record['instrumentation']={'counter_schema':'eligible_resolution_v2','phase_exclusive_seconds':diagnostic.seconds,'calls':diagnostic.counts,'input_elements':diagnostic.elements,'warning':'Instrumented time is not normal execution time; normalize elements excludes generators.'}
    if profile:
        import pstats
        destination=Path(args.output).with_suffix('.prof');profile.dump_stats(str(destination))
        stats=pstats.Stats(profile)
        record['profile']={'file':str(destination),'functions':sorted([{'file':key[0],'line':key[1],'function':key[2],'primitive_calls':v[0],'calls':v[1],'self_seconds':v[2],'cumulative_seconds':v[3]} for key,v in stats.stats.items()],key=lambda v:v['self_seconds'],reverse=True)}
    record['process_memory_peak']=process_memory_peak()
    Path(args.output).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')


def process_memory_peak():
    """Native process high-water marks, sampled after request timing."""
    if os.name!='nt':return None
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),
            *[(name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
            'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    current=ctypes.windll.kernel32.GetCurrentProcess;current.restype=wintypes.HANDLE
    query=ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    if not query(current(),ctypes.byref(counters),counters.cb):return None
    return {'peak_working_set_bytes':counters.PeakWorkingSetSize,
            'peak_process_commit_bytes':counters.PeakPagefileUsage,
            'scope':'Whole worker, including startup, semantic output and cold+warm requests; not an isolated per-request allocation count.'}


def system_cpu():
    if os.name!='nt':return None
    import ctypes
    values=[ctypes.c_ulonglong() for _ in range(3)]
    if not ctypes.windll.kernel32.GetSystemTimes(*(ctypes.byref(v) for v in values)):return None
    idle,kernel,user=(v.value for v in values);return idle,kernel+user


def snapshot(destination,revision):
    destination.mkdir(parents=True,exist_ok=True)
    archive=destination.with_suffix('.tar')
    subprocess.run(['git','archive','--format=tar',f'--output={archive}',revision],cwd=ROOT,check=True)
    import tarfile
    with tarfile.open(archive) as tar:tar.extractall(destination,filter='data')
    # No modifying archived source; entrypoint/oracle remain in current checkout.


def run(args):
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    trees=out/'snapshots';versions={'old':OLD,'new':NEW}
    if getattr(args,'board_before_ref',None):
        if not args.improved_ref:raise ValueError('--board-before-ref requires --improved-ref')
        versions={'new':subprocess.check_output(['git','rev-parse','--verify',args.board_before_ref],cwd=ROOT,text=True).strip()}
    if args.improved_ref:versions['improved']=subprocess.check_output(['git','rev-parse','--verify',args.improved_ref],cwd=ROOT,text=True).strip()
    for version,revision in versions.items():snapshot(trees/version,revision)
    cases=json.loads(Path(args.cases).read_text(encoding='utf-8'))
    chosen=args.select.split(',') if args.select else list(cases)
    records=[]
    for repetition in range(args.repeats):
        for name in chosen if repetition%2==0 else reversed(chosen):
            order=tuple(versions) if repetition%2==0 else tuple(reversed(versions))
            if args.experiment!='none':order=('new',)
            for version in order:
                target=out/f'{repetition:02d}-{name}-{version}-{args.diagnostic}-{args.experiment}.json'
                cmd=[sys.executable,'-B',str(Path(__file__).resolve()),'worker','--tree',str(trees/version),'--cases',str(Path(args.cases).resolve()),'--case',name,'--version',version,'--output',str(target),'--iterations',str(1 if args.diagnostic!='none' else 2),'--diagnostic',args.diagnostic,'--experiment',args.experiment]
                before=system_cpu();start=time.perf_counter()
                completed=subprocess.run(cmd,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=150)
                elapsed=time.perf_counter()-start;after=system_cpu()
                if completed.returncode:
                    failure={'command':cmd,'returncode':completed.returncode,'stdout':completed.stdout,'stderr':completed.stderr}
                    target.with_suffix('.error.json').write_text(json.dumps(failure,indent=2),encoding='utf-8');raise RuntimeError(str(target)+': '+completed.stderr[-1500:])
                record=json.loads(target.read_text(encoding='utf-8'));record['repetition']=repetition;record['subprocess_wall_seconds']=elapsed
                background=None
                if before and after:
                    busy=((after[1]-before[1])-(after[0]-before[0]))/1e7
                    total=(after[1]-before[1])/1e7
                    background=100*max(0,busy-record['worker_cpu_total'])/total if total else None
                record['estimated_background_cpu_percent']=background
                for row in record['rows']:row['high_background_load']=background is not None and background>10
                target.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');records.append(record)
                print(json.dumps({'repetition':repetition,'case':name,'version':version,'rows':[{k:r[k] for k in ('cache','seconds','complete')} for r in record['rows']],'background':background}),flush=True)
    groups={};semantics={};mismatches=[]
    for record in records:
        for row in record['rows']:
            key=f"{record['case']}/{record['version']}/{row['cache']}"
            groups.setdefault(key,[]).append(row)
            if row['complete']:
                previous=semantics.setdefault(record['case'],row['semantic_digest'])
                if previous!=row['semantic_digest']:mismatches.append({'case':record['case'],'version':record['version'],'cache':row['cache'],'repetition':record['repetition']})
    result={'environment':{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'processor':platform.processor(),'logical_cpus':os.cpu_count()},'versions':versions,'cases_file_sha256':hashlib.sha256(Path(args.cases).read_bytes()).hexdigest(),'budget':BUDGET,'method':'Fresh child process per version/case/repetition; serial alternating AB/BA and reversed case order. One cold and one identical warm request. Startup separate. All werewolf modules preloaded before evaluation. System busy minus worker CPU estimates background; >10% flagged and separate low-background subset reported, never silently dropped. Timeouts/Pending are censored. Diagnostics separate.','diagnostic':args.diagnostic,'experiment':args.experiment,'summaries':{k:summarize(v) for k,v in groups.items()},'completed_semantic_digests':semantics,'mismatches':mismatches,'records':records}
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if mismatches:raise AssertionError('Completed semantic mismatch: '+repr(mismatches))


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('run');p.add_argument('--output',required=True);p.add_argument('--repeats',type=int,default=5);p.add_argument('--select');p.add_argument('--improved-ref');p.add_argument('--board-before-ref',help='Compare two BoardData revisions, labelled new/improved; requires --improved-ref');p.add_argument('--cases',default=str(ROOT/'benchmarks/board_b_cases.json'))
    p.add_argument('--diagnostic',choices=('none','counts','profile'),default='none');p.add_argument('--experiment',choices=('none','bypass-generated'),default='none')
    p=sub.add_parser('worker');p.add_argument('--tree',required=True);p.add_argument('--cases',required=True);p.add_argument('--case',required=True);p.add_argument('--version',choices=('old','new','improved'),required=True);p.add_argument('--output',required=True);p.add_argument('--iterations',type=int,default=2);p.add_argument('--diagnostic',choices=('none','counts','profile'),default='none');p.add_argument('--experiment',choices=('none','bypass-generated'),default='none')
    args=parser.parse_args();worker(args) if args.command=='worker' else run(args)

if __name__=='__main__':main()
