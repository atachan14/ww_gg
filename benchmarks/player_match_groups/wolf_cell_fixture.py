"""Wolf-cell occupancy aggregation; all transport proofs are development-only."""
import json,sys,time,statistics,subprocess,hashlib
from pathlib import Path
from collections import defaultdict
from fractions import Fraction as F
from itertools import permutations,product
from unittest.mock import patch
from .representative_target_fixture import case,prepare
from .cut_out_compact_terminal_fixture import independent_cold
from .cut_out_joint_night_forecast_fixture import move_law,moved_source
from .cut_out_publication_orbit_value_fixture import forecast,tables
from .cut_out_uniform_game_fixture import peak_bytes
from werewolf.actor_information import wolf_information_groups,wolf_information_orbits
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.board_future import kernel_calculation


def occupancy(info,partition):
    return tuple(sum(bool(info.initial_roster&(1<<(p-1))) for p in g) for g in partition),info.attacks


def cell_audit(source,partition,engine):
    ordinary=wolf_information_groups(source.private);representatives=wolf_information_orbits(source.private,partition)
    classes=defaultdict(list)
    for info,mass,law in ordinary:classes[occupancy(info,partition)].append((info,mass,law))
    assert sum((mass for info,mass,law in representatives),F())==1
    comparisons=0
    for info,mass,law in representatives:
        members=classes[occupancy(info,partition)];chosen=next(row for row in members if row[0]==info)
        assert law==chosen[2] and mass==sum((row[1] for row in members),F())
        assert mass==len(members)*chosen[1]
        for other,weight,expanded in members:
            mapping=list(range(1,source.public.player_count+1))
            for group in partition:
                for bit in (False,True):
                    left=[p for p in group if bool(info.initial_roster&(1<<(p-1)))==bit]
                    right=[p for p in group if bool(other.initial_roster&(1<<(p-1)))==bit]
                    for a,b in zip(left,right):mapping[a-1]=b
            assert move_law(law,tuple(mapping))==expanded
            public=info.condition_public(source.public_state);other_public=other.condition_public(source.public_state)
            assert move_law(public,tuple(mapping))==other_public
            if source.public.phase=='night':
                expected={mapping[p-1]:q for p,q in engine.wolf_policy(source.public,source.public_state,source.past,info.initial_roster,info.attacks)}
                actual=dict(engine.wolf_policy(source.public,source.public_state,source.past,other.initial_roster,other.attacks))
                assert expected==actual
            comparisons+=1
    return dict(expanded_cells=len(ordinary),representative_cells=len(representatives),transported_joint_and_public_policy_comparisons=comparisons,
                representative_hypotheses=[len(s.hypotheses) for i,m,s in representatives],mass_sum='1')


def report_census(n,aggregate_wolf):
    graph=case(n);c,node,_=prepare(graph,True,aggregate_wolf=aggregate_wolf);e=c._ClosedCalculation__engine;original=e.report_children;rows=[]
    def run(payload):
        children=original(payload);parent=e.groups
        maps=[]
        for orders in product(*(permutations(g) for g in parent)):
            mapping=list(range(1,n+1))
            for group,order in zip(parent,orders):
                for a,b in zip(group,order):mapping[a-1]=b
            maps.append(tuple(mapping))
        if not maps:maps=[tuple(range(1,n+1))]
        grouped={}
        for q,p,child in children:
            def key(mapping):
                return (tuple(sorted((r.day,mapping[r.reporter-1],mapping[r.target-1],r.color) for r in child.public.reports)),tuple(sorted((r.acquired_day,r.published_day,mapping[r.player-1],mapping[r.target-1],r.color) for r in child.past)),tuple(sorted((day,mapping[a-1],mapping[t-1]) for day,a,t in child.public.report_resolved)))
            mapping=min(maps,key=key);canonical=key(mapping);transported=moved_source(child,mapping)
            if canonical in grouped:
                oldq,oldp,old=grouped[canonical];assert oldq==q and oldp==p and old==transported
            else:grouped[canonical]=(q,p,transported)
        rows.append(dict(parent_groups=parent,actual_vectors=len(children),possible_vector_orbits=len(grouped)))
        return children
    with patch.object(e,'report_children',run):node.forecast()
    return dict(players=n,aggregate_wolf=aggregate_wolf,calls=rows,actual_vectors=sum(r['actual_vectors'] for r in rows),possible_vector_orbits=sum(r['possible_vector_orbits'] for r in rows),development_only=True)


