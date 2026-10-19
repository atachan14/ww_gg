"""Exhaustive development tree: common transitions, independent terminal sum."""
import json,sys,time,hashlib
from pathlib import Path
from types import SimpleNamespace
from fractions import Fraction as F
from collections import Counter
from .initial_seven_entry_probe import watch,LIMITS
from .cut_out_publication_orbit_value_fixture import make_role_filter_scope,forecast,tables
from .cut_out_compact_terminal_fixture import independent_cold
from .cut_out_uniform_game_fixture import peak_bytes
from werewolf.closed_calculation import ClosedCalculation
from werewolf.board_flow import BoardData
from werewolf.board_future import kernel_calculation
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.actor_information import PersonalInformation,WolfInformation
from werewolf.calculation_budget import calculation_budget,budget_usage,CalculationBudgetExceeded,tick
from werewolf.exact import legal_targets,Strategy


def case(n,kind):
    base=make_role_filter_scope().graph;game=base.data.to_game();game.pop('public_log',None)
    claims=['seer']+['latent']*(n-1);inputs=[dict(day=1,reporter=1,target=3,color='white')]
    if kind=='dual':
        claims[1]='seer';inputs.append(dict(day=1,reporter=2,target=3,color='white'))
    if kind=='three':
        claims[:3]=['seer']*3;inputs=[dict(day=1,reporter=p,target=4,color='white') for p in (1,2,3)]
    if kind=='medium':claims[2]='medium'
    if kind=='medium-pair':
        claims[1]=claims[2]='medium';inputs=[dict(day=1,reporter=1,target=4,color='white')]
    game.update(players=n,seers=2 if kind=='three' else 1,mediums=int(kind in ('medium','medium-pair')),claims=claims,seer_inputs=inputs)
    return SimpleNamespace(data=BoardData.from_game(game),engine=base.engine)


def tree(graph,left,right,root_target=None):
    counts=Counter();memo={};cold_seen=set();phase=Counter();mass_checks=0;root_source=right.read()
    def same(a,b):
        assert a.read()==b.read();s=b.read();counts['named_source_comparisons']+=1
        if s in cold_seen:return
        cold=independent_cold(graph,b.export_request());assert cold==s;cold_seen.add(s)
        assert s.public_state.public_roles==tuple(sorted(s.public.worlds))
        assert sum((h.mass for h in s.private.hypotheses),F())==1
        counts['cold_joint_sources']+=1
    def visit(a,b):
        nonlocal mass_checks
        tick();s=b.read()
        if s in memo:return memo[s]
        same(a,b);phase[(len(s.public.alive),s.public.phase)]+=1
        if s.public.winner is not None:
            counts['terminal']+=1;return F(s.public.winner=='village')
        e=b._Node__calculation._ClosedCalculation__engine
        counts['nonterminal']+=1
        if s.public.phase=='day':
            targets=legal_targets(s.physical,e.rules,e.strategy)
            choices=[(F(1,len(targets)),a,b,target) for target in targets]
        else:
            ac=a.wolf_choices();bc=b.wolf_choices();assert len(ac)==len(bc)
            assert sum((r.mass for r in bc),F())==1;mass_checks+=1;choices=[]
            for u,v in zip(ac,bc):
                assert (u.information,u.mass,u.target)==(v.information,v.mass,v.target)
                same(u.node,v.node);choices.append((v.mass,u.node,v.node,v.target))
        value=F()
        if s==root_source and root_target is not None:choices=[r for r in choices if r[3]==root_target]
        for weight,u,v,target in choices:
            ar=u.action(target);br=v.action(target);assert len(ar)==len(br)
            assert sum((r.probability for r in br),F())==1;mass_checks+=1
            for x,y in zip(ar,br):
                counts['action_edges']+=1;assert x.probability==y.probability;same(x.node,y.node)
                child=y.node.read()
                if s.public.phase=='night' and child.public.winner is None:
                    ap=x.node.reports();bp=y.node.reports();assert len(ap)==len(bp)
                    assert sum((r.probability for r in bp),F())==1;mass_checks+=1
                    subtotal=F()
                    for p,q in zip(ap,bp):
                        assert (p.public_probability,p.probability)==(q.public_probability,q.probability)
                        counts['report_edges']+=1;same(p.node,q.node)
                        subtotal+=q.probability*visit(p.node,q.node)
                else:subtotal=visit(x.node,y.node)
                value+=weight*y.probability*subtotal
        memo[s]=value;return value
    value=visit(left,right)
    return value,dict(counts),{str(k):v for k,v in phase.items()},mass_checks


