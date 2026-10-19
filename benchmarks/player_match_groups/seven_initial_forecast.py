"""Actual supported seven-initial Forecast under unchanged resource limits."""
import json,sys,time,hashlib
from pathlib import Path
from unittest.mock import patch
from .initial_seven_entry_probe import watch,LIMITS


def worker(view):
    from .cut_out_user_seven_uniform_preparation import comparison_game,prepare
    from .cut_out_publication_orbit_value_fixture import tables
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.actor_information import PersonalInformation,WolfInformation
    from werewolf.information_set_forecast import Pending
    from werewolf.calculation_budget import calculation_budget,budget_usage,budget_stop,CalculationBudgetExceeded
    start=time.perf_counter();out=dict(view=view,forecast_completed=False,value=None);stages=[];depth=0;c=None
    try:
        with calculation_budget(LIMITS['max_work'],max_seconds=LIMITS['max_seconds']):
            original,game=comparison_game();prepared=prepare(game)
            assert (game['players'],game['wolves'],game['mediums'],game['seers'],game['hunters'])==(7,2,1,1,0)
            c=ClosedCalculation(prepared.data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
            node=c.root;assert node.read()==prepared.source and node.groups==prepared.groups
            out.update(initial_preparation_equal=True,game=game,initial_hypotheses=len(node.read().public_state.hypotheses),initial_groups=node.groups)
            if view!='public':
                h=next(h for h in node.read().private.hypotheses if h.roles[2]&1)
                info=PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)) if view=='seer' else WolfInformation.from_hypothesis(h)
                mass,node=node.personal(info);out['conditioning_mass']=str(mass)
            e=c._ClosedCalculation__engine
            def wrap(kind,fn):
                def call(*args,**kwargs):
                    nonlocal depth
                    stage=None
                    if depth==0:
                        stage=dict(kind=kind,completed=False)
                        if kind=='act':stage['target']=args[3]
                        stages.append(stage)
                    depth+=1
                    try:
                        value=fn(*args,**kwargs)
                        if stage is not None:stage.update(completed=True,value=str(value))
                        return value
                    finally:depth-=1
                return call
            with patch.object(e,'solve',wrap('solve',e.solve)),patch.object(e,'act',wrap('act',e.act)):
                f=node.forecast()
            out.update(status='completed',forecast_completed=True,value=str(f.village_win),forecast=repr(f),table_sha256=hashlib.sha256(repr(tables(node.read(),f)).encode()).hexdigest(),budget=budget_usage())
    except CalculationBudgetExceeded as error:out.update(status='budget_stopped',reason=error.kind)
    except Pending as error:out.update(status='pending',reason=error.reason)
    out.update(seconds=time.perf_counter()-start,budget_stop=budget_stop(),stages=stages)
    if c is not None:out['states']=c.stats()
    print(json.dumps(out),flush=True)


def run(view):
    r=watch('benchmarks.player_match_groups.seven_initial_forecast',('worker',view))
    r['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/closed_calculation.py','werewolf/grouped_forecast.py',__file__))}
    Path('benchmarks/player_match_groups/seven-initial-forecast-'+view+'.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');return r

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(sys.argv[2])
    else:print(json.dumps(run(sys.argv[1] if len(sys.argv)>1 else 'public')))
