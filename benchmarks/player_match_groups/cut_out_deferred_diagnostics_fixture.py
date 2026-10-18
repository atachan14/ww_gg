"""Bounded small-case comparison, never a full initial7 trial."""
import sys,json,time,os,threading
from pathlib import Path
from fractions import Fraction as F
from types import SimpleNamespace
from .cut_out_deferred_diagnostics import EagerSmallEngine,DeferredSmallEngine
from .cut_out_uniform_game import evaluate,OwnView
from .cut_out_uniform_game_fixture import peak_bytes
from .cut_out_model_a import adapt_model_a
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_live_medium_forecast import cold
from werewolf.board_future import same_role_board,SavedOrigin,reconstruction_kernel_reuse
from werewolf.calculation_budget import calculation_budget


def audit(players,view=None):
    sys.path.insert(0,str(Path('tests').resolve()))
    from test_cut_out_model_a import cases
    from test_cut_out_uniform_game import table
    graph=SavedCutOutGraph(adapt_model_a(cases(players)['single']))
    eager,old=evaluate(graph,engine_class=EagerSmallEngine,capture_terminal=True,view=view)
    actual,new=evaluate(graph,engine_class=DeferredSmallEngine,capture_terminal=True,view=view)
    reference,official=evaluate(graph,official_reference=True,view=view)
    assert actual==eager==reference
    assert table(graph,actual,view)==table(graph,eager,view)==table(graph,reference,view)
    assert new.deferred_ledger.materialized==0
    assert len(new.board_action_kernels)<len(old.board_action_kernels)
    assert len(new.full_branch_records)==len(old.full_branch_records)
    key=lambda rows:{(b,payload,target):outcomes for b,payload,target,outcomes in rows}
    assert key(new.full_branch_records)==key(old.full_branch_records)
    assert key(new.terminal_records)==key(old.terminal_records)
    assert list(new.branch_records)==list(old.branch_records)
    assert all(type(r.origin) is SavedOrigin for r in new.board_sources.values())
    reads=0
    # Every generated source is independently reconstructed from the same saved
    # initial input with an ordinary kernel, not a retained diagnostic outcome.
    for request in new.board_sources.values():
        warm=request.roles();rebuilt=cold(SimpleNamespace(registry=graph),request)
        assert warm.public_state==rebuilt.public_state and warm.private==rebuilt.private
        assert warm.past==rebuilt.past and warm.observer==rebuilt.observer
        assert same_role_board(warm.public,rebuilt.public) and same_role_board(warm.physical,rebuilt.physical)
        reads+=1
    return dict(players=players,view=None if view is None else view.role,status='verified',Forecast_Table_full_branches_terminal_mass_equal=True,
        full_branches=len(new.full_branch_records),terminal_records=len(new.terminal_records),
        old_retained_resolutions=len(old.board_action_kernels),new_retained_resolutions=len(new.board_action_kernels),
        terminal_memos_not_retained=new.board_action_kernels.terminal_not_retained,
        eager_diagnostic_outcome_rows=sum(len(r[3]) for r in old.full_branch_records),deferred_diagnostic_outcome_rows=0,
        diagnostic_materialization_only_after_value=True,independent_cold_reads=reads,generated_sources=len(new.board_sources),
        note='Small local equality; no initial7 time or memory speedup measurement')


def worker(case):
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    players=4 if case=='four' else 5;view=OwnView(2,'wolf') if case=='own-wolf' else None
    with calculation_budget(4000000,max_seconds=30):row=audit(players,view)
    row.update(seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    Path('benchmarks/player_match_groups/deferred-diagnostics-'+case+'-results.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)

if __name__=='__main__':worker(sys.argv[1] if len(sys.argv)>1 else 'four')
