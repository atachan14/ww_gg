"""Bounded local attribution; never rerun an unchanged whole seven MAX."""
import json,sys,time,cProfile,pstats,hashlib
from pathlib import Path
from .initial_seven_entry_probe import watch,LIMITS


def worker(case,mode):
    from .dead_history_design import dead_two_seers,actual_dead_seer_prefix,ModernDeadExperiment,PairedDeadExperiment
    from werewolf.grouped_forecast import GroupedForecast
    from werewolf.board_future import kernel_calculation
    from werewolf.calculation_budget import calculation_budget,budget_usage,CalculationBudgetExceeded
    from werewolf.information_set_forecast import Pending
    from werewolf.exact import Strategy
    result={'case':case,'mode':mode,'completed':False};at=time.perf_counter();prof=cProfile.Profile();e=None
    try:
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            c,n=(dead_two_seers() if case=='toy' else actual_dead_seer_prefix());source=n.read()
            result.update(source_hypotheses=len(source.public_state.hypotheses),alive=source.public.alive,phase=source.public.phase)
            cls={'base':GroupedForecast,'candidate':ModernDeadExperiment,'paired':PairedDeadExperiment,'production':GroupedForecast}[mode]
            e=cls(c.data.game_data.rules,Strategy(),aggregate_reports=True,exact_renaming=False,retire_uninformative_scans=False)
            e.retain_joint_guard_history=True
            if mode=='base':e.scalar_laws=lambda b,s,private,observer:(s,private)
            before=budget_usage()['work'];start=time.perf_counter();prof.enable()
            value=(e.solve(*source,physical=source.physical) if case=='toy' else e.action_policy.morning_value(source))
            prof.disable();result.update(value=str(value),completed=True,seconds=time.perf_counter()-start,work=budget_usage()['work']-before)
    except CalculationBudgetExceeded as error:result.update(status='budget_stopped',reason=error.kind)
    except Pending as error:result.update(status='unsupported',reason=error.reason)
    finally:
        prof.disable();result['whole_seconds']=time.perf_counter()-at
        if e:
            result.update(expansions=e.expansions,values=len(e.values),actions=len(e.action_values),mornings=len(e.mornings),report_kernels=len(e.report_kernels),projection_visits=dict(getattr(e,'visits',{})))
        stats=pstats.Stats(prof);result['profile_self_top']=sorted([{'file':name,'line':line,'function':fn,'calls':v[1],'self':v[2],'cumulative':v[3]} for (name,line,fn),v in stats.stats.items()],key=lambda row:row['self'],reverse=True)[:15]
    print(json.dumps(result))


def run():
    results=[watch('benchmarks.player_match_groups.dead_history_probe',('worker',case,mode)) for case in ('toy','actual-prefix') for mode in ('base','production')]
    output={'scope':'Local complete scalar comparisons on toy four-day and actual forced execute4/bite1 five-day premorning. No full initial-seven calculation. cProfile overhead is present.','results':results}
    Path('benchmarks/player_match_groups/dead-history-production-local-results.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    output['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/grouped_forecast.py','werewolf/evaluation_projection.py','benchmarks/player_match_groups/dead_history_probe.py'))}
    Path('benchmarks/player_match_groups/dead-history-production-local-results.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(output))

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(*sys.argv[2:])
    else:run()
