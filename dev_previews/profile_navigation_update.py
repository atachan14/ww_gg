"""Single cold seven-player public Update; optional process-local profiling only."""
import argparse,json,tempfile,hashlib,sys
from pathlib import Path
from time import perf_counter,process_time
from collections import defaultdict
from threading import local
from functools import wraps
from app import create_app
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.grouped_forecast import GroupedForecast

parser=argparse.ArgumentParser();parser.add_argument('--profile',action='store_true');parser.add_argument('--cpu-profile',action='store_true');parser.add_argument('--call-profile',action='store_true');parser.add_argument('--legacy-publication-label-flow',action='store_true');parser.add_argument('--detail',action='store_true');parser.add_argument('--sample',action='store_true');parser.add_argument('--partition-count',action='store_true');parser.add_argument('--transition-count',action='store_true');parser.add_argument('--uncached-death-transitions',action='store_true');parser.add_argument('--clone-actor-hypotheses',action='store_true');parser.add_argument('--output',default='.artifacts/navigation-update-timing.json');args=parser.parse_args()
# Optional dev-only stack sampler; do not label sampled time uninstrumented.
from threading import Thread,Event,get_ident
from collections import Counter
samples=Counter();sample_stop=Event();sample_thread=None;sample_owner=get_ident()
def sample_stacks():
 while not sample_stop.wait(.005):
  frame=sys._current_frames().get(sample_owner);stack=[]
  while frame is not None:
   if '/werewolf/' in frame.f_code.co_filename.replace('\\','/'):
    stack.append((Path(frame.f_code.co_filename).name,frame.f_code.co_name,frame.f_lineno))
   frame=frame.f_back
  if stack:samples[tuple(stack)]+=1
metrics=defaultdict(lambda:dict(calls=0,seconds=0.,exclusive=0.,hits=0,misses=0));stack=local()
def measured(name,fn,*a,**kw):
 frames=getattr(stack,'frames',None)
 if frames is None:frames=[];stack.frames=frames
 frame=[perf_counter(),0.];frames.append(frame)
 try:return fn(*a,**kw)
 finally:
  elapsed=perf_counter()-frame[0];frames.pop();row=metrics[name];row['calls']+=1;row['seconds']+=elapsed;row['exclusive']+=elapsed-frame[1]
  if frames:frames[-1][1]+=elapsed
class Cache(dict):
 def __init__(self,name,source):super().__init__(source);self.name=name
 def __contains__(self,key):
  found=measured('cache.'+self.name+'.contains',super().__contains__,key);metrics['cache.'+self.name+'.contains']['hits' if found else 'misses']+=1;return found
 def __getitem__(self,key):return measured('cache.'+self.name+'.getitem',super().__getitem__,key)
 def __setitem__(self,key,value):return measured('cache.'+self.name+'.setitem',super().__setitem__,key,value)
 def get(self,key,default=None):return measured('cache.'+self.name+'.get',super().get,key,default)
if args.profile:
 init=InformationSetForecast.__init__
 def initialize(self,*a,**kw):
  init(self,*a,**kw)
  for name in ('values','action_values','scores','policies','mornings','publication_values','public_support_values','exact_keys','reduced_descriptors','joint_keys','board_key_hashes'):
   value=getattr(self,name,None)
   if type(value)is dict:setattr(self,name,Cache(name,value))
 InformationSetForecast.__init__=initialize
 for cls in (InformationSetForecast,GroupedForecast):
  for name in ('solve','act','cached_flow','continuation_context','full_renamed_key','renamed_value_key','value_law','day_scores','public_day_max','wolf_policy','report_children','acquire','equivalent_targets','actor_equivalent_targets','scalar_descriptor',*(() if not args.detail else ('uncached_act','project','physical_children','public_children','generate_morning','morning','publications','report_outcomes','terminal_report_value','terminal_max_report_value','publication_kernel','wolf_cells','target_orbits','weighted_actor_targets','exchangeable','score_day_targets'))):
   if name not in cls.__dict__:continue
   original=getattr(cls,name)
   def wrapper(self,*a,__fn=original,__name=cls.__name__+'.'+name,**kw):return measured(__name,__fn,self,*a,**kw)
   setattr(cls,name,wraps(original)(wrapper))
 # Wrap imported references to the same pure normalization/key functions, no
 # argument changes or additional equality/hash operation is performed.
 from werewolf.seer_acquisition import normalize
 from werewolf.public_convergence import state_key
 for original,label in [(normalize,'normalize'),(state_key,'state_key')]:
  def wrapper(*a,__fn=original,__name=label,**kw):return measured(__name,__fn,*a,**kw)
  for module in list(sys.modules.values()):
   if not getattr(module,'__name__','').startswith('werewolf'):continue
   for name,value in list(vars(module).items()):
    if value is original:setattr(module,name,wraps(original)(wrapper))

