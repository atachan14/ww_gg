"""Complete finite comparisons with owner-scoped immutable joint sharing."""
import os,sys,time,json,threading
from pathlib import Path
from .cut_out_uniform_game_fixture import peak_bytes
from .cut_out_compact_terminal import CompactTerminalSmallEngine
from .cut_out_uniform_game import evaluate,OwnView
from .cut_out_compact_terminal_fixture import independent_cold,terminal_table
from .cut_out_max_fixture import complete_table
from .cut_out_immutable_joint_observation import census
from .cut_out_deferred_alternating import fingerprint_rows
from werewolf.joint_value_sharing import share_joint_values,independent_joint_values
from werewolf.calculation_budget import calculation_budget
from werewolf.board_future import source_key,ActionEvidence,kernel_snapshot,outcome_key


def audit(case):
    from .cut_out_model_a import adapt_model_a
    from .cut_out_saved_recipes import SavedCutOutGraph
    from .cut_out_two_nights import graph as six_graph
    sys.path.insert(0,str(Path('tests').resolve()))
    from test_cut_out_model_a import cases
    from test_cut_out_morning import medium_spec
    graph=six_graph() if case=='six' else SavedCutOutGraph(adapt_model_a(cases(4)['single'] if case=='four' else medium_spec() if case=='medium' else cases()['single']))
    view=OwnView(2,'wolf') if case=='own-wolf' else None
    out=[];engines=[];pool_info=None
    for mode in ('reference','off','on'):
        with share_joint_values(graph) if mode=='on' else independent_joint_values() as pool:
            forecast,engine=evaluate(graph,engine_class=CompactTerminalSmallEngine if mode!='reference' else None,official_reference=mode=='reference',capture_terminal=True,view=view)
            table=complete_table(graph,forecast,view)
        if mode=='on':
            pool_info=dict(counts=dict(pool.counts),live_before_close=pool.closed_live_counts,indices_empty_after_close=not pool.records and not pool.hypotheses,owner_released=pool.owner is None)
        out.append((forecast,table));engines.append(engine)
    assert out[0]==out[1]==out[2]
    old,new=engines[1:];old_census=census(old);new_census=census(new)
    # Capture counts before optional diagnostic/independent oracle generation.
    key=lambda e:{(b,p,t):rows for b,p,t,rows in e.full_branch_records}
    assert key(old)==key(new)
    assert list(old.terminal_records)==list(new.terminal_records)
    first=fingerprint_rows(new.full_branch_records);assert first==fingerprint_rows(new.full_branch_records)
    reads=0;tables=0
    with independent_joint_values():
        for e in (old,new):
            requests=list({id(r):r for r in e.board_sources.values()}.values());requests.sort(key=lambda r:len(r.history))
            for i in sorted({0,len(requests)//2,len(requests)-1}):
                warm=requests[i].roles();cold=independent_cold(graph,requests[i]);assert warm==cold;reads+=1
                assert all(a is not b for a in warm.private.hypotheses for b in cold.private.hypotheses)
            for i,(b,payload,target,rows) in enumerate(e.terminal_records):
                if i>=3:break
                parent=e.board_sources[source_key(b,payload,e)]
                for row in rows:
                    req=parent.child(ActionEvidence(kernel_snapshot(e),target,outcome_key(row),False),None)
                    assert req.roles()==independent_cold(graph,req);reads+=1
                    ref=next(r for r in key(old)[b,payload,target] if r.board.winner==row.board.winner)
                    assert terminal_table(ref.board)==terminal_table(row.board);tables+=1
                    if row.context is not None:assert terminal_table(ref.context)==terminal_table(row.context);tables+=1
    return dict(status='verified',case=case,complete_Forecast_Table_QP_and_full_diagnostics_equal=True,independent_cold_sharing_disabled=True,cold_reads=reads,terminal_QP_display_comparisons=tables,
        pool=pool_info,census_before=old_census,census_after=new_census,source_keys_before=len(old.board_sources),source_keys_after=len(new.board_sources),
        values_before=len(old.values),values_after=len(new.values),actions_before=len(old.scalar_actions),actions_after=len(new.scalar_actions),full_initial7_search=False)


def worker(case):
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    with calculation_budget(4000000,max_seconds=30):row=audit(case)
    row.update(seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    Path('benchmarks/player_match_groups/immutable-joint-'+case+'-results.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:row[k] for k in ('status','case','cold_reads','seconds','peak_working_set_bytes')}),flush=True)

if __name__=='__main__':worker(sys.argv[1] if len(sys.argv)>1 else 'four')
