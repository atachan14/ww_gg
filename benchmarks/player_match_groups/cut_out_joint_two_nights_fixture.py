"""Bounded two-night structure/Forecast/cold-independent-engine comparison."""
from pathlib import Path
from dataclasses import replace
from time import perf_counter
from fractions import Fraction as F
import json,sys,subprocess,time,threading,os
from .cut_out_joint_two_nights import *
from .cut_out_joint_night_forecast_fixture import full_readback,read_bound
from .cut_out_candidate_context_fixture import zero_legacy
from werewolf.board_future import reconstruction_kernel_reuse,SavedOrigin,source_key


def max_reachable_nights(n,w,phase='day',nights=0):
 from werewolf.exact import winner_for
 if winner_for(n,w):return nights
 if phase=='night':return max_reachable_nights(n-1,w,'day',nights+1)
 return max(max_reachable_nights(n-1,w-1,'night',nights),max_reachable_nights(n-1,w,'night',nights))


def path_mappings(cap,engine,b,payload,target,parent,cache):
 n=b.player_count;identity=tuple(range(1,n+1))
 if not isinstance(engine,TwoNightEngine):return (identity,)
 offset=len(cap.request.history);path=[]
 for i,op in enumerate(parent.history[offset:],offset):
  if isinstance(op,ActionEvidence):path.append((parent.history[:i],op.target))
 if target is not None:path.append((parent.history,target))
 accumulated=(identity,)
 for prefix,action_target in path:
  if prefix not in cache:cache[prefix]=GeneratedBoard(parent.origin,prefix).roles()
  source=cache[prefix];maskset={h.roles[0] for h in source.private.hypotheses}
  candidates=[node for node in engine.joint_nodes if (node.source.public,node.source.public_state,node.source.past,node.source.observer)==(source.public,source.public_state,source.past,source.observer) and prefix[:len(node.request.history)]==node.request.history]
  node=max(candidates,key=lambda v:len(v.request.history)) if candidates else None
  orbit=next((o for o in node.orbits if len(maskset)==1 and o.roster==next(iter(maskset)) and o.target==action_target),None) if node else None
  if orbit is not None:local=tuple(members(cap,node.source,orbit))
  else:
   groups=engine.groups(source.public,source.past,source.private,source.observer,public_state=source.public_state)
   group=next(g for g in groups if action_target in g);local=[]
   for p in group:
    if p not in legal_targets(source.physical,engine.rules,engine.strategy):continue
    mapping=list(identity);mapping[action_target-1],mapping[p-1]=mapping[p-1],mapping[action_target-1];local.append(tuple(mapping))
  accumulated=tuple(dict.fromkeys(tuple(previous[mapping[p-1]-1] for p in range(1,n+1)) for previous in accumulated for mapping in local))
 return accumulated


def complete_joint_selection(cap,engine,reference):
 from .cut_out_joint_night_forecast_fixture import moved_source
 from werewolf.actor_information import wolf_information_groups
 actual={};expected={};cache={}
 for node in engine.joint_nodes:
  require_node(node);selection={}
  for orbit in node.orbits:
   for mapping in members(cap,node.source,orbit):
    mask=sum(1<<(mapping[p-1]-1) for p in range(1,7) if orbit.roster&(1<<(p-1)))
    selection[mask,orbit.attacks,mapping[orbit.target-1]]=orbit.mass/orbit.multiplicity
  payload=ActionInputs(node.source.public_state,node.source.past,node.source.private,node.source.observer,node.source.physical)
  for mapping in path_mappings(cap,engine,node.source.public,payload,None,node.request,cache):
   transformed={}
   for (mask,attacks,target),mass in selection.items():
    moved_mask=sum(1<<(mapping[p-1]-1) for p in range(1,7) if mask&(1<<(p-1)))
    transformed[moved_mask,tuple(replace(a,target=mapping[a.target-1]) for a in attacks),mapping[target-1]]=mass
   source=moved_source(node.source,mapping)
   if source in actual:assert actual[source]==transformed
   actual[source]=transformed
 for source in reference.night_inputs:
  selection={}
  for info,mass,own in wolf_information_groups(source.private):
   for target,q in reference.wolf_policy(source.public,source.public_state,source.past,info.initial_roster,info.attacks):selection[info.initial_roster,info.attacks,target]=mass*q
  expected[source]=selection
 assert actual==expected,(len(actual),len(expected))
 return len(actual),sum(len(v) for v in actual.values())


