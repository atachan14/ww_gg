"""Development-only cost attribution and exposed-fake channel experiment.

Never runs a seven-player request or imports a separate evaluator.
"""
from collections import Counter
from contextlib import ExitStack
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch
import json,hashlib,time

from werewolf.calculation_budget import calculation_budget,budget_usage
from werewolf.grouped_forecast import GroupedForecast,GroupedPolicy
from werewolf.exact import Strategy,report_actions
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.board_future import kernel_calculation
from .max_structure_design import calculation


class Census:
    def __init__(self,source):
        self.source=source;self.stack=[];self.work=Counter();self.calls=Counter();self.events=[]
    def wrap(self,name,fn):
        category='report' if name in ('publications','generate_publications','report_outcomes','terminal_report_value','publication_kernel','report_children') else 'acquisition' if name=='acquire' else 'evaluation'
        def measured(*args,**kwargs):
            before=budget_usage()['work'];frame=[0];self.stack.append(frame);self.calls[name]+=1
            event=None
            if name=='act' and args[0]==self.source.public:
                event={'target':args[3],'observer':repr(args[5]),'completed':False,'started_work':before};self.events.append(event)
            try:
                value=fn(*args,**kwargs)
                if event is not None:event.update(completed=True,value=str(value))
                return value
            finally:
                inclusive=budget_usage()['work']-before;self.stack.pop();self.work[category]+=inclusive-frame[0]
                if self.stack:self.stack[-1][0]+=inclusive
                if event is not None:event.update(work=inclusive,finished_work=budget_usage()['work'])
        return measured
    def install(self,stack,e):
        for name in ('solve','act','wolf_policy','acquire','publications','generate_publications','report_outcomes','terminal_report_value','publication_kernel','report_children'):
            if hasattr(e,name):stack.enter_context(patch.object(e,name,self.wrap(name,getattr(e,name))))


def terminal_exposed(payload):
    """Experimental sufficient boundary: next execution terminates, no other report."""
    b,q,past,p,observer=payload
    co=tuple(x for x in b.alive if b.claims[x-1]=='seer')
    return (observer is None and b.phase=='day' and len(b.alive)==3 and set(b.wolf_count_distribution)=={1}
            and not b.initial_hunter_count and len(co)==1 and not b.role_probability(co[0],'seer')
            and not report_actions(b) and any(r.player==co[0] and r.acquired_day==1 for r in past))


class TerminalOnlyExperiment(GroupedPolicy):
    def morning_value(self,payload):
        if terminal_exposed(payload):return self.engine.solve(*payload,physical=payload.physical)
        return super().morning_value(payload)


def exposed():
    from dataclasses import asdict
    from .closed_full_tree_fixture import case
    from werewolf.closed_calculation import ClosedCalculation
    data=case(5,'dual').data
    inputs=[dict(day=1,reporter=1,target=3,color='white'),dict(day=1,reporter=2,target=3,color='black')]
    c=ClosedCalculation(data.updated(policy=asdict(Strategy()),seer_inputs=inputs),grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)
    n=c.root
    for target in (1,3):n=next(r.node for r in n.action(target) if r.node.read().public.winner is None)
    assert terminal_exposed(n.read())
    return c,n


def named_reference(e,source):
    ref=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False)
    ref.retain_joint_guard_history=True
    ref.equivalent_targets=lambda *a:False;ref.actor_equivalent_targets=lambda *a:False
    ref.exchangeable=lambda *a:False;ref.value_law=lambda x:x
    ref.full_renamed_key=lambda *a,**k:None;ref.renamed_value_key=lambda *a,**k:None;ref.scalar_descriptor=lambda *a,**k:None
    return ref


def run():
    rows=[]
    # Each genuinely small complete request has its original shared250000/30s budget.
    for kind in ('single','dual','three','medium-pair'):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=calculation(kind,'baseline','public');e=c._ClosedCalculation__engine;source=n.read();start=budget_usage()['work'];audit=Census(source)
            with ExitStack() as stack:
                audit.install(stack,e);f=n.forecast()
            total=budget_usage()['work']-start;assert sum(audit.work.values())<=total
            rows.append({'kind':kind,'value':str(f.village_win),'complete':True,'forecast_work':total,'setup_work':start,'exclusive_work':dict(audit.work),'outside_wrappers_work':total-sum(audit.work.values()),'calls':dict(audit.calls),'root_action_events':audit.events,'stats':c.stats()})
    experiments=[]
    for mode in ('expanded','moments','terminal-skip'):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c,n=exposed();e=c._ClosedCalculation__engine;s=n.read()
            if mode=='expanded':e=named_reference(e,s)
            if mode=='terminal-skip':e.action_policy=TerminalOnlyExperiment(e)
            start=budget_usage()['work'];audit=Census(s)
            with ExitStack() as stack:
                audit.install(stack,e);value=e.action_policy.morning_value(s)
            experiments.append({'mode':mode,'value':str(value),'work':budget_usage()['work']-start,'exclusive_work':dict(audit.work),'root_action_events':audit.events,'source_preserved':n.read()==s,'cold_equal':n.export_request().roles()==s})
    assert len({r['value'] for r in experiments})==1
    out={'scope':'Development only; four complete five-player public MAX inputs and a terminal-only exposed-fake experiment. No seven run, no nonterminal suppression. Exclusive work categories are disjoint nested budget deltas, not CPU timings. Root action events include scoring/cache/output calls; event work is inclusive and must not be added to exclusive categories.','initial_requests':rows,'terminal_exposed_experiment':experiments,'production_candidate':'NOT ADOPTED: terminal-only sufficient condition does not establish nonterminal history/policy sufficiency.','at':time.time()}
    files=('werewolf/grouped_forecast.py','werewolf/morning_publications.py','werewolf/seer_fake_uniform.py','werewolf/information_set_forecast.py','benchmarks/player_match_groups/exposed_fake_channel.py')
    out['source_sha256']={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in files}
    Path('benchmarks/player_match_groups/exposed-fake-channel-results.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'small':[(r['kind'],r['forecast_work'],r['exclusive_work']) for r in rows],'terminal':experiments}))

if __name__=='__main__':run()
