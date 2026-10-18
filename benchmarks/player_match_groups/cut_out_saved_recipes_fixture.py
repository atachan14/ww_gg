"""Small saved-recipe regression evidence; no full-game benchmark."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,subprocess,sys

def main():
    runs=[]
    for pattern in ('test_cut_out_saved_recipes.py','test_board_flow.py','test_cut_out_morning.py'):
        command=[sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v']
        result=subprocess.run(command,capture_output=True,text=True,timeout=30)
        log=Path('.artifacts')/(pattern.removesuffix('.py')+'-saved-final.log')
        log.parent.mkdir(exist_ok=True);log.write_text(result.stdout+result.stderr,encoding='utf-8')
        print(result.stdout+result.stderr)
        if result.returncode:raise SystemExit(result.returncode)
        runs.append(dict(pattern=pattern,exit=result.returncode,log=str(log),timeout_seconds=30))
    paths=('benchmarks/player_match_groups/cut_out_saved_recipes.py','tests/test_cut_out_saved_recipes.py')
    record=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),
        head_before_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        labelled_saved_branches=291,tests=runs,full_suite=False,heavy_worker=False,
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        scope='4/5 players, W1 H0, uniform, first execution/night/morning, public role stage',
        unsupported=['all CO cancelled: SavedOrigin secret support 180 vs formal adapter 60','whole-win loop','private view','arbitrary owned-graph editing'])
    Path('benchmarks/player_match_groups/cut-out-saved-recipes-results.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
