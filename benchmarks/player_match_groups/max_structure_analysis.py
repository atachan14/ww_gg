"""Saved-seven structure plus completed-small totals. Never forecast seven."""
import json,hashlib
from pathlib import Path
from collections import Counter
from unittest.mock import patch
from .max_structure_design import invariant,RefinedMaxOrbitExperiment


def structural_six_night():
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.board_flow import BoardData
    from werewolf.actor_information import wolf_information_groups,wolf_information_orbits
    from werewolf.calculation_budget import calculation_budget
    game=json.loads(Path('benchmarks/player_match_groups/actual-seven-max-results.json').read_text(encoding='utf-8'))['game']
    with calculation_budget(250000,max_seconds=30):
        c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)
        e=c._ClosedCalculation__engine
        with patch.object(e,'solve',side_effect=AssertionError('seven forecast forbidden')),patch.object(e,'act',side_effect=AssertionError('scalar evaluation forbidden')):
            n=next(r.node for r in c.root.action(3) if r.node.read().public.winner is None)
            s=n.read();assert invariant(s,n.groups)
            root=c.root.read();day_reps=[]
            for p in root.public.alive:
                if not any(e.equivalent_targets(root.public,root.public_state,p,t,root.past) for t in day_reps):day_reps.append(p)
            named=wolf_information_groups(s.private);compact=wolf_information_orbits(s.private,n.groups)
            score_counts=[]
            for info,mass,own in named:
                targets=tuple(p for p in s.public.alive if not info.initial_roster&(1<<(p-1)))
                reps=[]
                for p in targets:
                    if not any(e.actor_equivalent_targets(s.public,s.public_state,p,t,s.past,own) for t in reps):reps.append(p)
                score_counts.append(len(reps))
        e.__class__=RefinedMaxOrbitExperiment
        with e.group_scope(n.groups),e.actor_scope(compact[0][0]):
            mask=compact[0][0].initial_roster;targets=tuple(p for p in s.public.alive if not mask&(1<<(p-1)))
            bite_orbits=e.target_orbits(targets)
        with e.group_scope(c.root.groups):root_orbits=e.target_orbits(root.public.alive)
        assert not e.values and not e.action_values
        return dict(note='Only original input construction and named execute3 physical transition. No scalar/Forecast/MAX scoring calls.',root_groups=c.root.groups,existing_root_score_representatives=len(day_reps),constructed_root_action_orbits=len(root_orbits),night_alive=s.public.alive,night_groups=n.groups,full_joint_invariant=True,named_team_cells=len(named),constructed_team_orbits=len(compact),team_orbit_mass=str(compact[0][1]),raw_legal_bites_per_team=len(targets),existing_common_score_representatives_by_team=score_counts,existing_cold_score_queries=sum(score_counts),constructed_cold_score_queries=len(bite_orbits),representative_bite_orbits=bite_orbits)


def terminal_fanout():
    from tests.test_terminal_max_report import make
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.exact import Strategy
    from werewolf.board_future import kernel_calculation
    from werewolf.calculation_budget import calculation_budget
    rows=[]
    for kind,target in (('single',3),('dual',3),('three',4),('medium-pair',4)):
        c,n=make(kind,target);s=n.read()
        e=InformationSetForecast(c.data.game_data.rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False)
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            generated=e.report_children(s)
            rows.append(dict(kind=kind,alive=len(s.public.alive),joint_hypotheses=len(s.public_state.hypotheses),role_worlds=len(s.public.worlds),complete_joint_report_vectors=len(generated),medium_observation_families=len({child.public.reports for q,p,child in generated}),chance_mass=str(sum(p for q,p,child in generated))))
    return rows


def run():
    folder=Path('benchmarks/player_match_groups')
    small=json.loads((folder/'max-structure-small-results.json').read_text(encoding='utf-8'))
    seven=json.loads((folder/'public-moment-seven-results.json').read_text(encoding='utf-8'))['measurements'][0]['worker']
    pairs=[]
    for i in range(0,len(small['results']),2):
        a,b=[small['results'][j]['worker'] for j in (i,i+1)]
        assert a['completed'] and b['completed']
        assert all(a.get(k)==b.get(k) for k in ('value','actions','dawn','table_sha256'))
        assert b['budget']['work']<=a['budget']['work']
        pairs.append(dict(kind=a['kind'],view=a['view'],value=a['value'],work=[a['budget']['work'],b['budget']['work']],actions=[a['states']['expansions']['actions'],b['states']['expansions']['actions']],values=[a['states']['expansions']['values'],b['states']['expansions']['values']],moment_calls=[a['moments']['moment_calls'],b['moments']['moment_calls']],seconds=[a['seconds'],b['seconds']],exact_forecast_table_equal=True))
    modules=Counter();total=0
    for row in small['results']:
        w=row['worker']
        if w['mode']=='baseline':
            modules.update(w['profile_self_by_module']);total+=w['profile_total_self_seconds']
    out=dict(scope='Analysis only. Complete small totals and archived partial seven; no new seven request or production wiring.',saved_seven_partial=seven,complete_small_pairs=pairs,baseline_small_self_profile_total=total,baseline_small_self_profile_modules=dict(modules),structural_six_night=structural_six_night(),terminal_fanout=terminal_fanout(),limitations=['Action/row counters are not CPU shares.','Small self-profiles are instrumented, not a seven profile.','Initial/report/horizon/owner/actor stabilisers must all be preserved.','Candidate remains development-only; broad saved-history/prospective observation entry coverage is not established.'])
    out['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/grouped_forecast.py','werewolf/information_set_forecast.py','benchmarks/player_match_groups/max_structure_design.py','benchmarks/player_match_groups/max_structure_probe.py'))}
    (folder/'max-structure-analysis.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'completed_pairs':len(pairs),'structural_six_night':out['structural_six_night'],'largest_small_self_modules':sorted(modules.items(),key=lambda row:row[1],reverse=True)[:5]}))

if __name__=='__main__':run()
