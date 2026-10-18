"""Finite input-edit and demand-only display comparison, no normal UI hookup."""
import time,sys,json,subprocess,threading,os,hashlib
from pathlib import Path
from dataclasses import replace
from fractions import Fraction as F
from datetime import datetime,timezone
START=time.perf_counter()


def setup():
    from .cut_out_two_nights import spec
    from .cut_out_six_registry import SixInputRegistry
    from werewolf.exact import ClaimPolicy
    from werewolf.seer_acquisition import SeerReport
    base=replace(spec(),claim_policy=ClaimPolicy(villager='none',medium='none',seer='none',hunter='none'))
    return base,SixInputRegistry.create(base,(2,3),(SeerReport(2,2,1,2,'white'),))


def event(registry,key):
    from werewolf.public_log_changes import declarations
    return declarations(registry.data.to_game()['public_log'])[0][key][1]


def withdraw(registry,keys):
    return registry.edited({'mode':'simultaneous','events':[dict(e,action='withdraw',ref=e['id']) for e in (event(registry,key) for key in keys)]})


def assert_snapshot(registry,view=None):
    from .cut_out_six_registry import current_screen,preview_action
    from .cut_out_saved_recipes import InvalidatedBranch
    from werewolf.board_flow import BoardData
    from werewolf.board_future import SavedOrigin,same_role_board,evidence_reconstruction
    from werewolf.evaluation_branch import ActionInputs
    from werewolf.action_flow import resolve_action
    assert registry.problem is None,registry.problem
    from .cut_out_day_night import moved_law
    source=registry.read()
    group_audits=0
    for group in registry.engine.start().groups:
        for other in group[1:]:
            assert moved_law(source.public_state,group[0],other,6)==source.public_state
            assert moved_law(source.private,group[0],other,6)==source.private
            group_audits+=1
    cold=SavedOrigin(BoardData.from_game(registry.data.to_game()),registry.base.rules,registry.base.strategy,project_public=False)()
    assert source.public_state==cold.public_state and source.private==cold.private and source.past==cold.past
    assert same_role_board(source.public,cold.public) and same_role_board(source.physical,cold.physical)
    start=time.perf_counter();screen=current_screen(registry,view=view);screen_seconds=time.perf_counter()-start
    reference=current_screen(registry,view=view,official_reference=True)
    assert screen.forecast==reference.forecast and screen.table==reference.table
    assert screen.primary==reference.primary and screen.cumulative==reference.cumulative
    assert screen.public_joint==reference.public_joint and screen.own_belief==reference.own_belief and screen.physical_joint==reference.physical_joint
    for p in range(1,7):
        for q in range(1,7):assert screen.pair(p,'seer',q,'wolf',own=view is not None)==reference.pair(p,'seer',q,'wolf',own=view is not None)
    # No terminal histories are required to produce the entire display Table.
    assert screen.engine.capture_terminal is False and not screen.engine.terminal_records
    start=time.perf_counter();binding=preview_action(registry,5,view=view)
    assert binding._request is None
    observed=binding.read();assert not isinstance(observed,InvalidatedBranch),observed
    from .cut_out_six_registry import OwnEvidence
    actual_source=source if view is None else OwnEvidence(view)(source)
    with evidence_reconstruction():
        acquired,outcomes=resolve_action(actual_source.public,ActionInputs(actual_source.public_state,actual_source.past,actual_source.private,actual_source.observer,actual_source.physical),5,registry.kernel.action_policy,terminal_payoffs=False)
        outcome=next(o for o in outcomes if o.board.winner is None)
        expected=registry.kernel.action_policy._project_roles(actual_source.public,acquired,outcome,5)
    assert observed.public_state==expected.public_state and observed.private==expected.private and observed.past==expected.past
    assert same_role_board(observed.physical,expected.physical)
    assert binding.mass()==outcome.probability
    click_seconds=time.perf_counter()-start
    assert binding.request().origin is registry.origin
    registered=0
    for request in {id(r):r for r in screen.engine.board_sources.values()}.values():
        rebound=registry.register(request);actual=request.roles();regenerated=rebound.read()
        assert regenerated.public_state==actual.public_state and regenerated.private==actual.private
        registered+=1
    return dict(screen_seconds=screen_seconds,table_seconds=screen.timings['table_seconds'],evaluation_seconds=screen.timings['evaluation_seconds'],
        one_individual_branch_seconds=click_seconds,click_mass=str(binding.mass()),current_public_hypotheses=len(source.public_state.hypotheses),
        current_physical_hypotheses=len(source.private.hypotheses),scope_revision=registry.data.to_game().get('revision',0),semantic_representative_registrations=registered,group_audits_in_tests_only=group_audits,
        joint_table_forecast_pairwise_equal=True,terminal_tree_materialized_for_screen=False),screen,binding