def independent_second_night_cold(cap,engine):
 start=perf_counter();rootday=cap.source.public.day
 candidates=[record for record in engine.terminal_records if record[0].phase=='night' and record[0].day==rootday+1 and any(h.roles[2]&record[0].alive_mask for h in record[1].private.hypotheses)]
 chosen=next((record for record in candidates if record[1].public_state!=record[1].private),candidates[0] if candidates else None)
 if chosen is None:raise Pending('joint_two_night_live_seer_cold_witness_required')
 b,payload,target,outcomes=chosen;outcome=outcomes[0]
 parent=engine.board_sources[source_key(b,payload,engine)]
 warm_request=parent.child(ActionEvidence(kernel_snapshot(engine),target,outcome_key(outcome),False),None)
 warm=read_bound(cap,warm_request)
 fresh=InformationSetForecast(engine.rules,engine.strategy,exact_renaming=False,retire_uninformative_scans=False);fresh.retain_joint_guard_history=True
 origin=SavedOrigin(cap.registry.data,engine.rules,engine.strategy,project_public=False)
 operations=[]
 for op in warm_request.history:
  if type(op) in (ActionEvidence,PublicationEvidence):operations.append(replace(op,engine=fresh))
  elif type(op)is ConditionEvidence:operations.append(replace(op))
  else:raise Pending('joint_two_night_cold_unknown_recipe')
 request=GeneratedBoard(origin,tuple(operations))
 with calculation_budget(2000000,max_seconds=30),reconstruction_kernel_reuse(False):cold=request.roles()
 assert cold==warm and cold.public_state==warm.public_state and cold.private==warm.private
 assert fresh is not engine and origin is not parent.origin and len(fresh.values)==0
 assert sum(event.phase=='night' for event in cold.public.history)==2
 third=[a for h in cold.private.hypotheses for a in h.acquisitions if a.day==3]
 assert third and all(len(h.attacks)==2 for h in cold.private.hypotheses)
 return dict(seconds=perf_counter()-start,fresh_engine=True,fresh_SavedOrigin=True,completed_step_reuse=False,night_events=2,QP_different_before=payload.public_state!=payload.private,QP_different_after=cold.public_state!=cold.private,third_slot_scan_records=len(third),dead_scan_records=sum(a.target not in cold.public.alive for a in third))


def audit(known=True,kind='public'):
 start=perf_counter();cap=make_case(6,night_limit=2,known_wolf=known)
 view=OwnView(2,'wolf') if kind=='wolf' else None
 stack,mocks=zero_legacy()
 with stack:
  t=perf_counter();actual,engine,table=evaluate_two(cap,view);actual_s=perf_counter()-t
  t=perf_counter();expected,old,old_table=evaluate_two(cap,view,reference=True);reference_s=perf_counter()-t
  assert actual==expected and table==old_table
  joint_contexts,joint_pairs=complete_joint_selection(cap,engine,old)
  prototype=full_readback(cap,engine,max_seconds=30,mapping_fn=path_mappings)
  reference=full_readback(cap,old,max_seconds=30,mapping_fn=path_mappings)
  assert prototype['branches']==reference['branches'],(len(prototype['branches']),len(reference['branches']))
  assert prototype['terminals']==reference['terminals'],(len(prototype['terminals']),len(reference['terminals']))
  cold=independent_second_night_cold(cap,engine)
  if not known:assert cold['QP_different_before'] and cold['QP_different_after']
  assert any(node.source.public.day==cap.source.public.day+1 for node in engine.joint_nodes)
  # All current-source/group receipts remain linked to the initial prior.
  for node in engine.joint_nodes:
   assert node.request.origin is cap.request.origin and _valid_node(node)
  assert all(m.call_count==0 for m in mocks)
 return dict(status='verified',players=6,known_wolf=known,view=kind,village_win=str(actual.village_win),Forecast_Table_joint_equal=True,all_joint_selection_contexts_equal=joint_contexts,all_joint_selection_pairs_equal=joint_pairs,
  all_labelled_branches_equal=len(prototype['branches']),all_terminal_transitions_equal=len(prototype['terminals']),joint_nodes=len(engine.joint_nodes),QP_different_nodes=sum(node.source.public_state!=node.source.private for node in engine.joint_nodes),
  live_group_shapes={str(day):sorted({tuple(sorted(sum(p in node.source.public.alive for p in g) for g in node.groups if any(p in node.source.public.alive for p in g))) for node in engine.joint_nodes if node.source.public.day==day}) for day in (1,2)},
  joint_calls={k:v for k,v in engine.costs.items() if k.startswith('joint_')},prototype_action_generations=engine.costs['action_evaluations'],reference_action_generations=old.costs['action_evaluations'],
  preprocessing_seconds=cap.preprocessing_seconds,prototype_forecast_seconds=actual_s,reference_forecast_seconds=reference_s,
  prototype_restore_seconds=prototype['seconds'],reference_restore_seconds=reference['seconds'],second_night_independent_cold=cold,
  prototype_preprocessing_restore_cold_seconds=cap.preprocessing_seconds+actual_s+prototype['seconds']+cold['seconds'],total_comparison_seconds=perf_counter()-start,
  canonical_calls=0,CandidateRules_calls=0,initial_seven_executed=False)


