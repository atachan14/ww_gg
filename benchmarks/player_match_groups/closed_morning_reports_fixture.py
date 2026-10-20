"""Small simultaneous-report partition audit; enumeration stays in development."""
import json
from pathlib import Path
from types import SimpleNamespace
from fractions import Fraction as F
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.board_future import SavedOrigin,kernel_calculation,same_role_board
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.actor_information import PersonalInformation
from werewolf.exact import Strategy,MediumReport
from werewolf.seer_acquisition import SeerReport
from .closed_saved_day_fixture import saved_day
from .cut_out_publication_orbit_value_fixture import make_role_filter_scope,forecast,tables
from .cut_out_compact_terminal_fixture import independent_cold
from .cut_out_joint_night_forecast_fixture import moved_source


def case(n):
    base=make_role_filter_scope().graph;g=base.data.to_game();g.pop('public_log',None)
    count=2 if n==5 else 3
    g.update(players=n,seers=count-1,claims=['seer']*count+['latent']*(n-count),seer_inputs=[dict(day=1,reporter=p,target=3 if n==5 else 5,color='white') for p in range(1,count+1)])
    data=BoardData.from_game(g)
    return SimpleNamespace(data=data,engine=base.engine),(4,5 if n==5 else 6)


def report_vector(n,asymmetric=False):
    return tuple(SeerReport(2,2,p,1 if asymmetric and p==3 else (5 if n==5 else 6),'white') for p in range(1,3 if n==5 else 4))


def outputs(node,reference,data):
    e=InformationSetForecast(data.game_data.rules,Strategy(**data.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False)
    e.retain_joint_guard_history=True
    with kernel_calculation():want=forecast(e,reference)
    got=node.forecast();assert got==want and tables(node.read(),got)==tables(reference,want)
    h=next(h for h in node.read().private.hypotheses if h.roles[2]&1)
    info=PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1))
    mass,own=node.personal(info)
    with kernel_calculation():other_mass,other=e.personal_view(reference,info);want=forecast(e,other)
    assert mass==other_mass and own.read().private.hypotheses==other.private.hypotheses
    assert own.forecast()==want and tables(own.read(),want)==tables(other,want)


def check_groups(node):
    s=node.read();count=0
    for group in node.groups:
        for player in group[1:]:
            permutation=list(range(1,s.public.player_count+1));permutation[group[0]-1],permutation[player-1]=player,group[0]
            other=moved_source(s,tuple(permutation))
            assert same_role_board(s.public,other.public) and same_role_board(s.physical,other.physical)
            assert (s.public_state,s.private,s.past)==(other.public_state,other.private,other.past);count+=1
    return count


def medium_audit():
    base=make_role_filter_scope().graph;g=base.data.to_game();g.pop('public_log',None)
    g.update(players=6,mediums=1,claims=['seer','medium','medium','latent','latent','latent'],seer_inputs=[dict(day=1,reporter=1,target=4,color='white')])
    initial=BoardData.from_game(g);graph=SimpleNamespace(data=initial,engine=base.engine)
    node=ClosedCalculation(initial).root;data=initial
    for target in (4,6):node=node.observe(target)[1];data=saved_day(data,target)
    rows=[]
    for target in (5,2):
        seer=(SeerReport(2,2,1,target,'white'),)
        medium=(MediumReport(2,2,4,'white'),MediumReport(2,3,4,'white'))
        selected=next(r for r in node.reports() if tuple(x for x in r.node.read().past if x.acquired_day==2)==seer and r.node.read().public.reports==medium)
        cold=independent_cold(graph,selected.node.export_request());assert cold==selected.node.read()
        outputs(selected.node,cold,initial);count=check_groups(selected.node)
        mass,observed=node.observe_reports(seer,medium)
        assert independent_cold(graph,observed.export_request())==observed.read()
        current=data.updated(seer_inputs=g['seer_inputs']+[dict(day=2,reporter=1,target=target,color='white')],reports=[dict(day=r.day,reporter=r.reporter,target=r.target,color=r.color) for r in medium])
        reopened=ClosedCalculation(current);assert reopened.root.read()==observed.read()
        reference=SavedOrigin(current,initial.game_data.rules,Strategy(**g['policy']),False)()
        assert (reference.public,reference.physical,reference.past)==(observed.read().public,observed.read().physical,observed.read().past)
        assert reference.public_state.hypotheses==observed.read().public_state.hypotheses and reference.private.hypotheses==observed.read().private.hypotheses
        outputs(observed,reference,initial);count+=check_groups(observed)
        assert ((2,3) in selected.node.groups)==(target==5)
        rows.append(dict(seer_target=target,groups=selected.node.groups,generated_public_probability=str(selected.public_probability),generated_actual_probability=str(selected.probability),observed_truth_support_mass=str(mass),cold_named_public_owner_equal=True,independent_group_generators=count))
    return rows