if args.profile and args.detail:
 from werewolf.exact import Board
 from werewolf.seer_future_uniform import TrueScanState
 from werewolf.seer_acquisition import Hypothesis
 for cls in (Board,TrueScanState,Hypothesis):
  original=cls.__post_init__
  def wrapper(self,*a,__fn=original,__name=cls.__name__+'.construct',**kw):return measured(__name,__fn,self,*a,**kw)
  cls.__post_init__=wraps(original)(wrapper)
  for name in ('winner','worlds','alive_mask','wolf_count_distribution','initial_role_counts','public_roles'):
   prop=vars(cls).get(name)
   if not isinstance(prop,property):continue
   def getter(self,__fn=prop.fget,__name=cls.__name__+'.'+name):return measured(__name,__fn,self)
   setattr(cls,name,property(getter,prop.fset,prop.fdel,prop.__doc__))
 from werewolf.evaluation_branch import physical_board
 from werewolf.belief_projection import project_private,_normalized_immutable_state
 from werewolf.action_flow import resolve_action,action_flow
 from werewolf.board_future import reconstruct_child
 from werewolf.win_certificate import certify
 for original in (physical_board,project_private,_normalized_immutable_state,resolve_action,action_flow,reconstruct_child,certify):
  def wrapper(*a,__fn=original,__name=original.__name__,**kw):return measured(__name,__fn,*a,**kw)
  for module in list(sys.modules.values()):
   if not getattr(module,'__name__','').startswith('werewolf'):continue
   for name,value in list(vars(module).items()):
    if value is original:setattr(module,name,wraps(original)(wrapper))

# Dev-only wall timer around the actual evaluator entry; excludes streamed HTML.
from werewolf.closed_calculation import _Node
forecast_times=[]
_original_forecast=_Node.forecast
def _timed_forecast(node):
 t=perf_counter()
 try:return _original_forecast(node)
 finally:forecast_times.append(perf_counter()-t)
_Node.forecast=_timed_forecast
if args.profile and args.detail:
 from werewolf import guard_history_prior,guard_model,actor_information
 from werewolf.evaluation_graph import EvaluationGraph
 for module,names in [(guard_history_prior,('guard_history_ready','public_history_ready')),(guard_model,('scope_reason','live_guard_mass')),(actor_information,('wolf_information_groups','condition_actor_state'))]:
  for name in names:
   original=getattr(module,name)
   def wrapper(*a,__fn=original,__name=module.__name__+'.'+name,**kw):return measured(__name,__fn,*a,**kw)
   for m in list(sys.modules.values()):
    if not getattr(m,'__name__','').startswith('werewolf'):continue
    for key,value in list(vars(m).items()):
     if value is original:setattr(m,key,wraps(original)(wrapper))
 for name in ('record_day_value','recorded_day_scope','random_day_scope','personal_max_scope'):
  original=getattr(EvaluationGraph,name)
  def wrapper(self,*a,__fn=original,__name='EvaluationGraph.'+name,**kw):return measured(__name,__fn,self,*a,**kw)
  setattr(EvaluationGraph,name,wraps(original)(wrapper))

if args.clone_actor_hypotheses:
 # Process-local old-flow control; no production file or policy is changed.
 from dataclasses import replace as actor_replace
 from werewolf.seer_acquisition import normalize as actor_normalize
 from werewolf.night_knowledge import merge_night_records as actor_merge
 def clone_actor(state,compatible,guards=(),attacks=()):
  entries=tuple(actor_replace(h,guards=actor_merge(h.guards,guards) if guards else h.guards,
      attacks=actor_merge(h.attacks,attacks) if attacks else h.attacks)
      for h in state.hypotheses if compatible(h))
  return actor_replace(state,hypotheses=actor_normalize(entries))
 from werewolf.actor_information import condition_actor_state as original_actor
 for module in list(sys.modules.values()):
  if getattr(module,'__name__','').startswith('werewolf'):
   for name,value in list(vars(module).items()):
    if value is original_actor:setattr(module,name,clone_actor)

