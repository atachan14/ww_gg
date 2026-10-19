"""Current-source check of native complete APIs and bounded old references."""
import json,hashlib
from pathlib import Path
from fractions import Fraction as F
from types import SimpleNamespace
from .cut_out_user_seven_uniform_preparation import comparison_game
from .cut_out_publication_orbit_value_fixture import tables
from .cut_out_compact_terminal_fixture import independent_cold
from .closed_full_tree_fixture import case
from werewolf.closed_calculation import ClosedCalculation
from werewolf.board_flow import BoardData
from werewolf.actor_information import PersonalInformation,WolfInformation
from werewolf.forecast_result import Forecast
from werewolf.by_dawn import HorizonValues


def verify():
    r=json.loads(Path(__file__).with_name('report-integral-integration-results.json').read_text(encoding='utf-8'))
    raw=r['raw_measurements'];assert len(raw)==32
    for name,job in raw.items():
        assert job['returncode']==0 and job['termination'] is None,name
        assert job['limits']['max_work']==250000 and job['limits']['max_seconds']==30
        assert max(job['peak_private_committed_bytes'],job['observed_peak_working_set_bytes'])<384*1024*1024
        if not name.startswith('report-integral-expanded-seven-'):
            assert job['worker']['completed'] and job['worker']['budget']['work']<=250000 and job['worker']['seconds']<30,name
    for view in ('public','seer','wolf'):
        actual=raw[f'report-integral-integrated-seven-{view}.json']['worker']
        c=ClosedCalculation(BoardData.from_game(comparison_game()[1]),grouped=True,aggregate_wolf=True,aggregate_reports=True);n=c.root
        if view!='public':
            h=next(h for h in n.read().private.hypotheses if h.roles[2]&1)
            _,n=n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)) if view=='seer' else WolfInformation.from_hypothesis(h))
        s=n.read();digest=hashlib.sha256(repr(s).encode()).hexdigest();assert digest==actual['source_sha256']
        graph=SimpleNamespace(data=c.data,engine=case(5,'single').engine);assert independent_cold(graph,n.export_request())==s
        refs={p:raw[f'report-integral-expanded-branch-{view}-{p}.json']['worker'] for p in range(1,8)}
        zero=HorizonValues(F(),F())
        assert all(w['completed'] and w['source_sha256']==digest and w['dawn']==repr(zero) for w in refs.values())
        columns=tuple((p,F(w['value'])) for p,w in refs.items())
        expected=Forecast(sum((v for p,v in columns),F())/7,columns,tuple((p,zero) for p in refs))
        assert repr(expected)==actual['forecast'] and str(expected.village_win)==actual['value']=='8/35'
        assert hashlib.sha256(repr(tables(s,expected)).encode()).hexdigest()==actual['table_sha256']==r['comparison'][view]['table_sha256']
        six=raw[f'report-integral-integrated-six-{view}.json']['worker'];old=r['prior_six_native'][view]['worker']
        assert six['completed'] and six['forecast']==old['forecast'] and six['table_sha256']==old['table_sha256']==r['prior_six_independent_cold_evidence'][view]['table_sha256']
    a=raw['report-integral-expanded-branch-public-4.json']['worker'];b=raw['report-integral-integrated-branch-public-4.json']['worker']
    assert a['source_sha256']==b['source_sha256'] and a['value']==b['value']=='2/15' and a['dawn']==b['dawn']
    for key in ('actions','acquired','policies','resolution_cache','target_orbits'):assert a['states'][key]==b['states'][key]
    assert b['budget']['work']<a['budget']['work']
    local=raw['report-integral-integrated-local-public.json']['worker'];old=raw['report-integral-expanded-local-public.json']['worker']
    assert local['source_sha256']==old['source_sha256'] and local['value']==old['value']=='1/3'
    assert local['states']['report_vectors']['public_event_laws']==0 and old['states']['report_vectors']['fallback_public_vectors']==109
    assert r['regressions']['tests']==107 and len(r['regression_jobs'])==37
    for row in r['regression_jobs']:assert row['data']['worker']['status']=='verified'
    for name,digest in r['source_sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
    return dict(status='verified',native_complete_seven_views=['public','seer','wolf'],native_complete_six_views=['public','seer','wolf'],complete_expanded_named_references=21,tests=107)

if __name__=='__main__':print(json.dumps(verify()))