def audit():
    results=[]
    for n,asymmetric in ((5,False),(6,False),(6,True)):
        graph,targets=case(n);calc=ClosedCalculation(graph.data);node=calc.root;data=graph.data;path=F(1);action_masses=[]
        for t in targets:
            if node.read().public.phase=='night':
                choices=[c for c in node.wolf_choices() if c.target==t]
                choice_mass=sum((c.mass for c in choices),F())
                physical_mass=sum((c.mass*r.probability for c in choices for r in c.node.action(t) if r.node.read().public.winner is None),F())
            else:
                choice_mass=F(1,len(node.read().public.alive))
                physical_mass=choice_mass*sum((r.probability for r in node.action(t) if r.node.read().public.winner is None),F())
            mass,node=node.observe(t);assert mass==physical_mass
            action_masses.append(dict(target=t,actual_choice_mass=str(choice_mass),physical_continuation_given_choice=str(physical_mass/choice_mass),observed_action_mass=str(mass)))
            path*=mass;data=saved_day(data,t)
        desired=report_vector(n,asymmetric);branches=node.reports()
        assert sum((r.probability for r in branches),F())==1
        assert sum((r.public_probability for r in branches),F())==1
        selected=next(r for r in branches if tuple(r for r in r.node.read().past if r.acquired_day==2)==desired)
        generated=selected.node;cold=independent_cold(graph,generated.export_request())
        assert cold==generated.read();outputs(generated,cold,graph.data)
        groups=check_groups(generated)
        if n==6 and not asymmetric:
            h=next(h for h in node.read().private.hypotheses if h.roles[2]&1 and any(a.player==1 and a.day==2 and a.target==6 and a.color=='white' for a in h.acquisitions))
            info=PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1))
            owner_mass,owned=node.personal(info)
            row=next(r for r in owned.reports() if tuple(x for x in r.node.read().past if x.acquired_day==2)==desired)
            assert row.public_probability==selected.public_probability and row.probability!=row.public_probability
            cold_owned=independent_cold(graph,row.node.export_request());assert cold_owned==row.node.read()
            outputs(row.node,cold_owned,graph.data);check_groups(row.node)
            private_evidence=dict(owner_mass=str(owner_mass),public_probability=str(row.public_probability),actual_probability=str(row.probability),full_cold_public_owner_equal=True)
        if asymmetric:
            assert (1,2) not in generated.groups and all(len(g)==1 for g in generated.groups)
        else:assert tuple(range(1,3 if n==5 else 4)) in generated.groups
        # Saved hand reports use compatibility support, not sampled fake noise.
        observed_mass,observed=node.observe_reports(desired)
        new=[dict(day=r.acquired_day,reporter=r.player,target=r.target,color=r.color) for r in desired]
        data=data.updated(seer_inputs=data.to_game()['seer_inputs']+new)
        reopened=ClosedCalculation(data);assert reopened.root.read()==observed.read()
        assert reopened.entry_probability==path*observed_mass
        assert independent_cold(graph,reopened.root.export_request())==observed.read()
        reference=SavedOrigin(data,data.game_data.rules,reopened.root.export_request().origin.strategy,False)()
        for name in ('public_state','private'):
            assert getattr(reference,name).hypotheses==getattr(observed.read(),name).hypotheses
            assert getattr(reference,name).rosters==getattr(observed.read(),name).rosters
        assert (reference.public,reference.physical,reference.past)==(observed.read().public,observed.read().physical,observed.read().past)
        outputs(reopened.root,reference,graph.data);groups+=check_groups(observed)
        results.append(dict(players=n,asymmetric=asymmetric,action_masses=action_masses,initial_groups=calc.root.groups,generated_groups=generated.groups,observed_groups=observed.groups,
            independent_group_generators=groups,generated_public_probability=str(selected.public_probability),generated_actual_probability=str(selected.probability),observed_truth_support_mass=str(observed_mass),saved_path_mass=str(reopened.entry_probability),named_cold_public_owner_Forecast_Table_equal=True,
            generated_and_observed_public_role_weights_equal=generated.read().public.worlds==observed.read().public.worlds,
            canonical_metadata=dict(tracked=observed.read().private.tracked,observed_prefix=observed.read().private.observed_prefix),ordinary_metadata=dict(tracked=reference.private.tracked,observed_prefix=reference.private.observed_prefix)))
    result=dict(status='verified',private_report=private_evidence,medium=medium_audit(),cases=results,scope='uniform H0 current-morning complete seer/medium vectors; unchanged CO and initial conditions; saved new rows without public_log',state_pruning=False,ledger_used=False,full_initial7_search=False)
    Path('benchmarks/player_match_groups/closed-morning-reports-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':print(json.dumps(audit()))
