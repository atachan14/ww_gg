"""Finite root-boundary counting, full labelled readback and independent cold."""
import sys,os,time,json,threading
from pathlib import Path
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
from .cut_out_publication_orbit_value import *
from .cut_out_publication_orbit_value import _scopes
from .cut_out_uniform_game_fixture import peak_bytes
from .cut_out_compact_terminal import CompactTerminalSmallEngine
from .cut_out_model_a import adapt_model_a
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_structural_publications_fixture import build,condition_request
from .cut_out_live_medium_forecast import cold as seven_cold
from .cut_out_compact_terminal_fixture import independent_cold
from .cut_out_deferred_alternating import fingerprint_rows
from werewolf.actor_information import condition_actor_state
from werewolf.board_future import ActionEvidence,outcome_key,calculation_origin
from werewolf.player_view import private_api_rows
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,budget_stop
from werewolf.joint_value_sharing import independent_joint_values


def make_scope(case):
    if case=='five':
        sys.path.insert(0,str(Path('tests').resolve()))
        from test_cut_out_model_a import cases
        graph=SavedCutOutGraph(adapt_model_a(cases()['same_reports']));e=CompactTerminalSmallEngine(graph)
        request=graph.root;source=graph.origin()
        for target in (3,4):
            out=next(o for o in e.physical_children(source.physical,target) if o.board.winner is None)
            request=request.child(ActionEvidence(kernel_snapshot(e),target,outcome_key(out),False),None);source=request.roles()
        return issue_scope(graph,e,request,source),lambda req:independent_cold(graph,req)
    prefix=build(3,4);source=prefix.source;request=prefix.request
    if case in ('roster','asymmetric-scan'):
        seed=next(h for h in source.private.hypotheses if h.roles[0]==17 and (case=='roster' or h.acquisitions[-1].target==6))
        private=condition_actor_state(source.private,lambda h:h.roles==seed.roles and (case=='roster' or h.acquisitions==seed.acquisitions))
        source=replace(source,private=private,physical=physical_board(source.public,private,source.physical));request=condition_request(prefix,source)
    if case=='observer':
        obs=SeerObserver(2,(),2,6)
        private=condition_actor_state(source.private,lambda h:obs(h,source.private))
        source=replace(source,private=private,observer=obs,physical=physical_board(source.public,private,source.physical));request=condition_request(prefix,source)
    return issue_scope(prefix.registry,prefix.engine,request,source),lambda req:seven_cold(prefix,req)


def forecast(engine,source):
    from werewolf.exact import legal_targets
    value=engine.solve(*source,physical=source.physical)
    targets=legal_targets(source.physical,engine.rules,engine.strategy)
    actions=tuple((p,engine.act(*source[:3],p,source.private,source.observer,physical=source.physical)) for p in targets)
    dawn=tuple((p,horizon_for_action(engine,source.public,source.public_state,source.past,p,source.private,observer=source.observer)) for p in targets)
    return Forecast(value,actions,dawn)


def tables(source,result):
    role_names=('wolf','medium','seer','hunter','villager');rows=[]
    for board in (source.public,source.physical):
        roles=[{r:board.role_probability(p,r) for r in role_names} for p in range(1,board.player_count+1)]
        rows.append(private_api_rows(roles,targets=dict(result.action_values),final_values=dict(result.action_values),dawn_for=dict(result.by_dawn_values).get))
    return tuple(rows)


def audit(case,*,inherited_groups=False):
    scope,cold=make_scope(case);src=scope.source
    original_public_groups=scope.groups
    with calculation_origin(scope.graph.data):
        before=time.perf_counter();baseline,old,public,weighted,children=named_value(scope);baseline_seconds=time.perf_counter()-before
        prepared=None;root_audit_seconds=0;inherited_preparation_seconds=0
        if inherited_groups:
            from .cut_out_publication_orbit_value import with_audited_groups,prepare
            from . import cut_out_publication_orbit_value as value_module
            from . import cut_out_structural_publications as producer_module
            from werewolf.board_future import GeneratedBoard
            from unittest.mock import patch
            before=time.perf_counter();scope=with_audited_groups(scope);root_audit_seconds=time.perf_counter()-before
            roles=GeneratedBoard.roles
            def no_parent(request):
                if request is scope.request:raise AssertionError('scope parent replay')
                return roles(request)
            before=time.perf_counter()
            with patch.object(value_module,'move_law',side_effect=AssertionError('private permutation')),patch.object(producer_module,'move_law',side_effect=AssertionError('public permutation')),patch.object(GeneratedBoard,'roles',no_parent):
                for i in range(3):prepared=prepare(scope)
            inherited_preparation_seconds=time.perf_counter()-before
        before=time.perf_counter();plan=PublicationOrbitValue(scope,prepared=prepared);value=plan.value();orbit_seconds=time.perf_counter()-before
        assert value==baseline
        assert plan.label_restorations==0 and plan.engine.audit['root_named_Boards']==0
        value_counts=dict(named_root_Boards=old.audit['root_named_Boards'],representative_root_Boards=plan.representative_Boards,
            named_positive_P_solve_roots=len(weighted),representative_positive_P_solve_roots=len(plan.representatives),
            named_solve_requests=old.audit['solve_requests'],orbit_solve_requests=plan.engine.audit['solve_requests'],
            named_actions=len(old.scalar_actions),orbit_actions=len(plan.engine.scalar_actions),named_value_states=len(old.values),orbit_value_states=len(plan.engine.values),
            named_future_Boards=old.audit['future_named_Boards'],orbit_future_Boards=plan.engine.audit['future_named_Boards'])
        by_label={publication_key(child.public,child.past):(mass,child) for mass,child in children}
        q_by_label={publication_key(b,past):q for q,b,s,past in public}
        restored={};reads=0;table_checks=0
        # Label Boards are first created here, only for requested Table/Tree
        # readback. No additional nonrepresentative solve occurs on plan.engine.
        start_solves=plan.engine.audit['solve_requests']
        for rep in plan.representatives:
            for mapping in mappings(rep.pattern,src.public.player_count):
                q,p_mass,child,result,request=plan.labelled(rep,mapping)
                key=publication_key(child.public,child.past);mass,expected=by_label[key]
                assert q==q_by_label[key] and p_mass==mass and child==expected
                assert key not in restored;restored[key]=child
                expected_forecast=forecast(old,expected)
                assert result==expected_forecast and tables(child,result)==tables(expected,expected_forecast);table_checks+=1
                rebuilt=cold(request);assert rebuilt==child;reads+=1
        assert len(restored)==len(weighted)
        # Forecast calls for representatives are lazy inspection work. The plan
        # never solves each transported label; cached representative forecasts
        # and exact target-index transport serve all labels.
        return dict(status='verified',case=case,village_win=str(value),public_groups=original_public_groups,evaluation_scope_groups=scope.groups,private_stabilizer=plan.groups,split_groups=plan.private_splits,
            q_patterns=len(plan.patterns),q_named_vectors=plan.named_Q_vectors,p_zero_patterns=plan.p_zero_patterns,
            value_only=value_counts,value_only_named_restorations=0,value_only_root_named_Boards=0,
            baseline_value_seconds=baseline_seconds,orbit_value_seconds=orbit_seconds,
            requested_label_restorations=plan.label_restorations,full_label_Forecast_QP_Table_checks=table_checks,independent_saved_origin_cold_reads=reads,
            full_QP_mass_and_forecast_equal=True,future_publication_backup='ordinary independent labelled recursion; prototype compresses ONE boundary only',
            full_initial7_search=False,inherited_groups_enabled=inherited_groups,
            root_audit_seconds=root_audit_seconds,inherited_preparation_seconds=inherited_preparation_seconds,
            inherited_group_counts={} if scope.group_ledger is None else dict(scope.group_ledger.stats))


