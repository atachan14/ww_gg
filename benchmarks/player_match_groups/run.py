import sys,json,time
from pathlib import Path
from dataclasses import asdict,is_dataclass
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from werewolf.board_flow import BoardData
from werewolf.board_roles import prepare_evaluation
from werewolf.exact import Rules,Strategy,Values
from werewolf.public_log import migrate
from werewolf.player_view import ViewScope,ResultFrame,build_public_view
from werewolf.model_a_public import public_forecast
from benchmarks.board_b_benchmark import process_memory_peak

def source(n=6,wolves=1):
    strategy=Strategy('random','random',fake_reports='random');rules=Rules(initial_seer='none')
    g=dict(players=n,wolves=wolves,seers=1,mediums=0,hunters=0,rules=asdict(rules),policy=asdict(strategy),history=[],claims=['seer']+['latent']*(n-1),claim_policy={},revision=0,selection=None)
    g['public_log']=migrate(g);data=BoardData.from_game(g);roles=data.roles();b=roles.board
    kind,prepared=prepare_evaluation(g,b,rules,strategy,max_work=1000000,max_seconds=20)
    assert kind=='prior',kind
    s,past=prepared
    view=build_public_view(data,roles,b,ResultFrame(ViewScope.public(data),'roles'),state=g,event_history=b.history,alive=b.alive,action_values={},by_dawn_values={})
    return data,roles,b,s,past,rules,strategy,view

def run(n=6,wolves=1,enabled=False,audit=False):
    data,roles,b,s,past,rules,strategy,view=source(n,wolves);stats={};start=time.perf_counter()
    result=public_forecast(b,s,past,rules,strategy,max_work=1000000,max_seconds=20,match_groups=enabled,match_view=view,match_audit=audit,diagnostics=stats)
    elapsed=time.perf_counter()-start
    from werewolf.seer_future_uniform import FuturePending
    if isinstance(result,FuturePending):return dict(complete=False,reason=result.reason,seconds=elapsed,stats=stats)
    final_view=build_public_view(data,roles,b,ResultFrame(view.scope,'complete'),state=data.to_game(),event_history=b.history,alive=b.alive,action_values={p:Values(v,1-v)for p,v in result.action_values},by_dawn_values=dict(result.by_dawn_values))
    return dict(complete=True,players=n,wolves=wolves,enabled=enabled,audit=audit,seconds=elapsed,value=str(result.village_win),table=[p.to_legacy_row()for p in final_view.players],stats=stats,memory=process_memory_peak())

if __name__=='__main__':print(json.dumps(run(int(sys.argv[1]),int(sys.argv[2]),'--enabled'in sys.argv,'--audit'in sys.argv),default=lambda x:asdict(x)if is_dataclass(x)else str(x)))