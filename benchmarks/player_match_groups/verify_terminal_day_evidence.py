"""Recheck original complete Forecast/Table from bounded independent shards."""
import json,hashlib
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict
from .cut_out_user_seven_uniform_preparation import comparison_game
from .cut_out_publication_orbit_value_fixture import tables
from werewolf.closed_calculation import ClosedCalculation
from werewolf.board_flow import BoardData
from werewolf.actor_information import PersonalInformation
from werewolf.forecast_result import Forecast
from werewolf.by_dawn import HorizonValues


def verify():
    root=Path(__file__).parent;data=json.loads((root/'terminal-day-analysis.json').read_text(encoding='utf-8'))
    def completed(name):
        r=data['raw_jobs'][name]
        assert r['termination'] is None and r['returncode']==0 and r['worker']['status']=='completed'
        return r['worker']
    c=ClosedCalculation(BoardData.from_game(comparison_game()[1]),grouped=True,aggregate_wolf=True,aggregate_reports=True)
    node=c.root.observe(4)[1];h=next(h for h in node.read().private.hypotheses if h.roles[2]&1)
    seer=node.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1]
    for view,n,masks,prefix in [('public',node,(17,18,33,34,65,66),'wolf-'),('seer',seer,(18,34,66),'seer-roster-')]:
        s=n.read();got=defaultdict(F);value=F()
        want={repr((h.roles,h.acquisitions,h.guards,h.attacks)):h.mass for h in s.private.hypotheses}
        for mask in masks:
            r=completed(f'terminal-day-reference-{prefix}{mask}-scalar.json')
            assert r['cold_complete_source_equal'] and r['observer']==repr(s.observer)
            assert F(r['actual_P_partition_mass'] if view=='seer' else r['conditioning_mass'])==F(1,len(masks))
            for key,mass in r['private_rows']:got[key]+=F(mass)/len(masks)
            value+=F(r['value'])/len(masks)
        assert dict(got)==want
        targets=(1,2,3,5,6,7) if view=='public' else (1,3,5,6,7)
        refs={p:completed(f'terminal-day-reference-{view}-{p}.json') for p in targets}
        dawn=HorizonValues(F(),F());assert all(r['dawn']==repr(dawn) and r['cold_complete_source_equal'] for r in refs.values())
        f=Forecast(value,tuple((p,F(refs[p]['action'])) for p in targets),tuple((p,dawn) for p in targets))
        fast=completed(f'terminal-day-fast-{view}.json')
        assert repr(f)==fast['forecast'] and str(value)==fast['value']
        assert hashlib.sha256(repr(tables(s,f)).encode()).hexdigest()==fast['table_sha256']==data['proof'][view]['table_sha256']
    a=completed('terminal-day-fast-wolf.json');b=completed('terminal-day-reference-wolf.json')
    assert b['cold_complete_source_equal'] and a['forecast']==b['forecast'] and a['table_sha256']==b['table_sha256']
    for row in data['small_independent_regressions']:assert row['data']['worker']['status']=='verified'
    for name,digest in data['source_sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
    return dict(status='verified',views=['public','seer','wolf'],regression_jobs=len(data['small_independent_regressions']))

if __name__=='__main__':print(json.dumps(verify()))
