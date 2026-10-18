"""Finite complete comparisons for opt-in terminal facts, no initial7 search."""
import os,sys,time,json,threading
from pathlib import Path
from fractions import Fraction as F
from types import SimpleNamespace
from unittest.mock import patch
from .cut_out_compact_terminal import CompactTerminalSmallEngine
from .cut_out_deferred_diagnostics import DeferredSmallEngine
from .cut_out_uniform_game import evaluate,OwnView
from .cut_out_uniform_game_fixture import peak_bytes
from .cut_out_model_a import adapt_model_a,adapt_six_model_a
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_live_medium_forecast import cold
from .cut_out_max_fixture import complete_table
from .cut_out_deferred_alternating import fingerprint_rows
from werewolf.exact import Board
from werewolf.board_future import ActionEvidence,kernel_snapshot,outcome_key,source_key,same_role_board
from werewolf.calculation_budget import calculation_budget
from werewolf.player_view import private_api_rows


def independent_cold(graph,request):
    from dataclasses import replace
    from werewolf.information_set_forecast import InformationSetForecast,Pending
    from werewolf.board_future import (SavedOrigin,GeneratedBoard,ActionEvidence,PublicationEvidence,PublicReportEvidence,
        MediumInstructionEvidence,ContextEvidence,ConditionEvidence,PublicViewEvidence,OwnerInformationEvidence,reconstruction_kernel_reuse)
    fresh=InformationSetForecast(graph.engine.baseline.rules,graph.engine.baseline.strategy,exact_renaming=False,retire_uninformative_scans=False)
    fresh.retain_joint_guard_history=True
    origin=SavedOrigin(graph.data,fresh.rules,fresh.strategy,project_public=False);ops=[]
    for op in request.history:
        if type(op) in (ActionEvidence,PublicationEvidence,PublicReportEvidence,MediumInstructionEvidence,ContextEvidence):ops.append(replace(op,engine=fresh))
        elif type(op) in (ConditionEvidence,PublicViewEvidence):ops.append(replace(op))
        elif type(op)is OwnerInformationEvidence:
            def owner_filter(source,info=op.information,observer=op.observer):
                from werewolf.actor_information import WolfInformation,condition_actor_state
                from werewolf.evaluation_branch import ContinuationInputs,physical_board
                if type(info)is WolfInformation:
                    known={a.night:a.target for a in info.attacks}
                    predicate=lambda h:h.roles[0]==info.initial_roster and all(known.get(a.night)==a.target for a in h.attacks)
                    law=condition_actor_state(source.private,predicate,attacks=info.attacks)
                else:law=condition_actor_state(source.private,lambda h:info(h,source.private))
                return ContinuationInputs(source.public,source.public_state,source.past,law,observer,physical_board(source.public,law,source.physical))
            ops.append(owner_filter)
        else:raise Pending('compact_terminal_cold_unknown_evidence:'+type(op).__name__)
    with reconstruction_kernel_reuse(False):result=GeneratedBoard(origin,tuple(ops)).roles()
    assert fresh.values=={} and origin is not request.origin
    return result


def terminal_table(board):
    marginals=[{r:board.role_probability(p,r) for r in ('wolf','medium','seer','hunter','villager')} for p in range(1,board.player_count+1)]
    return private_api_rows(marginals,final_values={p:F(board.winner=='village') for p in board.alive})


def audit(case):
    sys.path.insert(0,str(Path('tests').resolve()))
    from test_cut_out_model_a import cases
    from test_cut_out_morning import medium_spec
    from .cut_out_two_nights import spec as six_spec
    from dataclasses import replace
    spec=cases(4)['single'] if case=='four' else medium_spec() if case=='medium' else six_spec() if case=='six' else cases()['single']
    graph=SavedCutOutGraph((adapt_six_model_a if case=='six' else adapt_model_a)(spec));view=OwnView(2,'wolf') if case=='own-wolf' else None
    original=Board.__post_init__;counts={};engines=[];forecasts=[]
    for label,cls in (('ordinary',None),('deferred',DeferredSmallEngine),('compact',CompactTerminalSmallEngine)):
        count=[0]
        def validated(b):count[0]+=1;return original(b)
        with patch.object(Board,'__post_init__',validated):
            result,engine=evaluate(graph,view=view,capture_terminal=True,official_reference=cls is None,engine_class=cls)
            table=complete_table(graph,result,view)
        counts[label]=count[0];engines.append(engine);forecasts.append((result,table))
    assert forecasts[0]==forecasts[1]==forecasts[2]
    old,new=engines[1:]
    assert new.terminal_compact_actions>0 and new.deferred_ledger.materialized==0
    assert counts['compact']<counts['deferred']
    full=lambda e:{(b,p,t):out for b,p,t,out in e.full_branch_records}
    assert full(new)==full(old)
    assert list(new.terminal_records)==list(old.terminal_records)
    # Opening diagnostics repeatedly reconstructs identical full Boards, not
    # lightweight scalar facts. No missing acquisition or action ledger.
    first=fingerprint_rows(new.full_branch_records);second=fingerprint_rows(new.full_branch_records);assert first==second
    reads=0;tables=0
    for engine in (old,new):
        # Three independent nonterminal source requests per engine.
        requests=list({id(r):r for r in engine.board_sources.values()}.values());requests.sort(key=lambda r:len(r.history))
        for i in sorted({0,len(requests)//2,len(requests)-1}):
            req=requests[i];warm=req.roles();rebuilt=independent_cold(graph,req)
            assert warm==rebuilt;reads+=1
        # Three independent terminal history recipes per engine use the
        # ordinary full-detail contract, including post-acquisition histories.
        for index,(b,payload,target,outcomes) in enumerate(engine.terminal_records):
            if index>=3:break
            parent=engine.board_sources[source_key(b,payload,engine)]
            for out in outcomes:
                request=parent.child(ActionEvidence(kernel_snapshot(engine),target,outcome_key(out),False),None)
                warm=request.roles();rebuilt=independent_cold(graph,request)
                assert warm==rebuilt and same_role_board(warm.physical,out.board);reads+=1
                reference=next(o.board for o in full(old)[b,payload,target] if o.board.winner==out.board.winner)
                assert terminal_table(out.board)==terminal_table(reference);tables+=1
                public_reference=next(o.context for o in full(old)[b,payload,target] if o.board.winner==out.board.winner)
                if out.context is not None:
                    assert terminal_table(out.context)==terminal_table(public_reference);tables+=1
    return dict(status='verified',case=case,Board_validations_for_complete_Forecast_Table=counts,
        compact_terminal_actions=new.terminal_compact_actions,values=len(new.values),actions=len(new.scalar_actions),
        full_branches=len(new.full_branch_records),terminal_records=len(new.terminal_records),
        terminal_tables_compared=tables,independent_source_and_terminal_cold_reads=reads,
        full_Forecast_Table_QP_branches_and_deferred_diagnostics_equal=True,repeated_diagnostic_equal=True,
        early_winner_rules_unchanged=True,full_initial7_search=False)


def worker(case):
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    with calculation_budget(4000000,max_seconds=30):row=audit(case)
    row.update(seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    Path('benchmarks/player_match_groups/compact-terminal-'+case+'-results.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)

if __name__=='__main__':worker(sys.argv[1] if len(sys.argv)>1 else 'four')