def worker(n,kind,selected_view,part):
    def mark(stage):print(json.dumps(dict(progress_stage=stage)),flush=True)
    start=time.perf_counter();result=dict(players=n,kind=kind,selected_view=selected_view,part=part,status='running');mark('setup')
    try:
        with calculation_budget(LIMITS['max_work'],max_seconds=LIMITS['max_seconds']):
            graph=case(n+1 if kind in ('night','known-night','mixed-night') else n,'dual' if kind=='mixed-night' else 'single' if kind in ('night','known-night','original') else kind)
            if kind in ('known-night','mixed-night'):
                game=graph.data.to_game();game['wolves']=2
                if kind=='known-night':
                    game['claims']=['seer','wolf','wolf']+['latent']*(n-2);game['seer_inputs']=[dict(day=1,reporter=1,target=4,color='white')]
                graph=SimpleNamespace(data=BoardData.from_game(game),engine=graph.engine)
            if kind=='original':
                from .cut_out_user_seven_uniform_preparation import comparison_game
                graph=SimpleNamespace(data=BoardData.from_game(comparison_game()[1]),engine=graph.engine)
            plain=ClosedCalculation(graph.data,max_work=LIMITS['max_work'],max_seconds=LIMITS['max_seconds'])
            fast=ClosedCalculation(graph.data,grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=LIMITS['max_work'],max_seconds=LIMITS['max_seconds'])
            left=plain.root;right=fast.root
            if kind in ('night','original','known-night','mixed-night'):
                target=6 if kind=='mixed-night' else 4 if kind in ('original','known-night') else 3
                p,left=left.observe(target);q,right=right.observe(target);assert p==q
            result['entry']=dict(alive=right.read().public.alive,phase=right.read().public.phase,day=right.read().public.day,wolf_counts=tuple(right.read().public.wolf_count_distribution),initial_wolf_masks=tuple(sorted({h.roles[0] for h in right.read().public_state.hypotheses})))
            views=[('public',left,right,F(1))]
            h=next(h for h in right.read().private.hypotheses if h.roles[2]&1)
            infos=[('seer',PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1))),('wolf',WolfInformation.from_hypothesis(h))]
            if kind=='medium-pair':infos.append(('medium',PersonalInformation(2,'medium')))
            for name,info in infos:
                p,a=left.personal(info);q,b=right.personal(info);assert p==q
                views.append((name,a,b,p))
            results=[];result['views']=results;result['forecasts']=[]
            for name,a,b,mass in views:
                if name!=selected_view:continue
                mark('Forecast_Table_'+name if part in ('all','forecast','fast') else 'root_target_'+part+'_'+name);cold=independent_cold(graph,b.export_request());assert a.read()==b.read()==cold
                e=InformationSetForecast(graph.data.game_data.rules,Strategy(**graph.data.to_game()['policy']),max_work=LIMITS['max_work'],exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
                if part=='fast':
                    got=b.forecast();result['forecasts'].append(dict(view=name,village_win=str(got.village_win),actions=[(p,str(v)) for p,v in got.action_values],forecast_counts=dict(grouped=fast.stats()),expanded_cold_Forecast_Table_equal=False,table_digest=hashlib.sha256(repr(tables(b.read(),got)).encode()).hexdigest()))
                    continue
                if part in ('all','forecast'):
                    want=a.forecast();got=b.forecast()
                    with kernel_calculation():other=forecast(e,cold)
                    assert want==got==other and tables(a.read(),want)==tables(b.read(),got)==tables(cold,other)
                    forecast_counts=dict(expanded=plain.stats(),grouped=fast.stats())
                    result['forecasts'].append(dict(view=name,village_win=str(got.village_win),actions=[(p,str(v)) for p,v in got.action_values],forecast_counts=forecast_counts,expanded_cold_Forecast_Table_equal=True))
                    if part=='forecast':continue
                mark('all_transitions_'+name)
                expected,counts,phases,masses=tree(graph,a,b,int(part) if part not in ('all','forecast') else None)
                if part=='all':assert expected==got.village_win
                results.append(dict(view=name,conditioning_mass=str(mass),expected_contribution=str(expected),counts=counts,phases=phases,mass_checks=masses,expanded_cold_joint_sources_equal=True))
            result.update(status='completed_without_full_reference' if part=='fast' else 'verified',views=results,expanded=plain.stats(),grouped=fast.stats(),budget=budget_usage())
    except CalculationBudgetExceeded as error:result.update(status='budget_stopped',reason=error.kind)
    except Pending as error:result.update(status='pending',reason=error.reason)
    from werewolf.calculation_budget import budget_stop
    result['budget_stop']=budget_stop()
    if 'plain' in locals():result['expanded']=plain.stats()
    if 'fast' in locals():result['grouped']=fast.stats()
    result.update(seconds=time.perf_counter()-start,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def run(n,kind,selected_view,part='all'):
    result=watch('benchmarks.player_match_groups.closed_full_tree_fixture',('worker',str(n),kind,selected_view,part))
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/closed_calculation.py','werewolf/grouped_forecast.py','werewolf/morning_publications.py','benchmarks/player_match_groups/closed_full_tree_fixture.py'))}
    Path(f'benchmarks/player_match_groups/closed-full-tree-{n}-{kind}-{selected_view}{'-'+part if part!='all' else ''}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(int(sys.argv[2]),sys.argv[3],sys.argv[4],sys.argv[5])
    else:
        result=run(int(sys.argv[1]),sys.argv[2],sys.argv[3] if len(sys.argv)>3 else 'public',sys.argv[4] if len(sys.argv)>4 else 'all');print(json.dumps(result))
