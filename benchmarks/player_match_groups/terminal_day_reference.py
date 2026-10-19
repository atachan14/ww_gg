"""Independent terminal enumeration and cold reconstruction, development only."""
import json,sys,time,hashlib
from pathlib import Path
from fractions import Fraction as F
from types import SimpleNamespace
from unittest.mock import patch
from .initial_seven_entry_probe import watch,LIMITS


def worker(mode,view,part='all'):
    from .cut_out_user_seven_uniform_preparation import comparison_game
    from .closed_full_tree_fixture import case
    from .cut_out_compact_terminal_fixture import independent_cold
    from .cut_out_publication_orbit_value_fixture import forecast,tables
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.board_flow import BoardData
    from werewolf.board_future import kernel_calculation
    from werewolf.actor_information import PersonalInformation,WolfInformation
    from werewolf.information_set_forecast import InformationSetForecast,Pending
    from werewolf.exact import Strategy,action_outcomes,legal_targets
    from werewolf.calculation_budget import calculation_budget,budget_usage,budget_stop,tick,CalculationBudgetExceeded
    started=time.perf_counter();out=dict(mode=mode,view=view,part=part,status='running');counts=dict(terminal_sources=0,physical_edges=0)
    try:
        with calculation_budget(LIMITS['max_work'],max_seconds=LIMITS['max_seconds']):
            data=BoardData.from_game(comparison_game()[1]);c=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
            node=c.root.observe(4)[1];h=next(h for h in node.read().private.hypotheses if (h.roles[0]==int(view.split('-')[1]) if view.startswith('wolf-') else h.roles[2]&1))
            if view!='public':
                mass,node=node.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)) if view.startswith('seer') else WolfInformation.from_hypothesis(h))
                out['conditioning_mass']=str(mass)
            source=node.read()
            if view.startswith('seer-roster-'):
                mask=int(view.split('-')[-1]);member=next(h for h in source.private.hypotheses if h.roles[0]==mask)
                mass,source=c._ClosedCalculation__engine.personal_view(source,WolfInformation.from_hypothesis(member))
                out['actual_P_partition_mass']=str(mass)
            out['private_rows']=[(repr((h.roles,h.acquisitions,h.guards,h.attacks)),str(h.mass)) for h in source.private.hypotheses]
            out['observer']=repr(source.observer)
            if mode=='reference':
                graph=SimpleNamespace(data=data,engine=case(5,'single').engine)
                cold=independent_cold(graph,node.export_request());assert node.read()==cold
                if view.startswith('seer-roster-'):
                    fresh=InformationSetForecast(data.game_data.rules,Strategy(**data.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False)
                    mass,cold=fresh.personal_view(cold,WolfInformation.from_hypothesis(member))
                assert source==cold
                e=InformationSetForecast(data.game_data.rules,Strategy(**data.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
                solve=e.solve
                def enumerated(b,s,past,private,observer,*,physical=None):
                    if b.phase=='day' and len(b.alive)==3 and set(b.wolf_count_distribution)=={1}:
                        # Explicit named actual physical outcomes; no count recurrence,
                        # no symmetry classes, no history-based cache key.
                        assert physical is not None;counts['terminal_sources']+=1;value=F()
                        targets=legal_targets(physical,e.rules,e.strategy)
                        for target in targets:
                            tick(len(physical.worlds));rows=action_outcomes(physical,target,e.rules,e.strategy)
                            assert all(r.board.winner is not None for r in rows)
                            counts['physical_edges']+=len(rows)
                            value+=sum((r.probability*F(r.board.winner=='village') for r in rows),F())/len(targets)
                        return value
                    return solve(b,s,past,private,observer,physical=physical)
                with patch.object(e,'solve',enumerated),kernel_calculation():
                    if part=='all':f=forecast(e,cold)
                    else:
                        from werewolf.model_a_public import horizon_for_action
                        if part=='scalar':out['value']=str(e.solve(*cold,physical=cold.physical))
                        else:
                            target=int(part);out['action']=str(e.act(*cold[:3],target,cold.private,cold.observer,physical=cold.physical))
                            out['dawn']=repr(horizon_for_action(e,cold.public,cold.public_state,cold.past,target,cold.private,observer=cold.observer))
                        out.update(status='completed',counts=counts,budget=budget_usage(),cold_complete_source_equal=True,source_sha256=hashlib.sha256(repr(cold).encode()).hexdigest(),seconds=time.perf_counter()-started)
                        print(json.dumps(out),flush=True);return
                out['cold_complete_source_equal']=True
            else:f=node.forecast()
            out.update(status='completed',value=str(f.village_win),forecast=repr(f),table_sha256=hashlib.sha256(repr(tables(source,f)).encode()).hexdigest(),budget=budget_usage(),counts=counts)
    except CalculationBudgetExceeded as error:out.update(status='budget_stopped',reason=error.kind)
    except Pending as error:out.update(status='pending',reason=error.reason)
    out.update(seconds=time.perf_counter()-started,budget_stop=budget_stop())
    print(json.dumps(out),flush=True)


def run(mode,view,part='all'):
    r=watch('benchmarks.player_match_groups.terminal_day_reference',('worker',mode,view,part))
    r['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/grouped_forecast.py','werewolf/information_set_forecast.py',__file__))}
    Path('benchmarks/player_match_groups/terminal-day-'+mode+'-'+view+('-'+part if part!='all' else '')+'.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');return r

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(*sys.argv[2:5])
    else:print(json.dumps(run(*sys.argv[1:4])))
