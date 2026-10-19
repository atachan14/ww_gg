"""First-edge seven-initial closure audit; full laws, separate bounded jobs."""
import json,sys,time,hashlib
from pathlib import Path
from fractions import Fraction as F
from types import SimpleNamespace
from .initial_seven_entry_probe import watch,LIMITS


def worker(target,view):
    from .cut_out_user_seven_uniform_preparation import comparison_game,prepare
    from .closed_full_tree_fixture import case
    from .cut_out_compact_terminal_fixture import independent_cold
    from werewolf.board_flow import BoardData
    from werewolf.closed_calculation import ClosedCalculation,_forecast_scope
    from werewolf.actor_information import PersonalInformation,WolfInformation
    from werewolf.calculation_budget import calculation_budget,budget_usage
    started=time.perf_counter()
    with calculation_budget(LIMITS['max_work'],max_seconds=LIMITS['max_seconds']):
        game=comparison_game()[1];prepared=prepare(game);data=BoardData.from_game(game)
        a=ClosedCalculation(data);b=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
        assert b.root.read()==a.root.read()==prepared.source and b.root.groups==prepared.groups
        left,right=a.root,b.root
        h=next(h for h in right.read().private.hypotheses if h.roles[2]&1)
        if view!='public':
            info=PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)) if view=='seer' else WolfInformation.from_hypothesis(h)
            am,left=left.personal(info);bm,right=right.personal(info);assert am==bm
        _forecast_scope(right.read(),b._ClosedCalculation__engine)
        graph=SimpleNamespace(data=data,engine=case(5,'single').engine)
        assert independent_cold(graph,right.export_request())==right.read()
        ac,bc=left.action(target),right.action(target);assert len(ac)==len(bc)
        assert sum((r.probability for r in bc),F())==1
        rows=[]
        for x,y in zip(ac,bc):
            assert x.probability==y.probability and x.node.read()==y.node.read()
            s=y.node.read();assert independent_cold(graph,y.node.export_request())==s
            assert len(s.public.alive)==6 and (s.public.winner is not None or s.public.phase=='night')
            _forecast_scope(s,b._ClosedCalculation__engine)
            assert s.public_state.public_roles==tuple(sorted(s.public.worlds))
            assert s.private.rosters==right.read().private.rosters
            assert sum((h.mass for h in s.private.hypotheses),F())==1
            rows.append(dict(probability=str(y.probability),alive=s.public.alive,phase=s.public.phase,wolf_counts=[(w,str(q)) for w,q in s.public.wolf_count_distribution.items()],public_hypotheses=len(s.public_state.hypotheses),private_hypotheses=len(s.private.hypotheses),full_joint_equal_and_cold=True))
        out=dict(status='verified',view=view,target=target,initial_scope_admitted=True,initial_preparation_equal=True,children=rows,budget=budget_usage(),seconds=time.perf_counter()-started)
    print(json.dumps(out),flush=True)


def run(target,view):
    r=watch('benchmarks.player_match_groups.seven_initial_transition',('worker',str(target),view))
    r['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,('werewolf/closed_calculation.py','werewolf/grouped_forecast.py',__file__))}
    return r

if __name__=='__main__':
    if sys.argv[1:2]==['worker']:worker(int(sys.argv[2]),sys.argv[3])
    else:print(json.dumps(run(int(sys.argv[1]),sys.argv[2])))
