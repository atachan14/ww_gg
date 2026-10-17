"""Finite fresh-process AB/BA comparisons; never shares solver instances."""
import json,subprocess,sys,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def child(n,w,enabled,seconds):
    code=('import json;from benchmarks.player_match_groups.measure_future_reuse import run;'
          f'print(json.dumps(run({n},{w},{enabled},max_seconds={seconds},physical_reuse={enabled},retired_reuse={enabled},compact_keys={enabled},fast_parts={enabled})))')
    started=time.perf_counter()
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,timeout=seconds+30,check=True)
    value=json.loads(result.stdout)
    return dict(fresh_process=True,wall_seconds=time.perf_counter()-started,result=value)

def main():
    rows=[]
    for pair,order in enumerate(((False,True),(True,False),(False,True)),1):
        values={}
        for enabled in order:
            row=child(6,2,enabled,30);row.update(pair=pair,enabled=enabled);rows.append(row);values[enabled]=row['result']
            print(pair,enabled,row['result'].get('seconds'),flush=True)
        a,b=values[False],values[True]
        assert a['complete'] and b['complete']
        assert (a['value'],a['table'])==(b['value'],b['table'])
    out=dict(protocol='AB/BA/AB, independent interpreter per trial, no checkpoint/cache import',exact_value_and_table_equal=True,rows=rows)
    (ROOT/'benchmarks/player_match_groups/future-reuse-fresh-results.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
