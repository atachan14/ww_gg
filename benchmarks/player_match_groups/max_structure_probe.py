"""Complete small-input cost decomposition, never a seven-player forecast."""
import json,sys,time,hashlib,cProfile,pstats
from pathlib import Path
from collections import Counter
from unittest.mock import patch
from .initial_seven_entry_probe import watch,LIMITS


def worker(kind,mode,view):
    from .max_structure_design import calculation
    from .cut_out_publication_orbit_value_fixture import tables
    from werewolf.information_set_forecast import InformationSetForecast,Pending
    from werewolf.morning_publications import CompiledPublications
    from werewolf.calculation_budget import calculation_budget,budget_usage,budget_stop,CalculationBudgetExceeded
    counters=Counter();phases=Counter();rows=Counter();branch_sizes=Counter();c=None;result={'kind':kind,'mode':mode,'view':view,'completed':False}
    old_act=InformationSetForecast.uncached_act;old_value=CompiledPublications.terminal_execution_value;old_build=CompiledPublications.terminal_execution_moments;old_publications=InformationSetForecast.generate_publications
    def act(e,b,s,past,target,private,observer,**kw):
        k=f'{len(b.alive)}-{b.phase}';phases[k]+=1;rows[k]+=len(s.hypotheses)+len(private.hypotheses)
        return old_act(e,b,s,past,target,private,observer,**kw)
    def value(k,private,targets,**kw):
        counters['moment_calls']+=1;return old_value(k,private,targets,**kw)
    def build(k,targets,**kw):
        counters['moment_builds']+=1
        before=k.stats['built_vectors'];out=old_build(k,targets,**kw)
        counters['moment_fibers']+=len(out);return out
    def publications(e,b,s,past):
        out=old_publications(e,b,s,past)
        if isinstance(out,tuple):branch_sizes[str(len(out))]+=1
        return out
    prof=cProfile.Profile();at=time.perf_counter()
    try:
        with calculation_budget(250000,max_seconds=30),patch.object(InformationSetForecast,'uncached_act',act),patch.object(CompiledPublications,'terminal_execution_value',value),patch.object(CompiledPublications,'terminal_execution_moments',build),patch.object(InformationSetForecast,'generate_publications',publications):
            c,n=calculation(kind,mode,view);prof.enable();f=n.forecast();prof.disable()
            result.update(completed=True,value=str(f.village_win),actions=[(p,str(v)) for p,v in f.action_values],dawn=[(p,str(v)) for p,v in f.by_dawn_values],table_sha256=hashlib.sha256(json.dumps(tables(n.read(),f),sort_keys=True,default=str).encode()).hexdigest(),budget=budget_usage())
    except CalculationBudgetExceeded as error:result.update(status='budget_stopped',reason=error.kind,stop=budget_stop())
    except Pending as error:result.update(status='unsupported',reason=error.reason)
    finally:prof.disable()
    result.update(seconds=time.perf_counter()-at,actions_by_phase=dict(phases),action_rows_by_phase=dict(rows),moments=dict(counters),publication_branch_histogram=dict(branch_sizes))
    if c:result['states']=c.stats()
    stats=pstats.Stats(prof)
    modules=Counter()
    for (name,line,fn),row in stats.stats.items():modules[Path(name).name]+=row[2]
    result['profile_self_by_module']=dict(modules);result['profile_total_self_seconds']=sum(modules.values())
    result['profile_self_top']=sorted([dict(file=name,line=line,function=fn,calls=v[1],self_seconds=v[2],cumulative_seconds=v[3]) for (name,line,fn),v in stats.stats.items()],key=lambda row:row['self_seconds'],reverse=True)[:15]
    print(json.dumps(result))


def run():
    jobs=[(kind,mode,view) for kind in ('single','dual','three','medium-pair') for view in ('public','seer','wolf') for mode in ('baseline','orbits')]
    results=[watch('benchmarks.player_match_groups.max_structure_probe',('worker',*job)) for job in jobs]
    out={'scope':'Complete five-player configured MAX requests: four configurations x three views x baseline/development orbit candidate. No seven run, no production modification. cProfile times include instrumentation.','results':results}
    out['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('benchmarks/player_match_groups/max_structure_design.py','benchmarks/player_match_groups/max_structure_probe.py','werewolf/grouped_forecast.py','werewolf/information_set_forecast.py'))}
    Path('benchmarks/player_match_groups/max-structure-small-results.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'runs':len(results),'completed':sum(r.get('worker',{}).get('completed',False) for r in results)}))

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(*sys.argv[2:])
    else:run()
