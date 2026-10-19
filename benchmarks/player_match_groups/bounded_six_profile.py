"""Development-only bounded profile: no production counters/proof ledger."""
import json,sys,time,hashlib
from pathlib import Path
from collections import Counter,defaultdict
from contextlib import ExitStack
from unittest.mock import patch
from .initial_seven_entry_probe import watch,LIMITS


class Census:
    def __init__(self,e):
        self.e=e;self.stack=[];self.last=time.perf_counter();self.last_work=0
        self.seconds=Counter();self.work=Counter();self.calls=Counter();self.hits=Counter();self.rows=Counter();self.depth=0
        self.depths=Counter();self.exact=set();self.public=set();self.private=set();self.role_public=set();self.colorless=set();self.known={};self.laws=set();self.law_requests=0
        self.depth_keys=defaultdict(set);self.stages=[];self.current_stage=None
    def used(self):
        from werewolf.calculation_budget import budget_usage
        r=budget_usage();return r['work'] if r else 0
    def charge(self):
        now=time.perf_counter();work=self.used()
        if self.stack:self.seconds[self.stack[-1]]+=now-self.last;self.work[self.stack[-1]]+=max(0,work-self.last_work)
        self.last=now;self.last_work=work
    def wrapper(self,name,original):
        def call(*args,**kwargs):
            self.charge();top=not self.stack;self.stack.append(name);self.calls[name]+=1
            before=dict(self.e.expansions) if name in ('solve','act') else None
            if name=='solve':
                b,s,past,private,observer=args[:5];self.depth+=1
                phase=(self.depth,b.day,b.phase,len(b.alive));self.depths[phase]+=1
                key=(b,s,past,private,observer);self.exact.add(key);self.depth_keys[phase].add(key)
                self.public.add((b,s,past));self.private.add((private,observer));self.role_public.add((b.alive,b.phase,b.history,tuple(sorted(b.worlds))))
                source=(b,s)
                if source not in self.known:
                    mask=0
                    for h in s.hypotheses:mask|=h.roles[2]
                    self.known[source]=frozenset(p for p in b.alive if b.claims[p-1]=='seer' and not mask&(1<<(p-1)))
                fake=self.known[source]
                coarse=tuple((r.acquired_day,r.published_day,r.player,r.target,None if r.player in fake else r.color) for r in past)
                self.colorless.add((b,s,coarse,private,observer))
                self.rows['solve_public_hypotheses']+=len(s.hypotheses);self.rows['solve_private_hypotheses']+=len(private.hypotheses)
            if name=='value_law':self.law_requests+=1;self.laws.add(args[0])
            if top and name in ('solve','act','horizon'):
                target=args[3] if name=='act' else args[4] if name=='horizon' else None
                self.current_stage=dict(kind=name,target=target,completed=False);self.stages.append(self.current_stage)
            stage=self.current_stage if top else None
            try:
                out=original(*args,**kwargs)
                if name in ('solve','act') and self.e.expansions['values' if name=='solve' else 'actions']==before['values' if name=='solve' else 'actions']:self.hits[name]+=1
                if name in ('future_publications','compiled_representatives') and isinstance(out,tuple):
                    self.rows[name]+=len(out);self.rows[name+'_hypotheses']+=sum(len(r.state.hypotheses) for r in out)
                if name=='push':self.rows['positive_P_rows']+=len(out)
                if name=='morning':self.rows['public_Q_rows']+=len(out)
                if name=='wolf_cells':self.rows['wolf_cells']+=len(out)
                if name=='value_law' and out is not args[0]:self.rows['value_law_rebuilt_or_cached_transform']+=1
                if stage is not None:
                    stage['completed']=True
                    if name=='solve':stage['completed_scalar']=str(out)
                return out
            finally:
                if name=='solve':self.depth-=1
                self.charge();self.stack.pop()
        return call
    def result(self):
        total=sum(self.seconds.values())
        return dict(calls=dict(self.calls),cache_hit_or_terminal_calls=dict(self.hits),exclusive_seconds=dict(self.seconds),exclusive_fraction={k:v/total for k,v in self.seconds.items()},exclusive_counted_work=dict(self.work),rows=dict(self.rows),solve_depths=[dict(depth=k[0],day=k[1],phase=k[2],alive=k[3],calls=n,distinct_full_inputs=len(self.depth_keys[k])) for k,n in sorted(self.depths.items())],distinct=dict(full_solve_inputs=len(self.exact),public_complete_inputs=len(self.public),private_complete_inputs=len(self.private),public_role_projection_only=len(self.role_public),same_full_inputs_repeated=self.calls['solve']-len(self.exact),known_fake_color_omitted_diagnostic_only=len(self.colorless),value_law_requests=self.law_requests,value_law_distinct_complete_inputs=len(self.laws),value_law_same_input_repeats=self.law_requests-len(self.laws)),top_stages=self.stages)


