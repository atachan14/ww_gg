"""Bounded actual7/W2 intermediate comparisons; no initial-root solve."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from pathlib import Path
from time import perf_counter
import json,sys,subprocess,time,threading,os
from .cut_out_seven_w2_mid import *
from .cut_out_seven_w2_mid import _mid,_check_choice
from .cut_out_joint_two_nights_fixture import path_mappings,complete_joint_selection
from .cut_out_joint_night_forecast_fixture import full_readback,read_bound
from .cut_out_candidate_context_fixture import zero_legacy
from werewolf.board_future import reconstruction_kernel_reuse,SavedOrigin,source_key
from werewolf.actor_information import wolf_information_groups
from werewolf.seer_acquisition import normalize

@dataclass(frozen=True)
class RawObservedChoice:
 original:object
 engine:object
 def __call__(self,source):
  _check_choice(self.original)
  if source!=self.original.expected:raise Pending('raw_mid_choice_source_changed')
  # Oracle only: explicitly enumerate information groups and their old joint
  # team policy. No per-wolf independent-choice multiplication is permitted.
  entries=[]
  for info,mass,own in wolf_information_groups(source.private):
   q=dict(self.engine.wolf_policy(source.public,source.public_state,source.past,info.initial_roster,info.attacks)).get(self.original.target,F())
   entries.extend(replace(h,mass=h.mass*mass*q) for h in own.hypotheses if q)
  private=replace(source.private,hypotheses=normalize(tuple(entries)))
  weighted=replace(source,private=private,physical=physical_board(source.public,private,source.physical))
  return ActionEvidence(self.engine,self.original.target,self.original.observation,False)(weighted)


def raw_cold_request(cap,request):
 require(cap)
 fresh=InformationSetForecast(cap.registry.engine.baseline.rules,cap.registry.engine.baseline.strategy,exact_renaming=False,retire_uninformative_scans=False);fresh.retain_joint_guard_history=True
 origin=SavedOrigin(cap.registry.data,fresh.rules,fresh.strategy,project_public=False);ops=[]
 for op in request.history:
  if type(op) in (ActionEvidence,PublicationEvidence):ops.append(replace(op,engine=fresh))
  elif type(op)is ConditionEvidence:ops.append(replace(op))
  elif type(op)is JointObservedChoice:ops.append(RawObservedChoice(op,fresh))
  else:raise Pending('seven_mid_cold_unknown_recipe')
 with reconstruction_kernel_reuse(False):result=GeneratedBoard(origin,tuple(ops)).roles()
 assert len(fresh.values)==0 and origin is not cap.request.origin
 return result


def first_team_proof(cap):
 meta=_mid[cap];first=meta['first'];source=first.source;orbits=initial_orbits(first);actual={};raw={}
 for orbit in orbits:
  for mask,target,mapping in initial_labels(first,orbit):actual[mask,target]=orbit.physical_mass/orbit.multiplicity
 kernel=InformationSetForecast(cap.registry.engine.baseline.rules,cap.registry.engine.baseline.strategy,exact_renaming=False)
 for info,mass,own in wolf_information_groups(source.private):
  for target,q in kernel.wolf_policy(source.public,source.public_state,source.past,info.initial_roster,info.attacks):raw[info.initial_roster,target]=mass*q
 assert actual==raw and sum(actual.values())==1
 victim=4 if meta['case']!='count-change' else 3
 chance=sum((mass for (mask,target),mass in actual.items() if target==victim),F())
 assert chance==meta['choice']
 if meta['case']!='count-change':assert chance==F(1,4) and chance!=F(1,16)
 else:assert chance==F(9,40)
 return dict(representatives=len(orbits),literal_pairs=len(raw),observed_choice_mass=str(chance),two_wolves_one_joint_choice=True)


def cold_future(cap,engine):
 # Prefer a terminal witness retaining Q/P difference, including its complete
 # follow-up reports. This replays the original stage and future on a new engine.
 records=[]
 for b,payload,target,outcomes in engine.terminal_records:
  if b.day!=3:continue
  for outcome in outcomes:
   parent=engine.board_sources[source_key(b,payload,engine)]
   request=parent.child(ActionEvidence(kernel_snapshot(engine),target,outcome_key(outcome),False),None)
   direct=engine.action_policy._project_roles(b,payload,outcome,target)
   records.append((direct.public_state==direct.private,request,direct))
 if not records:raise Pending('seven_mid_followup_cold_witness_missing')
 _,request,direct=min(records,key=lambda row:row[0]);start=perf_counter()
 cold=raw_cold_request(cap,request)
 assert cold==direct and cold.public_state==direct.public_state and cold.private==direct.private
 assert all(h.roles[0].bit_count()==2 and len(h.attacks)==2 for h in cold.private.hypotheses)
 return dict(seconds=perf_counter()-start,fresh_engine=True,fresh_SavedOrigin=True,reuse=False,raw_team_policy_oracle=True,
  QP_different=cold.public_state!=cold.private,initial_wolf_roster_bits=2,observed_attacks=2)


def audit(case):
 start=perf_counter();stack,mocks=zero_legacy()
 with stack:
  cap=make_mid(case);meta=_mid[cap];team=first_team_proof(cap)
  t=perf_counter();cold_mid=raw_cold_request(cap,cap.request);prefix_cold=perf_counter()-t
  assert cold_mid==cap.source
  t=perf_counter();a,e,table=evaluate_mid(cap);actual_s=perf_counter()-t
  t=perf_counter();b,old,old_table=evaluate_mid(cap,True);old_s=perf_counter()-t
  assert a==b and table==old_table
  joint_contexts,joint_pairs=complete_joint_selection(cap,e,old)
  actual=full_readback(cap,e,max_seconds=30,mapping_fn=path_mappings)
  expected=full_readback(cap,old,max_seconds=30,mapping_fn=path_mappings)
  assert actual['branches']==expected['branches'] and actual['terminals']==expected['terminals']
  cold=cold_future(cap,e)
  if case=='count-change':
   assert a.village_win==F(598,2085) and cap.source.public_state!=cap.source.private
   expectedQ={33:F(8,31),65:F(8,31),18:F(5,31),34:F(5,31),66:F(5,31)}
   expectedP={33:F(32,139),65:F(32,139),18:F(25,139),34:F(25,139),66:F(25,139)}
   q=lambda s:{h.roles[0]:h.mass for h in s.hypotheses}
   assert q(cap.source.public_state)==expectedQ and q(cap.source.private)==expectedP
   carried=next(node for node in e.joint_nodes if node.source.public.history[-1].target==2)
   assert q(carried.source.public_state)==expectedQ and q(carried.source.private)==expectedP
   assert meta['Q_report']==F(31,240) and meta['P_report']==F(139,1080)
  else:
   assert a.village_win==F(2,15)
   assert ((1,2) in cap.groups)==(case=='agree')
  # An execution can leave one wolf or end immediately at two-wolf parity;
  # the original two-bit roster is never replaced with a W1 initial cast.
  execution=next(rows for rows in e.full_branch_records if rows[0]==cap.source.public and rows[2]==1) if case!='count-change' else next(rows for rows in e.full_branch_records if rows[0]==cap.source.public and rows[2]==4)
  outcomes=execution[3]
  assert any(o.board.winner=='wolf' for o in outcomes) and any(o.board.winner is None for o in outcomes)
  assert all(m.call_count==0 for m in mocks)
 return dict(case=case,status='verified',village_win=str(a.village_win),action_values={p:str(v) for p,v in a.action_values},groups=cap.groups,
  root_QP_different=cap.source.public_state!=cap.source.private,first_night=team,Q_report_mass=str(meta['Q_report']),P_report_mass=str(meta['P_report']),
  complete_Forecast_Table_joint_equal=True,selection_contexts=joint_contexts,selection_pairs=joint_pairs,labelled_branches=len(actual['branches']),terminal_transitions=len(actual['terminals']),
  followup_joint_representatives=e.costs['joint_midnight_representatives'],followup_literal_pairs=e.costs['joint_midnight_literal_pairs'],
  preprocessing_seconds=cap.preprocessing_seconds,forecast_seconds=actual_s,reference_forecast_seconds=old_s,restore_seconds=actual['seconds'],reference_restore_seconds=expected['seconds'],prefix_independent_cold_seconds=prefix_cold,future_independent_cold=cold,
  prototype_including_preprocessing_restore_cold=cap.preprocessing_seconds+actual_s+actual['seconds']+prefix_cold+cold['seconds'],total_comparison_seconds=perf_counter()-start,
  canonical_calls=0,CandidateRules_calls=0,full_initial_search=False)


def negatives():
 cap=make_mid('agree');s=cap.source;rejected=[]
 def refuse(name,call):
  try:call()
  except Pending as error:rejected.append(dict(case=name,reason=error.reason))
  else:raise AssertionError(name+' accepted')
 refuse('unproved_prefix_or_vector',lambda:make_mid('arbitrary'))
 refuse('positive_Q_zero_P',lambda:make_mid('count-change',roster=17))
 refuse('private_view_not_admitted',lambda:view_source(cap,OwnView(1,'seer')))
 refuse('copied_cap',lambda:require(replace(cap)))
 for field in ('public_state','private'):
  law=getattr(s,field);hs=list(law.hypotheses);hs[0]=replace(hs[0],mass=hs[0].mass*2);bad=replace(law,hypotheses=normalize(tuple(hs)))
  refuse('one_sided_'+field,lambda field=field,bad=bad:require(cap,source=replace(s,**{field:bad})))
 op=next(op for op in cap.request.history if type(op)is JointObservedChoice)
 refuse('copied_joint_choice',lambda:replace(op)(op.expected))
 refuse('unproved_victim_orbit',lambda:choice_step(cap.registry,cap.witness,op.expected,6,op.engine))
 other=InformationSetForecast(op.engine.rules,replace(op.engine.strategy,night='max'),exact_renaming=False)
 refuse('max_or_changed_choice_policy',lambda:choice_step(cap.registry,cap.witness,op.expected,op.target,other))
 data=cap.registry.data;cap.registry.data=data.updated(revision=data.to_game().get('revision',0)+1)
 try:refuse('stale_joint_source',lambda:op(op.expected))
 finally:cap.registry.data=data
 return dict(status='verified',rejected=rejected)


def worker(case):
 from .cut_out_uniform_game_fixture import peak_bytes
 from werewolf.calculation_budget import CalculationBudgetExceeded,budget_stop
 start=perf_counter()
 def watch():
  while True:
   if perf_counter()-start>120 or peak_bytes()>1500000000:os._exit(124)
   time.sleep(.05)
 threading.Thread(target=watch,daemon=True).start()
 try:
  with calculation_budget(4000000,max_seconds=30):row=audit(case)
 except CalculationBudgetExceeded:row=dict(case=case,status='unverified',reason='comparison_budget',budget_stop=budget_stop())
 row['peak_working_set_bytes']=peak_bytes();print(json.dumps(row),flush=True)

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='negative':
  row=negatives();Path('benchmarks/player_match_groups/cut-out-seven-w2-mid-negatives.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))
 elif len(sys.argv)>1:worker(sys.argv[1])
 else:
  rows=[]
  for case in ('agree','disagree','count-change'):
   run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case],capture_output=True,text=True,timeout=121)
   if run.returncode:raise RuntimeError(run.stdout+run.stderr)
   row=json.loads(run.stdout);rows.append(row);print(json.dumps(row),flush=True)
  Path('benchmarks/player_match_groups/cut-out-seven-w2-mid-results.json').write_text(json.dumps(dict(cases=rows,limits=dict(comparison_seconds=30,worker_seconds=120,peak_working_set_bytes=1500000000),scope='selected actual7 W2 public intermediate only; no initial Forecast'),indent=2)+'\n')
  if any(row['status']!='verified' for row in rows):sys.exit(1)