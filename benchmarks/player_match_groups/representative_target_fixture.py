"""Representative targets before expansion; bounded ordinary/cold comparison."""
import json,sys,time,hashlib,statistics,subprocess
from pathlib import Path
from types import SimpleNamespace
from fractions import Fraction as F
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.seer_acquisition import SeerReport
from werewolf.actor_information import PersonalInformation
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.board_future import kernel_calculation
from .closed_morning_reports_fixture import case as morning_case,report_vector,check_groups
from .cut_out_joint_night_forecast_fixture import moved_source
from .cut_out_publication_orbit_value_fixture import forecast,tables
from .cut_out_compact_terminal_fixture import independent_cold
from .cut_out_uniform_game_fixture import peak_bytes


def case(n):
    graph,_=morning_case(6);data=graph.data
    if n==7:
        game=data.to_game();game.update(players=7,claims=['seer']*3+['latent']*4)
        data=BoardData.from_game(game)
    return SimpleNamespace(data=data,engine=graph.engine)


def prepare(graph,grouped,*,asymmetric=False,personal=False,aggregate_wolf=False):
    n=graph.data.game_data.players;c=ClosedCalculation(graph.data,grouped=grouped,aggregate_wolf=aggregate_wolf,max_seconds=30);node=c.root;trace=[]
    for target in (4,n):
        mass,node=node.observe(target);trace.append((mass,node.read(),node.groups))
    reports=report_vector(6,asymmetric) if n==6 else tuple(SeerReport(2,2,p,6,'white') for p in (1,2,3))
    mass,node=node.observe_reports(reports);trace.append((mass,node.read(),node.groups))
    if n==7:
        mass,node=node.observe(6);trace.append((mass,node.read(),node.groups))
    if personal:
        h=next(h for h in node.read().private.hypotheses if h.roles[2]&1)
        info=PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1))
        mass,node=node.personal(info);trace.append((mass,node.read(),node.groups))
    return c,node,trace


def worker(n,grouped):
    graph=case(n);start=time.perf_counter();c,node,trace=prepare(graph,grouped)
    result=node.forecast();table=tables(node.read(),result);elapsed=time.perf_counter()-start
    semantic=(trace,node.read(),result,table)
    return dict(players=n,grouped=grouped,seconds=elapsed,peak_bytes=peak_bytes(),states=c.stats(),digest=hashlib.sha256(repr(semantic).encode()).hexdigest())


def audit():
    rows=[]
    for n,asymmetric,personal in ((6,False,False),(7,False,False),(6,True,False),(6,False,True),(7,False,True)):
        graph=case(n);plain,node,trace=prepare(graph,False,asymmetric=asymmetric,personal=personal)
        fast,representative,other=prepare(graph,True,asymmetric=asymmetric,personal=personal)
        assert trace==other and representative.read()==node.read() and representative.groups==node.groups
        cold=independent_cold(graph,representative.export_request());assert cold==representative.read()
        e=InformationSetForecast(graph.data.game_data.rules,representative.export_request().origin.strategy,exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
        with kernel_calculation():cold_result=forecast(e,cold)
        want=node.forecast();got=representative.forecast()
        assert want==got==cold_result and tables(node.read(),want)==tables(cold,cold_result)==tables(representative.read(),got)
        check_groups(representative)
        a,b=plain.stats(),fast.stats()
        if not asymmetric and not personal:assert b['values']<a['values'] and b['expansions']['actions']<a['expansions']['actions']
        else:assert b['values']<=a['values'] and b['expansions']['actions']<=a['expansions']['actions']
        assert fast._ClosedCalculation__engine.groups==()
        # Enumerate skipped labelled transitions only in development. Compare
        # full transported Q/P, every history, physical outcome and branch mass.
        transitions=0
        alive=set(node.read().public.alive)
        for group in node.groups:
            targets=tuple(p for p in group if p in alive)
            if len(targets)<2:continue
            first=node.action(targets[0])
            for member in targets[1:]:
                mapping=list(range(1,n+1));mapping[targets[0]-1],mapping[member-1]=member,targets[0]
                expanded=node.action(member)
                assert len(expanded)==len(first)
                for left,right in zip(first,expanded):
                    assert left.probability==right.probability
                    assert moved_source(left.node.read(),tuple(mapping))==right.node.read()
                    assert independent_cold(graph,left.node.export_request())==left.node.read()
                    transitions+=1
        rows.append(dict(players=n,asymmetric=asymmetric,personal=personal,ordinary=a,representative=b,full_joint_trace_cold_Forecast_Table_equal=True,independent_labelled_transition_comparisons=transitions))
    result=dict(status='verified',cases=rows,scope='same validated uniform H0 complete simultaneous morning reports; finite <=4-alive scalar continuations',wolf_cells_and_report_vectors_still_enumerated=True,ledger_used=False,full_initial7_search=False)
    Path('benchmarks/player_match_groups/representative-target-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def measure():
    runs=[]
    for repeat in range(5):
        for n in (6,7):
            for mode in ((False,True) if repeat%2==0 else (True,False)):
                p=subprocess.run([sys.executable,'-m','benchmarks.player_match_groups.representative_target_fixture','worker',str(n),str(int(mode))],capture_output=True,text=True,timeout=45,check=True)
                row=json.loads(p.stdout);row['repeat']=repeat;runs.append(row)
    summary=[]
    for n in (6,7):
        assert len({r['digest'] for r in runs if r['players']==n})==1
        summary.append(dict(players=n,modes={str(mode):dict(seconds_median=statistics.median(r['seconds'] for r in runs if r['players']==n and r['grouped']==mode),seconds_range=[min(r['seconds'] for r in runs if r['players']==n and r['grouped']==mode),max(r['seconds'] for r in runs if r['players']==n and r['grouped']==mode)],peak_bytes_median=statistics.median(r['peak_bytes'] for r in runs if r['players']==n and r['grouped']==mode),states=next(r['states'] for r in runs if r['players']==n and r['grouped']==mode)) for mode in (False,True)}))
    result=dict(status='verified',repeats=5,summary=summary,runs=runs,boundary='snapshot opening plus finite saved-target/hand-report conditioning and public Forecast/Table; common fixture/import preparation excluded',full_initial7_search=False)
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/closed_calculation.py','werewolf/group_partition.py','werewolf/grouped_forecast.py','werewolf/information_set_forecast.py','benchmarks/player_match_groups/representative_target_fixture.py'))}
    Path('benchmarks/player_match_groups/representative-target-performance-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:print(json.dumps(worker(int(sys.argv[2]),bool(int(sys.argv[3])))))
    elif '--measure' in sys.argv:print(json.dumps(measure()['summary']))
    else:print(json.dumps(audit()))
