import sys,json,subprocess,statistics,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from benchmarks.player_match_groups.run import source
from werewolf.match_groups import PublicRelations,make_engine
from werewolf.seer_future_uniform import acquire_uniform,FuturePending
from werewolf.exact_renaming import board_signature,state_signature
from werewolf.calculation_budget import calculation_budget,tick
from fractions import Fraction as F
out=dict(base='63c4af9',math_base='03e4e31',prior_trial='c872d19 logic only; e203aac NOT applied',started=datetime.now(timezone.utc).isoformat(),runs=[])
for wolves in (1,2):
    reference=None
    for round in range(3):
        for enabled in ((False,True)if round%2==0 else(True,False)):
            args=[sys.executable,'-B',str(ROOT/'benchmarks/player_match_groups/run.py'),'6',str(wolves)]+(['--enabled']if enabled else[])
            child=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf8',timeout=30)
            if child.returncode:raise RuntimeError(child.stderr+child.stdout)
            r=json.loads(child.stdout);assert r['complete'];r['round']=round
            semantics={k:r[k]for k in('value','table')}
            if reference is None:reference=semantics
            assert semantics==reference;out['runs'].append(r)
    for enabled in(False,True):
        rows=[r for r in out['runs']if r['wolves']==wolves and r['enabled']==enabled]
        print(json.dumps(dict(wolves=wolves,enabled=enabled,median_seconds=statistics.median(r['seconds']for r in rows),median_peak_ws=statistics.median(r['memory']['peak_working_set_bytes']for r in rows),stats=rows[0]['stats'])),flush=True)
start=time.perf_counter();data,roles,b,s,past,rules,strategy,view=source(9,2);relations=PublicRelations.from_view(view)
with calculation_budget(100000,max_seconds=3):
    ids=tuple(range(1,10));masks=tuple(range(512));original=(board_signature(b,ids,masks),state_signature(s,ids,masks));proved=0
    for block in relations.candidate_groups():
        for a in block:
            for c in block:
                if a>=c:continue
                tick(1+len(s.hypotheses));permutation=list(ids);permutation[a-1],permutation[c-1]=permutation[c-1],permutation[a-1]
                mapping=tuple(sum(1<<(permutation[p]-1)for p in range(9)if m>>p&1)for m in range(512))
                assert (board_signature(b,tuple(permutation),mapping),state_signature(s,tuple(permutation),mapping))==original;proved+=1
    acquired=acquire_uniform(s,b.alive,max_work=100000)
    assert not isinstance(acquired,FuturePending);assert sum(h.mass for h in acquired.hypotheses)==1
    assert acquired.public_roles==s.public_roles
    weights={t:sum((h.mass for h in acquired.hypotheses if h.acquisitions[-1].target==t),F())for t in range(2,10)}
    assert set(weights.values())=={F(1,8)}
out['nine_generation_only']=dict(seconds=time.perf_counter()-start,source_worlds=len(s.hypotheses),candidate_groups=relations.candidate_groups(),proved_root_transpositions=proved,next_scan_rows=len(acquired.hypotheses),target_weights={str(t):str(q)for t,q in weights.items()},mass='1',future_evaluation_run=False,grouped_solver_enabled=make_engine(b,s,past,rules,strategy,enabled=True,view=view).grouping,budget=dict(seconds=3,work=100000),note='root symmetry and ordinary generation diagnostics, NOT a compressed nine-player forecast')
out['finished']=datetime.now(timezone.utc).isoformat()
(ROOT/'benchmarks/player_match_groups/results.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8');print(json.dumps(out['nine_generation_only']))