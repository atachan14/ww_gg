"""One saved-day migration unit; no night-history reinterpretation."""
import sys,json,time,statistics,subprocess,hashlib
from copy import deepcopy
from pathlib import Path


def saved_day(data,target):
    g=data.to_game();step={k:deepcopy(g[k]) for k in ('claims','claim_policy','policy','seer_options','result_disclosure_model')};step['target']=target
    return data.child(step)


def worker(mode):
    from .cut_out_publication_orbit_value_fixture import make_role_filter_scope,forecast,tables
    from .cut_out_uniform_game_fixture import peak_bytes
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.board_future import SavedOrigin,GeneratedBoard,remember,calculation_origin
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.exact import Strategy
    from werewolf.calculation_budget import calculation_budget
    from werewolf.joint_value_sharing import independent_joint_values
    data=make_role_filter_scope().graph.data;mid=saved_day(data,2)
    start=time.perf_counter()
    with calculation_budget(4000000,max_seconds=20),independent_joint_values():
        if mode=='ordinary':
            e=InformationSetForecast(mid.game_data.rules,Strategy(**mid.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
            origin=SavedOrigin(mid,e.rules,e.strategy,False);s=origin();request=GeneratedBoard(origin)
            with calculation_origin(mid):remember(e,request,s);result=forecast(e,s)
            states=dict(values=len(e.values),actions=len(e.action_values),saved_sources=len(e.board_sources),resolution_cache=len(e.board_action_kernels))
        else:
            c=ClosedCalculation(mid if mode=='saved' else data,max_seconds=20)
            node=c.root if mode=='saved' else next(r.node for r in c.root.action(2) if r.node.read().public.winner is None)
            s=node.read();result=node.forecast();states=c.stats()
        table=tables(s,result);elapsed=time.perf_counter()-start;peak=peak_bytes()
    # Complete joint measure, actual histories and named outputs. Keep the two
    # declaration/acquisition configuration fields separately visible.
    semantic=(s.public,s.physical,s.public_state.hypotheses,s.private.hypotheses,s.public_state.rosters,s.private.rosters,s.past,result,table)
    return dict(mode=mode,seconds=elapsed,peak_bytes=peak,states=states,digest=hashlib.sha256(repr(semantic).encode()).hexdigest(),
        law_config=dict(tracked=s.public_state.tracked,observed_prefix=s.public_state.observed_prefix))


def audit():
    from fractions import Fraction as F
    from .cut_out_publication_orbit_value_fixture import make_role_filter_scope,forecast,tables
    from .cut_out_first_cycle_coverage import base
    from .cut_out_compact_terminal_fixture import independent_cold
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.board_future import SavedOrigin,GeneratedBoard,remember,calculation_origin,same_role_board
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.exact import Strategy
    rows=[]
    for graph,target in ((make_role_filter_scope().graph,2),(base()[0],1)):
        initial=ClosedCalculation(graph.data);live=next(r.node for r in initial.root.action(target) if r.node.read().public.winner is None)
        data=saved_day(graph.data,target);reopened=ClosedCalculation(data);a=reopened.root.read();b=live.read()
        assert a==b and reopened.root.groups==live.groups
        assert independent_cold(graph,reopened.root.export_request())==b
        ordinary=SavedOrigin(data,data.game_data.rules,Strategy(**data.to_game()['policy']),False)()
        assert same_role_board(ordinary.public,a.public) and same_role_board(ordinary.physical,a.physical)
        assert ordinary.public_state.hypotheses==a.public_state.hypotheses and ordinary.private.hypotheses==a.private.hypotheses and ordinary.past==a.past
        row=dict(players=data.game_data.players,entry_probability=str(reopened.entry_probability),groups=reopened.root.groups,
            canonical_full_state_equal=True,independent_cold_equal=True,ordinary_complete_hypotheses_equal=True,
            canonical_config=dict(tracked=a.public_state.tracked,observed_prefix=a.public_state.observed_prefix),
            ordinary_config=dict(tracked=ordinary.public_state.tracked,observed_prefix=ordinary.public_state.observed_prefix))
        if data.game_data.players==5:
            e=InformationSetForecast(data.game_data.rules,Strategy(**data.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
            with calculation_origin(data):
                remember(e,GeneratedBoard(SavedOrigin(data,e.rules,e.strategy,False)),ordinary);want=forecast(e,ordinary)
            got=reopened.root.forecast();assert got==want==live.forecast() and tables(a,got)==tables(ordinary,want)
            row['Forecast_Table_equal']=True;row['states']=reopened.stats()
        else:
            choices=[c for c in reopened.root.wolf_choices() if c.target==4];total=sum((c.mass for c in choices),F())
            two=lambda c:(c.information.initial_roster&a.public.alive_mask).bit_count()==2
            row['night_next_unit_counterexample']=dict(target=4,choice_probabilities=sorted(set(str(c.probability) for c in choices)),
                observation_mass=str(total),two_wolves_prior=str(sum((c.information_mass for c in choices if two(c)),F())),
                two_wolves_after_observed_choice=str(sum((c.mass for c in choices if two(c)),F())/total))
        rows.append(row)
    result=dict(status='verified',unit='one saved uniform daytime execution; unchanged complete initial public conditions',rows=rows,
        nighttime_saved_entry=False,ledger_used=False,full_initial7_search=False)
    Path('benchmarks/player_match_groups/closed-saved-day-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def run(repeats=5):
    rows=[];modes=('ordinary','generated','saved');start=time.perf_counter()
    for i in range(repeats):
        for mode in modes[i%3:]+modes[:i%3]:
            if time.perf_counter()-start>180:raise TimeoutError('saved day measurement exceeded 180 seconds')
            p=subprocess.run([sys.executable,'-m','benchmarks.player_match_groups.closed_saved_day_fixture','worker',mode],capture_output=True,text=True,timeout=25,check=True)
            row=json.loads(p.stdout);row['repeat']=i;rows.append(row)
    assert len({r['digest'] for r in rows})==1
    summary={mode:dict(seconds_median=statistics.median(r['seconds'] for r in rows if r['mode']==mode),
        seconds_min=min(r['seconds'] for r in rows if r['mode']==mode),seconds_max=max(r['seconds'] for r in rows if r['mode']==mode),
        peak_bytes_median=statistics.median(r['peak_bytes'] for r in rows if r['mode']==mode),states=next(r['states'] for r in rows if r['mode']==mode)) for mode in modes}
    result=dict(status='verified',repeats=repeats,scope='one saved uniform daytime execution with unchanged complete initial public conditions; four-alive public Forecast',summary=summary,runs=rows,
        raw_configuration_difference='ordinary saved root uses tracked=None/observed_prefix=0; canonical generated replay retains initial tracked/prefix, never overwrites them',
        full_initial7_search=False,ledger_used=False)
    Path('benchmarks/player_match_groups/closed-saved-day-performance-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(status=result['status'],summary=summary)),flush=True);return result


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:print(json.dumps(worker(sys.argv[2])),flush=True)
    else:run()
