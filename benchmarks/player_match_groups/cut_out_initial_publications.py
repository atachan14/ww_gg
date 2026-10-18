"""Explicit initial7 experiment with inherited proofs and generic publications.

No ordinary factory change. Every later publication must pass the same full
structural guards; no regrouping or unaggregated fallback after a refusal.
"""
from dataclasses import asdict,is_dataclass,replace
from fractions import Fraction as F
from time import perf_counter
import hashlib,json
from pathlib import Path
from .cut_out_first_cycle_coverage import base
from .cut_out_user_seven_source import SevenInitialEngine,require_bound
from .cut_out_uniform_game import OfficialLabelledEngine
from .cut_out_joint_night_forecast import FullRecordedPolicy
from .cut_out_structural_publications import produce,restore
from werewolf.morning_publications import public_report_branches
from werewolf.information_set_forecast import Pending
from werewolf.board_future import remember,calculation_origin,GeneratedBoard,ActionEvidence,source_key,kernel_snapshot,outcome_key
from werewolf.forecast_result import Forecast
from werewolf.evaluation_branch import ContinuationInputs,ActionInputs,physical_board
from werewolf.actor_information import wolf_information_groups
from werewolf.model_a_public import horizon_for_action
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,budget_stop,budget_usage,tick


def clean(value):
    if isinstance(value,F):return str(value)
    if is_dataclass(value):return {k:clean(v) for k,v in vars(value).items() if not k.startswith('_') and k!='board_data'}
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [clean(v) for v in value]
    if value is None or isinstance(value,(str,int,float,bool)):return value
    return type(value).__name__


class TrialPolicy(FullRecordedPolicy):
    def morning_value(self,payload):
        old=getattr(self.engine,'active_morning',None);self.engine.active_morning=payload
        try:return super().morning_value(payload)
        finally:self.engine.active_morning=old


class InitialPublicationEngine(SevenInitialEngine):
    def __init__(self,graph,*,witness,**kwargs):
        super().__init__(graph,witness=witness,**kwargs)
        self.full_branch_records=[];self.action_policy=TrialPolicy(self)
        self.first_refusal=None;self.publication_patterns={};self.active_morning=None;self.last_board=None;self.night_inputs={}
    def solve(self,b,*args,**kwargs):
        if not getattr(self,'_board_evidence_snapshot',False):
            self.last_board=b;self.last_usage=budget_usage();self.last_context=(b,)+args
        if not b.winner and b.phase=='night':
            s,past,private,observer=args
            source=ContinuationInputs(b,s,past,private,observer,physical_board(b,private,kwargs.get('physical')))
            self.night_inputs[source]=source
        return super().solve(b,*args,**kwargs)
    def generate_publications(self,b,s,past):
        require_bound(self.graph,self.source_witness)
        if self.rules!=self.graph.engine.baseline.rules or self.strategy!=self.graph.engine.baseline.strategy:
            raise Pending('initial_publication_bound_configuration_changed')
        try:
            context=self.inherited_groups.require(b,s,past)
            patterns=produce(b,s,past,context.groups,fake_policy=self.strategy.fake_seer_policy)
        except Pending as error:
            if self.first_refusal is None:
                payload=self.active_morning
                self.first_refusal=dict(reason=error.reason,board=clean(b),public_state=clean(s),past=clean(past),
                    groups=clean(context.groups) if 'context' in locals() else None,
                    reporters=[p for p in b.alive if b.claims[p-1]=='seer'],
                    before_morning=clean(payload) if payload is not None else None,budget_usage=budget_usage())
            raise
        if not getattr(self,'_board_evidence_snapshot',False):
            self.publication_patterns[b,s,past]=(len(patterns),sum(p.multiplicity for p in patterns))
        return public_report_branches(b,past,restore(patterns,b.player_count))


