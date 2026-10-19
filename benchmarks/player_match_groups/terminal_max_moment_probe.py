"""Bounded measurement of opt-in terminal MAX moments; no default changes."""
import json,sys,time,hashlib
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone
from .initial_seven_entry_probe import watch,LIMITS


def worker(mode):
    from werewolf.calculation_budget import calculation_budget,budget_usage,CalculationBudgetExceeded
    from werewolf.information_set_forecast import InformationSetForecast,Pending
    from werewolf.grouped_forecast import GroupedForecast
    from werewolf.exact import Strategy
    from werewolf.board_future import kernel_calculation
    from werewolf.board_flow import BoardData
    from werewolf.closed_calculation import ClosedCalculation
    from .closed_full_tree_fixture import case
    result={'mode':mode,'completed':False};start=time.perf_counter()
    try:
        with kernel_calculation(),calculation_budget(LIMITS['max_work'],max_seconds=LIMITS['max_seconds']):
            if mode=='seven':
                game=json.loads(Path('benchmarks/player_match_groups/actual-seven-max-results.json').read_text(encoding='utf-8'))['game']
                assert Strategy(**game['policy'])==Strategy()
                c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_reports=True)
                result['input_sha256']=hashlib.sha256(json.dumps(game,sort_keys=True).encode()).hexdigest()
                f=c.root.forecast();result.update(value=str(f.village_win),actions=[(p,str(v)) for p,v in f.action_values],stats=c.stats())
            else:
                data=case(5,mode).data.updated(policy=asdict(Strategy()))
                c=ClosedCalculation(data,grouped=True,aggregate_reports=True)
                target=3 if mode in ('single','dual') else 4
                n=next(r.node for r in c.root.action(target) if r.node.read().public.winner is None)
                n=next(r.node for r in n.action(5) if r.node.read().public.winner is None)
                source=n.read();runs=[]
                for name,engine in [('ordinary',InformationSetForecast),('moments',GroupedForecast)]:
                    e=engine(c.data.game_data.rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False,**({'aggregate_reports':True} if name=='moments' else {}))
                    e.retain_joint_guard_history=True
                    before=budget_usage()['work'];at=time.perf_counter()
                    value=e.action_policy.morning_value(source)
                    runs.append(dict(name=name,value=str(value),seconds=time.perf_counter()-at,work=budget_usage()['work']-before,
                        posterior_events=sum(len(k.events) for k in getattr(e,'report_kernels',{}).values()),publication_rows=sum(len(v) for v in e.publication_values.values()),values=len(e.values),actions=len(e.action_values)))
                assert runs[0]['value']==runs[1]['value'];result['runs']=runs
            result.update(completed=True,budget=budget_usage())
    except CalculationBudgetExceeded as error:result.update(status='budget_stopped',reason=error.kind)
    except Pending as error:result.update(status='unsupported',reason=error.reason)
    result['seconds']=time.perf_counter()-start
    print(json.dumps(result),flush=True)


def run():
    rows=[watch('benchmarks.player_match_groups.terminal_max_moment_probe',('worker',mode)) for mode in ('single','dual','three','medium-pair','seven')]
    result={'at':datetime.now(timezone.utc).isoformat(),'measurements':rows,'note':'One seven MAX attempt only; limits unchanged. Small runs compare the same conditional frame, not the full initial game.'}
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/grouped_forecast.py','werewolf/morning_publications.py','werewolf/information_set_forecast.py','werewolf/information_weights.py','werewolf/closed_calculation.py'))}
    Path('benchmarks/player_match_groups/terminal-max-moment-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(sys.argv[2])
    else:run()