partition_stats=dict(calls=0,hits256=0,hits1024=0,seconds=0.)
if args.partition_count:
 from collections import OrderedDict
 from werewolf.group_partition import _frame_groups as _original_partition
 simulated={256:OrderedDict(),1024:OrderedDict()}
 def _count_partition(groups,b,past,observer=None,*,target=None):
  key=(groups,b,past,observer,target);partition_stats['calls']+=1
  for capacity,cache in simulated.items():
   if key in cache:
    partition_stats['hits'+str(capacity)]+=1;cache.move_to_end(key)
   else:
    cache[key]=None
    if len(cache)>capacity:cache.popitem(last=False)
  t=perf_counter()
  try:return _original_partition(groups,b,past,observer,target=target)
  finally:partition_stats['seconds']+=perf_counter()-t
 for module in list(sys.modules.values()):
  if getattr(module,'__name__','').startswith('werewolf'):
   for name,value in list(vars(module).items()):
    if value is _original_partition:setattr(module,name,_count_partition)

if args.uncached_death_transitions:
 from werewolf import information_set_forecast as transition_module
 def direct_transition(self,b,target,rules,strategy):return transition_module.action_outcomes(b,target,rules,strategy)
 InformationSetForecast.transition_children=direct_transition

if args.legacy_publication_label_flow:
 from dev_previews.publication_label_reference import install
 install()

transition_records={}
if args.transition_count:
 from collections import OrderedDict
 from werewolf import exact,phase_updates
 class TransitionKey:
  def __init__(self,value):
   t=process_time();self.value=value;self.hashed=hash(value);self.hash_cpu=process_time()-t
  def __hash__(self):return self.hashed
  def __eq__(self,other):return self.value==other.value
 def transition_call(name,fn,values,args,kwargs):
  row=transition_records.setdefault(name,dict(calls=0,failures=0,generate_wall=0.,generate_cpu=0.,duplicate_cpu=0.,hash_cpu=0.,lookup_cpu=0.,seen=set(),caches={256:OrderedDict(),1024:OrderedDict()},hits={256:0,1024:0}))
  row['calls']+=1;key=TransitionKey(values);row['hash_cpu']+=key.hash_cpu;t=process_time();duplicate=key in row['seen']
  for size,cache in row['caches'].items():
   if key in cache:row['hits'][size]+=1;cache.move_to_end(key)
  row['lookup_cpu']+=process_time()-t;wall=perf_counter();cpu=process_time()
  try:result=fn(*args,**kwargs)
  except BaseException:
   row['failures']+=1;raise
  else:
   elapsed=process_time()-cpu;row['generate_cpu']+=elapsed;row['generate_wall']+=perf_counter()-wall
   if duplicate:row['duplicate_cpu']+=elapsed
   row['seen'].add(key)
   for size,cache in row['caches'].items():
    cache[key]=None
    if len(cache)>size:cache.popitem(last=False)
   return result
 original_action=exact.action_outcomes;original_night=phase_updates.night_observation_outcomes;original_condition=phase_updates.condition_night_corpse
 def counted_action(b,target,rules,strategy):
  args=(b,target,rules,strategy);return transition_call('action_outcomes',original_action,args,args,{})
 def counted_night(b,target,rules,strategy,*,guard_state=None,transition=None):
  args=(b,target,rules,strategy);return transition_call('night_observation_outcomes',original_night,(*args,guard_state,transition),args,dict(guard_state=guard_state,transition=transition))
 def counted_condition(b,target,rules,*,guard_state=None):
  args=(b,target,rules);return transition_call('condition_night_corpse',original_condition,(*args,guard_state),args,dict(guard_state=guard_state))
 for original,wrapper in ((original_action,counted_action),(original_night,counted_night),(original_condition,counted_condition)):
  for module in list(sys.modules.values()):
   if getattr(module,'__name__','').startswith('werewolf'):
    for name,value in list(vars(module).items()):
     if value is original:setattr(module,name,wrapper)

