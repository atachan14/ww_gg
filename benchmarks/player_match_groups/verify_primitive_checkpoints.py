import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from benchmarks.player_match_groups.primitive_checkpoint import run,context,import_legacy,adapter_version
from benchmarks.player_match_groups import checkpoint_audit as base
reference=json.loads((ROOT/'benchmarks/player_match_groups/dual-white-before.json').read_text())
results=[]
for index,(n,w)in enumerate(((5,1),(6,2))):
    result=run(n,w,300,verify_fresh=True)
    assert result['complete']
    for mode in ('oracle','audit'):
        assert(result[mode]['value'],result[mode]['table'])==(reference[index]['value'],reference[index]['table'])
    assert len([a for a in result['attempts']if not a.get('reused')])==2
    results.append(dict(players=n,wolves=w,complete=True,value=result['oracle']['value'],imports=result['imports'],fresh_calls=2,verified_primitives=len(result['verified_primitives']),seconds=result['consumed_seconds']))
path,game,plans,items=context(7,2)
parts,imports=import_legacy(7,2,game,plans,items,base.engine_version(),adapter_version())
assert imports['complete_unit_pairs']==14 and imports['verified_prefix_terms']==3
base.write(ROOT/'benchmarks/player_match_groups/primitive-small-validation.json',dict(cases=results,seven_imports=imports,core_engine=base.engine_version(),adapter=adapter_version()))
print(json.dumps(dict(cases=results,seven_imports=imports)),flush=True)