def audit():
    rows=[]
    for n,asymmetric,personal in ((6,False,False),(7,False,False),(6,True,False),(6,False,True),(7,False,True)):
        graph=case(n);results=[];stats=[];traces=[]
        for grouped,aggregate in ((False,False),(True,False),(True,True)):
            c,node,trace=prepare(graph,grouped,aggregate_wolf=aggregate,asymmetric=asymmetric,personal=personal)
            result=node.forecast();results.append((result,tables(node.read(),result)));stats.append(c.stats());traces.append(trace)
        assert results[0]==results[1]==results[2] and traces[0]==traces[1]==traces[2]
        cold=independent_cold(graph,node.export_request());assert cold==node.read()
        e=InformationSetForecast(graph.data.game_data.rules,node.export_request().origin.strategy,exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
        with kernel_calculation():expected=forecast(e,cold)
        assert expected==results[2][0] and tables(cold,expected)==results[2][1]
        assert stats[2]['values']<=stats[1]['values'] and stats[2]['expansions']['actions']<=stats[1]['expansions']['actions']
        if n==7 and not asymmetric and not personal:assert stats[2]['values']<stats[1]['values']
        cells=cell_audit(node.read(),node.groups,e)
        rows.append(dict(players=n,asymmetric=asymmetric,personal=personal,expanded=stats[0],target_only=stats[1],target_and_cells=stats[2],root_cells=cells,full_joint_trace_expanded_cold_public_owner_Forecast_Table_equal=True))
    census=[report_census(7,mode) for mode in (False,True)]
    result=dict(status='verified',cases=rows,report_orbit_census=census,report_vector_generation_unchanged=True,ledger_used=False,full_initial7_search=False)
    Path('benchmarks/player_match_groups/wolf-cell-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def worker(n,mode):
    graph=case(n);start=time.perf_counter();c,node,trace=prepare(graph,mode!='expanded',aggregate_wolf=mode=='cells')
    result=node.forecast();table=tables(node.read(),result);elapsed=time.perf_counter()-start
    semantic=(trace,node.read(),result,table)
    return dict(players=n,mode=mode,seconds=elapsed,peak_bytes=peak_bytes(),states=c.stats(),digest=hashlib.sha256(repr(semantic).encode()).hexdigest())


def measure():
    runs=[];modes=('expanded','targets','cells')
    for repeat in range(5):
        for n in (6,7):
            for mode in modes[repeat%3:]+modes[:repeat%3]:
                p=subprocess.run([sys.executable,'-m','benchmarks.player_match_groups.wolf_cell_fixture','worker',str(n),mode],capture_output=True,text=True,check=True,timeout=45)
                row=json.loads(p.stdout);row['repeat']=repeat;runs.append(row)
    summary=[]
    for n in (6,7):
        assert len({r['digest'] for r in runs if r['players']==n})==1
        summary.append(dict(players=n,modes={m:dict(seconds_median=statistics.median(r['seconds'] for r in runs if r['players']==n and r['mode']==m),seconds_range=[min(r['seconds'] for r in runs if r['players']==n and r['mode']==m),max(r['seconds'] for r in runs if r['players']==n and r['mode']==m)],peak_bytes_median=statistics.median(r['peak_bytes'] for r in runs if r['players']==n and r['mode']==m),states=next(r['states'] for r in runs if r['players']==n and r['mode']==m)) for m in modes}))
    result=dict(status='verified',repeats=5,summary=summary,runs=runs,boundary='same immutable opening/finite target/hand-report conditioning/public Forecast/Table; fixture/import setup excluded',full_initial7_search=False)
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/actor_information.py','werewolf/closed_calculation.py','werewolf/grouped_forecast.py','werewolf/information_set_forecast.py','benchmarks/player_match_groups/wolf_cell_fixture.py','benchmarks/player_match_groups/representative_target_fixture.py'))}
    Path('benchmarks/player_match_groups/wolf-cell-performance-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:print(json.dumps(worker(int(sys.argv[2]),sys.argv[3])))
    elif '--measure' in sys.argv:print(json.dumps(measure()['summary']))
    else:print(json.dumps(audit()))
