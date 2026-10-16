"""Validate semantic references and produce compact local benchmark evidence."""
import argparse,json,statistics
from pathlib import Path
from board_b_benchmark import ROOT


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def validate(summary,reference=None):
    if summary['mismatches']:raise AssertionError(summary['mismatches'])
    expected={'basic':'7/15','seven':'149/324','seven-observed':'113/504'}
    count=0
    for record in summary['records']:
        for row in record['rows']:
            if not row['complete']:continue
            semantic=row['semantic'];result=semantic['result'];name=record['case']
            if name in expected:
                assert result['village_win']=={'fraction':expected[name]},(name,result)
                if name in ('seven','seven-observed'):
                    assert len(result['action_values'])==7
                    assert semantic['public_day_policy']==[[2,{'fraction':'1/2'}],[3,{'fraction':'1/2'}]]
            if name=='private-history':
                for i in (3,4):assert result['players'][i]['final']=={'village':'5/6','wolf':'1/6'}
            if reference:assert row['semantic_digest']==reference['completed_semantic_digests'][name],(name,'reference mismatch')
            count+=1
    return count


def rows(summary):
    result=[]
    for key,s in summary['summaries'].items():
        case,version,cache=key.split('/')
        cpus=[r['cpu_seconds'] for record in summary['records'] if record['case']==case and record['version']==version for r in record['rows'] if r['cache']==cache and r['complete']]
        result.append({'case':case,'version':version,'cache':cache,**s,'median_cpu_seconds':statistics.median(cpus) if cpus else None})
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',required=True);p.add_argument('--ablation');p.add_argument('--counts');p.add_argument('--profile');p.add_argument('--cache');p.add_argument('--joint');p.add_argument('--warm-control');p.add_argument('--ablation-counts');p.add_argument('--output',required=True);a=p.parse_args()
    baseline=load(a.baseline);validation=validate(baseline)
    report={'baseline':rows(baseline),'environment':baseline['environment'],'versions':baseline['versions'],'method':baseline['method'],'complete_semantic_comparisons':validation,'budget':baseline['budget'],'source_cases_sha256':baseline['cases_file_sha256'],'raw_trials':[{k:v for k,v in record.items() if k!='rows'}|{'rows':[{k:v for k,v in row.items() if k!='semantic'} for row in record['rows']]} for record in baseline['records']]}
    if a.ablation:
        ablation=load(a.ablation);report['ablation']={'summaries':rows(ablation),'matching_complete_results':validate(ablation,baseline),'note':'Diagnostic removal of generated evidence orchestration only; not product code. Temporal block order may confound wall time. CPU times and background load also reported.'}
    if a.ablation_counts:
        ac=load(a.ablation_counts);report['ablation_counts']={'matching_complete_results':validate(ac,baseline),'runs':[{k:v for k,v in r.items() if k!='rows'} for r in ac['records']]}
    if a.counts:
        counts=load(a.counts);report['counts']={'matching_complete_results':validate(counts,baseline),'runs':[{k:v for k,v in r.items() if k!='rows'}|{'completion':[{'complete':v['complete'],'pending':v['pending']} for v in r['rows']]} for r in counts['records']]}
    if a.profile:
        profiles=load(a.profile);report['profile']={'matching_complete_results':validate(profiles,baseline),'runs':[{k:v for k,v in r.items() if k!='rows'} for r in profiles['records']]}
    if a.warm_control:
        control=load(a.warm_control);report['warm_control']={'summaries':rows(control),'matching_complete_results':validate(control,baseline),'note':'Same process and same input; both revisions enter the existing completed-result public facade. B still reconstructs root marginals. Cold wiring differs from native B, so use this control for reuse eligibility, not native cold attribution.'}
    if a.joint:
        joint=load(a.joint);assert not joint['failures'];entries={}
        for name,row in joint['versions']['new'].items():
            v=row['semantic'];prepared=v['public_and_secret_joint'];law=prepared[0] if v['kind']=='prior' else prepared.get('public_law') if isinstance(prepared,dict) else None
            entries[name]={'kind':v['kind'],'hypotheses_count':len(law['hypotheses']) if law else None,'old_digest':joint['versions']['old'][name]['digest'],'new_digest':row['digest'],'own_observation_compared':v['own_observations'] is not None}
        report['joint_audit']={'cases':entries,'failures':joint['failures'],'raw_summary':str(Path(a.joint))}
    if a.cache:
        audit=load(a.cache);assert not audit['failures'];report['cache_audit']={'cases':audit['cases'],'input_immutability_checked':audit.get('input_immutability_checked',False),'warm_request_count_per_version':audit['warm_request_count_per_version'],'failures':audit['failures'],'pending':{v:{k:row['pending'] for k,row in audit['versions'][v]['fresh'].items() if row['pending']} for v in ('old','new')}}
    for section in ('counts','ablation_counts'):
        for r in report.get(section,{}).get('runs',[]):
            info=r.get('instrumentation',{});calls=info.get('calls',{})
            if info.get('counter_schema')!='eligible_resolution_v2' and 'resolution_replay.miss' in calls:
                calls['resolution_replay.returned_none_including_ineligible']=calls.pop('resolution_replay.miss')
                info['cache_counter_note']='Historical probe counted all None returns; includes non-lookups. Do not interpret as a lookup miss rate. Raw unchanged; final harness separates eligible lookups.'
    from datetime import datetime,timezone,timedelta
    def window(summary,summary_path):
        starts=[];ends=[]
        for record in summary['records']:
            name=f"{record['repetition']:02d}-{record['case']}-{record['version']}-{record['diagnostic']}-{record['experiment']}.json"
            raw=Path(record.get('raw_record_path',str(Path(summary_path).parent/name)))
            if raw.exists():
                end=datetime.fromtimestamp(raw.stat().st_mtime,timezone.utc)
                ends.append(end);starts.append(end-timedelta(seconds=record['subprocess_wall_seconds']))
        return {'approx_start':min(starts).isoformat(),'approx_end':max(ends).isoformat(),'method':'Raw worker file mtime minus subprocess wall; approximate interval, not an exact event log.'} if starts else None
    report['observation_window_utc']=window(baseline,a.baseline)
    if a.warm_control:report['warm_control']['observation_window_utc']=window(control,a.warm_control)
    report['connection_notice']={'reconnected_utc':'2026-10-16T17:43:00Z','primary_completed_before_notice':True,'warm_control_started_after_reconnect':True,'exact_disconnect_start_unknown':True,'no_suspension_outlier_observed':True}
    report['completion_scope']={'public':'Final Forecast/actions/requested by-dawn metrics; nonempty pending_metrics is incomplete.','private-history':'Final win values on legal scan rows; seer dawn is unsupported and compared as None, never claimed computed.','primary_public_pending_metrics_empty':all(not row['semantic']['result'].get('pending_metrics',[]) for record in baseline['records'] if record['view']=='public' for row in record['rows'])}
    assert report['completion_scope']['primary_public_pending_metrics_empty']
    report['proof_normalization']=baseline.get('normalization')
    report['raw_baseline_summary']=baseline.get('raw_summary_path',a.baseline)
    report['power_plan_observation']='AMD Ryzen Balanced; sampled read-only, not changed'
    before=(ROOT/'.artifacts/b-benchmark/formal-harness-before-normalization.py')
    if before.exists():
        import hashlib
        def timed_source(s):
            start=s.index('        start=time.perf_counter();cpu=time.process_time()');end=s.index('        if profile:profile.disable()',start);return s[start:end]
        previous=timed_source(before.read_text(encoding='utf-8'));current=timed_source((ROOT/'benchmarks/board_b_benchmark.py').read_text(encoding='utf-8'))
        assert previous==current
        report['timed_evaluation_sha256']=hashlib.sha256(current.encode()).hexdigest()
        report['final_harness_timed_code_identical']=True
    for r in report.get('profile',{}).get('runs',[]):
        functions=r['profile']['functions'];selected=functions[:30]
        selected.extend(f for f in functions if f not in selected and f['function'] in ('identity','condition_recipe','kernel_snapshot','evidence_key'))
        r['profile']['functions']=selected
        r['profile']['note']='Compact list: top30 self-time and targeted functions; full stats retained in raw profile summary/prof.'
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in report['baseline']:
        print(r['case'],r['version'],r['cache'],r['median_seconds'],[r['min_seconds'],r['max_seconds']],r['censored'])
if __name__=='__main__':main()
