"""Bounded max information-set comparison with independent small-game values."""
import json,time,sys,subprocess,threading,os
from pathlib import Path
from fractions import Fraction as F
from .cut_out_max_game import graph,evaluate
from .cut_out_uniform_game import OwnView
from .partitioned_match_groups import UnsupportedPartition
from werewolf.information_set_forecast import optimal_targets


def complete_table(source,forecast,view):
    # The public formatter already derives row count from the supplied roles.
    from werewolf.actor_information import condition_actor_state
    from werewolf.exact import replace_worlds,Values
    from werewolf.player_view import build_public_view,ViewScope,ResultFrame,private_api_rows
    from types import SimpleNamespace
    root=source.origin();law=root.public_state if view is None else condition_actor_state(root.public_state,view.accepts)
    board=replace_worlds(root.public,law.public_roles)
    rows=[{r:board.role_probability(p,r) for r in ('wolf','medium','seer','hunter','villager')} for p in range(1,board.player_count+1)]
    if view is not None:return private_api_rows(rows,targets=dict(forecast.action_values),final_values=dict(forecast.action_values),dawn_for=dict(forecast.by_dawn_values).get)
    primary=Values(forecast.village_win,1-forecast.village_win)
    table=build_public_view(source.data,SimpleNamespace(probabilities=lambda p:rows[p-1]),board,
        ResultFrame(ViewScope.public(source.data),'complete','max-comparison'),state=source.data.to_game(),
        event_history=board.history,alive=board.alive,action_values={p:Values(v,1-v) for p,v in forecast.action_values},
        by_dawn_values=dict(forecast.by_dawn_values),manual=True)
    return table,primary,source.data.roles().progress.total_values(primary)


def audit(players=5,mediums=0,night='random',private=False,_fake_reports='random'):
    from .cut_out_two_nights import restore_terminals
    from werewolf.board_future import same_role_board
    from werewolf.actor_information import WolfInformation
    start=time.perf_counter();source=graph(players,mediums,night,fake_reports=_fake_reports);root=source.origin()
    view=OwnView(2,'medium') if private else None
    actual=evaluate(source,view=view,capture_terminal=True)
    expected=evaluate(source,view=view,official_reference=True,capture_terminal=True)
    if isinstance(actual,UnsupportedPartition) or isinstance(expected,UnsupportedPartition):raise AssertionError((actual,expected))
    forecast,engine=actual;reference,full=expected
    assert forecast==reference
    assert complete_table(source,forecast,view)==complete_table(source,reference,view)
    best=(2,4) if players==4 else (2,4,5)
    policy=optimal_targets(engine.day_scores(root.public,root.public_state,root.past),maximize=True)
    assert tuple(policy)==best
    value=F(1,2) if players==4 else F(23,27) if night=='random' else F(2,3)
    assert forecast.village_win==value
    actions=dict(forecast.action_values)
    if not private:
        expected_actions={p:(value if p in best else F(0) if players==4 else (F(4,9) if p==1 else F(2,3)) if night=='random' else F(1,3)) for p in root.public.alive}
        assert actions==expected_actions,(actions,expected_actions)
    else:
        expected_best=F(1) if players==4 else F(8,9) if night=='random' else F(3,4)
        assert max(actions.values())==expected_best and value<expected_best
        assert actions[2]==(F(0) if players==4 else F(7,9) if night=='random' else F(1,2))
    assert all(v.village_win==(F(1) if private and players==4 and p==4 else F(0) if private and p==2 else F(1,2) if private and players==5 and p in (4,5) else F(1,len(best)) if p in best else F(0)) for p,v in forecast.by_dawn_values)
    for key,policy_row in engine.policies.items():
        assert full.wolf_policy(key[0],key[1],key[2],key[3].initial_roster,key[3].attacks)==policy_row
        assert sum((q for _,q in policy_row),F())==1
        assert len({q for _,q in policy_row})==1
    comparisons=0
    for key,result in engine.scalar_actions.items():
        b,s,past,own,observer,physical,target=key
        assert result==full.act(b,s,past,target,own,observer,physical=physical)
        comparisons+=1
    small,small_stats=restore_terminals(engine);large,large_stats=restore_terminals(full)
    for key,(q,state,request) in small.items():
        old_q,old,_=large[key]
        assert q==old_q and state.public_state==old.public_state and state.private==old.private and state.past==old.past
        assert same_role_board(state.public,old.public) and same_role_board(state.physical,old.physical)
        assert request.origin is source.origin
    # Wolf policy beliefs must retain unknown medium roles even for a medium viewer.
    wolf_groups=0
    for key in engine.policies:
        b,s,past,info=key
        belief=info.condition_public(s)
        if mediums and b.day==1 and b.phase=='night':
            assert len({h.roles[1] for h in belief.hypotheses})==players-2
            wolf_groups+=1
    if mediums and players==5:assert wolf_groups
    return dict(players=players,mediums=mediums,night=night,view='medium2' if private else 'public',
        village_win=str(value),public_policy=list(policy),private_best=str(max(actions.values())),
        scalar_context_comparisons=comparisons,terminal_readbacks=len(small),unknown_medium_wolf_information_sets=wolf_groups,
        complete_table_action_horizon_joint_physical_history_equal=True,grouped=dict(engine.costs),labelled=dict(full.costs),
        seconds=time.perf_counter()-start)


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    def watch():
        while True:
            if peak_bytes()>1_500_000_000:os._exit(137)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result=audit(*json.loads(case));result['peak_working_set_bytes']=peak_bytes();print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    started=time.monotonic();rows=[];logs=[]
    cases=[(4,0,'random',False),(4,1,'max',True),(5,0,'random',False),(5,1,'random',True),(5,1,'max',False),(5,1,'max',True)]
    for case in cases:
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,json.dumps(case)],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+str(case),flush=True)
    previous=json.loads(Path('benchmarks/player_match_groups/withdraw-standard-results.json').read_text(encoding='utf-8'))
    checks=[(c['kind'],c['target']) for c in previous['checks']]+[('pattern','test_cut_out_seven_minimal.py'),('pattern','test_cut_out_max_game.py')]
    for kind,target in checks:
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture',kind,target],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/max-regressions-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,regression_checks=checks,existing42_preserved=True,regression_tests=44,overall_seconds=time.monotonic()-started)
    Path('benchmarks/player_match_groups/cut-out-max-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'],checks=len(checks))),flush=True)

if __name__=='__main__':main()
