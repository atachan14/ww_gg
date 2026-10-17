import sys,json,time,threading,cProfile,pstats,hashlib
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from benchmarks.player_match_groups.future_reuse import FutureReuseForecast
from benchmarks.player_match_groups.initial_white import initial_white_source
from benchmarks.board_b_benchmark import process_memory_peak
from werewolf.model_a_public import public_forecast
from werewolf.exact import Values
from werewolf.player_view import build_public_view,ResultFrame
from werewolf.calculation_budget import cancellation_scope,CalculationCancelled
from werewolf.seer_future_uniform import FuturePending
from benchmarks.player_match_groups.checkpoint_audit import encode,write


def run(n=6,w=2,enabled=False,profile=False,max_seconds=30,physical_reuse=False,retired_reuse=False,compact_keys=False,fast_parts=False,game=None,retirement_proof=False,max_work=1000000,prepared=None,engine_class=None,engine_options=None):
    if prepared is not None:data,roles,b,state,past,rules,strategy,view=prepared
    elif game is None:data,roles,b,state,past,rules,strategy,view=initial_white_source(n,w,actors=(1,2))
    else:
        from benchmarks.player_match_groups.checkpoint_audit import prepared_game
        data,roles,b,state,past,rules,strategy,view=prepared_game(game)
    n=b.player_count;w=b.initial_role_counts['wolf']
    engines=[]
    def factory(*args,**kwargs):
        from benchmarks.player_match_groups.retirement_proof import RetirementProofForecast
        e=(engine_class or RetirementProofForecast)(*args,**(engine_options or {}),retirement_proof=retirement_proof,future_reuse=enabled,physical_reuse=physical_reuse,retired_reuse=retired_reuse,compact_keys=compact_keys,fast_parts=fast_parts,**kwargs);engines.append(e);return e
    cancel=threading.Event();done=threading.Event()
    def memory_guard():
        while not done.wait(.1):
            peak=process_memory_peak()
            if max(peak['peak_working_set_bytes'],peak['peak_process_commit_bytes'])>=1500000000:cancel.set()
    watcher=threading.Thread(target=memory_guard,daemon=True);watcher.start();started=time.perf_counter();profiler=cProfile.Profile()
    try:
        with patch('werewolf.model_a_public.InformationSetForecast',factory),cancellation_scope(cancel):
            if profile:profiler.enable()
            result=public_forecast(b,state,past,rules,strategy,max_work=max_work,max_seconds=max_seconds)
            if profile:profiler.disable()
    except CalculationCancelled:return dict(complete=False,reason='memory_limit')
    finally:done.set();watcher.join()
    elapsed=time.perf_counter()-started;e=engines[0]
    if profile:
        profiler.dump_stats(str(ROOT/'.artifacts/player-match-groups/future-baseline.prof'))
        pstats.Stats(profiler).sort_stats('cumulative').print_stats(20)
    if isinstance(result,FuturePending):return dict(complete=False,reason=result.reason,seconds=elapsed,stats=e.reuse_stats,mask_stats=e.mask_stats,expansions=e.expansions,memory=process_memory_peak())
    final=build_public_view(data,roles,b,ResultFrame(view.scope,'complete'),state=data.to_game(),event_history=b.history,alive=b.alive,action_values={p:Values(v,1-v)for p,v in result.action_values},by_dawn_values=dict(result.by_dawn_values))
    return encode(dict(trial_source={name:hashlib.sha256((ROOT/'benchmarks/player_match_groups'/name).read_bytes()).hexdigest() for name in ('future_reuse.py','fast_key_parts.py','measure_future_reuse.py','retirement_proof.py','extension_reuse.py','extension_cases.py')},complete=True,players=n,wolves=w,enabled=enabled,physical_reuse=physical_reuse,retired_reuse=retired_reuse,compact_keys=compact_keys,fast_parts=fast_parts,retirement_proof=retirement_proof,retirement_proof_hits=e.retirement_proof_hits,seconds=elapsed,value=result.village_win,table=[p.to_legacy_row()for p in final.players],stats=e.reuse_stats,mask_stats=e.mask_stats,expansions=e.expansions,memory=process_memory_peak()))

if __name__=='__main__':
    result=run(int(sys.argv[1]),int(sys.argv[2]),'--enabled'in sys.argv,'--profile'in sys.argv,physical_reuse='--physical'in sys.argv,retired_reuse='--retired'in sys.argv,compact_keys='--compact'in sys.argv,fast_parts='--fast-parts'in sys.argv,retirement_proof='--retirement-proof'in sys.argv)
    if '--profile'not in sys.argv:print(json.dumps(result),flush=True)