def worker():
    from .cut_out_user_seven_uniform_preparation import comparison_game
    from .cut_out_uniform_game_fixture import peak_bytes
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.board_flow import BoardData
    from werewolf.calculation_budget import calculation_budget,budget_stop,budget_usage,CalculationBudgetExceeded
    from werewolf.information_set_forecast import Pending
    import werewolf.information_set_forecast as info
    import werewolf.morning_publications as reports
    import werewolf.closed_calculation as closed
    started=time.perf_counter();result=dict(forecast_completed=False,value=None);c=None;profile=None
    try:
        with calculation_budget(LIMITS['max_work'],max_seconds=LIMITS['max_seconds']):
            c=ClosedCalculation(BoardData.from_game(comparison_game()[1]),grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=LIMITS['max_work'],max_seconds=LIMITS['max_seconds'])
            node=c.root.observe(4)[1];e=c._ClosedCalculation__engine;profile=Census(e)
            with ExitStack() as stack:
                for name in ('solve','act','value_law','morning','push','wolf_cells','wolf_policy','acquire','public_children','physical_children'):
                    stack.enter_context(patch.object(e,name,profile.wrapper(name,getattr(e,name))))
                for name in ('acquire','project'):
                    stack.enter_context(patch.object(e.action_policy,name,profile.wrapper('flow_'+name,getattr(e.action_policy,name))))
                for owner,name,label in ((info,'future_publications','future_publications'),(reports.CompiledPublications,'representatives','compiled_representatives'),(info,'normalize','value_key_normalize'),(closed,'horizon_for_action','horizon')):
                    stack.enter_context(patch.object(owner,name,profile.wrapper(label,getattr(owner,name))))
                print(json.dumps(dict(progress_stage='bounded_instrumented_forecast')),flush=True)
                out=node.forecast();result.update(forecast_completed=True,value=str(out.village_win))
            result['budget']=budget_usage()
    except CalculationBudgetExceeded as error:result.update(status='budget_stopped',reason=error.kind)
    except Pending as error:result.update(status='pending',reason=error.reason)
    result['budget_stop']=budget_stop();result['seconds']=time.perf_counter()-started
    if c is not None:result['states']=c.stats()
    if profile is not None:result['profile']=profile.result()
    result['peak_working_set_bytes']=peak_bytes();result['notes']=['Exclusive timing/counts include development instrumentation overhead; fractions describe this bounded prefix, not an unmeasured complete run.','Projection-only/color-omitted counts are diagnostics, not evidence that those branches may be merged. Complete histories, P/Q and policy may differ.','Cached calls are not repeated expansions; value_law is a pure helper and repeats are counted separately.']
    print(json.dumps(result),flush=True)


def run(label):
    result=watch('benchmarks.player_match_groups.bounded_six_profile',('worker',))
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/information_set_forecast.py','werewolf/grouped_forecast.py','werewolf/morning_publications.py','werewolf/closed_calculation.py','benchmarks/player_match_groups/bounded_six_profile.py'))}
    Path(f'benchmarks/player_match_groups/bounded-six-profile-{label}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker()
    else:
        r=run(sys.argv[1]);print(json.dumps(r))
