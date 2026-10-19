"""Read-only check of exact scalar reuse, frozen cold evidence and stop scope."""
import json,hashlib
from pathlib import Path


def verify():
    p=Path(__file__).with_name('terminal-scalar-key-analysis.json');r=json.loads(p.read_text(encoding='utf-8'))
    a=r['completed_equal_branch']['before'];b=r['completed_equal_branch']['after']
    for job in (a,b):
        assert job['termination'] is None and job['returncode']==0 and job['worker']['status']=='verified'
        assert job['worker']['six_child_scalar_cached_without_reexpansion']
        assert job['worker']['forced_and_observed_six_joint_equal']
    assert a['worker']['value']==b['worker']['value']=='2/15'
    for key in ('actions','acquired','mornings','publications','policies','target_orbits','report_vectors'):
        assert a['worker']['states'][key]==b['worker']['states'][key]
    assert b['worker']['states']['values']<a['worker']['states']['values']
    assert b['worker']['budget']['work']<a['worker']['budget']['work']
    for view,row in r['six_complete_verification'].items():
        new=row['new_complete_job'];old=row['old_complete_job']
        assert new['termination'] is None and new['returncode']==0
        assert new['worker']['status']=='completed'
        assert new['worker']['forecast']==old['worker']['forecast']
        assert new['worker']['table_sha256']==old['worker']['table_sha256']==row['prior_proof']['table_sha256']
    job=r['seven_uninstrumented_after'];w=job['worker']
    assert job['termination'] is None and job['returncode']==0
    assert w['status']=='budget_stopped' and w['reason']=='work' and w['value'] is None and not w['forecast_completed']
    assert w['stages']==[dict(kind='solve',completed=False)]
    for job in [a,b,r['heavy_branch'],r['seven_uninstrumented_before'],r['seven_uninstrumented_after']]:
        assert job['limits']['max_work']==250000 and job['limits']['max_seconds']==30
        assert max(job['peak_private_committed_bytes'],job['observed_peak_working_set_bytes'])<384*1024*1024
    assert r['regression']['tests']==87
    for job in r['regression_jobs']:assert job['data']['worker']['status']=='verified'
    for name,digest in r['source_sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
    return dict(status='verified',complete_six_views=['public','seer','wolf'],regression_jobs=len(r['regression_jobs']),complete_seven=False)

if __name__=='__main__':print(json.dumps(verify()))
