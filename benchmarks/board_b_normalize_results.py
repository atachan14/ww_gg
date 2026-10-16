"""Normalize role-name/probability pairs for comparison; preserve original raw data.

Only proof serialization changes. No timings, probabilities or expectations change.
"""
import argparse,copy,json
from pathlib import Path
from board_b_benchmark import digest


def normalize(record):
 result=copy.deepcopy(record)
 for row in result['rows']:
  roles=row['semantic']['public_roles']
  if roles and isinstance(roles[0],list):
   mapped=[]
   for player in roles:
    assert all(isinstance(p,list) and len(p)==2 and isinstance(p[0],str) for p in player)
    assert len({p[0] for p in player})==len(player)
    mapped.append(dict(player))
   row['semantic']['public_roles']=mapped
  row['original_semantic_digest']=row['semantic_digest']
  row['semantic_digest']=digest(row['semantic'])
 result['normalization']='Only native RoleState role-name/probability pairs converted to dictionaries after timing; raw source unchanged.'
 return result


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 source=Path(a.input).resolve();target=Path(a.output).resolve();target.mkdir(parents=True,exist_ok=True)
 summary=json.loads(source.read_text(encoding='utf-8'));records=[normalize(r) for r in summary['records']]
 known={};mismatch=[]
 for r in records:
  for row in r['rows']:
   if row['complete']:
    previous=known.setdefault(r['case'],row['semantic_digest'])
    if previous!=row['semantic_digest']:mismatch.append([r['case'],r['version'],r['repetition'],row['cache']])
  name=f"{r['repetition']:02d}-{r['case']}-{r['version']}-{r['diagnostic']}-{r['experiment']}.json"
  r['raw_record_path']=str(source.parent/name)
  (target/name).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 summary.update(records=records,completed_semantic_digests=known,mismatches=mismatch,raw_summary_path=str(source),normalization='Role-rate representation only; times and exact values unchanged.')
 (target/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'records':len(records),'mismatches':mismatch}))
 if mismatch:raise AssertionError(mismatch)
if __name__=='__main__':main()
