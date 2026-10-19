"""Bounded saved-night/multiple-action checks and fresh-process measurement."""
import json,hashlib,time,sys,subprocess,statistics
from pathlib import Path
from fractions import Fraction as F
from types import SimpleNamespace
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.board_future import SavedOrigin,GeneratedBoard,remember,calculation_origin,kernel_calculation
from werewolf.exact import Strategy
from werewolf.information_set_forecast import InformationSetForecast
from .closed_saved_day_fixture import saved_day
from .cut_out_publication_orbit_value_fixture import make_role_filter_scope,forecast,tables
from .cut_out_compact_terminal_fixture import independent_cold


def case(players):
    original=make_role_filter_scope().graph
    game=original.data.to_game()
    game.update(players=players,wolves=1 if players==5 else 2,claims=['seer']+['latent']*(players-1))
    initial=BoardData.from_game(game)
    graph=SimpleNamespace(data=initial,engine=original.engine)
    targets=(1,2) if players==5 else (2,1,3,4)
    return graph,targets


def ordinary(data):
    e=InformationSetForecast(data.game_data.rules,Strategy(**data.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False)
    e.retain_joint_guard_history=True
    origin=SavedOrigin(data,e.rules,e.strategy,False)
    return e,origin,origin()


def named(e,origin,s):
    with calculation_origin(origin.board_data):
        remember(e,GeneratedBoard(origin),s)
        result=forecast(e,s)
    return result,tables(s,result)


def audit():
    from werewolf.actor_information import PersonalInformation
    rows=[]
    for n in (5,7):
        graph,targets=case(n);symmetries=0;data=graph.data;live=ClosedCalculation(data).root;event=F(1);prefix=[]
        for target in targets:
            data=saved_day(data,target);mass,live=live.observe(target);event*=mass
            reopened=ClosedCalculation(data);s=reopened.root.read()
            assert s==live.read() and reopened.entry_probability==event and reopened.root.groups==live.groups
            assert independent_cold(graph,reopened.root.export_request())==s
            from .cut_out_joint_night_forecast_fixture import moved_source
            from werewolf.board_future import same_role_board
            for group in reopened.root.groups:
                for p in group[1:]:
                    permutation=list(range(1,n+1));permutation[group[0]-1],permutation[p-1]=p,group[0]
                    other=moved_source(s,tuple(permutation))
                    assert same_role_board(s.public,other.public) and same_role_board(s.physical,other.physical)
                    assert (s.public_state,s.private,s.past)==(other.public_state,other.private,other.past)
                    symmetries+=1
            e,origin,reference=ordinary(data)
            for attr in ('public_state','private'):
                a,b=getattr(s,attr),getattr(reference,attr)
                assert a.hypotheses==b.hypotheses and a.rosters==b.rosters
            assert (s.public,s.physical,s.past)==(reference.public,reference.physical,reference.past)
            prefix.append(dict(target=target,probability=str(mass),path_probability=str(event),alive=s.public.alive,groups=reopened.root.groups,hypotheses=len(s.private.hypotheses)))
            if len(s.public.alive)<=4:
                want,table=named(e,origin,reference);got=reopened.root.forecast()
                assert want==got and table==tables(s,got)
                # Compare an owner-only view, with no other actor's secrets.
                actor=next(p for p in s.public.alive if any(not any(m&(1<<(p-1)) for m in h.roles) for h in s.private.hypotheses))
                info=PersonalInformation(actor,'villager');mass,owned=reopened.root.personal(info)
                with kernel_calculation():other_mass,other=e.personal_view(reference,info);own_forecast=forecast(e,other)
                assert mass==other_mass and owned.read().private.hypotheses==other.private.hypotheses
                assert owned.forecast()==own_forecast and tables(owned.read(),own_forecast)==tables(other,own_forecast)
        rows.append(dict(players=n,prefixes=prefix,independent_group_generators=symmetries,full_canonical_cold_equal=True,ordinary_joint_history_boards_equal=True,public_personal_Forecast_Table_equal=True,
            canonical_metadata=dict(tracked=s.private.tracked,observed_prefix=s.private.observed_prefix),ordinary_metadata=dict(tracked=reference.private.tracked,observed_prefix=reference.private.observed_prefix),states=reopened.stats()))
    result=dict(status='verified',scope='unchanged complete initial public reports; uniform H0 known-target nonterminal histories with no newly due reports',cases=rows,state_pruning=False,ledger_used=False,full_initial7_search=False)
    Path('benchmarks/player_match_groups/closed-saved-history-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def worker(n,mode):
    from .cut_out_uniform_game_fixture import peak_bytes
    graph,targets=case(n);data=graph.data
    for target in targets:data=saved_day(data,target)
    start=time.perf_counter()
    if mode=='saved':
        c=ClosedCalculation(data);s=c.root.read();r=c.root.forecast();table=tables(s,r);states=c.stats()
    else:
        e,origin,s=ordinary(data);r,table=named(e,origin,s)
        states=dict(values=len(e.values),actions=len(e.action_values),saved_sources=len(e.board_sources),resolution_cache=len(e.board_action_kernels))
    elapsed=time.perf_counter()-start
    semantic=(s.public,s.physical,s.public_state.hypotheses,s.private.hypotheses,s.public_state.rosters,s.private.rosters,s.past,r,table)
    return dict(players=n,mode=mode,seconds=elapsed,peak_bytes=peak_bytes(),states=states,digest=hashlib.sha256(repr(semantic).encode()).hexdigest())


def measure():
    rows=[]
    for i in range(5):
        for n in (5,7):
            for mode in (('ordinary','saved') if i%2==0 else ('saved','ordinary')):
                p=subprocess.run([sys.executable,'-m','benchmarks.player_match_groups.closed_saved_history_fixture','worker',str(n),mode],capture_output=True,text=True,check=True,timeout=30)
                row=json.loads(p.stdout);row['repeat']=i;rows.append(row)
    summary=[]
    for n in (5,7):
        assert len({r['digest'] for r in rows if r['players']==n})==1
        summary.append(dict(players=n,modes={m:dict(seconds_median=statistics.median(r['seconds'] for r in rows if r['players']==n and r['mode']==m),seconds_range=[min(r['seconds'] for r in rows if r['players']==n and r['mode']==m),max(r['seconds'] for r in rows if r['players']==n and r['mode']==m)],states=next(r['states'] for r in rows if r['players']==n and r['mode']==m)) for m in ('ordinary','saved')}))
    result=dict(status='verified',repeats=5,summary=summary,runs=rows,boundary='engine/root reconstruction plus public Forecast/Table; common fixture preparation and imports excluded',state_pruning=False,full_initial7_search=False)
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/action_flow.py','werewolf/closed_calculation.py','werewolf/actor_information.py','werewolf/belief_projection.py','werewolf/root_secret_flow.py','benchmarks/player_match_groups/closed_saved_history_fixture.py'))}
    Path('benchmarks/player_match_groups/closed-saved-history-performance-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:print(json.dumps(worker(int(sys.argv[2]),sys.argv[3])))
    elif '--measure' in sys.argv:print(json.dumps(measure()['summary']))
    else:print(json.dumps(audit()))
