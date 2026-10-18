"""Bounded complete Forecast and cold SavedOrigin readback for joint experiment."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
from time import perf_counter
from pathlib import Path
import json,sys,subprocess,threading,time,os
from .cut_out_joint_night_forecast import *
from .cut_out_candidate_context_fixture import zero_legacy
from werewolf.board_future import source_key,reconstruction_kernel_reuse,SavedOrigin


def moved_source(source,mapping):
 q=move_law(source.public_state,mapping);p=move_law(source.private,mapping)
 past=tuple(sorted(replace(v,player=mapping[v.player-1],target=mapping[v.target-1]) for v in source.past))
 return ContinuationInputs(move_board(source.public,q,mapping),q,past,p,source.observer,move_board(source.physical,p,mapping))


def moved_board(b,mapping):
 def mask(m):return sum(1<<(mapping[p-1]-1) for p in range(1,len(mapping)+1) if m&(1<<(p-1)))
 worlds=tuple(sorted(tuple(mask(m) for m in row[:-1])+(row[-1],) for row in b.worlds))
 return move_board(b,SimpleNamespace(public_roles=worlds),mapping)


def read_bound(cap,request):
 require(cap)
 if request.origin is not cap.request.origin or request.history[:len(cap.request.history)]!=cap.request.history:raise Pending('joint_forecast_wrong_origin_prefix')
 if not isinstance(request.origin,SavedOrigin):raise Pending('joint_forecast_saved_origin_required')
 return request.roles()


def mapping_options(cap,engine,b,payload,target,parent,root_cache):
 n=b.player_count;identity=tuple(range(1,n+1));global_maps=[identity];associated=False;root_input=None
 if hasattr(engine,'root_orbits'):
  own_masks={h.roles[0] for h in payload.private.hypotheses}
  if b==cap.source.public:root_target=target;root_masks=own_masks
  else:
   offset=len(engine.root_request.history);indices=[i for i,op in enumerate(parent.history[offset:],offset) if isinstance(op,ActionEvidence)]
   if indices:
    idx=indices[0];root_target=parent.history[idx].target;prefix=parent.history[:idx]
    if prefix not in root_cache:root_cache[prefix]=GeneratedBoard(parent.origin,prefix).roles()
    root_input=root_cache[prefix];root_masks={h.roles[0] for h in root_input.private.hypotheses}
   else:root_target=None;root_masks=set()
  if len(root_masks)==1:
   orbit=next((o for o in engine.root_orbits if o.roster==next(iter(root_masks)) and o.target==root_target),None)
   if orbit is not None:
    global_maps=list(members(cap,engine.root_context,orbit));associated=True
  if not associated and root_input is not None:
   root_groups=engine.groups(root_input.public,root_input.past,root_input.private,root_input.observer,public_state=root_input.public_state)
   group=next(g for g in root_groups if root_target in g);global_maps=[]
   for p in group:
    if p not in legal_targets(root_input.physical,engine.rules,engine.strategy):continue
    mapping=list(identity);mapping[root_target-1],mapping[p-1]=mapping[p-1],mapping[root_target-1];global_maps.append(tuple(mapping))
 local=[identity]
 if isinstance(engine,JointForecastEngine) and not (associated and b==cap.source.public):
  groups=engine.groups(b,payload.past,payload.private,payload.observer,public_state=payload.public_state)
  group=next(g for g in groups if target in g)
  local=[]
  for p in group:
   if p not in legal_targets(payload.physical,engine.rules,engine.strategy):continue
   mapping=list(identity);mapping[target-1],mapping[p-1]=mapping[p-1],mapping[target-1];local.append(tuple(mapping))
 return tuple(dict.fromkeys(tuple(g[l[p-1]-1] for p in range(1,n+1)) for l in local for g in global_maps))


def full_readback(cap,engine,*,max_seconds=10,mapping_fn=None):
 start=perf_counter();branches={};terminals={};cache={};cold=0;fully_cold=0;mapper=mapping_fn or mapping_options
 with calculation_budget(1000000,max_seconds=max_seconds):
  for b,payload,target,outcomes in engine.full_branch_records:
   parent=engine.board_sources[source_key(b,payload,engine)]
   source=ContinuationInputs(b,payload.public_state,payload.past,payload.private,payload.observer,payload.physical)
   for mapping in mapper(cap,engine,b,payload,target,parent,cache):
    moved=moved_source(source,mapping);mt=mapping[target-1]
    outs=tuple((o.probability,moved_board(o.board,mapping),None if o.context is None else moved_board(o.context,mapping)) for o in outcomes)
    branches[moved,mt]=outs
  for b,payload,target,outcomes in engine.terminal_records:
   parent=engine.board_sources[source_key(b,payload,engine)]
   for outcome in outcomes:
    request=parent.child(ActionEvidence(kernel_snapshot(engine),target,outcome_key(outcome),False),None)
    expected=engine.action_policy._project_roles(b,payload,outcome,target)
    for mapping in mapper(cap,engine,b,payload,target,parent,cache):
     expected_moved=moved_source(expected,mapping)
     parent_source=ContinuationInputs(b,payload.public_state,payload.past,payload.private,payload.observer,payload.physical)
     terminal_key=(moved_source(parent_source,mapping),mapping[target-1],expected_moved)
     if terminal_key in terminals:
      assert terminals[terminal_key]==outcome.probability
      continue
     restored=transport_request(cap,request,expected,mapping)
     # One full cold path per case, then existing exact completed-step reuse.
     with reconstruction_kernel_reuse(fully_cold>0):actual=read_bound(cap,restored)
     if not fully_cold:fully_cold+=1
     assert actual==expected_moved and actual.public_state==expected_moved.public_state and actual.private==expected_moved.private
     terminals[terminal_key]=outcome.probability;cold+=1
 return dict(branches=branches,terminals=terminals,saved_reads=cold,fully_cold_samples=fully_cold,seconds=perf_counter()-start)


def audit(players=5,kind='public'):
 from werewolf.seer_acquisition import Acquisition
 start=perf_counter();cap=make_case(players);view=None
 if kind=='seer':
  acquisitions=(Acquisition(1,1,4,'white'),Acquisition(2,1,7,'white')) if players==7 else (Acquisition(1,1,3,'white'),)
  view=OwnView(1,'seer',acquisitions)
 if kind=='wolf':view=OwnView(2,'wolf')
 stack,mocks=zero_legacy()
 with stack:
  t=perf_counter();actual,engine,table=evaluate(cap,view);actual_seconds=perf_counter()-t
  t=perf_counter();expected,old,old_table=evaluate(cap,view,reference=True);old_seconds=perf_counter()-t
  assert actual==expected and table==old_table
  from werewolf.actor_information import wolf_information_groups
  root,_,_=view_source(cap,view);joint={}
  for orbit in engine.root_orbits:
   for mapping in members(cap,root,orbit):
    mask=sum(1<<(mapping[p-1]-1) for p in range(1,root.public.player_count+1) if orbit.roster&(1<<(p-1)))
    joint[mask,mapping[orbit.target-1]]=orbit.mass/orbit.multiplicity
  raw_joint={}
  for info,mass,own in wolf_information_groups(root.private):
   for target,probability in old.wolf_policy(root.public,root.public_state,root.past,info.initial_roster,info.attacks):raw_joint[info.initial_roster,target]=mass*probability
  assert joint==raw_joint and sum(joint.values())==1
  prototype=full_readback(cap,engine);reference=full_readback(cap,old)
  assert prototype['branches']==reference['branches'],(len(prototype['branches']),len(reference['branches']))
  assert prototype['terminals']==reference['terminals'],(len(prototype['terminals']),len(reference['terminals']))
  require(cap)
  assert all(m.call_count==0 for m in mocks)
 return dict(players=players,view=kind,village_win=str(actual.village_win),status='verified',
  complete_Forecast_action_horizon_Table_joint_equal=True,full_joint_selection_mass_equal=True,all_labelled_branch_mass_equal=True,all_terminal_sources_equal=True,
  branch_readbacks=len(prototype['branches']),terminal_readbacks=len(prototype['terminals']),saved_reads=prototype['saved_reads'],fully_cold_samples=prototype['fully_cold_samples'],
  preprocessing_seconds=cap.preprocessing_seconds,prototype_forecast_seconds=actual_seconds,reference_forecast_seconds=old_seconds,
  prototype_restore_seconds=prototype['seconds'],reference_restore_seconds=reference['seconds'],
  prototype_with_preprocessing_restore_seconds=cap.preprocessing_seconds+actual_seconds+prototype['seconds'],total_check_seconds=perf_counter()-start,
  root_joint_representatives=len(engine.root_orbits),root_literal_pairs=sum(o.multiplicity for o in engine.root_orbits),
  canonical_calls=0,CandidateRules_calls=0,initial_full_seven_executed=False)



def negatives():
 from werewolf.seer_acquisition import normalize
 cap=make_case(5);s=cap.source;rejected=[]
 def refuse(name,call):
  try:call()
  except Pending:rejected.append(name)
  else:raise AssertionError(name+' accepted')
 refuse('copied_certificate',lambda:require(replace(cap)))
 for field in ('public_state','private'):
  law=getattr(s,field);hs=list(law.hypotheses)
  # First representative mass is unchanged: a mere orbit-total check could
  # miss the skew between the remaining exchangeable assignments.
  for i,mass in enumerate((F(1,3),F(1,2),F(1,6))):hs[i]=replace(hs[i],mass=mass)
  bad=replace(law,hypotheses=normalize(tuple(hs)));source=replace(s,**{field:bad})
  refuse('one_sided_'+field,lambda source=source:require(cap,source=source))
  refuse('producer_skew_'+field,lambda source=source:produce(cap,source,cap.groups))
 private,request,groups=view_source(cap,OwnView(2,'wolf'))
 refuse('private_changed_without_view',lambda:produce(cap,replace(private,observer=None),cap.groups))
 refuse('view_changed_without_private',lambda:produce(cap,replace(s,observer=OwnView(2,'wolf')),groups))
 identity=tuple(range(1,6));transported=transport_request(cap,cap.request,s,identity)
 op=transported.history[-1]
 refuse('copied_transport',lambda:replace(op)(s))
 refuse('transport_other_private_source',lambda:op(private))
 refuse('transport_outside_inherited_group',lambda:transport_request(cap,cap.request,s,(2,1,3,4,5)))
 changed_view=transport_request(cap,request,private,(1,4,3,2,5)).history[-1]
 refuse('transport_changes_own_owner',lambda:changed_view(private))
 other=make_case(5)
 refuse('other_owner_origin',lambda:read_bound(other,cap.request))
 data=cap.registry.data
 cap.registry.data=data.updated(revision=data.to_game().get('revision',0)+1)
 try:
  refuse('stale_revision_forecast',lambda:evaluate(cap))
  refuse('stale_revision_saved_read',lambda:read_bound(cap,transported))
 finally:cap.registry.data=data
 original_strategy=cap.registry.engine.baseline.strategy
 object.__setattr__(cap.registry.engine.baseline,'strategy',replace(original_strategy,night='max'))
 try:refuse('max',lambda:evaluate(cap))
 finally:object.__setattr__(cap.registry.engine.baseline,'strategy',original_strategy)
 engine=JointForecastEngine(ExperimentalGraph(cap),cap=cap)
 future=replace(s.public,day=s.public.day+1)
 refuse('second_generated_night',lambda:engine.solve(future,s.public_state,s.past,s.private,None,physical=s.physical))
 refuse('unsupported_large_initial_case',lambda:make_case(6))
 assert len(rejected)==17
 return dict(status='verified',rejected=rejected)


def worker(players,kind):
 from .cut_out_uniform_game_fixture import peak_bytes
 start=perf_counter()
 def watch():
  while True:
   if perf_counter()-start>25 or peak_bytes()>1500000000:os._exit(124)
   time.sleep(.05)
 threading.Thread(target=watch,daemon=True).start()
 result=audit(players,kind);result['peak_working_set_bytes']=peak_bytes();print(json.dumps(result),flush=True)

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='negative':
  result=negatives();Path('benchmarks/player_match_groups/cut-out-joint-night-forecast-negatives.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
 elif len(sys.argv)>1:worker(int(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else 'public')
 else:
  rows=[]
  for n,kind in ((4,'public'),(5,'public'),(5,'seer'),(5,'wolf'),(7,'public'),(7,'seer')):
   run=subprocess.run([sys.executable,'-B','-m',__spec__.name,str(n),kind],capture_output=True,text=True,timeout=26)
   if run.returncode:raise RuntimeError(run.stdout+run.stderr)
   row=json.loads(run.stdout);rows.append(row);print(json.dumps(row),flush=True)
  record=dict(cases=rows,scope='opt-in fixed source; one generated night; no ordinary route',limits=dict(worker_seconds=25,evaluation_seconds=5,readback_seconds=10,peak_working_set_bytes=1500000000),fully_cold_samples_per_engine_case=1,remaining_restores='exact completed-step cache enabled',speed_measurement_claimed=False,initial_full_seven_executed=False)
  Path('benchmarks/player_match_groups/cut-out-joint-night-forecast-results.json').write_text(json.dumps(record,indent=2)+'\n')