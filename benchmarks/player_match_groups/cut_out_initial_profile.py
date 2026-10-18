"""One <=10s diagnostic worker; no Forecast completion or speedup claim."""
import cProfile,pstats,json,os,time,threading,sys,gc
from collections import Counter
from pathlib import Path
from .cut_out_initial_publications import base,scope,InitialPublicationEngine,stats
from .cut_out_uniform_game_fixture import peak_bytes
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,budget_stop
from werewolf.board_future import calculation_origin,remember
from werewolf.information_set_forecast import Pending


def census(e):
    keys=list(e.board_sources)
    fields={}
    for i,name in ((0,'public_Board'),(1,'Q'),(2,'past'),(3,'P'),(5,'physical_Board')):
        rows=[k.values[i] for k in keys]
        fields[name]=dict(references=len(rows),distinct_identity=len({id(x) for x in rows}),distinct_value=len(set(rows)))
    requests=list(e.board_sources.values());ops={id(op):op for r in requests for op in r.history}
    frozen={id(op.engine):op.engine for op in ops.values() if hasattr(op,'engine')}
    return dict(source_keys=len(keys),unique_request_objects=len({id(r) for r in requests}),fields=fields,
        distinct_full_public_keys=len({k.values[:3] for k in keys}),
        evidence_history_references=sum(len(r.history) for r in requests),unique_evidence_operations=len(ops),
        evidence_operation_types=dict(Counter(type(op).__name__ for op in ops.values())),frozen_kernel_count=len(frozen),
        frozen_kernel_dict_bytes=sum(sys.getsizeof(vars(k)) for k in frozen.values()),
        frozen_empty_board_sources_bytes=sum(sys.getsizeof(k.board_sources) for k in frozen.values()),
        completed_operation_memos=sum(bool(getattr(op,'_completed',())) for op in ops.values()),
        containers={name:dict(entries=len(value),shallow_bytes=sys.getsizeof(value)) for name,value in vars(e).items() if isinstance(value,(dict,list))})


def run():
    start=time.monotonic();output=Path('benchmarks/player_match_groups/initial-publications-profile.json')
    def save(row):output.write_text(json.dumps(row,indent=2)+'\n')
    save(dict(status='running',scope='one_initial7_profile',hard_wall_seconds=10,search_budget_seconds=7))
    def watch():
        while True:
            if time.monotonic()-start>9.8 or peak_bytes()>1500000000:
                # Keep the last finished diagnostic stage; never restart.
                os._exit(124)
            time.sleep(.025)
    threading.Thread(target=watch,daemon=True).start()
    engine=None;prof=cProfile.Profile();prof.enable();reason=None
    try:
        with calculation_budget(None,max_seconds=7):
            graph,w=base();source=scope(graph,w);engine=InitialPublicationEngine(graph,witness=w);engine.capture_terminal=True
            with calculation_origin(graph.data):
                remember(engine,graph.root,source);engine.solve(*source,physical=source.physical)
    except CalculationBudgetExceeded:reason=budget_stop()
    except Pending as error:reason=error.reason
    finally:prof.disable()
    data=pstats.Stats(prof);rows=[]
    for (path,line,name),(cc,nc,tt,ct,callers) in data.stats.items():
        if 'ww_gg-recovery-git' in path:
            rows.append(dict(file=path.split('ww_gg-recovery-git')[-1],line=line,name=name,primitive_calls=cc,calls=nc,self_seconds=tt,cumulative_seconds=ct))
    row=dict(status='bounded_profile',stop=reason,stats=stats(engine),peak_working_set_bytes=peak_bytes(),
        top_self=sorted(rows,key=lambda x:x['self_seconds'],reverse=True)[:25],
        top_cumulative=sorted(rows,key=lambda x:x['cumulative_seconds'],reverse=True)[:25],search_and_profile_seconds=time.monotonic()-start)
    save(row)
    row['census']=census(engine);row['total_worker_seconds']=time.monotonic()-start;row['peak_working_set_bytes']=peak_bytes();save(row)
    print(json.dumps({k:row[k] for k in ('status','stop','search_and_profile_seconds','total_worker_seconds','peak_working_set_bytes')}),flush=True)

if __name__=='__main__':run()
