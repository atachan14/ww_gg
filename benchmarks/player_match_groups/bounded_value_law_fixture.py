"""Bounded exact cache comparison; completed entries are streamed, not copied."""
import hashlib,json,sys,time
from pathlib import Path
from contextlib import nullcontext
from unittest.mock import patch
from .initial_seven_entry_probe import watch,LIMITS


COMPARE_WORK=100000
COMPARE_SECONDS=20


def worker(mode):
    from .cut_out_user_seven_uniform_preparation import comparison_game
    from .cut_out_uniform_game_fixture import peak_bytes
    from werewolf.board_flow import BoardData
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.information_set_forecast import InformationSetForecast,Pending
    from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,budget_stop
    begin=time.perf_counter();r=dict(mode=mode,forecast_completed=False,value=None,comparison_work_limit=COMPARE_WORK,comparison_seconds=COMPARE_SECONDS);c=None
    try:
        with calculation_budget(COMPARE_WORK,max_seconds=COMPARE_SECONDS):
            c=ClosedCalculation(BoardData.from_game(comparison_game()[1]),grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=COMPARE_WORK,max_seconds=COMPARE_SECONDS)
            node=c.root.observe(4)[1];e=c._ClosedCalculation__engine
            context=patch.object(e,'value_law',InformationSetForecast.value_law.__get__(e,type(e))) if mode=='uncached' else nullcontext()
            with context:
                print(json.dumps(dict(progress_stage='bounded_full_forecast_'+mode)),flush=True)
                out=node.forecast();r.update(forecast_completed=True,value=str(out.village_win))
    except CalculationBudgetExceeded as error:r.update(status='budget_stopped',reason=error.kind)
    except Pending as error:r.update(status='pending',reason=error.reason)
    r['calculation_seconds']=time.perf_counter()-begin;r['budget_stop']=budget_stop()
    if c is not None:
        r['states']=c.stats();r['derived_cache_inputs']=len(e.value_laws)
        print(json.dumps(dict(progress_stage='stream_completed_entry_digest',completed_numeric_prefix=r)),flush=True)
        before=time.perf_counter();digests={}
        for name in ('values','action_values'):
            digest=hashlib.sha256()
            for key,value in getattr(e,name).items():digest.update(repr((key,value)).encode());digest.update(b'\n')
            digests[name]=digest.hexdigest()
        r['completed_entry_digests']=digests;r['digest_seconds']=time.perf_counter()-before
    r['peak_working_set_bytes']=peak_bytes();print(json.dumps(r),flush=True)


def run(mode):
    result=watch('benchmarks.player_match_groups.bounded_value_law_fixture',('worker',mode))
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/grouped_forecast.py','werewolf/information_set_forecast.py','werewolf/closed_calculation.py','benchmarks/player_match_groups/bounded_value_law_fixture.py'))}
    Path(f'benchmarks/player_match_groups/value-law-cache-{mode}-prefix.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(sys.argv[2])
    else:print(json.dumps(run(sys.argv[1])))