def _valid_node(node):
 from .cut_out_joint_two_nights import _nodes
 return node in _nodes and node.source.public.phase=='night'


def negatives_and_reachability():
 from werewolf.seer_acquisition import normalize
 cap=make_case(6,night_limit=2,known_wolf=True)
 result,engine,table=evaluate_two(cap);node=next(n for n in engine.joint_nodes if n.source.public.day==2 and len(n.source.private.hypotheses)>1)
 rejected=[]
 def refuse(name,call):
  try:call()
  except Pending:rejected.append(name)
  else:raise AssertionError(name+' accepted')
 refuse('copied_node',lambda:require_node(replace(node)))
 for field in ('public_state','private'):
  law=getattr(node.source,field);hs=list(law.hypotheses);hs[0]=replace(hs[0],mass=hs[0].mass*2)
  bad=replace(law,hypotheses=normalize(tuple(hs)));source=replace(node.source,**{field:bad})
  # Roles/marginals are unchanged here; only hidden scan-history weights differ.
  assert bad.public_roles==law.public_roles
  refuse('secret_only_skew_'+field,lambda source=source:issue_node(engine,source,node.request))
 wrong_view=replace(node.source,observer=OwnView(1,'seer'))
 refuse('one_sided_view',lambda:issue_node(engine,wrong_view,node.request))
 fake=node.request.child(lambda source:source,None)
 refuse('unowned_fake_recipe',lambda:issue_node(engine,node.source,fake))
 data=cap.registry.data;cap.registry.data=data.updated(revision=data.to_game().get('revision',0)+1)
 try:refuse('stale_revision_node',lambda:require_node(node))
 finally:cap.registry.data=data
 root=cap.source;third=replace(root.public,day=root.public.day+2)
 refuse('third_generated_night',lambda:engine.solve(third,root.public_state,root.past,root.private,None,physical=root.physical))
 reach={f'{n}/W{w}':max_reachable_nights(n,w) for n in (4,5) for w in range(1,(n-1)//2+1)}
 assert all(value<=1 for value in reach.values()) and max_reachable_nights(6,1)==2
 return dict(status='verified',small_max_nights=reach,minimum_W1_six_nights=2,rejected=rejected)


def worker(known,kind):
 from .cut_out_uniform_game_fixture import peak_bytes
 start=perf_counter()
 def watch():
  while True:
   if perf_counter()-start>120 or peak_bytes()>1500000000:os._exit(124)
   time.sleep(.05)
 threading.Thread(target=watch,daemon=True).start()
 from werewolf.calculation_budget import CalculationBudgetExceeded,budget_stop
 try:
  with calculation_budget(4000000,max_seconds=30):row=audit(known,kind)
 except CalculationBudgetExceeded:row=dict(status='unverified',reason='comparison_budget_exhausted',budget_stop=budget_stop())
 row['peak_working_set_bytes']=peak_bytes();print(json.dumps(row),flush=True)

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='negative':
  row=negatives_and_reachability();Path('benchmarks/player_match_groups/cut-out-joint-two-nights-negatives.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))
 elif len(sys.argv)>1:worker(sys.argv[1]=='known',sys.argv[2] if len(sys.argv)>2 else 'public')
 else:
  rows=[]
  for known,kind in (('known','public'),('unknown','public'),('unknown','wolf')):
   run=subprocess.run([sys.executable,'-B','-m',__spec__.name,known,kind],capture_output=True,text=True,timeout=121)
   if run.returncode:raise RuntimeError(run.stdout+run.stderr)
   row=json.loads(run.stdout);rows.append(row);print(json.dumps(row),flush=True)
  Path('benchmarks/player_match_groups/cut-out-joint-two-nights-results.json').write_text(json.dumps(dict(cases=rows,unreachable_small={str(n):max_reachable_nights(n,1) for n in (4,5)},limits=dict(comparison_seconds=30,worker_seconds=120,peak_working_set_bytes=1500000000),scope='opt-in six-player W1 H0; two generated nights; heavy seven not executed',cold_policy='one second-night representative on fresh engine and fresh SavedOrigin, reuse disabled; all-label restoration uses exact completed-step reuse'),indent=2)+'\n')
  if any(row['status']!='verified' for row in rows):sys.exit(1)