def edits_case():
    from .cut_out_six_registry import RecipeDescriptor,WolfEvidence
    from .cut_out_saved_recipes import InvalidatedBranch
    from werewolf.seer_acquisition import SeerReport
    from werewolf.exact import action_outcomes
    from werewolf.board_future import outcome_key
    base,registry=setup();states=[registry];input_before=registry.data.inputs;root_before=registry.read()
    first,screen,preview=assert_snapshot(registry)
    old=event(registry,('seer',2,1))
    corrected=registry.edited({'mode':'single','events':[dict(old,target=4,action='change',ref=old['id'])]})
    current_row,new_screen,_=assert_snapshot(corrected)
    assert screen.table.players[0].metric('action',current_frame=new_screen.table.players[0].frame).status=='stale'
    states.append(corrected);rows=[first,current_row]
    actor=WolfEvidence(1<<3)(preview.read())
    outcome=next(o for o in action_outcomes(actor.physical,6,base.rules,base.strategy) if o.board.winner=='wolf')
    descriptor=RecipeDescriptor(preview.descriptor.operations+(('wolf',1<<3),('action',(6,outcome_key(outcome)))))
    old_binding=registry.bind_descriptor(descriptor)
    assert not isinstance(old_binding.read(),InvalidatedBranch)
    expected_mass=sum((h.mass for h in root_before.private.hypotheses if h.roles[0]==1<<3),F())/2
    assert old_binding.mass()==expected_mass
    rebound=corrected.rebind(old_binding);assert rebound._request is None
    assert isinstance(rebound.read(),InvalidatedBranch) and isinstance(rebound.mass(),InvalidatedBranch)
    cancelled=withdraw(corrected,(('seer',2,1),));states.append(cancelled);rows.append(assert_snapshot(cancelled)[0])
    restored=cancelled.edited({'mode':'single','events':[{'kind':'seer','player':1,'day':2,'target':2,'color':'white'}]})
    states.append(restored);rows.append(assert_snapshot(restored)[0])
    assert restored.read().public_state==root_before.public_state and restored.read().private==root_before.private
    assert restored.rebind(old_binding).read().private==old_binding.read().private
    root_cancel=registry.corrected_root(replace(base,claims=('latent',)*6,reports=()),())
    states.append(root_cancel);rows.append(assert_snapshot(root_cancel)[0])
    assert len(root_cancel.read().public_state.hypotheses)>len(root_before.public_state.hypotheses)
    root_restore=root_cancel.corrected_root(base,(SeerReport(2,2,1,2,'white'),))
    states.append(root_restore);rows.append(assert_snapshot(root_restore)[0])
    assert root_restore.read().public_state==root_before.public_state and root_restore.read().private==root_before.private
    assert registry.data.inputs==input_before and registry.read()==root_before
    assert all(s.data.game_data is registry.data.game_data and s.data.runtime is registry.data.runtime for s in states)
    return dict(snapshots=rows,old_snapshot_immutable=True,unsupported_recipe_invalidated=True,root_cancel_redo_exact=True,
        physical_public_separate=root_before.public_state!=root_before.private,old_private_actor_mass=str(expected_mass))


def blocked_case():
    from .cut_out_saved_recipes import InvalidatedBranch
    from .cut_out_six_registry import SixInputRegistry
    from werewolf.board_flow import BoardData
    from werewolf.board_future import SavedOrigin
    from werewolf.information_set_forecast import Pending
    base,registry=setup();before=registry.data.inputs
    blocked=withdraw(registry,(('co',1),('seer',1,1),('seer',2,1)))
    assert isinstance(blocked,SixInputRegistry) and isinstance(blocked.problem,InvalidatedBranch)
    assert blocked.data.inputs!=before and registry.data.inputs==before
    try:SavedOrigin(BoardData.from_game(blocked.data.to_game()),base.rules,base.strategy,project_public=False)()
    except Pending as error:assert error.reason==blocked.problem.reason
    else:raise AssertionError('old official path unexpectedly accepted late CO withdraw')
    batch=blocked.data.to_game()['public_log']['batches'][-1]['id']
    recovered=blocked.edited({'delete':batch})
    assert recovered.problem is None and recovered.read().public_state==registry.read().public_state and recovered.read().private==registry.read().private
    return dict(blocked_action='late CO+reports withdraw at saved Day2',reason=blocked.problem.reason,
        candidate_input_preserved=True,old_input_immutable=True,delete_withdraw_batch_recovers_exactly=True)


