"""Development-only split profile of remaining cell/report enumeration."""
import json,time,cProfile,pstats,tracemalloc,sys,hashlib
from pathlib import Path
from unittest.mock import patch
from collections import defaultdict,Counter
from .representative_target_fixture import case,prepare
from .cut_out_publication_orbit_value_fixture import tables


def profile(n,aggregate_wolf=False):
    graph=case(n);c,node,_=prepare(graph,True,aggregate_wolf=aggregate_wolf);e=c._ClosedCalculation__engine;counts=defaultdict(lambda:dict(calls=0,rows=0,hypotheses=0,seconds=0.0,max_incremental_peak_bytes=0,retained_bytes_sum=0))
    def wrap(name,original,kind):
        def run(*args,**kwargs):
            before=tracemalloc.get_traced_memory()[0];tracemalloc.reset_peak();start=time.perf_counter();rows=original(*args,**kwargs)
            elapsed=time.perf_counter()-start;current,peak=tracemalloc.get_traced_memory();r=counts[name];r['calls']+=1;r['rows']+=len(rows);r['seconds']+=elapsed;r['max_incremental_peak_bytes']=max(r['max_incremental_peak_bytes'],peak-before);r['retained_bytes_sum']+=max(0,current-before)
            if kind=='wolf':r['hypotheses']+=sum(len(state.hypotheses) for info,mass,state in rows)
            elif kind=='generation':r['hypotheses']+=sum(len(branch.state.hypotheses) for branch in rows)
            else:r['hypotheses']+=sum(len(row[-1].hypotheses) for row in rows)
            return rows
        return run
    import werewolf.information_set_forecast as module
    import werewolf.model_a_public as horizons
    profiler=cProfile.Profile();tracemalloc.start()
    with patch.object(e,'wolf_cells',wrap('solver_wolf_information_cells',e.wolf_cells,'wolf')),patch.object(horizons,'wolf_information_groups',wrap('horizon_wolf_information_cells',horizons.wolf_information_groups,'wolf')),patch.object(module,'future_publications',wrap('public_report_vectors',module.future_publications,'generation')),patch.object(module,'observer_report_weights',wrap('actual_report_likelihood_transfer',module.observer_report_weights,'push')):
        profiler.enable();start=time.perf_counter();result=node.forecast();tables(node.read(),result);elapsed=time.perf_counter()-start;profiler.disable()
    traced_current,traced_peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    stats=pstats.Stats(profiler);top=sorted((dict(function=f'{key[0]}:{key[1]}:{key[2]}',primitive_calls=v[0],calls=v[1],exclusive_seconds=v[2],inclusive_seconds=v[3]) for key,v in stats.stats.items()),key=lambda r:r['exclusive_seconds'],reverse=True)[:12]
    caches={name:dict(vectors=sum(len(rows) for rows in getattr(e,name).values()),hypotheses=sum(len(row[2].hypotheses) for rows in getattr(e,name).values() for row in rows)) for name in ('mornings','publication_values')}
    value_phases=Counter((key[0].day,key[0].phase,len(key[0].alive)) for key in e.values)
    action_phases=Counter((key[1].day,key[1].phase,len(key[1].alive)) for key in e.action_values)
    phase=lambda histogram:[dict(day=day,phase=phase,alive=alive,states=count) for (day,phase,alive),count in sorted(histogram.items())]
    return dict(players=n,aggregate_wolf=aggregate_wolf,diagnostic_seconds=elapsed,parts=dict(counts),cached_report_vectors=caches,value_states_by_phase=phase(value_phases),action_states_by_phase=phase(action_phases),states=c.stats(),traced_current_bytes=traced_current,traced_peak_since_last_reset_bytes=traced_peak,top_exclusive=top,warning='cProfile/tracemalloc are diagnostic only; per-function peaks reset and are incremental, not independent-process peak memory')


def run():
    rows=[profile(n,mode) for n in (6,7) for mode in (False,True)]
    result=dict(status='profiled',cases=rows,full_initial7_search=False,memory_note='Per-call incremental traced peaks; retained allocation sums may include shared objects and are not whole-cache ownership attribution')
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/actor_information.py','werewolf/closed_calculation.py','werewolf/grouped_forecast.py','werewolf/information_set_forecast.py','benchmarks/player_match_groups/remaining_enumeration_profile.py'))}
    Path('benchmarks/player_match_groups/remaining-enumeration-profile.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([dict(players=r['players'],aggregate_wolf=r['aggregate_wolf'],parts=r['parts'],cached_report_vectors=r['cached_report_vectors']) for r in rows]))
    return result


if __name__=='__main__':run()
