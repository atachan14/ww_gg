"""Development-only sufficient-history key experiment; complete histories retained."""
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from dataclasses import asdict
from fractions import Fraction as F
import json,hashlib
from werewolf.calculation_budget import calculation_budget,budget_usage,tick
from werewolf.board_future import kernel_calculation
from werewolf.closed_calculation import ClosedCalculation
from werewolf.exact import Strategy
from werewolf.group_partition import _frame_groups
from .closed_full_tree_fixture import case
from .max_structure_design import calculation
from .exposed_fake_channel import Census,named_reference
from .cut_out_publication_orbit_value_fixture import forecast,tables


def history_summary(board,q,past):
    """Only one always-fake live CO; every other live CO always true in full Q.

    All initial declarations, other actors' records and complete Q/P are retained.
    Future reports remain generated. This changes DEVELOPMENT scalar keys only.
    """
    co=tuple(p for p in board.alive if board.claims[p-1]=='seer')
    false_sets={tuple(p for p in co if not h.roles[2]&(1<<(p-1))) for h in q.hypotheses}
    if len(false_sets)!=1:return None
    fake=next(iter(false_sets))
    if len(fake)!=1:return None
    actor=fake[0];own=tuple(r for r in past if r.player==actor)
    initial=tuple(r for r in own if r.acquired_day==1)
    if q.initial_rule!='none' and not initial:return None
    return ('one-known-fake',actor,initial,tuple(sorted({r.target for r in own})),
            tuple(sorted({r.acquired_day for r in own})),tuple(r for r in past if r.player!=actor))


def calculation_key(e,name,args,kwargs):
    b,q,past=args[:3];summary=history_summary(b,q,past)
    if not e.max_grouped or summary is None:return None
    observer=args[5] if name=='act' else args[4]
    target=args[3] if name=='act' else None
    groups=_frame_groups(e.groups,b,past,observer,target=target)
    return (name,*args[:2],summary,*args[3:],tuple(sorted(kwargs.items())),groups)


class ScalarKeyExperiment:
    def __init__(self,e):self.engine=e;self.cache={};self.stats=Counter();self.keys={}
    def install(self,stack):
        for name in ('solve','act'):
            original=getattr(self.engine,name)
            def wrapper(*args,_name=name,_original=original,**kwargs):
                key=calculation_key(self.engine,_name,args,kwargs)
                if key is None:return _original(*args,**kwargs)
                full=(_name,args,tuple(sorted(kwargs.items())),key[-1])
                self.keys.setdefault(key,set()).add(full);self.stats['eligible_calls']+=1
                if key in self.cache:
                    tick(0);self.stats['hits']+=1;return self.cache[key]
                value=_original(*args,**kwargs);self.cache[key]=value;self.stats['builds']+=1;return value
            stack.enter_context(patch.object(self.engine,name,wrapper))
    def counts(self):return {**self.stats,'summary_keys':len(self.keys),'full_keys':sum(len(v) for v in self.keys.values()),'distinct_full_aliases':sum(len(v)-1 for v in self.keys.values())}


def small_six():
    # Independently defined SIX-player input. No seven origin or subproblem.
    data=case(6,'dual').data.updated(policy=asdict(Strategy()),seer_inputs=[
        dict(day=1,reporter=1,target=3,color='white'),dict(day=1,reporter=2,target=3,color='black')])
    c=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)
    n=c.root
    for target in (3,4):n=next(r.node for r in n.action(target) if r.node.read().public.winner is None)
    return c,n


def audit_six():
    with calculation_budget(250000,max_seconds=30),kernel_calculation():
        c,n=small_six();source=n.read();e=c._ClosedCalculation__engine
        rows=n.reports();buckets={}
        from werewolf.actor_information import PersonalInformation,WolfInformation
        for row in rows:
            s=row.node.read();h=s.private.hypotheses[0]
            views=(('public',row.node),('seer',row.node.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1]),('wolf',row.node.personal(WolfInformation.from_hypothesis(h))[1]))
            for view,node in views:
                own=node.read();k=(view,own.public,own.public_state,history_summary(own.public,own.public_state,own.past),own.private,own.observer,own.physical,node.groups)
                buckets.setdefault(k,[]).append(node)
        checked=0
        for bucket in buckets.values():
            first=None;initial=None
            for node in bucket:
                s=node.read();ref=named_reference(e,s);f=forecast(ref,s)
                if first is None:first=f;initial=tables(s,f)
                assert f==first and tables(s,f)==initial
                assert node.export_request().roles()==s
                checked+=1
        assert n.read()==source
        return {'report_rows':len(rows),'views':3,'summary_buckets':len(buckets),'bucket_sizes':dict(Counter(map(len,buckets.values()))),'independent_Forecast_Table_cold_checks':checked,'complete':True,'value':'1','note':'Complete six-origin four-alive report children; full Q/P, observer, physical and group keys retained. Known wolf makes this a certain-win example.'}


def run():
    rows=[]
    for kind in ('single','dual','three','medium-pair'):
        for mode in ('baseline','summary-key'):
            with calculation_budget(250000,max_seconds=30),kernel_calculation():
                c,n=calculation(kind,'baseline','public');e=c._ClosedCalculation__engine;exp=ScalarKeyExperiment(e);a=Census(n.read());before=budget_usage()['work']
                with ExitStack() as stack:
                    if mode=='summary-key':exp.install(stack)
                    a.install(stack,e);f=n.forecast()
                rows.append({'kind':kind,'mode':mode,'forecast':repr(f),'work':budget_usage()['work']-before,'exclusive_work':dict(a.work),'keys':exp.counts(),'complete':True})
    for i in range(0,len(rows),2):assert rows[i]['forecast']==rows[i+1]['forecast']
    six=[]
    for mode in ('baseline','summary-key'):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=small_six();e=c._ClosedCalculation__engine;exp=ScalarKeyExperiment(e);a=Census(n.read());before=budget_usage()['work']
            with ExitStack() as stack:
                if mode=='summary-key':exp.install(stack)
                a.install(stack,e);value=e.action_policy.morning_value(n.read())
            six.append({'mode':mode,'value':str(value),'work':budget_usage()['work']-before,'exclusive_work':dict(a.work),'keys':exp.counts(),'complete':True})
    assert six[0]['value']==six[1]['value']
    out={'scope':'DEVELOPMENT only, scalar result keys. All reports and full source/history remain generated. Four independent five-player MAX requests in two modes and an independent six-player report frame. No seven request/sharding, no production connection.','five':rows,'six':six,'six_independent_audit':audit_six(),'source_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('benchmarks/player_match_groups/report_history_summary.py','werewolf/seer_fake_uniform.py','werewolf/morning_publications.py','werewolf/grouped_forecast.py','werewolf/information_set_forecast.py')}}
    Path('benchmarks/player_match_groups/report-history-summary-results.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'five':[(r['kind'],r['mode'],r['work'],r['keys']) for r in rows],'six':six,'audit':out['six_independent_audit']}))

if __name__=='__main__':run()
