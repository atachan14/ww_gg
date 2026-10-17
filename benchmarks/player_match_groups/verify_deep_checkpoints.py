import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from benchmarks.player_match_groups.deep_checkpoint import run
from benchmarks.player_match_groups.checkpoint_audit import write
reference=json.loads((ROOT/'benchmarks/player_match_groups/dual-white-before.json').read_text())
results=[]
for index,(n,w)in enumerate(((5,1),(6,2))):
    summary=run(n,w,total_seconds=300)
    assert summary['complete']
    for mode in ('oracle','audit'):
        assert(summary[mode]['value'],summary[mode]['table'])==(reference[index]['value'],reference[index]['table'])
    reused=run(n,w,total_seconds=300)
    assert all(a['reused']for a in reused['attempts'])and reused['complete']
    results.append(dict(players=n,wolves=w,identity=summary['identity'],complete=True,value=summary['oracle']['value'],units=len(summary['verified_units']),verified_targets=summary['verified_targets'],seconds=summary['consumed_seconds'],reused=True))
    write(ROOT/'benchmarks/player_match_groups/checkpoint-deep-small-validation.json',results)
print(json.dumps(results),flush=True)
