"""Compact evidence for the three-revision Game cache comparison."""
import argparse,json
from pathlib import Path
from board_b_report import validate,rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--cache',required=True);p.add_argument('--joint',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 load=lambda name:json.loads(Path(name).read_text(encoding='utf-8'))
 b=load(a.baseline);c=load(a.cache);j=load(a.joint)
 assert not c['failures'] and not j['failures']
 result={'versions':b['versions'],'environment':b['environment'],'budget':b['budget'],'cases_sha256':b['cases_file_sha256'],'complete_semantic_comparisons':validate(b),'baseline':rows(b),'method':'Three fixed revisions; fresh process per case/repetition/version; five repetitions, serial old/new/improved then reversed order. Cold then same-Game warm. Runtime creation outside measured request, matching Game lifetime. No concurrent test/browser benchmark. All requested results retained; no Pending silently omitted.','cache_audit':{'cases':c['cases'],'warm_request_count_per_version':c['warm_request_count_per_version'],'failures':c['failures'],'input_immutability_checked':c['input_immutability_checked']},'joint_audit':{'cases':j['cases'],'failures':j['failures']},'raw_summary_paths':[a.baseline,a.cache,a.joint],'counters':[{'case':r['case'],'version':r['version'],'repetition':r['repetition'],'rows':[{k:v for k,v in x.items() if k in ('cache','complete','pending','cache_before','cache_after','seconds','cpu_seconds')} for x in r['rows']]} for r in b['records']]}
 result['cache_audit']['fresh_semantic_digests']={v:{k:x['digest'] for k,x in data['fresh'].items()} for v,data in c['versions'].items()}
 result['cache_audit']['pending']={v:{k:x['pending'] for k,x in data['fresh'].items() if x['pending']} for v,data in c['versions'].items()}
 result['joint_audit']['digests']={v:{k:x['digest'] for k,x in data.items()} for v,data in j['versions'].items()}
 from datetime import datetime,timezone,timedelta
 ends=[];starts=[]
 for record in b['records']:
  raw=Path(a.baseline).parent/f"{record['repetition']:02d}-{record['case']}-{record['version']}-{record['diagnostic']}-{record['experiment']}.json"
  end=datetime.fromtimestamp(raw.stat().st_mtime,timezone.utc);ends.append(end);starts.append(end-timedelta(seconds=record['subprocess_wall_seconds']))
 result['observation_window_utc']={'approx_start':min(starts).isoformat(),'approx_end':max(ends).isoformat(),'method':'Raw file mtime minus child process wall; approximate.'}
 Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'complete':result['complete_semantic_comparisons'],'cache_failures':c['failures'],'joint_failures':j['failures']}))
if __name__=='__main__':main()
