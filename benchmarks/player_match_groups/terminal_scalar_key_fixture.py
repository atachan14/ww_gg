"""Equal completed branch and exact owned six-child cache comparison."""
import json,sys,time,hashlib
from pathlib import Path
from unittest.mock import patch
from contextlib import nullcontext
from .initial_seven_entry_probe import watch,LIMITS


def worker(mode,target=4):
    from .cut_out_user_seven_uniform_preparation import comparison_game
    from werewolf.closed_calculation import ClosedCalculation,_forecast_scope
    from werewolf.board_flow import BoardData
    from werewolf.calculation_budget import calculation_budget,budget_usage
    start=time.perf_counter()
    with calculation_budget(LIMITS['max_work'],max_seconds=LIMITS['max_seconds']):
        c=ClosedCalculation(BoardData.from_game(comparison_game()[1]),grouped=True,aggregate_wolf=True,aggregate_reports=True)
        e=c._ClosedCalculation__engine;n=c.root;s=n.read()
        observed=n.observe(target)[1]
        forced=next(r.node for r in n.action(target) if r.node.read().public.winner is None)
        assert observed.read()==forced.read()
        scope=patch.object(e,'full_renamed_key',return_value=None) if mode=='before' else nullcontext()
        _forecast_scope(s,e)
        with scope,c._ClosedCalculation__kernel(),e.group_scope(n.groups):
            value=e.act(*s[:3],target,s.private,s.observer,physical=s.physical)
            before=dict(e.expansions);work=budget_usage()['work'];child=observed.read()
            with e.group_scope(observed.groups):other=e.solve(*child,physical=child.physical)
            assert value==other and before==e.expansions
            assert budget_usage()['work']==work
        out=dict(status='verified',mode=mode,target=target,value=str(value),complete_same_branch=True,forced_and_observed_six_joint_equal=True,six_child_scalar_cached_without_reexpansion=True,states=c.stats(),budget=budget_usage(),seconds=time.perf_counter()-start)
    print(json.dumps(out),flush=True)


def run(mode,target=4):
    r=watch('benchmarks.player_match_groups.terminal_scalar_key_fixture',('worker',mode,str(target)))
    r['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/grouped_forecast.py','werewolf/information_set_forecast.py',__file__))}
    Path('benchmarks/player_match_groups/terminal-scalar-key-'+mode+('-'+str(target) if target!=4 else '')+'.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');return r

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 4)
    else:print(json.dumps(run(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 4)))