def worker(case,*,inherited_groups=False):
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    try:
        with calculation_budget(4000000,max_seconds=30),independent_joint_values():row=audit(case,inherited_groups=inherited_groups)
    except CalculationBudgetExceeded:row=dict(status='unverified',case=case,reason='case_calculation_budget',budget_stop=budget_stop(),full_initial7_search=False)
    row.update(seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    suffix='-inherited' if inherited_groups else ''
    Path('benchmarks/player_match_groups/publication-orbit-value-'+case+suffix+'-results.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)

def recursive_audit(case):
    from .cut_out_publication_orbit_value import RecursivePublicationOracle,labelled_descendant
    from .cut_out_joint_night_forecast_fixture import moved_source
    scope,cold=make_scope(case.removesuffix('-sampled'));src=scope.source;timings={}
    with calculation_origin(scope.graph.data):
        with calculation_budget(4000000,max_seconds=25):
            start=time.perf_counter();baseline,old,public,weighted,children=named_value(scope);timings['named']=time.perf_counter()-start
        with calculation_budget(4000000,max_seconds=25):
            start=time.perf_counter();single=PublicationOrbitValue(scope);assert single.value()==baseline;timings['one_boundary']=time.perf_counter()-start
        with calculation_budget(4000000,max_seconds=25):
            e=RecursivePublicationOracle(scope);remember(e,scope.request,src)
            start=time.perf_counter();assert e.publication_value(src)==baseline;timings['recursive']=time.perf_counter()-start
        plans=tuple(e.plans);root=plans[0]
        counts=dict(named=dict(values=len(old.values),actions=len(old.scalar_actions)),one_boundary=dict(values=len(single.engine.values),actions=len(single.engine.scalar_actions)),recursive=dict(values=len(e.values),actions=len(e.scalar_actions)))
        boundaries={str(day):{k:n for (d,k),n in e.boundary_counts.items() if d==day} for day in sorted({d for d,k in e.boundary_counts})}
        labels=Counter();cold_reads=Counter();composed=0;nonidentity=0
        selected_plans=plans if not case.endswith('-sampled') else (root,)+tuple(p for p in plans[1:] if p.representatives)[:4]
        with calculation_budget(4000000,max_seconds=25):
            start=time.perf_counter()
            for plan in selected_plans:
                source=plan.scope.source;day=source.public.day
                rows=old.morning(source.public,source.public_state,source.past)
                own=old.push(source.public_state,source.private,rows)
                lookup={publication_key(b,p):(mass,ContinuationInputs(b,q,p,priv,source.observer,physical_board(b,priv,source.physical))) for mass,b,q,p,priv in own}
                qs={publication_key(b,p):q for q,b,law,p in rows}
                restored={}
                for row in plan.representatives:
                    for mapping in mappings(row.pattern,source.public.player_count):
                        q,mass,child,result,request=plan.labelled(row,mapping)
                        key=publication_key(child.public,child.past);expected_mass,expected=lookup[key]
                        assert q==qs[key] and mass==expected_mass and child==expected
                        expected_result=forecast(old,expected)
                        assert result==expected_result and tables(child,result)==tables(expected,expected_result)
                        assert key not in restored;restored[key]=child;labels[day]+=1
                        if plan is root or cold_reads[day]<4:
                            assert cold(request)==child;cold_reads[day]+=1
                assert len(restored)==len(own)
            # Compose an outer report-label map with later action and report
            # evidence. Never solve each outer label on the optimized engine.
            for root_row in root.representatives:
                options=list(mappings(root_row.pattern,src.public.player_count))
                if len(options)<2:continue
                descendants=[p for p in plans[1:] if p.scope.request.history[:len(root_row.request.history)]==root_row.request.history]
                if not descendants:continue
                later=next((p for p in descendants if p.representatives),None)
                if later is None:continue
                leaf=later.representatives[0];local=next(mappings(leaf.pattern,src.public.player_count))
                _,_,leaf_source,leaf_forecast,leaf_request=later.labelled(leaf,local)
                for outer in (options[0],options[-1]):
                    request=labelled_descendant(root,root_row,outer,leaf_request)
                    expected=moved_source(leaf_source,outer);actual=cold(request)
                    assert actual==expected
                    mapped=Forecast(leaf_forecast.village_win,tuple(sorted((outer[p-1],v) for p,v in leaf_forecast.action_values)),tuple(sorted((outer[p-1],v) for p,v in leaf_forecast.by_dawn_values)))
                    independent=forecast(old,expected)
                    assert mapped==independent and tables(expected,mapped)==tables(actual,independent)
                    composed+=1;nonidentity+=outer!=tuple(range(1,len(outer)+1))
                if composed>=8:break
            timings['detail_validation']=time.perf_counter()-start
        return dict(status='verified',case=case,village_win=str(baseline),seconds_by_phase=timings,value_only=counts,boundaries=boundaries,refusals=dict(e.refusals),
            selected_boundary_named_QP_mass_Forecast_Table_checks=dict(labels),computed_boundaries=len(plans),validated_boundaries=len(selected_plans),independent_cold_reads=dict(cold_reads),composed_two_boundary_cold_paths=composed,nonidentity_outer_composed_paths=nonidentity,
            full_initial7_search=False,public64_aggregate_retried=False,immutable_sharing=False,
            scope='recursive certified publication backup; ordinary labelled actions; unsupported preflight returns to ordinary morning')


def recursive_worker(case):
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    try:
        with independent_joint_values():row=recursive_audit(case)
    except CalculationBudgetExceeded:row=dict(status='unverified',case=case,reason='bounded_phase_budget',budget_stop=budget_stop())
    row.update(seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    Path('benchmarks/player_match_groups/publication-orbit-recursive-'+case+'-results.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)


def make_role_filter_scope(*,known_wolf=False):
    from .cut_out_model_a import InitialModelASpec
    from werewolf.exact import Rules
    from werewolf.seer_acquisition import SeerReport
    claims=('seer','wolf','latent','latent','latent') if known_wolf else ('seer',)+('latent',)*4
    spec=InitialModelASpec(5,claims,True,mediums=0,rules=Rules(initial_seer='random_white'),reports=(SeerReport(1,1,1,3,'white'),))
    graph=SavedCutOutGraph(adapt_model_a(spec));builder=CompactTerminalSmallEngine(graph)
    return issue_scope(graph,builder,graph.root,graph.origin())


def structural_audit():
    from .cut_out_publication_orbit_value import seed_structural,condition_known_role,require_structural,structural_request
    from .cut_out_structural_publications import require_groups
    from .cut_out_joint_night_forecast_fixture import moved_source
    from unittest.mock import patch
    from . import cut_out_publication_orbit_value as module
    from werewolf.seer_acquisition import Acquisition,Hypothesis,normalize
    scope=make_role_filter_scope();start=time.perf_counter();seed=seed_structural(scope);seed_seconds=time.perf_counter()-start
    full_checks=0;cold_reads=0;positive=0;zero=0;checks=0
    old=InitialReferenceEngine(scope.graph)
    with calculation_origin(scope.graph.data):
        for player in range(1,6):
            for role in ('wolf','medium','seer','villager'):
                view=OwnView(player,role)
                mass=sum((h.mass for h in scope.source.private.hypotheses if view.accepts(h)),F())
                if not mass:
                    try:condition_known_role(seed,player,role)
                    except Pending as error:assert error.reason=='role_filter_zero_private_support';zero+=1
                    else:raise AssertionError('zero support accepted')
                    continue
                proof=condition_known_role(seed,player,role);source=require_structural(proof)
                expected_private=condition_actor_state(scope.source.private,view.accepts)
                expected=replace(scope.source,private=expected_private,observer=view,physical=physical_board(scope.source.public,expected_private,scope.source.physical),board_data=None)
                assert source==expected and proof.private_mass==mass and source.public_state is scope.source.public_state
                # Independent complete comparisons are validation only, never
                # invoked by the structurally certified filter operation.
                require_groups(source.public,source.public_state,source.past,proof.groups)
                for group in proof.groups:
                    for p in group[1:]:
                        mapping=list(range(1,6));mapping[group[0]-1],mapping[p-1]=p,group[0];mapping=tuple(mapping)
                        assert moved_source(source,mapping)==source;full_checks+=1
                request=structural_request(proof);assert independent_cold(scope.graph,request)==source;cold_reads+=1
                result=forecast(old,expected)
                # Fresh common engine evaluates the certified carrier unchanged.
                fresh=InitialReferenceEngine(scope.graph);actual=forecast(fresh,source)
                assert actual==result and tables(source,actual)==tables(expected,result);checks+=1
                positive+=1
        # Prove that carrying/validating a receipt cannot invoke full symmetry
        # functions or replay the seed scope. Actual Bayesian filtering remains.
        proof=seed;start=time.perf_counter()
        with patch.object(module,'move_law',side_effect=AssertionError('full law comparison')),patch.object(module,'same_role_board',side_effect=AssertionError('physical comparison')),patch.object(module,'check_scope',side_effect=AssertionError('seed replay')):
            for i in range(32):proof=condition_known_role(proof,2,'villager');require_structural(proof)
        carry_seconds=time.perf_counter()-start
        assert set(proof.groups)=={(1,),(2,),(3,),(4,5)}
        # Concrete counterexample: fixed roles and physical marginal, unequal
        # own scan histories. A raw posterior cannot inherit a receipt.
        source=scope.source;h=next(h for h in source.private.hypotheses if h.roles[0]==2)
        history=tuple(replace(h,acquisitions=h.acquisitions+(Acquisition(2,1,t,'white'),),mass=F(1,2)) for t in (4,5))
        symmetric=replace(source.private,hypotheses=normalize(history),rosters=source.private.rosters+(source.public.alive,))
        asymmetric=condition_actor_state(symmetric,lambda h:h.acquisitions[-1].target==4)
        mapping=(1,2,3,5,4)
        assert move_law(asymmetric,mapping).public_roles==asymmetric.public_roles and move_law(asymmetric,mapping)!=asymmetric
        try:require_structural(replace(proof,source=replace(proof.source,private=asymmetric)))
        except Pending as error:assert error.reason=='role_filter_minted_receipt_required'
        else:raise AssertionError('arbitrary posterior certified')
    return dict(status='verified',scope='five original players; exact known-role private conditioning only',seed_full_audits=1,seed_seconds=seed_seconds,
        positive_role_conditions=positive,zero_support_declined=zero,complete_symmetry_validation_generators=full_checks,independent_Forecast_Table_checks=checks,independent_cold_reads=cold_reads,
        structural_carry_operations=32,structural_carry_seconds=carry_seconds,carry_full_law_comparisons=0,carry_seed_replays=0,remaining_group=proof.groups,
        private_role_mass=str(condition_known_role(seed,2,'villager').private_mass),Q_unchanged=True,asymmetric_same_role_marginal_rejected=True,
        recursive_engine_adopted=False,full_initial7_search=False,public64_aggregate_retried=False,immutable_sharing=False)


def structural_worker():
    start=time.perf_counter()
    with calculation_budget(4000000,max_seconds=20),independent_joint_values():row=structural_audit()
    row.update(seconds=time.perf_counter()-start,peak_working_set_bytes=peak_bytes())
    Path('benchmarks/player_match_groups/publication-orbit-structural-role-results.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)


def death_audit():
    from .cut_out_publication_orbit_value import seed_structural,require_structural,condition_known_role,known_villager_death,structural_request
    from .cut_out_joint_night_forecast_fixture import moved_source
    from . import cut_out_publication_orbit_value as module
    from werewolf.action_flow import resolve_action
    from werewolf.evaluation_branch import ActionInputs
    from werewolf.board_future import GeneratedBoard
    from unittest.mock import patch
    scope=make_role_filter_scope();seed=seed_structural(scope)
    parents=[(scope,seed,3)]
    for player in range(1,6):
        for role in ('wolf','medium','seer','villager'):
            if any(OwnView(player,role).accepts(h) for h in seed.source.private.hypotheses):parents.append((scope,condition_known_role(seed,player,role),3))
    known=make_role_filter_scope(known_wolf=True);known_seed=seed_structural(known)
    parents.extend((known,known_seed,target) for target in (4,5))
    metrics=Counter();roots={};checks=0;generators=0;copies=32
    timings=Counter()
    for graph_scope,parent,target in parents:
        source=require_structural(parent);request=structural_request(parent)
        with calculation_origin(graph_scope.graph.data):
            reference=InitialReferenceEngine(graph_scope.graph);remember(reference,request,source)
            payload=ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical)
            start=time.perf_counter();acquired,outcomes=resolve_action(source.public,payload,target,reference.action_policy,terminal_payoffs=False)
            assert len(outcomes)==1 and outcomes[0].probability==1
            expected=reference.action_policy.project(source.public,acquired,outcomes[0],target)
            timings['ordinary_resolve_reconstruct_seconds']+=time.perf_counter()-start
            with patch.object(module,'move_law',side_effect=AssertionError('full comparison')),patch.object(module,'same_role_board',side_effect=AssertionError('physical comparison')),patch.object(module,'check_scope',side_effect=AssertionError('seed replay')),patch.object(GeneratedBoard,'roles',side_effect=AssertionError('parent replay')),patch.object(module.InformationSetActionPolicy,'acquire',side_effect=AssertionError('day acquired secrets')):
                start=time.perf_counter();proof=known_villager_death(parent,target,stats=metrics);timings['structural_death_seconds']+=time.perf_counter()-start
                assert proof is not None
                for i in range(copies):assert require_structural(proof) is proof.source
            child=require_structural(proof)
            assert child==expected and proof.public_mass==1 and proof.private_mass==1 and proof.choice_probability==F(1,5)
            # Entire laws and metadata must survive this deterministic daytime
            # event, rather than retaining merely role marginals.
            assert child.public_state==source.public_state and child.private==source.private and child.past==source.past
            for group in proof.groups:
                for p in group[1:]:
                    mapping=list(range(1,6));mapping[group[0]-1],mapping[p-1]=p,group[0]
                    assert moved_source(child,tuple(mapping))==child;generators+=1
            result=forecast(reference,expected);fresh=InitialReferenceEngine(graph_scope.graph)
            actual=forecast(fresh,child)
            assert actual==result and tables(child,actual)==tables(expected,result)
            assert independent_cold(graph_scope.graph,structural_request(proof))==child
            checks+=1
            if parent is seed:roots['death']=proof
            if parent.selector==(2,'villager'):roots['own_before_death']=proof
            if graph_scope is known:
                assert (4,5) in parent.groups and all(target not in g or len(g)==1 for g in proof.groups)
    # Role knowledge and a certain-villager death commute in this exact scope.
    later=condition_known_role(roots['death'],2,'villager')
    assert later.source==roots['own_before_death'].source
    assert independent_cold(scope.graph,structural_request(later))==later.source
    # A valid but outside-scope selected action declines; caller retains the
    # ordinary full named event distribution, with no uniform substitution.
    with calculation_origin(scope.graph.data):
        assert known_villager_death(seed,2) is None
        normal=InitialReferenceEngine(scope.graph);remember(normal,scope.request,scope.source)
        s=scope.source;payload=ActionInputs(s.public_state,s.past,s.private,s.observer,s.physical)
        _,ordinary=resolve_action(s.public,payload,2,normal.action_policy,terminal_payoffs=False)
        assert len(ordinary)==2 and sum((o.probability for o in ordinary),F())==1
        own=condition_known_role(seed,2,'villager');s=own.source
        assert known_villager_death(own,2) is None  # P knows; Q does not.
        normal=InitialReferenceEngine(scope.graph);remember(normal,structural_request(own),s)
        payload=ActionInputs(s.public_state,s.past,s.private,s.observer,s.physical)
        _,physical=resolve_action(s.public,payload,2,normal.action_policy,terminal_payoffs=False)
        public=normal.public_children(s.public,2,s.public_state)
        q_continue=sum((o.probability for o in public if o.board.winner is None),F())
        p_continue=sum((o.probability for o in physical if o.board.winner is None),F())
        assert q_continue==F(2,3) and p_continue==1
    return dict(status='verified',scope='Day1 five alive W1/S1/V3/H0/M0; target villager in Q and P; uniform configured strategy',
        seed_full_audits=2,certified_named_deaths=checks,public_and_personal_Forecast_Table_checks=checks,independent_cold_reads=checks+1,
        residual_complete_symmetry_generators=generators,receipt_only_rechecks=checks*copies,death_full_symmetry_comparisons=0,death_parent_replays=0,death_acquisition_calls=0,
        Q_death_chance='1',P_death_chance='1',separate_uniform_choice='1/5',complete_QP_histories_unchanged=True,
        semantic_visits_and_projection_cost=dict(metrics),timings=dict(timings),
        explicit_endpoint_split_targets=[4,5],outside_scope_ordinary_branches=len(ordinary),outside_scope_P_only_known_Q_continue=str(q_continue),outside_scope_P_only_known_P_continue=str(p_continue),role_death_order_commutes=True,
        full_initial7_search=False,public64_aggregate_retried=False,recursive_engine_adopted=False,immutable_sharing=False)


def death_worker():
    start=time.perf_counter()
    with calculation_budget(4000000,max_seconds=20),independent_joint_values():row=death_audit()
    row.update(seconds=time.perf_counter()-start,peak_working_set_bytes=peak_bytes())
    Path('benchmarks/player_match_groups/publication-orbit-structural-death-results.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)


def seven_coverage_audit(*,track_provenance=False):
    """Verification-only census of physical kernels; never Forecast/solve/MAX."""
    from .cut_out_first_cycle_coverage import base
    from .cut_out_joint_night_forecast_fixture import moved_source
    from .cut_out_user_seven_source import ROOT_GROUPS
    from .cut_out_day_night import point_fix
    from werewolf.action_flow import resolve_action
    from werewolf.evaluation_branch import ActionInputs
    from werewolf.seer_acquisition import acquire,normalize
    from werewolf.information_set_forecast import InformationSetForecast
    from itertools import product
    from .cut_out_user_seven_uniform_preparation import comparison_game
    original,uniform=comparison_game()
    registry,witness=base();root=registry.origin()
    def no_value(*args,**kwargs):raise AssertionError('coverage audit must not solve/act')
    def ordinary_engine(track=False):
        e=InformationSetForecast(registry.engine.baseline.rules,registry.engine.baseline.strategy,exact_renaming=False,retire_uninformative_scans=False,track_acquisition_provenance=track)
        e.retain_joint_guard_history=True;e.solve=e.act=no_value;return e
    def instructed_reference(law,alive):
        # Independent route: exhaustively select each deterministic legal
        # instruction, call acquire(), then mix instruction masses. Never call
        # acquire_uniform or its candidate helper in this reference.
        records=[];instructions=0;domain=law.rosters[0]
        for h in law.hypotheses:
            owners=tuple(p for p in alive if h.roles[2]&(1<<(p-1)))
            assert law.tracked is None or all(p in law.tracked for p in owners)
            options=[]
            for player in owners:
                legal=set(domain)-{player};seen={a.target for a in h.acquisitions if a.player==player}
                options.append(tuple(sorted(legal-seen or legal)))
            count=1
            for choices in options:count*=len(choices)
            for targets in product(*options):
                row=acquire((replace(h,mass=F(1)),),len(law.rosters)+1,alive,dict(zip(owners,targets)),target_players=domain)
                records.extend(replace(v,mass=v.mass*h.mass/count) for v in row);instructions+=1
        return replace(law,hypotheses=normalize(records),rosters=law.rosters+(alive,)),instructions
    def same_source(left,right):
        return (same_role_board(left.public,right.public) and same_role_board(left.physical,right.physical)
            and all(getattr(left,k)==getattr(right,k) for k in ('public_state','private','past','observer')))
    seer1_record=next(a for h in root.private.hypotheses if h.roles[2]&1 for a in h.acquisitions if a.player==1)
    contexts=[];day_checks=0;kernel_checks=0;symmetry_checks=0;instruction_count=0;input_rows=0;output_rows=0;seconds=Counter();negative=None;lineage=Counter()
    with calculation_origin(registry.data):
        for target in range(1,8):
            e=ordinary_engine();remember(e,registry.root,root)
            payload=ActionInputs(root.public_state,root.past,root.private,None,root.physical)
            acquired,outcomes=resolve_action(root.public,payload,target,e.action_policy,terminal_payoffs=False)
            assert acquired==payload and len(outcomes)==1 and outcomes[0].probability==1 and outcomes[0].board.winner is None
            night=e.action_policy.project(root.public,acquired,outcomes[0],target)
            assert night.public_state==root.public_state and night.private==root.private
            groups=point_fix(ROOT_GROUPS,target);day_checks+=1
            for view in (None,OwnView(1,'seer',(seer1_record,))):
                if view is None:source=night;private_groups=groups
                else:
                    # All true-seer1 initial records are the published white4.
                    own=condition_actor_state(night.private,view.accepts)
                    source=replace(night,private=own,observer=view,physical=physical_board(night.public,own,night.physical),board_data=None)
                    private_groups=point_fix(groups,1,4)
                e=ordinary_engine(track_provenance);payload=ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical)
                permutations=[]
                for group in private_groups:
                    for position in group[1:]:
                        mapping=list(range(1,8));mapping[group[0]-1],mapping[position-1]=position,group[0]
                        mapping=tuple(mapping)
                        assert same_source(moved_source(source,mapping),source)
                        permutations.append(mapping)
                if track_provenance:
                    # This verification adapter has just completed the full
                    # input audit. The runtime ledger never invents a root.
                    receipt=e.acquisition_provenance._register_audited_root(source.public,payload,private_groups,(registry,registry.data))
                    payload=replace(payload,provenance=receipt)
                start=time.perf_counter();actual=e.action_policy.acquire(source.public,payload);seconds['common_acquisition']+=time.perf_counter()-start
                if track_provenance:
                    from unittest.mock import patch
                    from werewolf.seer_future_uniform import TrueScanState
                    from werewolf.board_future import GeneratedBoard
                    if view is None:
                        assert actual.provenance is not None
                        with patch.object(TrueScanState,'__eq__',side_effect=AssertionError('lineage full equality')),patch.object(TrueScanState,'__hash__',side_effect=AssertionError('lineage full hashing')),patch.object(GeneratedBoard,'roles',side_effect=AssertionError('lineage parent replay')):
                            for i in range(32):
                                assert e.acquisition_provenance.validates(actual.provenance,source.public,payload,actual)
                                assert e.acquisition_provenance.groups_for(actual.provenance,source.public,actual)==private_groups
                    else:assert actual.provenance is None
                    lineage.update(e.acquisition_provenance.stats)
                start=time.perf_counter();q,qn=instructed_reference(source.public_state,source.public.alive);p,pn=instructed_reference(source.private,source.public.alive);seconds['deterministic_instruction_reference']+=time.perf_counter()-start
                instruction_count+=qn+pn
                assert actual.public_state==q and actual.private==p and actual.physical==source.physical and actual.observer==source.observer
                assert q.public_roles==source.public_state.public_roles and p.public_roles==source.private.public_roles
                input_rows+=len(source.public_state.hypotheses)+len(source.private.hypotheses);output_rows+=len(q.hypotheses)+len(p.hypotheses);kernel_checks+=1
                generated=replace(source,public_state=q,private=p,physical=actual.physical,board_data=None)
                for mapping in permutations:
                    assert same_source(moved_source(generated,mapping),generated);symmetry_checks+=1
                contexts.append(dict(executed=target,view='public' if view is None else 'true_seer1_with_initial_white4',groups=private_groups,Q_before=len(source.public_state.hypotheses),P_before=len(source.private.hypotheses),Q_after=len(q.hypotheses),P_after=len(p.hypotheses)))
                if target==3 and view is not None:negative=generated
        # Observing a privately selected target is NOT the unobserved mixture.
        observed=condition_actor_state(negative.private,lambda h:any(a.day==2 and a.player==1 and a.target==6 for a in h.acquisitions))
        mapping=(1,2,3,4,5,7,6)
        assert observed.public_roles==negative.private.public_roles
        assert move_law(observed,mapping).public_roles==observed.public_roles and move_law(observed,mapping)!=observed
        assert move_law(observed,(1,2,3,4,7,6,5))==observed
    return dict(status='verified',scope='actual seven-player cast/CO/white4 snapshot; explicit uniform comparison only',cast=dict(villagers=3,mediums=1,seers=1,wolves=2,hunters=0),
        original_strategy=original['policy'],tested_strategy=uniform['policy'],first_execution_targets=7,day_full_law_continuations=day_checks,
        QP_acquisition_contexts=kernel_checks,independent_deterministic_instructions=instruction_count,complete_source_and_output_symmetry_generators=symmetry_checks,
        input_hypotheses=input_rows,output_hypotheses=output_rows,timings=dict(seconds),contexts=contexts,
        observed_target6_same_role_marginal_breaks_swap67=True,observed_target6_preserves_swap57=True,
        role_certainty_required=False,typed_acquisition_receipt_implemented=track_provenance,parent_replay_avoidance_implemented=False,
        new_evaluator_implemented=False,kernel_lineage_enabled=track_provenance,kernel_lineage_counts=dict(lineage),
        parent_groups_audited_before_registration=track_provenance,full_cycle_group_inheritance_implemented=False,
        kernel_lineage_root_symmetry_proved=False,solve_calls=0,act_calls=0,MAX_evaluated=False,full_initial7_search=False,public64_aggregate_retried=False,immutable_sharing=False)


def seven_coverage_worker():
    start=time.perf_counter()
    with calculation_budget(4000000,max_seconds=20),independent_joint_values():row=seven_coverage_audit(track_provenance=True)
    row.update(seconds=time.perf_counter()-start,peak_working_set_bytes=peak_bytes())
    Path('benchmarks/player_match_groups/publication-orbit-seven-coverage-results.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:v for k,v in row.items() if k!='contexts'}),flush=True)


def shared_transition_audit():
    """One common H0 transition implementation, independent named oracles.

    Five-player branches finish; actual-seven paths use finite observations and
    only forecast final three-alive nodes. No initial-seven value recursion.
    """
    from .cut_out_publication_orbit_value import seed_structural,scope_from_inherited,prepare,private_stabilizer
    from .cut_out_first_cycle_coverage import base
    from .cut_out_user_seven_source import ROOT_GROUPS
    from .cut_out_day_night import point_fix
    from .cut_out_joint_night_forecast_fixture import moved_source
    from . import cut_out_publication_orbit_value as value_module
    from . import cut_out_structural_publications as producer_module
    from werewolf.action_flow import resolve_action
    from werewolf.evaluation_branch import ActionInputs
    from werewolf.board_future import condition_recipe,PublicViewEvidence,PublicationEvidence,GeneratedBoard,kernel_snapshot,publication_key
    from werewolf.exact import legal_targets,report_actions
    from unittest.mock import patch
    from werewolf.seer_future_uniform import TrueScanState
    counts=Counter();totals=Counter();cases=[];forecast_jobs=[]
    def same(a,b):
        return (same_role_board(a.public,b.public) and same_role_board(a.physical,b.physical)
            and all(getattr(a,k)==getattr(b,k) for k in ('public_state','private','past','observer')))
    def engine(graph,tracked):
        e=InformationSetForecast(graph.engine.baseline.rules,graph.engine.baseline.strategy,exact_renaming=False,
            retire_uninformative_scans=False,track_acquisition_provenance=tracked)
        e.retain_joint_guard_history=True;return e
    def build(graph,source,request,groups,private_filter=None):
        if private_filter is not None:
            own=condition_actor_state(source.private,private_filter)
            desired=replace(source,private=own,physical=physical_board(source.public,own,source.physical),board_data=None)
            op=condition_recipe(source,desired);assert op is not None
            request=request.child(op,None);source=desired
        rebuilt=request.roles();assert same(rebuilt,source);source=rebuilt
        for group in groups:
            for p in group[1:]:
                m=list(range(1,source.public.player_count+1));m[group[0]-1],m[p-1]=p,group[0]
                assert same(moved_source(source,tuple(m)),source);counts['root_full_generators']+=1
        a=engine(graph,True);r=engine(graph,False)
        token=a.acquisition_provenance._register_audited_root(source.public,source,groups,(graph,graph.data),request=request)
        actual=replace(source,provenance=token,board_data=request);reference=replace(source,provenance=None,board_data=request)
        remember(a,request,actual);remember(r,request,reference);counts['audited_roots']+=1
        return a,r,actual,reference
    def inspect(graph,a,actual,expected,*,value=False):
        assert same(actual,expected);counts['complete_QP_history_physical_checks']+=1
        groups=a.acquisition_provenance.groups_for(actual.provenance,actual.public,actual)
        assert groups is not None
        for group in groups:
            for p in group[1:]:
                m=list(range(1,actual.public.player_count+1));m[group[0]-1],m[p-1]=p,group[0]
                assert same(moved_source(actual,tuple(m)),actual);counts['independent_child_symmetry_generators']+=1
        assert same(independent_cold(graph,actual.board_data),actual);counts['cold_reads']+=1
        with patch.object(TrueScanState,'__eq__',side_effect=AssertionError('proof full equality')),patch.object(TrueScanState,'__hash__',side_effect=AssertionError('proof full hashing')),patch.object(value_module,'move_law',side_effect=AssertionError('private recheck')),patch.object(GeneratedBoard,'roles',side_effect=AssertionError('parent replay')):
            cap=scope_from_inherited(graph,a,actual);assert cap is not None
            private_stabilizer(cap)
        if value:forecast_jobs.append((graph,a,actual,expected))
    def step(graph,a,r,actual,expected,target,*,values=False):
        p=ActionInputs(actual.public_state,actual.past,actual.private,actual.observer,actual.physical,provenance=actual.provenance)
        rp=ActionInputs(expected.public_state,expected.past,expected.private,expected.observer,expected.physical)
        with patch.object(GeneratedBoard,'roles',side_effect=AssertionError('live death replay')):
            acquired,outcomes=resolve_action(actual.public,p,target,a.action_policy,terminal_payoffs=False)
            children=[a.action_policy.project(actual.public,acquired,o,target) for o in outcomes]
        ra,reference_outcomes=resolve_action(expected.public,rp,target,r.action_policy,terminal_payoffs=False)
        assert acquired.public_state==ra.public_state and acquired.private==ra.private
        result=[];qout={o.board.winner:o for o in r.public_children(expected.public,target,expected.public_state)}
        for o,c in zip(outcomes,children):
            ro=next(v for v in reference_outcomes if v.board.winner==o.board.winner)
            assert o.probability==ro.probability
            rc=r.action_policy.project(expected.public,ra,ro,target)
            assert c.provenance.public_mass==qout[o.board.winner].probability
            assert c.provenance.private_mass==ro.probability
            inspect(graph,a,c,rc,value=values)
            counts['day_deaths' if actual.public.phase=='day' else 'night_deaths']+=1
            result.append((o,c,rc))
        counts['public_only_death_rows']+=len(a.acquisition_provenance.public_only_deaths(actual.public,acquired,target))
        return result
    def reports(graph,a,r,actual,expected,*,values=False,prepare_input=False):
        if prepare_input:
            cap=scope_from_inherited(graph,a,actual);assert cap is not None
            with patch.object(value_module,'move_law',side_effect=AssertionError('private recheck')),patch.object(producer_module,'move_law',side_effect=AssertionError('public recheck')),patch.object(GeneratedBoard,'roles',side_effect=AssertionError('live preparation replay')):
                prepare(cap);prepare(cap)
        with patch.object(GeneratedBoard,'roles',side_effect=AssertionError('live report replay')):
            rows=a.report_children(actual)
        reference=r.report_children(expected)
        assert len(rows)==len(reference)
        bykey={publication_key(c.public,c.past):(q,p,c) for q,p,c in reference}
        for q,p,c in rows:
            rq,rp,rc=bykey[publication_key(c.public,c.past)]
            assert q==rq and p==rp
            if c is actual:counts['identity_mornings']+=1
            else:
                assert c.provenance.public_mass==q and c.provenance.private_mass==p
                counts['report_children']+=1
            inspect(graph,a,c,rc,value=values)
        raw=a.morning(actual.public,actual.public_state,actual.past)
        only=a.acquisition_provenance.public_only_reports(actual,raw)
        counts['public_only_report_rows']+=len(only)
        if only:
            # Ordinary explicit public counterfactual, never invented actual P.
            q,b,law,past=only[0]
            request=actual.board_data.child(PublicViewEvidence(),None).child(PublicationEvidence(kernel_snapshot(r),publication_key(b,past)),None)
            public=independent_cold(graph,request)
            assert public.public_state==law and public.private==law;counts['public_only_cold_reads']+=1
        return rows,bykey
    small=make_role_filter_scope();seed=seed_structural(small)
    for private in (False,True):
        with calculation_origin(small.graph.data):
            groups=point_fix(seed.groups,2) if private else seed.groups
            a,r,source,reference=build(small.graph,seed.source,small.request,groups,
                (lambda h:not h.roles[0]&2) if private else None)
            day=step(small.graph,a,r,source,reference,2,values=True)
            continuing=next((c,rc) for o,c,rc in day if c.public.winner is None)
            for target in legal_targets(continuing[0].physical,a.rules,a.strategy):
                night=step(small.graph,a,r,*continuing,target)
                for o,c,rc in night:
                    assert all(any(v.day==2 for v in h.acquisitions) for h in c.private.hypotheses)
                    reports(small.graph,a,r,c,rc,values=True,prepare_input=True)
            cases.append(dict(case='five-private-city2' if private else 'five-public',stats=dict(a.acquisition_provenance.stats)))
    for private in (False,True):
        graph,witness=base();source=graph.origin();groups=point_fix(ROOT_GROUPS,1,6) if private else ROOT_GROUPS
        with calculation_origin(graph.data):
            a,r,source,reference=build(graph,source,graph.root,groups,(lambda h:h.roles[0]==33) if private else None)
            _,source,reference=next(v for v in step(graph,a,r,source,reference,1) if v[1].public.winner is None)
            _,source,reference=next(v for v in step(graph,a,r,source,reference,4) if v[1].public.winner is None)
            rows,lookup=reports(graph,a,r,source,reference)
            selected=next((q,p,c) for q,p,c in rows if any(v.reporter==3 and v.target==1 and v.color=='black' for v in c.public.reports)
                and any(v.player==2 and v.acquired_day==2 and v.target==5 and v.color=='white' for v in c.past))
            q,p,source=selected;reference=lookup[publication_key(source.public,source.past)][2]
            cases.append(dict(case='seven-private-W1-6' if private else 'seven-public',selected_first_report_Q=str(q),selected_first_report_P=str(p)))
            _,source,reference=next(v for v in step(graph,a,r,source,reference,5) if v[1].public.winner is None)
            _,source,reference=next(v for v in step(graph,a,r,source,reference,3) if v[1].public.winner is None)
            assert len(source.public.alive)==3 and len(source.public_state.rosters)==3
            assert all(any(v.day==3 for v in h.acquisitions) and len(h.attacks)==2 for h in source.private.hypotheses)
            reports(graph,a,r,source,reference,values=True,prepare_input=True)
            cases[-1]['stats']=dict(a.acquisition_provenance.stats)
    # Only completed tiny continuations are valued, after the raw chain was
    # checked. Actual-seven initial/intermediate states are never forecast.
    for graph,a,source,expected in forecast_jobs:
        with calculation_origin(graph.data):
            fresh=engine(graph,False)
            remember(fresh,expected.board_data,expected)
            remember(a,source.board_data,source)
            want=forecast(fresh,expected);got=forecast(a,source)
            assert got==want and tables(source,got)==tables(expected,want)
            counts['independent_Forecast_Table_checks']+=1
    for case in cases:totals.update(case.get('stats',{}))
    return dict(status='verified',counts=dict(counts),proof_counts=dict(totals),cases=cases,
        generated_operations='generic H0 fixed-target day/night kernels and configured uniform medium/seer reports',
        choice_probability='fixed-target receipt excludes selection; typed H0 uniform actor choices certified separately in owner_information',
        whole_initial7_search=False,MAX_evaluated=False,default_provenance=False,immutable_sharing=False)



def owner_information_audit():
    """Finite owner/wolf kernels, no initial-seven scalar search."""
    from .cut_out_publication_orbit_value import seed_structural,scope_from_inherited,private_stabilizer
    from .cut_out_first_cycle_coverage import base
    from .cut_out_user_seven_source import ROOT_GROUPS
    from .cut_out_joint_night_forecast_fixture import moved_source
    from . import cut_out_publication_orbit_value as value_module
    from werewolf.actor_information import PersonalInformation,WolfInformation,condition_personal,wolf_information_groups
    from werewolf.seer_intervention import SeerObserver
    from werewolf.action_flow import resolve_action
    from werewolf.evaluation_branch import ActionInputs
    from werewolf.board_future import GeneratedBoard,publication_key
    from werewolf.seer_future_uniform import TrueScanState
    from unittest.mock import patch
    counts=Counter();stats=Counter();cases=[]
    def same(a,b):
        return (same_role_board(a.public,b.public) and same_role_board(a.physical,b.physical)
            and all(getattr(a,k)==getattr(b,k) for k in ('public_state','private','past','observer')))
    def engine(graph,track):
        e=InformationSetForecast(graph.engine.baseline.rules,graph.engine.baseline.strategy,exact_renaming=False,
            retire_uninformative_scans=False,track_acquisition_provenance=track)
        e.retain_joint_guard_history=True;return e
    def check(graph,e,a,b):
        assert same(a,b);counts['complete_QP_history_physical_checks']+=1
        assert same(independent_cold(graph,a.board_data),a);counts['cold_reads']+=1
        assert e.acquisition_provenance.groups_for(a.provenance,a.public,a) is not None
        # Complete law comparisons belong only to this independent oracle.
        groups=e.acquisition_provenance.groups_for(a.provenance,a.public,a)
        for group in groups:
            for p in group[1:]:
                m=list(range(1,a.public.player_count+1));m[group[0]-1],m[p-1]=p,group[0]
                assert same(moved_source(a,tuple(m)),a);counts['independent_symmetry_generators']+=1
        with patch.object(TrueScanState,'__eq__',side_effect=AssertionError('proof equality')),patch.object(TrueScanState,'__hash__',side_effect=AssertionError('proof hash')),patch.object(value_module,'move_law',side_effect=AssertionError('private permutation')),patch.object(GeneratedBoard,'roles',side_effect=AssertionError('parent replay')):
            cap=scope_from_inherited(graph,e,a);assert cap is not None
            private_stabilizer(cap)
    def death(graph,e,r,a,b,target):
        pa=ActionInputs(a.public_state,a.past,a.private,a.observer,a.physical,provenance=a.provenance)
        pb=ActionInputs(b.public_state,b.past,b.private,b.observer,b.physical)
        with patch.object(GeneratedBoard,'roles',side_effect=AssertionError('death replay')):
            ac,outs=resolve_action(a.public,pa,target,e.action_policy,terminal_payoffs=False)
            rows=[(o,e.action_policy.project(a.public,ac,o,target)) for o in outs]
        rc,ros=resolve_action(b.public,pb,target,r.action_policy,terminal_payoffs=False)
        if ac.provenance is not None and a.public.phase=='night':
            generated=r.acquire(b.public,b.private)
            expected_mass=sum((h.mass for h in generated.hypotheses if b.observer is None or b.observer(h,generated)),F())
            assert ac.provenance.observation_mass==expected_mass
            counts['observed_or_unobserved_acquisitions']+=1
        result=[]
        for o,c in rows:
            ro=next(v for v in ros if v.board.winner==o.board.winner)
            assert o.probability==ro.probability
            ref=r.action_policy.project(b.public,rc,ro,target)
            check(graph,e,c,ref);result.append((c,ref))
        return result
    def reports(graph,e,r,a,b):
        with patch.object(GeneratedBoard,'roles',side_effect=AssertionError('report replay')):rows=e.report_children(a)
        refs={publication_key(c.public,c.past):(q,p,c) for q,p,c in r.report_children(b)}
        for q,p,c in rows:
            rq,rp,ref=refs[publication_key(c.public,c.past)];assert(q,p)==(rq,rp)
            check(graph,e,c,ref)
        return rows,refs
    small=make_role_filter_scope();seed=seed_structural(small)
    graph7,witness=base()
    sources=[('five',small.graph,seed.source,small.request,seed.groups),('seven',graph7,graph7.origin(),graph7.root,ROOT_GROUPS)]
    for name,graph,root,request,groups in sources:
        with calculation_origin(graph.data):
            for group in groups:
                for p in group[1:]:
                    m=list(range(1,root.public.player_count+1));m[group[0]-1],m[p-1]=p,group[0]
                    assert same(moved_source(root,tuple(m)),root)
            e=engine(graph,True);r=engine(graph,False)
            token=e.acquisition_provenance._register_audited_root(root.public,root,groups,(graph,graph.data),request=request)
            actual=replace(root,provenance=token,board_data=request);reference=replace(root,board_data=request)
            remember(e,request,actual);remember(r,request,reference)
            owner=1 if name=='five' else 2
            h=next(h for h in root.private.hypotheses if h.roles[2]&(1<<(owner-1)))
            known=tuple(a for a in h.acquisitions if a.player==owner)
            information=PersonalInformation(owner,'seer',known)
            with patch.object(GeneratedBoard,'roles',side_effect=AssertionError('information replay')):
                mass,own=e.personal_view(actual,information)
            rmass,law=condition_personal(reference.private,information);assert mass==rmass
            ref=replace(reference,private=law,observer=information,physical=physical_board(reference.public,law,reference.physical))
            remember(r,own.board_data,ref);check(graph,e,own,ref)
            assert own.public_state is actual.public_state
            own,ref=next((c,rc) for c,rc in death(graph,e,r,own,ref,2 if name=='five' else 1) if c.public.winner is None)
            # Existing intervention type: predeath owner scan; no secret from
            # another actor enters either the public acquisition or wolf policy.
            intervention=SeerObserver(owner,known,2,4 if name=='five' else 5)
            mass,own=e.personal_view(own,intervention)
            rmass,law=condition_personal(ref.private,intervention);assert mass==rmass
            ref=replace(ref,private=law,observer=intervention,physical=physical_board(ref.public,law,ref.physical))
            remember(r,own.board_data,ref);check(graph,e,own,ref)
            night_owner,night_reference=own,ref
            with patch.object(GeneratedBoard,'roles',side_effect=AssertionError('wolf information replay')):choices=e.wolf_choices(own)
            expected=[]
            for info,p_mass,group in wolf_information_groups(ref.private):
                for target,q in r.wolf_policy(ref.public,ref.public_state,ref.past,info.initial_roster,info.attacks):
                    expected.append((p_mass*q,info,target,q,group))
            assert len(choices)==len(expected)
            for (mass,c,target,proof),(want,info,rt,q,group) in zip(choices,expected):
                assert(mass,target,c.private)==(want,rt,group)
                assert proof is not None and proof.probability==q
                assert proof.information_mass*q==mass
                qmass,qgroup=condition_personal(ref.public_state,info)
                assert proof.public_information_mass==qmass
                # Only reference fields/short descriptors checked at consumption.
                with patch.object(TrueScanState,'__eq__',side_effect=AssertionError('choice equality')),patch.object(TrueScanState,'__hash__',side_effect=AssertionError('choice hash')),patch.object(GeneratedBoard,'roles',side_effect=AssertionError('choice replay')):
                    assert e.acquisition_provenance.validates_choice(proof,c)
                counts['independent_wolf_choice_mass_checks']+=1
                if proof.public_information_mass!=proof.information_mass:counts['distinct_QP_information_weights']+=1
                refgroup=replace(ref,private=group,physical=physical_board(ref.public,group,ref.physical))
                check(graph,e,c,refgroup)
            # Continue on the unpartitioned owner law: choice is separate from
            # fixed-target resolution; day/night receipts retain that contract.
            own,ref=next((c,rc) for c,rc in death(graph,e,r,own,ref,owner if name=='five' else 4) if c.public.winner is None)
            assert any(a.player==owner and a.day==2 for h in own.private.hypotheses for a in h.acquisitions)
            rows,refs=reports(graph,e,r,own,ref)
            if name=='seven':
                q,p,own=next(row for row in rows if any(v.reporter==3 and v.target==1 and v.color=='black' for v in row[2].public.reports)
                    and any(v.player==2 and v.acquired_day==2 and v.target==5 and v.color=='white' for v in row[2].past))
                ref=refs[publication_key(own.public,own.past)][2]
                own,ref=next((c,rc) for c,rc in death(graph,e,r,own,ref,5) if c.public.winner is None)
                own,ref=next((c,rc) for c,rc in death(graph,e,r,own,ref,3) if c.public.winner is None)
                rows,refs=reports(graph,e,r,own,ref)
            for q,p,own in rows:
                ref=refs[publication_key(own.public,own.past)][2]
                if own.public.winner is None and len(own.public.alive)>4:continue
                remember(r,own.board_data,ref)
                got=forecast(e,own);want=forecast(r,ref)
                assert got==want and tables(own,got)==tables(ref,want)
                counts['independent_Forecast_Table_checks']+=1
            if name=='five':
                got=forecast(e,night_owner);want=forecast(r,night_reference)
                assert got==want and tables(night_owner,got)==tables(night_reference,want)
                counts['independent_Forecast_Table_checks']+=1
                assert e.acquisition_provenance.stats['uniform_wolf_solve_uses']>0
            stats.update(e.acquisition_provenance.stats)
            cases.append(dict(case=name,owner=owner,stats=dict(e.acquisition_provenance.stats)))
    return dict(status='verified',counts=dict(counts),proof_counts=dict(stats),cases=cases,
        scope='typed role/own-result observation, existing own scan intervention, H0 uniform wolf information/choice',
        full_initial7_search=False,MAX_evaluated=False,default_provenance=False)



if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='recursive':recursive_worker(sys.argv[2])
    elif len(sys.argv)>1 and sys.argv[1]=='structural-role':structural_worker()
    elif len(sys.argv)>1 and sys.argv[1]=='structural-death':death_worker()
    elif len(sys.argv)>1 and sys.argv[1]=='seven-coverage':seven_coverage_worker()
    elif len(sys.argv)>1 and sys.argv[1]=='inherited-groups':
        from .closed_calculation_fixture import audit as closed_audit,run as closed_measure
        if '--reference' in sys.argv:raise SystemExit('Ledger reference comparison is historical; use measure_shared_transition.compare_boundary directly')
        if '--measure' in sys.argv:
            if '--wolf-cells' in sys.argv:
                from .wolf_cell_fixture import measure as wolf_cell_measure
                print(json.dumps(wolf_cell_measure()['summary']))
            elif '--representatives' in sys.argv:
                from .representative_target_fixture import measure as representative_measure
                print(json.dumps(representative_measure()['summary']))
            elif '--saved-history' in sys.argv:
                from .closed_saved_history_fixture import measure as saved_history_measure
                saved_history_measure()
            elif '--saved-day' in sys.argv:
                from .closed_saved_day_fixture import run as saved_day_measure
                saved_day_measure()
            else:closed_measure()
        elif '--wolf-cells' in sys.argv:
            from .wolf_cell_fixture import audit as wolf_cell_audit
            print(json.dumps(wolf_cell_audit()))
        elif '--representatives' in sys.argv:
            from .representative_target_fixture import audit as representative_audit
            print(json.dumps(representative_audit()))
        else:closed_audit()
    else:worker(sys.argv[1] if len(sys.argv)>1 else 'five')
