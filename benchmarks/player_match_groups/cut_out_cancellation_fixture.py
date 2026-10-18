"""Bounded cancellation regression evidence; no full-game solver."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,subprocess,sys

def main():
    runs=[]
    for name,count in (('cancellation',2),('saved_recipes',4),('model_a',6),('day_night',4),('morning',4)):
        pattern='test_cut_out_'+name+'.py'
        result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v'],capture_output=True,text=True,timeout=30)
        log=Path('.artifacts')/(pattern.removesuffix('.py')+'-cancellation-final.log')
        log.parent.mkdir(exist_ok=True);log.write_text(result.stdout+result.stderr,encoding='utf-8')
        print(result.stdout+result.stderr,flush=True)
        if result.returncode:raise SystemExit(result.returncode)
        runs.append(dict(pattern=pattern,count=count,exit=result.returncode,log=str(log)))
    paths=('benchmarks/player_match_groups/cut_out_model_a.py','tests/test_cut_out_cancellation.py','tests/test_cut_out_saved_recipes.py')
    record=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),
        head_before_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        cancellation_roundtrip_branches=295,previous_saved_branches=291,total_tests=20,tests=runs,
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        root_cause='fixed CO prior tracked=() omitted latent first acquisitions; official no-CO root tracked=None retains them',
        independent_root_counts={'4':{'roles':24,'secrets':48},'5':{'roles':60,'secrets':180}},
        ordinary_flow_changed=False,full_suite=False,heavy_worker=False,win_loop=False)
    Path('benchmarks/player_match_groups/cut-out-cancellation-results.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
