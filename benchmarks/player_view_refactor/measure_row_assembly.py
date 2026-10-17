"""Bounded display assembly only; no future solver or claimed win benchmark."""
import sys,json,time,gc,tracemalloc,subprocess,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from fractions import Fraction as F
from werewolf.board_flow import BoardData
from werewolf.exact import Values
from werewolf.player_view import ViewScope,ResultFrame,public_view,personal_view,build_public_view,private_api_rows
from tests.test_board_flow import game
from tests.fixtures.player_rows_96da610 import build_rows
from benchmarks.board_b_benchmark import process_memory_peak

def run(mode,n):
    from werewolf.public_log import migrate
    g=game(players=n,claims=['latent']*n);g['public_log']=migrate(g)
    data=BoardData.from_game(g);roles=data.roles();b=roles.board
    scope=ViewScope.public(data);frame=ResultFrame(scope,'complete');private_frame=ResultFrame(scope.personal('wolf',(1,),[]),'complete')
    kw=dict(state=g,event_history=b.history,alive=b.alive,action_values={i:Values(F(1,3),F(2,3))for i in b.alive},by_dawn_values={})
    marginals=[roles.probabilities(i)for i in b.alive]
    def assemble():
        if mode=='public-old':return public_view(data,build_rows(role_state=roles,board=b,**kw),frame)
        if mode=='public-direct':return build_public_view(data,roles,b,frame,**kw)
        rows=private_api_rows(marginals)
        if mode=='private-old':return [p.to_legacy_row()for p in personal_view(data,rows,private_frame).players]
        return rows
    value=assemble()
    comparable=[p.to_legacy_row()for p in value.players]if mode.startswith('public')else value
    gc.collect();tracemalloc.start();start=time.perf_counter()
    for _ in range(50):value=assemble()
    seconds=time.perf_counter()-start;current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    return dict(mode=mode,players=n,iterations=50,seconds=seconds,python_peak_bytes=peak,process_memory=process_memory_peak(),full_legacy_row_dicts_per_assembly=n if mode=='public-old'else 0 if mode=='public-direct'else n,full_row_freezes_per_assembly=n if mode.endswith('old')else 0,full_row_exports_per_assembly=n if mode=='private-old'else 0,semantic_rows=comparable)

if __name__=='__main__':
    if '--child'in sys.argv:print(json.dumps(run(sys.argv[2],int(sys.argv[3])),default=str));raise SystemExit()
    result=dict(base='96da610',scope='representation-only fixed display values; does not evaluate final win rates',runs=[])
    for n in(5,9):
        for round in range(3):
            modes=['public-old','public-direct','private-old','private-direct']
            if round%2:modes.reverse()
            for mode in modes:
                p=subprocess.run([sys.executable,'-B',__file__,'--child',mode,str(n)],cwd=ROOT,capture_output=True,text=True,encoding='utf8',timeout=30)
                if p.returncode:raise RuntimeError(p.stderr)
                row=json.loads(p.stdout);row['round']=round;result['runs'].append(row)
        for prefix in('public','private'):
            a=[x for x in result['runs']if x['players']==n and x['mode']==prefix+'-old'];b=[x for x in result['runs']if x['players']==n and x['mode']==prefix+'-direct']
            assert all(x['semantic_rows']==a[0]['semantic_rows']for x in a+b)
            print(json.dumps(dict(players=n,kind=prefix,old_seconds=statistics.median(x['seconds']for x in a),new_seconds=statistics.median(x['seconds']for x in b),old_python_peak=statistics.median(x['python_peak_bytes']for x in a),new_python_peak=statistics.median(x['python_peak_bytes']for x in b))),flush=True)
    (ROOT/'benchmarks/player_view_refactor/direct-row-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')