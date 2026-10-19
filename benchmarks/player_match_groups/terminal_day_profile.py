"""Development-only bounded group census and terminal-cut comparison."""
import json,sys,time,hashlib
from pathlib import Path
from collections import Counter
from unittest.mock import patch
from .initial_seven_entry_probe import watch,LIMITS


def worker(mode):
    from .cut_out_user_seven_uniform_preparation import comparison_game
    from .cut_out_uniform_game_fixture import peak_bytes
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.board_flow import BoardData
    from werewolf.grouped_forecast import GroupedForecast
    from werewolf.information_set_forecast import InformationSetForecast,Pending
    from werewolf.calculation_budget import calculation_budget,budget_usage,budget_stop,CalculationBudgetExceeded
    counts=Counter();phases=Counter();partitions=Counter();stages=[];examples={};depth=0;c=None;result=dict(forecast_completed=False)
    started=time.perf_counter()
    try:
        with calculation_budget(LIMITS['max_work'],max_seconds=LIMITS['max_seconds']):
            c=ClosedCalculation(BoardData.from_game(comparison_game()[1]),grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=LIMITS['max_work'],max_seconds=LIMITS['max_seconds'])
            node=c.root.observe(4)[1];e=c._ClosedCalculation__engine
            solve=e.solve;act=e.act;partition=e.report_partition
            def s(*args,**kw):
                nonlocal depth
                b=args[0];phases[str((b.day,b.phase,len(b.alive)))]+=1
                counts['solve_calls']+=1
                if b.phase=='day' and len(b.alive)==3 and set(b.wolf_count_distribution)=={1}:counts['terminal_uniform_day_calls']+=1
                top=depth==0;stage=None
                if top:stage=dict(kind='solve',completed=False);stages.append(stage)
                depth+=1
                try:
                    v=solve(*args,**kw)
                    if stage is not None:stage.update(completed=True,value=str(v))
                    return v
                finally:depth-=1
            def a(*args,**kw):
                nonlocal depth
                b=args[0];counts['act_calls']+=1
                counts['act_target_members']+=len(b.alive)
                counts['act_inherited_blocks']+=len(tuple(g for g in e.groups if any(p in b.alive for p in g)))
                if b.phase=='day' and len(b.alive)==3:counts['three_day_act_calls']+=1
                top=depth==0;stage=None
                if top:stage=dict(kind='act',target=args[3],completed=False);stages.append(stage)
                depth+=1
                try:
                    v=act(*args,**kw)
                    if stage is not None:stage.update(completed=True,value=str(v))
                    return v
                finally:depth-=1
            def part(b,past):
                value=partition(b,past);reporters=tuple(p for p in b.alive if b.claims[p-1]=='seer')
                label=str((len(reporters),tuple(map(len,value))))
                partitions[label]+=1
                if len(reporters)==2 and label not in examples:
                    examples[label]=dict(alive=b.alive,groups=e.groups,past=[repr(r) for r in past],public_reports=[repr(r) for r in b.reports],partition=value,hypotheses=None)
                return value
            with patch.object(e,'solve',s),patch.object(e,'act',a),patch.object(e,'report_partition',part):
                if mode=='baseline':
                    with patch.object(e,'exchangeable',InformationSetForecast.exchangeable.__get__(e)):
                        f=node.forecast()
                else:f=node.forecast()
                result.update(forecast_completed=True,value=str(f.village_win),forecast=repr(f))
            result['budget']=budget_usage()
    except CalculationBudgetExceeded as error:result.update(status='budget_stopped',reason=error.kind)
    except Pending as error:result.update(status='pending',reason=error.reason)
    result.update(mode=mode,seconds=time.perf_counter()-started,budget_stop=budget_stop(),counts=dict(counts),phases=dict(phases),report_partitions=dict(partitions),partition_examples=examples,stages=stages,peak_working_set_bytes=peak_bytes())
    if c is not None:result['states']=c.stats()
    print(json.dumps(result),flush=True)


def run(mode):
    result=watch('benchmarks.player_match_groups.terminal_day_profile',('worker',mode))
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/grouped_forecast.py','werewolf/information_set_forecast.py',__file__))}
    Path('benchmarks/player_match_groups/terminal-day-'+mode+'.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(sys.argv[2])
    else:print(json.dumps(run(sys.argv[1])))
