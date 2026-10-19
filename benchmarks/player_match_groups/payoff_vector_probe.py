"""Small isolated scalar/vector requests; existing250000/30s/384MiB supervisor."""
from pathlib import Path
from datetime import datetime,timezone
from time import perf_counter
from dataclasses import asdict
import json,sys,hashlib
from .initial_seven_entry_probe import watch


def nodes(c,multi):
    from werewolf.actor_information import PersonalInformation,WolfInformation
    root=c.root;out=[root]
    if not multi:return out
    seen=set()
    for h in root.read().private.hypotheses:
        for actor in root.read().public.alive:
            if h.roles[2]&(1<<(actor-1)):
                info=PersonalInformation(actor,'seer',tuple(a for a in h.acquisitions if a.player==actor))
                if info not in seen:seen.add(info);out.append(root.personal(info)[1])
        info=WolfInformation.from_hypothesis(h)
        if info not in seen:seen.add(info);out.append(root.personal(info)[1])
    return out


def worker(kind,mode,multi):
    from .closed_full_tree_fixture import case
    from .cut_out_publication_orbit_value_fixture import tables
    from .payoff_vector_experiment import PayoffVectorExperiment
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.exact import Strategy
    from werewolf.calculation_budget import calculation_budget,budget_usage,budget_stop,CalculationBudgetExceeded
    from werewolf.information_set_forecast import Pending
    out={'kind':kind,'mode':mode,'multi':multi,'completed':False};at=perf_counter();c=None;vector=None
    try:
        with calculation_budget(250000,max_seconds=30):
            data=case(5,kind).data.updated(policy=asdict(Strategy()))
            c=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)
            selected=nodes(c,multi);out['view_count']=len(selected)
            if mode=='vector':vector=PayoffVectorExperiment(c)
            setup=budget_usage()['work'];start=perf_counter();results=[];times=[]
            for node in selected:
                before=budget_usage()['work'];began=perf_counter()
                f=vector.forecast(node) if vector else node.forecast()
                results.append({'forecast':repr(f),'table_sha256':hashlib.sha256(repr(tables(node.read(),f)).encode()).hexdigest()})
                times.append({'seconds':perf_counter()-began,'work':budget_usage()['work']-before})
            out.update(completed=True,results=results,view_costs=times,forecast_seconds=perf_counter()-start,forecast_work=budget_usage()['work']-setup,setup_work=setup,budget=budget_usage())
    except CalculationBudgetExceeded as error:out.update(status='budget_stopped',reason=error.kind,stop=budget_stop())
    except Pending as error:out.update(status='pending',reason=error.reason,stop=budget_stop())
    out['seconds']=perf_counter()-at
    if c:out['scalar_engine']=c.stats()
    if vector:out['vector']=vector.stats()
    print(json.dumps(out))


def run():
    rows=[]
    for kind in ('dual','three'):
        for multi in (False,True):
            for mode in ('scalar','vector'):
                row=watch('benchmarks.player_match_groups.payoff_vector_probe',('worker',kind,mode,str(int(multi))))
                rows.append(row)
    for i in range(0,len(rows),2):
        a,b=rows[i:i+2]
        if a.get('worker',{}).get('completed') and b.get('worker',{}).get('completed'):assert a['worker']['results']==b['worker']['results']
    out={'at':datetime.now(timezone.utc).isoformat(),'scope':'Development initial-five full-horizon root-secret vector with existing public/actor-Q scalar policy engine; public only vs all supported root seer/wolf owner views. All by-dawn outputs stay existing exact horizon calls and are included. Separate fresh workers, unchanged250000work/30s/384MiB sampled supervisor. No seven run.','measurements':rows,'source_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('benchmarks/player_match_groups/payoff_vector_experiment.py','benchmarks/player_match_groups/payoff_vector_probe.py','werewolf/information_set_forecast.py','werewolf/grouped_forecast.py')}}
    Path('benchmarks/player_match_groups/payoff-vector-results.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{'kind':r.get('worker',{}).get('kind'),'mode':r.get('worker',{}).get('mode'),'multi':r.get('worker',{}).get('multi'),'complete':r.get('worker',{}).get('completed'),'work':r.get('worker',{}).get('forecast_work'),'seconds':r.get('worker',{}).get('forecast_seconds'),'ws':r.get('observed_peak_working_set_bytes'),'vector':r.get('worker',{}).get('vector'),'error':r.get('partial_stdout',r.get('stderr'))} for r in rows]))

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(sys.argv[2],sys.argv[3],bool(int(sys.argv[4])))
    else:run()
