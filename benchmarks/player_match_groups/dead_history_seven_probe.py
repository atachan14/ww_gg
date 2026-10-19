"""One bounded changed-code MAX request with development-only attribution."""
import json,sys,time,hashlib
from pathlib import Path
from collections import Counter
from unittest.mock import patch
from .initial_seven_entry_probe import watch,LIMITS


def worker():
    from werewolf.board_flow import BoardData
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.information_set_forecast import InformationSetForecast,Pending
    from werewolf.morning_publications import CompiledPublications
    from werewolf.calculation_budget import calculation_budget,budget_usage,budget_stop,CalculationBudgetExceeded
    actions=Counter();action_rows=Counter();moments=Counter();result={'completed':False};c=None
    old=InformationSetForecast.uncached_act;old_moment=CompiledPublications.terminal_execution_value
    def counted(e,b,s,past,target,private,observer,**kwargs):
        key=f'{len(b.alive)}-{b.phase}';actions[key]+=1;action_rows[key]+=len(s.hypotheses)+len(private.hypotheses)
        return old(e,b,s,past,target,private,observer,**kwargs)
    def counted_moment(kernel,private,targets,**kwargs):
        moments['calls']+=1;moments['public_rows']+=len(kernel.state.hypotheses);moments['private_rows']+=len(private.hypotheses)
        return old_moment(kernel,private,targets,**kwargs)
    at=time.perf_counter()
    try:
        with calculation_budget(250000,max_seconds=30),patch.object(InformationSetForecast,'uncached_act',counted),patch.object(CompiledPublications,'terminal_execution_value',counted_moment):
            game=json.loads(Path('benchmarks/player_match_groups/actual-seven-max-results.json').read_text(encoding='utf-8'))['game']
            result['input_sha256']=hashlib.sha256(json.dumps(game,sort_keys=True).encode()).hexdigest()
            c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_reports=True)
            f=c.root.forecast();result.update(completed=True,value=str(f.village_win),actions=[(p,str(v)) for p,v in f.action_values],dawn=[(p,str(v)) for p,v in f.by_dawn_values],budget=budget_usage())
    except CalculationBudgetExceeded as error:result.update(status='budget_stopped',reason=error.kind,stop=budget_stop())
    except Pending as error:result.update(status='unsupported',reason=error.reason,stop=budget_stop())
    result.update(seconds=time.perf_counter()-at,uncached_actions_by_phase=dict(actions),action_input_hypotheses_by_phase=dict(action_rows),terminal_moments=dict(moments))
    if c:
        e=c._ClosedCalculation__engine;result['states']=c.stats()
        result['derived_projection_cache']={'entries':len(e.scalar_projections),'hypotheses_before':sum(len(key[0].hypotheses) for key in e.scalar_projections),'hypotheses_after':sum(len(st.hypotheses) for st in e.scalar_projections.values())}
    print(json.dumps(result))


def run():
    r=watch('benchmarks.player_match_groups.dead_history_seven_probe',('worker',))
    r['note']='One changed-code initial-seven MAX request. Lightweight development wrappers count uncached action input rows and moment calls; not a full CPU profile or an unchanged repeat.'
    r['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/grouped_forecast.py','werewolf/evaluation_projection.py','werewolf/information_weights.py','werewolf/morning_publications.py'))}
    Path('benchmarks/player_match_groups/dead-history-seven-results.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r))

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker()
    else:run()
