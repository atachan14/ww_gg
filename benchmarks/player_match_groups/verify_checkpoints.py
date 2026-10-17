import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from benchmarks.player_match_groups.checkpoint_audit import run_case,write
from benchmarks.player_match_groups.run import run
from benchmarks.player_match_groups.initial_white import initial_white_source
results=[]
for n,w in((5,1),(6,2)):
    summary=run_case(n,w,total_seconds=300)
    assert summary['complete']
    baseline=run(n,w,prepared=initial_white_source(n,w,actors=(1,2)))
    from benchmarks.player_match_groups.checkpoint_audit import encode
    baseline=encode(baseline)
    assert baseline['complete']
    for mode in ('oracle','audit'):
        assert(summary[mode]['value'],summary[mode]['table'])==(baseline['value'],baseline['table'])
    # Missing interventions must remain pending, never a zero-valued forecast.
    from benchmarks.player_match_groups.checkpoint_audit import aggregate,case_input
    _,game=case_input(n,w)
    partial=dict(summary['parts']['oracle']);partial.pop(str(n))
    pending=aggregate(game,partial)
    assert pending['status']=='pending'and pending['value']is None and pending['table']is None
    reused=run_case(n,w,total_seconds=300)
    assert all(a['reused']for a in reused['attempts'])
    assert reused['complete']and reused['verified_targets']==list(range(1,n+1))
    results.append(dict(players=n,wolves=w,identity=summary['identity'],complete=True,verified_targets=summary['verified_targets'],value=summary['oracle']['value'],initial_consumed_seconds=summary['consumed_seconds'],cache_reused=True,missing_value_pending=True))
    write(ROOT/'benchmarks/player_match_groups/checkpoint-small-validation.json',results)
print(json.dumps(results),flush=True)
