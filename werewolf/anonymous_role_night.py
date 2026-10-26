"""Common anonymous ability generation, existing named Q/projection boundary.

Named priors are ingested once into relational families. Choices are generated
from slot counts before resolution. No permutation/swap safety loop is used.
Public law and continuation remain the established exact named adapters.
"""
from dataclasses import replace
from fractions import Fraction as F
from .anonymous_abilities import Context,run,resolve
from .ability_adapters import Medium,Divination,Guard,WolfAttack
from .anonymous_night import ingest,Program,Leaf,symbolic_steps,selection,SymbolStep,Transport
from .actor_information import WolfInformation
from .evaluation_branch import ActionInputs,physical_board
from .seer_acquisition import Acquisition
from .group_partition import _fix
from .board_future import outcome_key
from .joint_action_kernel import report_signature
from .calculation_budget import tick


def compile_abilities(engine,source,groups):
    from .night_program import supported
    if not supported(engine,source) or engine.strategy.include_self_bite:return None
    # Ordered policy variants not represented by these adapters retain the
    # existing exact named path; never silently substitute uniform choices.
    if tuple(engine.strategy.seer_position)!=('unvisited','uniform') or tuple(engine.strategy.guard_position)!=('uniform',):return None
    if source.public.initial_hunter_count and (engine.strategy.day,engine.strategy.night,engine.strategy.fake_reports)!=('random',)*3:return None
    cache=getattr(engine,'anonymous_ability_programs',None)
    if cache is None:engine.anonymous_ability_programs={};cache=engine.anonymous_ability_programs
    b=source.public;groups=tuple(groups)+tuple((p,) for p in range(1,b.player_count+1) if not any(p in g for g in groups));key=(source,groups)
    if key in cache:return cache[key]
    families={}
    for h in source.private.hypotheses:
        tick();pop,transport=ingest(h,groups,b.alive,b.history)
        if pop not in families:families[pop]=[F(),h,transport]
        families[pop][0]+=h.mass
    public=engine.acquire(b,source.public_state);leaves=[];policies={};offset=0;paths=0
    for population,(family_mass,h,transport) in families.items():
        info=WolfInformation.from_hypothesis(h)
        if info not in policies:
            with engine.actor_scope(info):policy=dict(engine.wolf_policy(b,source.public_state,source.past,info.initial_roster,info.attacks))
            policies[info]=(policy,offset);offset+=len(policy)
        policy,owner_index=policies[info]
        execution=next((e.target for e in reversed(b.history) if e.phase=='day'),None)
        # The execution participant is already distinguished by ingestion history.
        execution_ref=None if execution is None else next(i for i,p in enumerate(transport.people) if p==execution)
        context=Context(b.day,b.day+1,allow_repeat_guard=engine.rules.allow_repeat_guard,execution=execution_ref)
        def factory(ability,actor,initial):
            if ability.key!='attack':return None
            def committed(choice,bindings):
                extra=((choice.target,choice.fresh_cell),) if choice.fresh_cell is not None else ()
                names=transport.apply((*bindings,*extra));return policy.get(names[choice.target],F())
            return committed
        for planned in run(population,(Medium(),Divination(),Guard(),WolfAttack()),context,factory):
            paths+=1;path,dead=resolve(planned,context);names=transport.apply(path.bindings)
            attack=next(step for step in path.steps if step.kind=='wolf_target');target=names[attack.value]
            acquired=tuple(sorted(Acquisition(a.day,names[a.actor],names[a.target],a.color) for a in path.population.scans))
            own=replace(source.private,hypotheses=(replace(h,acquisitions=acquired,mass=F(1)),),rosters=source.private.rosters+(b.alive,))
            observer=None;guard=next((step for step in path.steps if step.kind=='guard_target'),None)
            if guard is not None:
                from .guard_model import GuardObserver
                observer=GuardObserver(b,names[guard.actor],names[guard.value],(h.roles,))
            payload=ActionInputs(public,source.past,own,observer,physical_board(b,own,source.physical))
            from .action_flow import NightFrame
            deaths=engine.action_policy.night_outcomes(NightFrame(b,target,payload,payload),None)
            symbols,binding_map=symbolic_steps(path,groups)
            for index,death in enumerate(deaths):
                child=replace(engine.action_policy._project_roles(b,payload,death,target),observer=None)
                # P is now one distinguished structural history. Preserve its
                # actor/target identities while the named report adapter runs; Q
                # itself remains unchanged. A parent symmetric P cannot justify
                # report-orbit averaging after selecting one private history.
                fixed_wolves=tuple(p for p in range(1,b.player_count+1) if h.roles[0]&(1<<(p-1)))
                with engine.group_scope(_fix(groups,(*fixed_wolves,*names))):
                    reports=engine.report_children(child) if child.public.winner is None else ()
                outcomes=tuple((p,c,report_signature(c)) for q,p,c in reports) if reports else ((F(1),child,None),)
                for report_mass,after,report in outcomes:
                    steps=tuple(replace(step,public_fact=child.public.winner) if step.kind=='death_notice' else step for step in symbols)
                    if child.public.winner is None and any(c in ('seer','medium') for c in b.claims):
                        from .tree_public_updates import publication_label
                        from .public_convergence import public_transport
                        mapping=public_transport(source,after,groups)
                        label=publication_label(child,after,mapping=mapping)
                        steps=(*steps,SymbolStep('publication',None,label))
                    wolves=tuple(p for p in range(1,b.player_count+1) if h.roles[0]&(1<<(p-1)))
                    scans=tuple(sorted((a.player,a.target) for a in acquired if a.day==b.day+1))
                    correspondence=[]
                    for ref,symbol in binding_map:
                        if type(ref)is int:person=names[ref]
                        else:
                            _,cell,slot=ref;person=tuple(p for p in transport.free[cell] if p not in names)[slot]
                        correspondence.append((symbol.index,person))
                    factor=family_mass*death.probability*report_mass
                    leaves.append(Leaf(factor*path.mass,factor*path.counter,replace(after,board_data=None,provenance=None),steps,info,owner_index,target,index,outcome_key(death),report,wolves,scans,_fix(groups,(*wolves,*names)),path.multiplicity,binding_map,selection(after.private.hypotheses[0]),tuple(correspondence),arrival=child,population=path.population,named_transport=Transport(names,tuple(tuple(p for p in row if p not in names) for row in transport.free))))
    program=Program(source,groups,leaves,dict(named_prior_atoms=len(source.private.hypotheses),relational_families=len(families),structural_joint_paths=paths,permutation_checks=0,belief_owned=False,ability_adapters=True))
    program.private_contexts=not (b.initial_medium_count or b.initial_hunter_count)
    cache[key]=program;return program
