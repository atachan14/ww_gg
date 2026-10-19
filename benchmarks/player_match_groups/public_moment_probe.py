"""Bounded Q-moment cache comparisons; one explicit seven run after locals."""
import json,sys,time,hashlib
from pathlib import Path
from collections import Counter
from unittest.mock import patch
from .initial_seven_entry_probe import watch,LIMITS


def worker(kind,mode):
    from .closed_full_tree_fixture import case
    from .dead_history_design import actual_dead_seer_prefix
    from .cut_out_publication_orbit_value_fixture import tables
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.board_flow import BoardData
    from werewolf.board_future import kernel_calculation
    from werewolf.exact import Strategy
    from dataclasses import asdict
    from werewolf.morning_publications import CompiledPublications
    from werewolf.information_set_forecast import InformationSetForecast,Pending
    from werewolf.calculation_budget import calculation_budget,budget_usage,budget_stop,CalculationBudgetExceeded
    counts=Counter();phase=Counter();input_rows=Counter();c=None;e=None;result=dict(kind=kind,mode=mode,completed=False)
    old_value=CompiledPublications.terminal_execution_value;old_build=CompiledPublications.terminal_execution_moments;old_act=InformationSetForecast.uncached_act
    def value(kernel,private,targets,**kwargs):
        counts['calls']+=1;counts['private_rows']+=len(private.hypotheses)
        return old_value(kernel,private,targets,**kwargs)
    def build(kernel,targets,**kwargs):
        counts['builds']+=1;counts['public_build_rows']+=len(kernel.state.hypotheses)
        out=old_build(kernel,targets,**kwargs);counts['completed_builds']+=1;counts['built_fibers']+=len(out)
        return out
    def act(engine,b,s,past,target,private,observer,**kwargs):
        key=f'{len(b.alive)}-{b.phase}';phase[key]+=1;input_rows[key]+=len(s.hypotheses)+len(private.hypotheses)
        return old_act(engine,b,s,past,target,private,observer,**kwargs)
    started=time.perf_counter()
    try:
        with calculation_budget(250000,max_seconds=30),kernel_calculation(),patch.object(CompiledPublications,'terminal_execution_value',value),patch.object(CompiledPublications,'terminal_execution_moments',build),patch.object(InformationSetForecast,'uncached_act',act):
            if kind=='actual-prefix':c,n=actual_dead_seer_prefix()
            elif kind=='seven':
                game=json.loads(Path('benchmarks/player_match_groups/actual-seven-max-results.json').read_text(encoding='utf-8'))['game']
                assert Strategy(**game['policy'])==Strategy()
                result['input_sha256']=hashlib.sha256(json.dumps(game,sort_keys=True).encode()).hexdigest()
                c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_reports=True);n=c.root
            else:
                c=ClosedCalculation(case(5,kind).data.updated(policy=asdict(Strategy())),grouped=True,aggregate_reports=True);n=c.root
            e=c._ClosedCalculation__engine
            if mode=='off':e.terminal_moments=None
            if kind=='actual-prefix':result['value']=str(e.action_policy.morning_value(n.read()))
            else:
                f=n.forecast();result.update(value=str(f.village_win),actions=[(p,str(v)) for p,v in f.action_values],dawn=[(p,str(v)) for p,v in f.by_dawn_values])
                result['table_sha256']=hashlib.sha256(json.dumps(tables(n.read(),f),sort_keys=True,default=str).encode()).hexdigest()
                if kind=='seven':assert f.village_win==__import__('fractions').Fraction(3487,7200)
            result.update(completed=True,budget=budget_usage())
    except CalculationBudgetExceeded as error:result.update(status='budget_stopped',reason=error.kind,stop=budget_stop())
    except Pending as error:result.update(status='unsupported',reason=error.reason,stop=budget_stop())
    result.update(seconds=time.perf_counter()-started,moments=dict(counts),uncached_actions_by_phase=dict(phase),action_input_hypotheses_by_phase=dict(input_rows))
    if c:result['states']=c.stats()
    if e:
        cache=e.terminal_moments
        result['cache']={'entries':len(cache.entries) if cache else 0,'rows':cache.rows if cache else 0,'max_entries':128,'max_rows':4096}
    print(json.dumps(result))


def run(which):
    jobs=[('seven','on')] if which=='seven' else [(kind,mode) for kind in ('single','dual','three','medium-pair','actual-prefix') for mode in ('off','on')]
    rows=[watch('benchmarks.player_match_groups.public_moment_probe',('worker',*job)) for job in jobs]
    r={'scope':which,'measurements':rows,'note':'Same work/time/memory/watchdog limits. Development wrappers count Q vector builds and P applications; no production instrumentation.'}
    r['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/grouped_forecast.py','werewolf/morning_publications.py','werewolf/information_weights.py'))}
    Path(f'benchmarks/player_match_groups/public-moment-{which}-results.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r))

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(*sys.argv[2:])
    else:run(sys.argv[1] if len(sys.argv)>1 else 'local')