def events(response):return [json.loads(row) for row in response.data.splitlines() if row.strip()]
with tempfile.TemporaryDirectory() as directory:
 app=create_app(dict(TESTING=True,SECRET_KEY='profile-fixture-only',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True,CALCULATION_POSITION_ENABLED=False,NAVIGATION_DIRECTORY=directory))
 client=app.test_client();client.post('/start',data=dict(citizens=3,mediums=1,seers=1,wolves=2,day='max',night='max',fake_reports='max',win_cutoff=1))
 t=perf_counter();client.get('/main',headers={'Sec-Fetch-Dest':'document'});initial=events(client.get('/navigation/calculation?occurrence=h0&revision=0',headers={'Accept':'application/x-ndjson'}));assert initial[-1]['event']=='complete';initial_s=perf_counter()-t
 # Replay the actual initial browser expansion sequence from the baseline.
 for node in [None,'h0~1','h0~6','h0~16','h0~28']:
  response=client.get('/game-tree',query_string={**({} if node is None else dict(node=node)),**dict(expand=1,format='public-tree',defer_analysis=1)});assert response.status_code==200,response.status_code
 payload=dict(claims=['seer','seer','medium','latent','latent','latent','latent'],seers=[dict(day=1,reporter=p,target=3,color='white') for p in (1,2)],mediums=[])
 t=perf_counter();adopted=client.post('/table-publish',data=dict(revision=0,payload=json.dumps(payload)),headers={'X-WW-Staged':'1'});adopt_s=perf_counter()-t;assert adopted.status_code==200,adopted.json
 metrics.clear();forecast_times.clear();transition_records.clear()
 if args.sample:
  sample_thread=Thread(target=sample_stacks,daemon=True);sample_thread.start()
 if args.cpu_profile or args.call_profile:
  import cProfile
  cpu_profile=(cProfile.Profile(timer=process_time,builtins=False) if args.cpu_profile else cProfile.Profile());cpu_profile.enable()
 else:cpu_profile=None
 cpu_start=process_time();t=perf_counter();response=client.get('/navigation/calculation?occurrence=h1&revision=1',headers={'Accept':'application/x-ndjson'},buffered=False);roles=None;complete=None
 try:
  for raw in response.response:
   row=json.loads(raw)
   if row['event']=='roles':roles=perf_counter()-t
   if row['event']=='error':raise RuntimeError(row)
   if row['event']=='complete':complete=row
 finally:
  if cpu_profile is not None:
   cpu_profile.disable();cpu_profile.dump_stats(str(Path(args.output).with_suffix('.prof')))
 solve_s=perf_counter()-t;cpu_seconds=process_time()-cpu_start;sample_stop.set();
 if sample_thread is not None:sample_thread.join(2)
 evaluator_times=tuple(forecast_times);response.close();assert complete and complete['value_complete']
 doc=next(iter(app.extensions['navigation_store']._documents.values()))
 from werewolf.navigation_evaluation import capture
 from werewolf.public_convergence import state_key as source_key
 evaluation=capture(doc);value=evaluation.forecast();node=evaluation.current.navigation.node
 fingerprint=hashlib.sha256(repr(source_key(node.read())).encode()).hexdigest()
 engine=getattr(node,'_Node__calculation')._ClosedCalculation__engine
 sizes={name:len(getattr(engine,name)) for name in ('values','action_values','scores','policies','mornings')}
 transition_summary={name:{**{k:v for k,v in row.items() if k not in ('seen','caches')},'distinct_completed_inputs':len(row['seen'])} for name,row in transition_records.items()}
 result=dict(legacy_publication_label_flow=args.legacy_publication_label_flow,call_profiled=args.call_profile,cpu_profiled=args.cpu_profile,uncached_death_transitions=args.uncached_death_transitions,transitions=transition_summary,transition_instrumented=args.transition_count,profiled=args.profile,sampled=args.sample,clone_actor_hypotheses=args.clone_actor_hypotheses,partition_instrumented=args.partition_count,partition_stats=partition_stats,samples=[(list(k),v) for k,v in samples.most_common()],initial_seconds=initial_s,adoption_seconds=adopt_s,roles_seconds=roles,win_seconds=solve_s,calculation_cpu_seconds=cpu_seconds,evaluator_forecast_seconds=evaluator_times,forecast=dict(village_win=str(value.village_win),action_values=[(p,str(v)) for p,v in value.action_values],by_dawn_values=[(p,str(v)) for p,v in value.by_dawn_values]),source_fingerprint=fingerprint,cache_sizes=sizes,expansions=engine.expansions,metrics=dict(metrics))
 t=perf_counter();again=events(client.get('/navigation/calculation?occurrence=h1&revision=1',headers={'Accept':'application/x-ndjson'}));result['warm_win_seconds']=perf_counter()-t;assert again[-1]['event']=='complete'
 Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ('metrics','samples')}));print('profile',args.output)