class InitialReferenceEngine(OfficialLabelledEngine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.full_branch_records=[];self.action_policy=TrialPolicy(self);self.night_inputs={}


    def solve(self,b,s,past,private,observer,*,physical=None):
        if not b.winner and b.phase=='night':
            source=ContinuationInputs(b,s,past,private,observer,physical_board(b,private,physical))
            self.night_inputs[source]=source
        return super().solve(b,s,past,private,observer,physical=physical)


def scope(graph,witness):
    source=require_bound(graph,witness).source;b=source.public
    if b.day!=1 or b.phase!='day' or b.history or len(b.alive)!=7 or b.initial_hunter_count:
        raise Pending('initial_publication_actual_initial7_source_required')
    strategy=graph.engine.baseline.strategy
    if (strategy.day,strategy.night,strategy.fake_reports)!=('random',)*3:
        raise Pending('initial_publication_explicit_uniform_only')
    return source


def stats(engine):
    if engine is None:return {}
    result=dict(values=len(engine.values),actions=len(engine.scalar_actions),generated=len(engine.board_sources),
        branch_records=len(engine.full_branch_records),terminal_records=len(engine.terminal_records),
        policies=len(engine.policies),costs=dict(engine.costs))
    if hasattr(engine,'publication_patterns'):
        patterns=tuple(engine.publication_patterns.values())
        result.update(publication_laws=len(patterns),
            pattern_representatives=sum(p for p,n in patterns),
            named_public_vectors=sum(n for p,n in patterns))
    if engine.inherited_groups is not None:result['group_stats']=dict(engine.inherited_groups.stats)
    if hasattr(engine,'last_board'):result['last_board']=clean(engine.last_board)
    if hasattr(engine,'last_usage'):result['last_budget_usage']=engine.last_usage
    return result


def canonical_board(board):
    if board is None:return None
    return {k:clean(v) for k,v in vars(board).items() if not k.startswith('_') and k not in ('belief','role_belief','world_belief')}|{'worlds':clean(tuple(sorted(board.worlds)))}


def canonical_source(source):
    return dict(board=canonical_board(source.public),Q=clean(source.public_state),past=clean(source.past),
        P=clean(source.private),observer=clean(source.observer),physical=canonical_board(source.physical))


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def path_maps(engine,parent,target,cache):
    if isinstance(engine,InitialReferenceEngine):return (tuple(range(1,8)),)
    from werewolf.exact import legal_targets
    identity=tuple(range(1,8));maps=(identity,);steps=[]
    for i,op in enumerate(parent.history):
        if isinstance(op,ActionEvidence):steps.append((parent.history[:i],op.target))
    if target is not None:steps.append((parent.history,target))
    for prefix,chosen in steps:
        if prefix not in cache:cache[prefix]=GeneratedBoard(parent.origin,prefix).roles()
        source=cache[prefix]
        groups=engine.groups(source.public,source.past,source.private,source.observer,public_state=source.public_state)
        group=next(g for g in groups if chosen in g);local=[]
        for p in group:
            if p not in legal_targets(source.physical,engine.rules,engine.strategy):continue
            mapping=list(identity);mapping[chosen-1],mapping[p-1]=p,chosen;local.append(tuple(mapping))
        maps=tuple(dict.fromkeys(tuple(previous[mapping[p-1]-1] for p in range(1,8)) for previous in maps for mapping in local))
    return maps


def completed_evidence(engine,graph):
    """Hash complete named outputs; only three terminal paths get cold replay."""
    from .cut_out_joint_night_forecast_fixture import moved_source,moved_board
    from .cut_out_live_medium_forecast import cold
    from types import SimpleNamespace
    cache={};branches={};terminals={};joint={};cold_rows=[]
    def insert(table,key,value):
        k=digest(key);v=digest(value)
        if k in table:assert table[k]==v
        table[k]=v
    for b,payload,target,outcomes in engine.full_branch_records:
        tick()
        parent=engine.board_sources[source_key(b,payload,engine)]
        source=ContinuationInputs(b,payload.public_state,payload.past,payload.private,payload.observer,payload.physical)
        for mapping in path_maps(engine,parent,target,cache):
            moved=moved_source(source,mapping);mt=mapping[target-1]
            rows=[(str(o.probability),canonical_board(moved_board(o.board,mapping)),canonical_board(moved_board(o.context,mapping)) if o.context is not None else None) for o in outcomes]
            insert(branches,(canonical_source(moved),mt),rows)
    for source in engine.night_inputs:
        tick()
        payload=ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical)
        parent=engine.board_sources[source_key(source.public,payload,engine)]
        selection=[]
        for info,mass,own in wolf_information_groups(source.private):
            for target,q in engine.wolf_policy(source.public,source.public_state,source.past,info.initial_roster,info.attacks):
                selection.append((info.initial_roster,info.attacks,target,mass*q))
        for mapping in path_maps(engine,parent,None,cache):
            mask=lambda value:sum(1<<(mapping[p-1]-1) for p in range(1,8) if value&(1<<(p-1)))
            rows=sorted((mask(roster),tuple(replace(a,target=mapping[a.target-1]) for a in attacks),mapping[target-1],mass) for roster,attacks,target,mass in selection)
            insert(joint,canonical_source(moved_source(source,mapping)),clean(rows))
    for b,payload,target,outcomes in engine.terminal_records:
        tick()
        parent=engine.board_sources[source_key(b,payload,engine)]
        for outcome in outcomes:
            expected=engine.action_policy._project_roles(b,payload,outcome,target)
            for mapping in path_maps(engine,parent,target,cache):
                source=ContinuationInputs(b,payload.public_state,payload.past,payload.private,payload.observer,payload.physical)
                insert(terminals,(canonical_source(moved_source(source,mapping)),mapping[target-1],canonical_source(moved_source(expected,mapping))),str(outcome.probability))
            if len(cold_rows)<3:
                request=parent.child(ActionEvidence(kernel_snapshot(engine),target,outcome_key(outcome),False),None)
                assert cold(SimpleNamespace(registry=graph),request)==expected
                cold_rows.append(dict(history=clean(expected.public.history),winner=expected.public.winner))
    return dict(branches=branches,terminals=terminals,joint=joint,representative_cold=cold_rows)