def own_case():
    from .cut_out_uniform_game import OwnView
    from werewolf.seer_acquisition import Acquisition
    base,registry=setup();view=OwnView(1,'seer',(Acquisition(1,1,3,'white'),))
    row,_,_=assert_snapshot(registry,view)
    return dict(own_screen=row)


def initial_case():
    from .cut_out_two_nights import spec,graph
    from .cut_out_saved_recipes import SavedCutOutGraph,PathObservation,InvalidatedBranch
    from werewolf.seer_acquisition import SeerReport
    original=graph();baseline=original.origin()
    branch=original.bind(PathObservation(2,3,None,(SeerReport(2,2,1,2,'white'),),()))
    assert not isinstance(branch.read(),InvalidatedBranch)
    cancelled=original.corrected(replace(spec(),claims=('latent',)*6,reports=()))
    restored=cancelled.corrected(spec())
    assert type(cancelled) is SavedCutOutGraph and type(restored) is SavedCutOutGraph
    assert restored.origin().public_state==baseline.public_state
    assert original.origin()==baseline
    return dict(initial_six_registry_corrected=True,initial_cancel_support=len(cancelled.origin().public_state.hypotheses),first_morning_mass=str(branch.mass()))


def screen_case():
    from .cut_out_six_registry import current_screen,preview_action
    from .cut_out_uniform_game import OwnView
    from werewolf.seer_acquisition import Acquisition
    started=time.perf_counter();base,registry=setup();setup_seconds=time.perf_counter()-started
    started=time.perf_counter();screen=current_screen(registry);current_seconds=time.perf_counter()-started
    display_ready=time.perf_counter()
    assert not registry.bindings and not screen.engine.terminal_records
    started=time.perf_counter();binding=preview_action(registry,5)
    assert binding._request is None
    detail=binding.read();mass=binding.mass();detail_seconds=time.perf_counter()-started
    detail_ready=time.perf_counter()
    started=time.perf_counter();own=current_screen(registry,view=OwnView(1,'seer',(Acquisition(1,1,3,'white'),Acquisition(2,1,2,'white'))))
    private_seconds=time.perf_counter()-started
    reference=current_screen(registry,official_reference=True)
    assert screen.forecast==reference.forecast and screen.table==reference.table
    assert screen.primary==reference.primary and screen.cumulative==reference.cumulative
    assert detail.public_state and detail.private and detail.observer is None
    assert mass==sum((h.mass for h in registry.origin().private.hypotheses if not h.roles[0]&(1<<(5-1))),F())
    assert len(screen.table.players)==len(own.table)==6
    return dict(setup_seconds=setup_seconds,current_screen_seconds=current_seconds,table_seconds=screen.timings['table_seconds'],
        display_ready_counter=display_ready,detail_ready_counter=detail_ready,one_label_detail_seconds=detail_seconds,
        private_full_table_request_seconds=private_seconds,selected_label=5,selected_path_mass=str(mass),
        full_original_rows=6,all_terminal_materialization=False,full_current_public_joint=len(screen.public_joint.hypotheses),
        full_current_physical_joint=len(screen.physical_joint.hypotheses),detail_joint_public=len(detail.public_state.hypotheses),
        detail_joint_physical=len(detail.private.hypotheses),scope='Python startup/import + SavedOrigin snapshot + Forecast + complete Table; no HTTP/template rendering')


