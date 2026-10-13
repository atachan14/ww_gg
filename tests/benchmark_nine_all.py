"""Fixed nine-player scope audit, never a public benchmark endpoint."""
import json,platform,sys,time
from pathlib import Path
from unittest.mock import patch
from contextlib import contextmanager
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from werewolf.exact import initial_board,group_initial_board,ClaimPolicy,Rules,Strategy,action_outcomes
from werewolf.model_a_public import evaluate_public_game,clear_public_cache
from werewolf.public_prior import clear_public_prior_cache,prepare_public_prior
from werewolf.information_set_forecast import InformationSetForecast,exchangeable_value,Pending
from werewolf.seer_future_uniform import TrueScanState,FuturePending
from werewolf.calculation_budget import calculation_budget,_current
from werewolf.joint_value_key import renamings

CASES=[
 ('single',2,0,1,0,('seer',)+('latent',)*8,'none','all','all'),
 ('certain',2,0,1,0,('seer',)+('latent',)*8,'filled','all','all'),
 ('mixed',2,2,1,0,('seer','medium','medium')+('latent',)*6,'none','all','all'),
 ('named',2,2,1,0,('seer','medium','medium','villager','villager')+('latent',)*4,'none','all','all'),
 ('hunter-free',2,2,1,1,('seer','medium','medium')+('latent',)*6,'none','all','all'),
 ('medium-none',2,2,1,0,('seer','medium','medium')+('latent',)*6,'none','all','none'),
 ('seer-none',2,2,1,0,('seer','medium','medium')+('latent',)*6,'none','none','all'),
 ('multi-law',2,0,2,0,('seer','seer')+('latent',)*7,'none','all','all'),
]


def joint_law_probe(b,game,rules,strategy):
 s,past=prepare_public_prior(game,b,rules);engine=InformationSetForecast(rules,strategy)
 night=next(o.board for o in action_outcomes(b,9,rules,strategy) if o.board.winner is None)
 acquired=engine.acquire(night,engine.project(s,night))
 day=next(o.board for o in engine.public_children(night,8) if o.board.winner is None)
 try:engine.publications(day,engine.project(acquired,day),past);reason=None
 except Pending as error:reason=error.reason
 return {'execution':9,'night_corpse':8,'day':2,'reason':reason}


def run(case):
 name,w,m,s,h,claims,cco,seer_open,medium_open=case
 for clear in (clear_public_cache,clear_public_prior_cache,exchangeable_value.cache_clear,renamings.cache_clear):clear()
 rules=Rules(initial_seer='none');strategy=Strategy(seer_disclosure=seer_open,medium_disclosure=medium_open)
 b=group_initial_board(initial_board(9,w,m,s,h),claims,ClaimPolicy(villager='none',medium='none',seer=cco,hunter='none'))
 game={'players':9,'rules':{'initial_seer':'none'},'seer_options':{'initial_rule':'none'},'seer_inputs':[],'public_log':{'version':2}}
 engines=[];work=[0];marginal={'calls':0,'unique':{},'seconds':0.0}
 original= TrueScanState.public_roles.fget
 def marginal_getter(state):
  marginal['calls']+=1;marginal['unique'][id(state)]=state
  started=time.perf_counter();value=original(state);marginal['seconds']+=time.perf_counter()-started
  return value
 @contextmanager
 def budget(*args,**kwargs):
  with calculation_budget(*args,**kwargs):
   state=_current.get()
   try:yield
   finally:
    if state:work[0]=max(work[0],state[1])
 class Diagnostic(InformationSetForecast):
  def __init__(self,*args,**kwargs):
   kwargs['trace']={};super().__init__(*args,**kwargs);engines.append(self)
 started=time.perf_counter()
 with patch('werewolf.model_a_public.InformationSetForecast',Diagnostic), \
      patch('werewolf.model_a_public.calculation_budget',budget), \
      patch.object(TrueScanState,'public_roles',property(marginal_getter)):
  result=evaluate_public_game(game,b,rules,strategy)
 elapsed=time.perf_counter()-started;engine=engines[-1]
 co=tuple(p for p in b.alive if b.claims[p-1]=='seer')
 possible_fakes=max(sum(not world[2]&(1<<(p-1)) for p in co) for world in b.worlds)
 return {'id':name,'cast':{'wolf':w,'medium':m,'seer':s,'hunter':h,'villager':9-w-m-s-h},
  'claims':claims,'co_seer_condition':cco,'model':'group','rules':rules.__dict__,'strategy':strategy.__dict__,
  'hunter_scope':'ability-free only; no protection evaluation','seconds':elapsed,'work':work[0],
  'initial_worlds':len(b.worlds),'max_live_fake_seers':possible_fakes,
  'joint_law_unselected':seer_open=='all' and possible_fakes>1,
  'reachable_law_probe':joint_law_probe(b,game,rules,strategy) if possible_fakes>1 and seer_open=='all' else None,
  'pending':result.reason if isinstance(result,FuturePending) else None,
  'village_win':None if isinstance(result,FuturePending) else str(result.village_win),
  'rows':0 if isinstance(result,FuturePending) else len(result.action_values),
  'horizon_rows':0 if isinstance(result,FuturePending) else len(result.by_dawn_values),
  'cache_sizes':{k:len(getattr(engine,k)) for k in ('values','scores','policies','acquired','action_values','mornings','publication_values')},
  'flow_memo':engine.trace.get('flow_memo',{}),
  'role_marginal':{'calls':marginal['calls'],'unique_states':len(marginal['unique']),'seconds':marginal['seconds']}}


if __name__=='__main__':
 records=[]
 for case in CASES:
  record=run(case);records.append(record);print(json.dumps(record),flush=True)
  Path('docs/nine-all-benchmark.json').write_text(json.dumps({'python':platform.python_version(),
   'method':'Fixed set nine-player-audit-set.md; cold public/prior/count/renaming caches; 250000work/20sec unchanged. Complete facade or explicit Pending. Counting role marginals adds overhead; no general performance guarantee.',
   'cases':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
