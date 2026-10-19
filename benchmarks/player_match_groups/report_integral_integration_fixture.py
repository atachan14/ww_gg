"""Bounded expanded-report reference and integrated opt-in measurements."""
import json,sys,time,hashlib
from pathlib import Path
from unittest.mock import patch
from contextlib import nullcontext
from .initial_seven_entry_probe import watch,LIMITS


def worker(mode,query,view,target):
    from .cut_out_user_seven_uniform_preparation import comparison_game,prepare
    from .report_integral_design import make
    from .cut_out_publication_orbit_value_fixture import tables
    from werewolf.closed_calculation import ClosedCalculation,_forecast_scope
    from werewolf.board_flow import BoardData
    from werewolf.actor_information import PersonalInformation,WolfInformation
    from werewolf.information_set_forecast import Pending
    from werewolf.calculation_budget import calculation_budget,budget_usage,budget_stop,CalculationBudgetExceeded
    from werewolf.model_a_public import horizon_for_action
    start=time.perf_counter();out=dict(mode=mode,query=query,view=view,target=target,completed=False);c=None
    try:
        with calculation_budget(LIMITS['max_work'],max_seconds=LIMITS['max_seconds']):
            if query=='local':c,n=make(5,'three',4,5)
            else:
                game=comparison_game()[1];prepared=prepare(game)
                c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=LIMITS['max_work'],max_seconds=LIMITS['max_seconds'])
                assert c.root.read()==prepared.source and c.root.groups==prepared.groups
                n=c.root.observe(4)[1] if query=='six' else c.root
            if view!='public':
                h=next(h for h in n.read().private.hypotheses if h.roles[2]&1)
                info=PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)) if view=='seer' else WolfInformation.from_hypothesis(h)
                mass,n=n.personal(info);out['conditioning_mass']=str(mass)
            e=c._ClosedCalculation__engine;s=n.read();out['source_sha256']=hashlib.sha256(repr(s).encode()).hexdigest()
            scope=patch.object(e,'terminal_report_value',return_value=None) if mode=='expanded' else nullcontext()
            with scope:
                if query=='local':
                    with c._ClosedCalculation__kernel(),e.group_scope(()):value=e.action_policy.morning_value(s)
                    out['value']=str(value)
                elif query=='branch':
                    with c._ClosedCalculation__kernel(),e.group_scope(n.groups):
                        _forecast_scope(s,e)
                        value=e.act(*s[:3],target,s.private,s.observer,physical=s.physical)
                        dawn=horizon_for_action(e,s.public,s.public_state,s.past,target,s.private,observer=s.observer)
                    out.update(value=str(value),dawn=repr(dawn))
                else:
                    f=n.forecast()
                    out.update(value=str(f.village_win),forecast=repr(f),actions=[(p,str(v)) for p,v in f.action_values],dawn=[(p,str(v.village_win),str(v.wolf_win)) for p,v in f.by_dawn_values],table_sha256=hashlib.sha256(repr(tables(s,f)).encode()).hexdigest())
            out.update(status='completed',completed=True,budget=budget_usage())
    except CalculationBudgetExceeded as error:out.update(status='budget_stopped',reason=error.kind)
    except Pending as error:out.update(status='pending',reason=error.reason)
    out.update(seconds=time.perf_counter()-start,budget_stop=budget_stop())
    if c is not None:out['states']=c.stats()
    print(json.dumps(out),flush=True)


def run(mode,query,view='public',target=4):
    r=watch('benchmarks.player_match_groups.report_integral_integration_fixture',('worker',mode,query,view,str(target)))
    r['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/grouped_forecast.py','werewolf/information_set_forecast.py','werewolf/morning_publications.py','werewolf/information_weights.py',__file__))}
    name=f'report-integral-{mode}-{query}-{view}'+('-'+str(target) if query=='branch' else '')+'.json'
    Path('benchmarks/player_match_groups',name).write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');return r

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(sys.argv[2],sys.argv[3],sys.argv[4],int(sys.argv[5]))
    else:print(json.dumps(run(*sys.argv[1:4],target=int(sys.argv[4]) if len(sys.argv)>4 else 4)))