def medium_case():
    from .cut_out_two_nights import spec
    from .cut_out_six_registry import SixInputRegistry,current_screen,preview_action
    from werewolf.exact import MediumReport
    from werewolf.seer_acquisition import SeerReport
    base=replace(spec(),mediums=1,claims=('seer','medium','medium','latent','latent','latent'),reports=(SeerReport(1,1,1,4,'white'),))
    reports=(MediumReport(2,2,5,'white'),MediumReport(2,3,5,'white'))
    registry=SixInputRegistry.create(base,(5,6),(SeerReport(2,2,1,5,'white'),),reports)
    assert registry.problem is None,registry.problem
    screen=current_screen(registry);reference=current_screen(registry,official_reference=True)
    assert screen.forecast==reference.forecast and screen.table==reference.table
    assert screen.primary==reference.primary and screen.cumulative==reference.cumulative
    query=preview_action(registry,4);assert query._request is None
    state=query.read();assert state.public.reports==reports and state.past==registry.origin().past
    assert query.mass()==1
    return dict(medium_current_table_equal=True,medium_reports_preserved=True,private_and_public_joint_available=True)


def late_co_case():
    from .cut_out_six_registry import SixInputRegistry
    base,_=setup();base=replace(base,claims=('latent',)*6,reports=())
    initial=SixInputRegistry.create(base,(2,3))
    payload={'mode':'simultaneous','events':[{'kind':'co','player':1,'role':'seer'},
        {'kind':'seer','player':1,'day':1,'target':3,'color':'white'},
        {'kind':'seer','player':1,'day':2,'target':2,'color':'white'}]}
    declared=initial.edited(payload);a,_,_=assert_snapshot(declared)
    cancelled=withdraw(declared,(('co',1),('seer',1,1),('seer',2,1)));b,_,_=assert_snapshot(cancelled)
    assert cancelled.read().public_state==initial.read().public_state and cancelled.read().private==initial.read().private
    restored=cancelled.edited(payload);c,_,_=assert_snapshot(restored)
    assert restored.read().public_state==declared.read().public_state and restored.read().private==declared.read().private
    early=setup()[1].read().public.wolf_probability(1)
    late=declared.read().public.wolf_probability(1)
    assert early!=late # DO NOT construct an initial prior from the current CO!
    return dict(owned_late_co_cancel_redo_exact=True,late_co_wolf1=str(late),initial_co_wolf1=str(early),snapshots=[a,b,c])


def worker(case):
    from .cut_out_uniform_game_fixture import peak_bytes
    def watch():
        while True:
            if peak_bytes()>1_500_000_000:print('1.5GB working-set limit exceeded',file=sys.stderr,flush=True);os._exit(137)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    start=time.perf_counter();result={'edits':edits_case,'blocked':blocked_case,'own':own_case,'initial':initial_case,'screen':screen_case,'medium':medium_case,'late-co':late_co_case}[case]()
    result.update(case=case,work_seconds=time.perf_counter()-start,startup_and_work_seconds=time.perf_counter()-START,peak_working_set_bytes=peak_bytes())
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1:return worker(sys.argv[1])
    start=time.monotonic();rows=[]
    for case in ('edits','own','blocked','initial','screen','screen','screen','medium','late-co'):
        remaining=300-(time.monotonic()-start)
        if remaining<=0:raise SystemExit('300s budget exhausted')
        launched=time.perf_counter();run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=min(60,remaining))
        if run.returncode:print(case,run.stdout+run.stderr);raise SystemExit(run.returncode)
        row=json.loads(run.stdout);row['repeat_index']=1+sum(r['case']==case for r in rows);row['process_seconds']=time.perf_counter()-launched
        if case=='screen':
            row['fresh_process_to_complete_table_seconds']=row.pop('display_ready_counter')-launched
            row['fresh_process_through_one_detail_seconds']=row.pop('detail_ready_counter')-launched
        rows.append(row)
        print(case,round(row['process_seconds'],3),flush=True)
    paths=('benchmarks/player_match_groups/cut_out_six_registry.py','benchmarks/player_match_groups/cut_out_six_registry_fixture.py','benchmarks/player_match_groups/cut_out_uniform_game.py','benchmarks/player_match_groups/cut_out_saved_recipes.py','tests/test_cut_out_six_registry.py')
    record=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),head_before_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),cases=rows,
        total_seconds=time.monotonic()-start,per_process_seconds=60,total_budget_seconds=300,memory_limit_bytes=1_500_000_000,
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        normal_ui_or_public_changed=False,remaining_blocker='old official late CO withdraw replays old historical CO without active report; Pending, input retained and reversible')
    Path('benchmarks/player_match_groups/cut-out-six-registry-results.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
