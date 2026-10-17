"""Offline exact root-intervention checkpoints; never a production evaluator.

Day/random only. No maximization or observer conditioning is moved across sums.
Each worker has independent ungrouped/grouped engines and finite resource limits.
"""
import argparse,hashlib,json,subprocess,sys,time,threading
from dataclasses import asdict,fields,is_dataclass
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
CACHE=ROOT/'.artifacts/player-match-checkpoints'


def encode(value):
    if isinstance(value,F):return str(value)
    if is_dataclass(value):return {f.name:encode(getattr(value,f.name))for f in fields(value)}
    if isinstance(value,(tuple,list)):return [encode(v)for v in value]
    if isinstance(value,dict):return {k:encode(v)for k,v in value.items()}
    return value

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(encode(value),indent=2),encoding='utf-8')
    for attempt in range(5):
        try:temp.replace(path);break
        except PermissionError:
            if attempt==4:raise
            time.sleep(.01)

def read(path):
    for attempt in range(5):
        try:return json.loads(path.read_text(encoding='utf-8'))
        except PermissionError:
            if attempt==4:raise
            time.sleep(.01)

def numeric(row):return {k:row.get(k)for k in ('engine','input','target','bite','mode','status','action','dawn','root_branches','plan','completed_terms')}


def digest(value):return hashlib.sha256(json.dumps(encode(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def engine_version():
    paths=[ROOT/'app.py',*sorted((ROOT/'werewolf').glob('*.py')),
        Path(__file__),ROOT/'benchmarks/player_match_groups/deep_checkpoint.py',ROOT/'benchmarks/player_match_groups/initial_white.py',ROOT/'benchmarks/player_match_groups/run.py']
    return digest([(str(p.relative_to(ROOT)),hashlib.sha256(p.read_bytes()).hexdigest())for p in paths])

def prepared_game(game):
    from werewolf.board_flow import BoardData
    from werewolf.board_roles import prepare_evaluation
    from werewolf.exact import Strategy
    from werewolf.player_view import build_public_view,ViewScope,ResultFrame
    data=BoardData.from_game(game);roles=data.roles();b=roles.board;strategy=Strategy(**game['policy'])
    kind,value=prepare_evaluation(game,b,roles.rules,strategy,max_work=4000000,max_seconds=120)
    if kind!='prior':raise ValueError('Only the existing prepared-prior route is partitioned')
    state,past=value
    view=build_public_view(data,roles,b,ResultFrame(ViewScope.public(data),'roles'),state=game,event_history=b.history,alive=b.alive,action_values={},by_dawn_values={})
    if b.phase!='day'or strategy.day!='random'or strategy.night!='random'or strategy.fake_reports!='random'or b.initial_hunter_count:
        raise ValueError('Partition contract is random daytime/no-hunter only; max is not repartitioned')
    return data,roles,b,state,past,roles.rules,strategy,view

def case_input(n,w):
    path=CACHE/f'inputs/dual-{n}-{w}.json'
    if path.exists():game=json.loads(path.read_text(encoding='utf-8'))
    else:
        from benchmarks.player_match_groups.initial_white import initial_white_source
        game=initial_white_source(n,w,actors=(1,2))[0].to_game();write(path,game)
    if(game['players'],game['wolves'],game['claims'])!=(n,w,['seer','seer']+['latent']*(n-2)):
        raise ValueError('Saved original input does not match requested case')
    return path,game

def night_plan(prepared,engine,target):
    """Exact expansion of day action_flow followed by solve(night/random).

    Coefficients retain root physical mass * actor-information mass * configured
    bite probability. They are not normalized within a selected bite partition.
    """
    from werewolf.action_flow import resolve_action
    from werewolf.evaluation_branch import ActionInputs,physical_board
    from werewolf.actor_information import wolf_information_groups
    from werewolf.model_a_public import horizon_for_action
    _,_,b,state,past,rules,strategy,_=prepared
    initial=ActionInputs(state,past,state,None,physical_board(b,state))
    acquired,outcomes=resolve_action(b,initial,target,engine.action_policy,terminal_payoffs=True)
    terms=[];direct=[]
    for outcome in outcomes:
        q=outcome.probability
        if outcome.board.winner is not None:
            direct.append(dict(weight=q,value=F(outcome.board.winner=='village'),kind='terminal'));continue
        payload=engine.action_policy.project(b,acquired,outcome,target)
        child,public,history,own,observer=engine.continuation_context(*payload)
        physical=physical_board(child,own,payload.physical)
        if engine.exchangeable(child):
            direct.append(dict(weight=q,value=engine.solve(child,public,history,own,observer,physical=physical),kind='existing_exchangeable'));continue
        if child.phase!='night'or observer is not None:raise ValueError('Unexpected continuation scope')
        for info,mass,group in wolf_information_groups(own):
            actual=physical_board(child,group,physical)
            for bite,probability in engine.wolf_policy(child,public,history,info.initial_roster,info.attacks):
                weight=q*mass*probability
                inputs=(child,public,history,group,observer,actual,bite)
                terms.append(dict(bite=bite,weight=weight,physical_mass=q,information_mass=mass,policy_probability=probability,signature=digest(inputs),inputs=inputs))
    if sum((t['weight']for t in terms),F())+sum((d['weight']for d in direct),F())!=1:
        raise ValueError('Partition coefficients do not preserve unit incoming mass')
    metadata=encode(dict(root_branches=outcomes,dawn=horizon_for_action(engine,b,state,past,target,state),direct=direct,
        terms=[{k:v for k,v in t.items()if k!='inputs'}for t in terms]))
    return terms,metadata


def worker(case_path,target,mode,output,seconds,memory,expected_engine,bite=None):
    from benchmarks.board_b_benchmark import process_memory_peak
    from werewolf.calculation_budget import calculation_budget,cancellation_scope,CalculationCancelled,CalculationBudgetExceeded,budget_stop
    from werewolf.information_set_forecast import InformationSetForecast,Pending
    from werewolf.evaluation_projection import project_evaluation
    from werewolf.evaluation_branch import ActionInputs,physical_board
    from werewolf.action_flow import resolve_action
    from werewolf.model_a_public import horizon_for_action
    from werewolf.exact import legal_targets
    from werewolf.match_groups import make_engine
    started=time.perf_counter();cancel=threading.Event();done=threading.Event();reason=[None];engine=[None];lock=threading.Lock()
    game=json.loads(case_path.read_text(encoding='utf-8'))
    row=dict(status='pending',target=target,bite=bite,mode=mode,engine=expected_engine,input=digest(game),action=None,dawn=None,root_branches=None,completed_terms=[])
    def checkpoint():
        with lock:
            peak=process_memory_peak();e=engine[0]
            row.update(seconds=time.perf_counter()-started,memory=peak,stats=dict(e.stats)if e and hasattr(e,'stats')else {},expansions=dict(e.expansions)if e else {},audited_batches=len(e.audits)if e and hasattr(e,'audits')else 0)
            write(output,row)
            if peak and max(peak['peak_working_set_bytes'],peak['peak_process_commit_bytes'])>=memory:
                reason[0]='memory_limit';cancel.set()
    def monitor():
        while not done.wait(.25):checkpoint()
    thread=threading.Thread(target=monitor,daemon=True)
    try:
        if engine_version()!=expected_engine:raise ValueError('Engine fingerprint changed before worker start')
        thread.start()
        with calculation_budget(4000000,max_seconds=seconds),cancellation_scope(cancel):
            data,roles,b,state,past,rules,strategy,view=prepared_game(game)
            b,state=project_evaluation(b,state,strategy)
            if target not in legal_targets(b,rules,strategy):raise ValueError('Illegal root intervention')
            if mode=='audit':
                # Provisional scope exists only in this isolated acceptance worker.
                import werewolf.match_groups as matching
                import inspect
                source=inspect.getsource(matching._dual_white_ledger_supported)
                exec(compile(source.replace('    if board.player_count>6:return False\n',''),matching.__file__,'exec'),matching.__dict__)
                e=make_engine(b,state,past,rules,strategy,enabled=True,view=view,audit=True,max_work=4000000)
                if not e.grouping:raise ValueError('Fixture outside provisional dual-white contract')
            else:e=InformationSetForecast(rules,strategy,max_work=4000000)
            engine[0]=e
            initial=ActionInputs(state,past,state,None,physical_board(b,state))
            _,outcomes=resolve_action(b,initial,target,e.action_policy,terminal_payoffs=True)
            if sum((o.probability for o in outcomes),F())!=1:raise ValueError('Root physical mass does not sum to one')
            row['root_branches']=encode(outcomes)
            # Horizon is an independent exact metric; preserve it even if final
            # continuation later runs out of budget. No missing final is zero.
            row['dawn']=encode(horizon_for_action(e,b,state,past,target,state));checkpoint()
            if bite is None:value=e.act(b,state,past,target,state,None)
            else:
                terms,metadata=night_plan((data,roles,b,state,past,rules,strategy,view),e,target)
                row['plan']=metadata
                selected=[t for t in terms if t['bite']==bite]
                if not selected:raise ValueError('Unknown night partition')
                value=F()
                for term in selected:
                    child,public,history,group,observer,actual,fixed=term['inputs']
                    v=e.act(child,public,history,fixed,group,observer,physical=actual)
                    value+=term['weight']*v
                    row['completed_terms'].append(dict(signature=term['signature'],weight=str(term['weight']),value=str(v)))
                    checkpoint()
            row['action']=str(value)
            if engine_version()!=expected_engine:raise ValueError('Engine fingerprint changed during computation')
            if cancel.is_set():raise CalculationCancelled()
            row['status']='complete'
    except CalculationCancelled:row['reason']=reason[0]or'cancelled'
    except CalculationBudgetExceeded:row['reason']=(budget_stop()or{}).get('kind','budget')+'_limit';row['budget_stop']=budget_stop()
    except Pending as error:row['reason']=error.reason
    except Exception as error:row['reason']=f'{type(error).__name__}: {error}'
    finally:
        done.set()
        if thread.is_alive():thread.join()
        checkpoint()
        if cancel.is_set():row['status']='pending';row['reason']=reason[0]or row.get('reason','cancelled');write(output,row)
        if row['status']=='complete':row['numeric_digest']=digest(numeric(row));write(output,row)
    return row

def aggregate(game,parts):
    from werewolf.exact import legal_targets,Values
    from werewolf.by_dawn import HorizonValues
    from werewolf.player_view import build_public_view,ResultFrame
    data,roles,b,state,past,rules,strategy,view=prepared_game(game)
    targets=legal_targets(b,rules,strategy)
    complete=[t for t in targets if str(t)in parts and parts[str(t)]['status']=='complete']
    if tuple(complete)!=targets:return dict(status='pending',completed_targets=complete,missing_targets=[t for t in targets if t not in complete],value=None,table=None)
    # Existing solve(day=random, public private=state) is exactly the arithmetic
    # expectation over these full intervention values. No max/per-world choice.
    values={t:F(parts[str(t)]['action'])for t in targets}
    dawn={t:HorizonValues(**{k:F(v)for k,v in parts[str(t)]['dawn'].items()})for t in targets}
    result=build_public_view(data,roles,b,ResultFrame(view.scope,'complete'),state=game,event_history=b.history,alive=b.alive,action_values={t:Values(v,1-v)for t,v in values.items()},by_dawn_values=dawn)
    return encode(dict(status='complete',completed_targets=complete,missing_targets=[],value=sum(values.values(),F())/len(targets),table=[p.to_legacy_row()for p in result.players]))

def run_case(n,w,*,total_seconds=600,chunk_seconds=120,memory_bytes=1500000000,cache=CACHE):
    global CACHE
    CACHE=cache
    case_path,game=case_input(n,w);version=engine_version();identity=digest(dict(game=game,engine=version,contract='day-random-root-interventions-v1'))
    folder=CACHE/identity;meter_path=folder/'meter.json';summary_path=folder/'summary.json'
    old=json.loads(meter_path.read_text())if meter_path.exists()else {'consumed_seconds':0}
    charged=old['consumed_seconds'];started=time.perf_counter();parts={'oracle':{},'audit':{}};attempts=[]
    def snapshot():
        summary=dict(identity=identity,engine=version,input=digest(game),limits=dict(total_seconds=total_seconds,chunk_seconds=chunk_seconds,memory_bytes=memory_bytes),consumed_seconds=charged+time.perf_counter()-started,parts=parts,attempts=attempts)
        for mode in parts:summary[mode]=aggregate(game,parts[mode])
        summary['verified_targets']=[]
        for t in parts['oracle'].keys()&parts['audit'].keys():
            a=parts['oracle'][t];b=parts['audit'][t]
            if a['status']=='complete'and b['status']=='complete':
                for key in ('action','dawn','root_branches'):
                    if a[key]!=b[key]:raise AssertionError(f'Partition mismatch target={t} {key}')
                summary['verified_targets'].append(int(t))
        summary['verified_targets'].sort()
        summary['complete']=summary['oracle']['status']=='complete'and summary['audit']['status']=='complete'
        if summary['complete']and summary['oracle']!=summary['audit']:raise AssertionError('Aggregated forecasts differ')
        write(summary_path,summary);write(meter_path,{'consumed_seconds':summary['consumed_seconds']})
        return summary
    for target in range(1,n+1):
        for mode in ('oracle','audit'):
            output=folder/f'{mode}-{target}.json'
            if output.exists():
                row=json.loads(output.read_text())
                if row.get('engine')!=version or row.get('input')!=digest(game):raise ValueError('Checkpoint identity mismatch')
                parts[mode][str(target)]=row
                # Completed and pending attempts are not automatically rerun.
                attempts.append(dict(target=target,mode=mode,reused=True,status=row['status']));continue
            if mode=='audit'and parts['oracle'].get(str(target),{}).get('status')!='complete':continue
            remaining=total_seconds-(charged+time.perf_counter()-started)
            if remaining<=0:break
            limit=min(chunk_seconds,remaining)
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'worker','--input',str(case_path),'--target',str(target),'--mode',mode,'--output',str(output),'--seconds',str(limit),'--memory',str(memory_bytes),'--engine',version],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            worker_started=time.perf_counter()
            while process.poll()is None:
                time.sleep(.25)
                used=time.perf_counter()-worker_started
                if output.exists():
                    row=json.loads(output.read_text())
                    peak=row.get('memory')or{}
                    hard_memory=max(peak.get('peak_working_set_bytes',0),peak.get('peak_process_commit_bytes',0))>memory_bytes+50000000
                else:hard_memory=False
                if used>limit+2 or charged+time.perf_counter()-started>=total_seconds or hard_memory:
                    process.kill();process.wait()
                    row=json.loads(output.read_text())if output.exists()else dict(target=target,mode=mode,engine=version,input=digest(game),action=None,dawn=None,root_branches=None)
                    row.update(status='pending',reason='memory_limit'if hard_memory else 'time_limit',seconds=used);write(output,row);break
                write(meter_path,{'consumed_seconds':charged+time.perf_counter()-started})
            stdout,stderr=process.communicate()
            row=json.loads(output.read_text())
            if stderr:row['worker_log']=stderr;write(output,row)
            parts[mode][str(target)]=row;attempts.append(dict(target=target,mode=mode,reused=False,status=row['status'],seconds=time.perf_counter()-worker_started))
            print(json.dumps(dict(target=target,mode=mode,status=row['status'],reason=row.get('reason'),seconds=row.get('seconds'),memory=row.get('memory'))),flush=True)
            snapshot()
        if charged+time.perf_counter()-started>=total_seconds:break
    return snapshot()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['worker','run']);parser.add_argument('--input',type=Path);parser.add_argument('--target',type=int);parser.add_argument('--mode',choices=['oracle','audit']);parser.add_argument('--bite',type=int);parser.add_argument('--output',type=Path);parser.add_argument('--seconds',type=float,default=120);parser.add_argument('--memory',type=int,default=1500000000);parser.add_argument('--engine');parser.add_argument('--players',type=int,default=7);parser.add_argument('--wolves',type=int,default=2);parser.add_argument('--total',type=float,default=600);args=parser.parse_args()
    if args.action=='worker':worker(args.input,args.target,args.mode,args.output,args.seconds,args.memory,args.engine,args.bite)
    else:
        result=run_case(args.players,args.wolves,total_seconds=args.total,chunk_seconds=args.seconds,memory_bytes=args.memory)
        print(json.dumps({k:result[k]for k in ('identity','consumed_seconds','verified_targets','complete','oracle','audit')}),flush=True)
