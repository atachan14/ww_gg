"""Development-only complete-vector oracle and reproducible process measurements."""
import hashlib,json,statistics,subprocess,sys,time
from pathlib import Path
from itertools import permutations,product
from fractions import Fraction as F
from .representative_target_fixture import case,prepare
from .cut_out_compact_terminal_fixture import independent_cold
from .cut_out_publication_orbit_value_fixture import forecast,tables
from .cut_out_uniform_game_fixture import peak_bytes
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.board_future import kernel_calculation
from werewolf.morning_publications import compile_publications,future_publications


def kernel_audit(node):
    s=node.read();b=s.public
    old=future_publications(s.public_state,s.past,b.alive,b.claims)
    kernel=compile_publications(s.public_state,s.past,b.alive,b.claims,board=b)
    reporters=kernel.reporters
    partition=tuple(tuple(p for p in g if p in reporters) for g in node.groups if any(p in reporters for p in g))
    compact=kernel.representatives(partition);named={r.reports:r for r in old};covered=set()
    for branch in compact:
        original=named[branch.reports]
        assert original.state==branch.state and branch.probability==original.probability*branch.multiplicity
        targets={r.target for r in branch.reports};blocks=[]
        for g in partition:
            blocks.extend((p,) for p in g if p in targets)
            rest=tuple(p for p in g if p not in targets)
            if rest:blocks.append(rest)
        images=set()
        for image in product(*(tuple(permutations(g)) for g in blocks)):
            mapping=list(range(1,b.player_count+1))
            for group,ordered in zip(blocks,image):
                for a,z in zip(group,ordered):mapping[a-1]=z
            from dataclasses import replace
            reports=tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in branch.reports))
            other=named[reports];assert other.probability==original.probability
            # Full joint roles/scans/guards/attacks, not report marginals.
            from .cut_out_joint_night_forecast_fixture import move_law
            assert move_law(original.state,tuple(mapping))==other.state
            images.add(reports)
        assert len(images)==branch.multiplicity and not covered.intersection(images)
        covered.update(images)
    assert covered==set(named) and sum((r.probability for r in compact),F())==1
    return dict(expanded=len(old),representatives=len(compact),named_coverage=len(covered))


def audit():
    rows=[]
    for n,asymmetric,personal in ((6,False,False),(7,False,False),(6,True,False),(6,False,True),(7,False,True)):
        graph=case(n);outputs=[];counts=[]
        for mode in ('expanded','cells','reports'):
            c,node,trace=prepare(graph,mode!='expanded',aggregate_wolf=mode!='expanded',aggregate_reports=mode=='reports',asymmetric=asymmetric,personal=personal)
            result=node.forecast();outputs.append((trace,node.read(),result,tables(node.read(),result)));counts.append(c.stats())
        assert outputs[0]==outputs[1]==outputs[2]
        cold=independent_cold(graph,node.export_request());assert cold==node.read()
        e=InformationSetForecast(graph.data.game_data.rules,node.export_request().origin.strategy,exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
        with kernel_calculation():expected=forecast(e,cold)
        assert expected==result and tables(cold,expected)==outputs[-1][-1]
        rows.append(dict(players=n,asymmetric=asymmetric,personal=personal,counts=counts,expanded_cold_Forecast_Table_equal=True))
    result=dict(status='verified',cases=rows,scope='existing uniform H0 finite continuations; no target-name quotient',full_initial7_search=False)
    Path('benchmarks/player_match_groups/report-vector-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def worker(n,mode):
    graph=case(n);start=time.perf_counter()
    c,node,trace=prepare(graph,mode!='expanded',aggregate_wolf=mode!='expanded',aggregate_reports=mode=='reports')
    result=node.forecast();table=tables(node.read(),result);elapsed=time.perf_counter()-start
    return dict(players=n,mode=mode,seconds=elapsed,peak_bytes=peak_bytes(),states=c.stats(),digest=hashlib.sha256(repr((trace,node.read(),result,table)).encode()).hexdigest())


def measure():
    runs=[];modes=('expanded','cells','reports')
    for repeat in range(5):
        for n in (6,7):
            for mode in modes[repeat%3:]+modes[:repeat%3]:
                p=subprocess.run([sys.executable,'-X','utf8','-m','benchmarks.player_match_groups.report_vector_fixture','worker',str(n),mode],capture_output=True,text=True,check=True,timeout=45)
                row=json.loads(p.stdout);row['repeat']=repeat;runs.append(row)
    summary=[]
    for n in (6,7):
        assert len({r['digest'] for r in runs if r['players']==n})==1
        summary.append(dict(players=n,modes={m:dict(seconds_median=statistics.median(r['seconds'] for r in runs if r['players']==n and r['mode']==m),peak_bytes_median=statistics.median(r['peak_bytes'] for r in runs if r['players']==n and r['mode']==m),states=next(r['states'] for r in runs if r['players']==n and r['mode']==m)) for m in modes}))
    result=dict(status='verified',repeats=5,summary=summary,runs=runs,boundary='opening/prefix/Forecast/Table; fixture/import setup excluded; fresh process peak',full_initial7_search=False)
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/morning_publications.py','werewolf/grouped_forecast.py','werewolf/closed_calculation.py',__file__))}
    Path('benchmarks/player_match_groups/report-vector-performance-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:print(json.dumps(worker(int(sys.argv[2]),sys.argv[3])))
    elif '--measure' in sys.argv:print(json.dumps(measure()['summary']))
    else:print(json.dumps(audit()))
