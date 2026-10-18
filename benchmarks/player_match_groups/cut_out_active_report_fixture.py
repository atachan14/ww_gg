"""Full report-action identity, tie mass, posterior recipes and no-read checks."""
import json,time,sys,subprocess,threading,os
from pathlib import Path
from fractions import Fraction as F


def white_prior_dependency():
    from werewolf.exact import initial_board,Rules,Strategy
    from werewolf.root_secret_flow import prepare_root_secrets
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.evaluation_branch import ActionInputs
    from werewolf.action_flow import resolve_action
    from .cut_out_no_read_night_max import guarded_profile_probe,certify_night
    rules=Rules();strategy=Strategy();b=initial_board(5,1,1,1,0,experimental_cast=True)
    root=prepare_root_secrets(b,rules);e=InformationSetForecast(rules,strategy,exact_renaming=False,retire_uninformative_scans=False)
    payload,outcomes=resolve_action(b,ActionInputs(root.public_law,(),root.physical_law,None,root.physical),1,e.action_policy)
    outcome=next(o for o in outcomes if o.board.winner is None)
    c=e.action_policy.project(b,payload,outcome,1)
    restricted,_=certify_night(c.public,c.public_state,c.past,rules,strategy)
    assert restricted.selected is None and restricted.reason=='five_player_no_read_structure_unproved'
    proof,diagnostics=guarded_profile_probe(c.public,c.public_state,c.past,rules,strategy)
    assert proof.selected is not None and diagnostics['profile_reads']==0 and diagnostics['complete_candidate_scores']==12
    assert all(v==F(1,3) for info,row in proof.selected.scores for target,v in row)
    return dict(case='M1-white-dependency',initial_hypotheses=len(root.public_law.hypotheses),night_hypotheses=len(c.public_state.hypotheses),
        restricted_entry_reason=restricted.reason,guarded_proof=proof.proof,diagnostics=diagnostics,
        actual_profile_dependency_detected=False,scope_limit_for_this_context=True,full_entry_expanded=False)


def independent_report_law(initial,state,fake_colors):
    from .cut_out_latent_max_fixture import independent_terminal
    from werewolf.seer_acquisition import normalize
    before=independent_terminal(initial,state);instructions=dict(fake_colors)
    rows=[]
    for h in before:
        valid=True
        for report in state.public.reports:
            color=('black' if h.roles[0]&(1<<(report.target-1)) else 'white') if h.roles[1]&(1<<(report.reporter-1)) else instructions[report.reporter]
            if color!=report.color:valid=False;break
        if valid:rows.append(h)
    mass=sum((h.mass for h in rows),F())
    return mass,normalize(rows)


