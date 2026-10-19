"""Read-only verification of design evidence and unchanged production hashes."""
import json,hashlib
from pathlib import Path


def verify():
    r=json.loads(Path(__file__).with_name('report-integral-design-results.json').read_text(encoding='utf-8'))
    assert r['production_unchanged']
    for key in ('production_source_sha256','development_source_sha256'):
        for name,digest in r[key].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
    for name in ('study','tests'):
        job=r[name];assert job['returncode']==0 and job['termination'] is None and job['worker']['status']=='verified'
        assert job['limits']['max_work']==250000 and job['limits']['max_seconds']==30
        assert job['worker']['budget']['work']<=250000 and job['worker']['seconds']<30
        assert max(job['peak_private_committed_bytes'],job['observed_peak_working_set_bytes'])<384*1024*1024
    study=r['study']['worker'];assert len(study['cases'])==12 and len(study['complete_five_player_integrals'])==12
    for case in study['cases']:
        assert case['full_joint_oracle_equal'] and case['expanded']==case['contracted']=='1/3'
        probe=case['current_common_index_probe'];assert probe['built_conditional_seer_event_laws']==0
        assert all(i['built_event_laws']==0 for i in probe['indices'])
    for case in study['complete_five_player_integrals']:
        assert case['value']=='7/15' and case['current_full_Forecast_values_equal']
        assert case['named_physical_report_terminal_enumeration']['terminal_executions']>0
    prediction=study['initial_seven_conditional_theorem_prediction']
    assert prediction['value']=='8/35' and prediction['actual_complete_seven_API_obtained'] is False
    assert r['tests']['worker']['tests']==25
    actual=r['last_measured_production_seven_run']['worker']
    assert not actual['forecast_completed'] and actual['value'] is None and actual['reason']=='work'
    return dict(status='verified',production_changed=False,tests=25,terminal_joint_cases=12,complete_five_integrals=12,complete_seven_API=False)

if __name__=='__main__':print(json.dumps(verify()))
