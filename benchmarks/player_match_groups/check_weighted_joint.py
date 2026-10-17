import sys,json,time
from pathlib import Path
from dataclasses import asdict,is_dataclass
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from benchmarks.player_match_groups.run import run
from benchmarks.player_match_groups.weighted_joint import weighted_source
from werewolf.calculation_budget import calculation_budget
from fractions import Fraction as F

rows=[];started=time.perf_counter()
with calculation_budget(4000000,max_seconds=300):
    before=json.loads(Path('benchmarks/player_match_groups/weighted-before.json').read_text(encoding='utf-8'))
    for i,(n,w,kind)in enumerate(((5,1,'point'),(6,2,'cycle'))):
        prepared=weighted_source(n,w,kind)
        b,s=prepared[2:4]
        if kind=='cycle':
            assert {b.role_probability(p,'wolf')for p in range(2,n+1)}=={F(2,5)}
            assert b.joint_wolf_probability((2,3))!=b.joint_wolf_probability((2,4))
        result=run(n,w,True,True,max_seconds=300,max_work=4000000,prepared=prepared)
        result=json.loads(json.dumps(result,default=lambda x:asdict(x)if is_dataclass(x)else str(x)))
        assert result['complete']and result['stats']['active']and result['stats']['audited_batches']>0
        assert (result['value'],result['table'])==(before[i]['value'],before[i]['table'])
        result['joint']=[list(map(str,(*h.roles,h.mass)))for h in s.hypotheses]
        rows.append(result)
        Path('benchmarks/player_match_groups/weighted-after.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print(n,w,result['value'],result['seconds'],result['stats'],flush=True)
print('total_seconds',time.perf_counter()-started)