def audit(n=5,initial='none',private=False):
    from .cut_out_active_report_max import graph,evaluate,scan_values
    from .cut_out_uniform_game import OwnView
    from .cut_out_max_fixture import complete_table
    from .cut_out_latent_max_fixture import independent_initial
    from .cut_out_two_nights import restore_terminals
    from werewolf.seer_acquisition import Acquisition,normalize
    from werewolf.board_future import MediumInstructionEvidence,same_role_board,reconstruction_kernel_reuse
    from werewolf.exact import report_actions
    from werewolf.morning_flow import report_flow,continuation_value
    from werewolf.policy_choice import optimal_targets,uniform_policy
    from werewolf.calculation_budget import calculation_budget
    source=graph(n,initial);root=source.origin()
    initial_joint=normalize(h for h in independent_initial(n,1,initial) if (h.roles[0],h.roles[1]) in ((1,2),(2,1)))
    assert root.public_state.hypotheses==initial_joint
    view=OwnView(3,'seer',(Acquisition(1,3,1,'white'),)) if private else None
    forecast,engine=evaluate(source,view=view,capture_terminal=True)
    reference,full=evaluate(source,view=view,official_reference=True,capture_terminal=True)
    assert forecast==reference and complete_table(source,forecast,view)==complete_table(source,reference,view)
    expected=F(1,2) if n==4 else F(1)
    assert forecast.village_win==expected
    if not private:assert dict(forecast.action_values)=={p:expected if p in (1,2) else F(0) if n==4 else F(1,2) for p in root.public.alive}
    if private and n==4:assert dict(forecast.action_values)=={p:F(int(p==2)) for p in root.public.alive}
    assert tuple(optimal_targets(engine.day_scores(root.public,root.public_state,root.past),maximize=True))==(1,2)
    for key,v in engine.scalar_actions.items():
        b,s,past,own,observer,physical,target=key
        assert v==full.act(b,s,past,target,own,observer,physical=physical)
    small,_=restore_terminals(engine);large,_=restore_terminals(full)
    for key,(q,c,request) in small.items():
        old_q,old,_=large[key]
        assert q==old_q and c.public_state==old.public_state and c.private==old.private and c.past==old.past
        assert same_role_board(c.public,old.public) and same_role_board(c.physical,old.physical)
    four_vector_witness=tie_witness=0;branches=0;all_candidate_recipe_checks=0;choice_evidence=[]
    for (b,s,past),(scores,chosen) in list(engine.report_decisions.items()):
        original_actions=report_actions(b)
        assert tuple(a for a,v in scores)==original_actions
        reference_scores=tuple((a,continuation_value(report_flow(a.outcomes,s,past,full,source_board=b,fake_colors=a.fake_colors),full.scalar)) for a in original_actions)
        assert scores==reference_scores and chosen==uniform_policy(optimal_targets(reference_scores,maximize=False))
        assert engine.morning(b,s,past)==full.morning(b,s,past)
        choice_evidence.append(dict(history=[(e.day,e.phase,e.target) for e in b.history],alive=b.alive,
            public_hypotheses=len(s.hypotheses),scores=[dict(fake_colors=a.fake_colors,value=str(v)) for a,v in scores],
            chosen=[dict(fake_colors=a.fake_colors,weight=str(q)) for a,q in chosen]))
        for action,value in scores:
            for outcome in action.outcomes:
                from types import SimpleNamespace
                state=SimpleNamespace(public=outcome.board)
                mass,law=independent_report_law(initial_joint,state,action.fake_colors)
                assert mass==outcome.probability
                assert engine.project(s,outcome.board).hypotheses==law
                from werewolf.board_future import register_origin,kernel_snapshot
                from werewolf.evaluation_branch import ActionInputs,physical_board
                parent=register_origin(engine,b,ActionInputs(s,past,s,None,physical_board(b,s)))
                operation=MediumInstructionEvidence(kernel_snapshot(engine),action.fake_colors,outcome.board.reports,outcome.board.report_resolved)
                request=parent.child(operation,(outcome.board.day,outcome.board.phase,outcome.board.alive))
                rebuilt=request.roles()
                assert rebuilt.public_state.hypotheses==law and rebuilt.private.hypotheses==law
                assert same_role_board(rebuilt.public,outcome.board) and rebuilt.past==past
                assert request.origin is source.origin and operation.fake_colors==action.fake_colors
                with reconstruction_kernel_reuse(False):cold=request.roles()
                assert cold==rebuilt
                all_candidate_recipe_checks+=1
                branches+=1
        if len(scores)==4:
            assert [v for a,v in scores]==[F(1,2),F(1),F(1),F(1)]
            assert chosen==((scores[0][0],F(1)),)
            four_vector_witness+=1
        if len(scores)==2:
            assert all(v==1 for a,v in scores) and len(chosen)==2 and all(q==F(1,2) for a,q in chosen)
            tie_witness+=1
    if n==5:assert four_vector_witness and tie_witness
    else:assert not engine.report_decisions
    recipe_checks=0
    # Includes every public candidate instruction, not only optimal reports.
    for request in list(engine.board_sources.values()):
        if not request.history or not isinstance(request.history[-1],MediumInstructionEvidence):continue
        c=request.roles();op=request.history[-1]
        _,law=independent_report_law(initial_joint,c,op.fake_colors)
        assert c.public_state.hypotheses==law and c.private.hypotheses==law and c.observer is None
        assert c.public.reports==op.reports and c.public.report_resolved==op.resolved and request.origin is source.origin
        with reconstruction_kernel_reuse(False):
            cold=request.roles()
        assert cold==c
        recipe_checks+=1
    if n==5:assert recipe_checks
    private_report_witnesses=0
    if private and n==5:
        for request in list(engine.board_sources.values()):
            c=request.roles()
            if (c.observer!=view or c.public.day!=2 or c.public.phase!='day' or c.public.winner
                or {h.roles[0] for h in c.public_state.hypotheses}!={1,2}
                or {h.roles[0] for h in c.private.hypotheses}!={2}):continue
            owned_initial=normalize(h for h in initial_joint if view.accepts(h))
            _,owned=independent_report_law(owned_initial,c,((1,'white'),(2,'white')))
            assert c.private.hypotheses==owned
            assert tuple(optimal_targets(engine.day_scores(c.public,c.public_state,c.past),maximize=True))==(1,2)
            assert engine.solve(*c,physical=c.physical)==F(1,2)
            assert engine.act(c.public,c.public_state,c.past,2,c.private,c.observer,physical=c.physical)==1
            with reconstruction_kernel_reuse(False):assert request.roles()==c
            private_report_witnesses+=1
        assert private_report_witnesses
    scans=[]
    if private:
        scans,scan_engine=scan_values(source,view);old_scans,_=scan_values(source,view,official_reference=True)
        assert scans==old_scans and all(v==expected for p,v in scans)
    assert all(search.selected is not None and diagnostic['profile_reads']==0 for search,diagnostic in engine.report_diagnostics.values())
    return dict(players=n,initial=initial,private=private,village_win=str(expected),report_frames=len(engine.report_decisions),
        four_candidate_witnesses=four_vector_witness,two_candidate_uniform_tie_witnesses=tie_witness,
        candidate_outcome_joint_checks=branches,all_candidate_instruction_cold_readbacks=all_candidate_recipe_checks,medium_instruction_cold_readbacks=recipe_checks,private_report_posterior_witnesses=private_report_witnesses,
        complete_table_action_joint_history_physical_equal=True,own_scan_targets=[p for p,v in scans],
        initial_public_policy=[1,2],night_proofs=len(engine.report_certificates),report_choice_evidence=choice_evidence)


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    started=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-started>60 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    result=white_prior_dependency() if case=='dependency' else audit(*json.loads(case))
    result.update(worker_seconds=time.monotonic()-started,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    started=time.monotonic();rows=[];logs=[]
    for case in [json.dumps(c) for c in [(4,'none',False),(4,'random_white',True),(5,'none',False),(5,'random_white',True)]]+['dependency']:
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        rows.append(json.loads(run.stdout));print('passed '+case,flush=True)
    previous=json.loads(Path('benchmarks/player_match_groups/withdraw-standard-results.json').read_text(encoding='utf-8'))
    checks=[(c['kind'],c['target']) for c in previous['checks']]+[('pattern','test_cut_out_seven_minimal.py'),('pattern','test_cut_out_max_game.py'),('pattern','test_cut_out_latent_max.py'),('pattern','test_cut_out_terminal_night_max.py'),('pattern','test_cut_out_no_read_night_max.py'),('pattern','test_cut_out_triple_max.py'),('pattern','test_cut_out_active_report_max.py')]
    for kind,target in checks:
        run=subprocess.run([sys.executable,'-B','-m','benchmarks.player_match_groups.withdraw_prefix_diagnostic_fixture',kind,target],capture_output=True,text=True,timeout=min(60,300-(time.monotonic()-started)))
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        logs.append(run.stdout+run.stderr)
    Path('.artifacts/active-report-max-regressions-final.log').write_text('\n'.join(logs),encoding='utf-8')
    result=dict(cases=rows,checks=checks,existing56_preserved=True,regression_tests=59,timing_interpretation='bounded correctness only',overall_seconds=time.monotonic()-started)
    Path('benchmarks/player_match_groups/cut-out-active-report-max-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(overall_seconds=result['overall_seconds'])),flush=True)

if __name__=='__main__':main()
