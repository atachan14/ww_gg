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


def audit(case):
    scope,cold=make_scope(case);src=scope.source
    with calculation_origin(scope.graph.data):
        before=time.perf_counter();baseline,old,public,weighted,children=named_value(scope);baseline_seconds=time.perf_counter()-before
        before=time.perf_counter();plan=PublicationOrbitValue(scope);value=plan.value();orbit_seconds=time.perf_counter()-before
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
        return dict(status='verified',case=case,village_win=str(value),public_groups=scope.groups,private_stabilizer=plan.groups,split_groups=plan.private_splits,
            q_patterns=len(plan.patterns),q_named_vectors=plan.named_Q_vectors,p_zero_patterns=plan.p_zero_patterns,
            value_only=value_counts,value_only_named_restorations=0,value_only_root_named_Boards=0,
            baseline_value_seconds=baseline_seconds,orbit_value_seconds=orbit_seconds,
            requested_label_restorations=plan.label_restorations,full_label_Forecast_QP_Table_checks=table_checks,independent_saved_origin_cold_reads=reads,
            full_QP_mass_and_forecast_equal=True,future_publication_backup='ordinary independent labelled recursion; prototype compresses ONE boundary only',
            full_initial7_search=False)


def worker(case):
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    try:
        with calculation_budget(4000000,max_seconds=30),independent_joint_values():row=audit(case)
    except CalculationBudgetExceeded:row=dict(status='unverified',case=case,reason='case_calculation_budget',budget_stop=budget_stop(),full_initial7_search=False)
    row.update(seconds=time.monotonic()-start,peak_working_set_bytes=peak_bytes())
    Path('benchmarks/player_match_groups/publication-orbit-value-'+case+'-results.json').write_text(json.dumps(row,indent=2)+'\n')
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


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='recursive':recursive_worker(sys.argv[2])
    elif len(sys.argv)>1 and sys.argv[1]=='structural-role':structural_worker()
    elif len(sys.argv)>1 and sys.argv[1]=='structural-death':death_worker()
    else:worker(sys.argv[1] if len(sys.argv)>1 else 'five')