def run(kind='new',path=None):
    import os,time,threading
    from .cut_out_uniform_game_fixture import peak_bytes
    start=perf_counter();engine=None;graph=None;lock=threading.Lock()
    output=Path(path or ('benchmarks/player_match_groups/initial-publications-'+kind+'-trial.json'))
    def save(row):
        with lock:
            row.update(kind=kind,elapsed_seconds=perf_counter()-start,peak_working_set_bytes=peak_bytes(),stats=stats(engine))
            tmp=output.with_suffix('.tmp');tmp.write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8');tmp.replace(output)
    def watch():
        while True:
            if peak_bytes()>1500000000:
                save(dict(status='unverified',reason='worker_memory_limit_1500000000'));os._exit(124)
            if perf_counter()-start>64:
                save(dict(status='unverified',reason='worker_wall_limit_after_60s_budget'));os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    save(dict(status='running',reason='one_authorized_attempt'))
    try:
        with calculation_budget(None,max_seconds=60):
            graph,witness=base();source=scope(graph,witness)
            engine=InitialPublicationEngine(graph,witness=witness) if kind=='new' else InitialReferenceEngine(graph)
            engine.capture_terminal=True
            with calculation_origin(graph.data):
                remember(engine,graph.root,source)
                value=engine.solve(*source,physical=source.physical)
                actions=tuple((p,engine.act(*source[:3],p,source.private,None,physical=source.physical)) for p in source.public.alive)
                dawn=tuple((p,horizon_for_action(engine,source.public,source.public_state,source.past,p,source.private)) for p in source.public.alive)
            result=Forecast(value,actions,dawn)
            from .cut_out_max_fixture import complete_table
            table=complete_table(graph,result,None)
            save(dict(status='forecast_completed_validation_pending',forecast=clean(result),table=clean(table),budget_usage=budget_usage()))
            evidence=completed_evidence(engine,graph)
            # Completed portable outputs precede the separate peer process.
            save(dict(status='completed',forecast=clean(result),table=clean(table),evidence=evidence,budget_usage=budget_usage()))
    except Pending as error:
        save(dict(status='unverified',reason=error.reason,first_refusal=engine.first_refusal if engine is not None and hasattr(engine,'first_refusal') else None,
            root_game=graph.data.to_game() if graph is not None else None,last_context=clean(getattr(engine,'last_context',None)),budget_usage=budget_usage()))
    except CalculationBudgetExceeded:
        partial=json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
        save(dict(status='unverified',reason='comparison_budget',budget_stop=budget_stop(),forecast=partial.get('forecast'),table=partial.get('table')))
    except Exception as error:
        save(dict(status='unverified',reason=type(error).__name__,detail=str(error)))
        raise
    return json.loads(output.read_text(encoding='utf-8'))


if __name__=='__main__':
    import sys
    result=run(sys.argv[1] if len(sys.argv)>1 else 'new')
    print(json.dumps({k:result[k] for k in ('kind','status','reason','elapsed_seconds','peak_working_set_bytes') if k in result}),flush=True)