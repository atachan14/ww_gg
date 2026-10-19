"""One bounded production MAX-orbit request after entry-contract validation."""
import json,sys,time,hashlib
from pathlib import Path
from .initial_seven_entry_probe import watch,LIMITS


def worker():
    from fractions import Fraction as F
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.board_flow import BoardData
    from werewolf.calculation_budget import calculation_budget,budget_usage,budget_stop,CalculationBudgetExceeded
    from werewolf.information_set_forecast import Pending
    from .cut_out_publication_orbit_value_fixture import tables
    started=time.perf_counter();out={'completed':False};c=None
    try:
        with calculation_budget(250000,max_seconds=30):
            game=json.loads(Path('benchmarks/player_match_groups/actual-seven-max-results.json').read_text(encoding='utf-8'))['game']
            out['input_sha256']=hashlib.sha256(json.dumps(game,sort_keys=True).encode()).hexdigest()
            c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)
            assert c._ClosedCalculation__engine.max_grouped
            f=c.root.forecast()
            expected={1:F(19,48),2:F(19,48),3:F(4,15),4:F(4,15),5:F(3487,7200),6:F(3487,7200),7:F(3487,7200)}
            assert f.village_win==F(3487,7200) and dict(f.action_values)==expected
            assert all(v.village_win==v.wolf_win==0 for p,v in f.by_dawn_values)
            rendered=tables(c.root.read(),f)
            out.update(completed=True,value=str(f.village_win),actions=[(p,str(v)) for p,v in f.action_values],dawn=[(p,str(v)) for p,v in f.by_dawn_values],tables=rendered,root_source_sha256=hashlib.sha256(repr(c.root.read()).encode()).hexdigest(),budget=budget_usage(),historical_named_values_equal=True)
    except CalculationBudgetExceeded as error:out.update(status='budget_stopped',reason=error.kind,stop=budget_stop())
    except Pending as error:
        stop=budget_stop()
        out.update(status='budget_stopped' if stop else 'unsupported',reason=stop['kind'] if stop else error.reason,pending_reason=error.reason,stop=stop)
    out['seconds']=time.perf_counter()-started
    if c:out['states']=c.stats()
    print(json.dumps(out,default=str))


def run():
    r=watch('benchmarks.player_match_groups.group_entry_probe',('worker',))
    r['scope']='One changed production public initial-seven request; explicit full aggregation opt-in. Historical vector comparison is not a fresh full named-reference proof.'
    r['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/group_partition.py','werewolf/grouped_forecast.py','werewolf/actor_information.py','werewolf/closed_calculation.py'))}
    Path('benchmarks/player_match_groups/group-entry-seven-results.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r))

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker()
    else:run()
