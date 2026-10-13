"""Local root-snapshot audit; excludes warm-cache reuse and is not a guarantee."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from werewolf.exact import initial_board,condition_claims,group_initial_board,ClaimPolicy,Rules,Strategy
from werewolf.model_a_public import evaluate_public_game,clear_public_cache
from werewolf.public_prior import clear_public_prior_cache
from werewolf.seer_future_uniform import FuturePending

cases=[
 (9,2,2,1,1,('medium',)+('latent',)*8,'equal',Strategy(seer_disclosure='none')),
 (9,2,2,1,1,('medium','medium')+('latent',)*7,'group',Strategy(seer_disclosure='none')),
 (9,2,2,1,1,('medium','medium','seer','hunter')+('latent',)*5,'group',Strategy(fake_reports='random',seer_disclosure='none')),
 (9,2,2,2,2,('medium','medium')+('latent',)*7,'equal',Strategy('random','random',fake_reports='random',seer_disclosure='none')),
 (9,2,2,2,2,('medium',)*3+('latent',)*6,'group',Strategy(include_self_bite=True,seer_disclosure='none')),
 (9,3,2,1,1,('medium','seer','hunter')+('latent',)*6,'group',Strategy(fake_reports='random',seer_disclosure='none')),
 (9,2,2,0,0,('medium',)*4+('latent',)*5,'group',Strategy(fake_reports='random',seer_disclosure='none')),
 (9,2,0,2,2,('seer','hunter')+('latent',)*7,'group',Strategy(seer_disclosure='none')),
 (9,1,8,0,0,('medium',)*9,'equal',Strategy(seer_disclosure='none')),
 (9,2,7,0,0,('medium',)*9,'group',Strategy(fake_reports='random',seer_disclosure='none')),
 (7,2,2,1,0,('seer','medium','medium')+('latent',)*4,'equal',Strategy()),
]
records=[]
for n,w,m,s,h,claims,mode,strategy in cases:
 clear_public_cache();clear_public_prior_cache();started=time.perf_counter()
 b=initial_board(n,w,m,s,h);initial_worlds=len(b.worlds)
 policy=ClaimPolicy(villager='none',medium='none',seer='none',hunter='none')
 b=(group_initial_board if mode=='group' else condition_claims)(b,claims,policy)
 game={'players':n,'rules':{'initial_seer':'none'},'seer_options':{'initial_rule':'none'},'seer_inputs':[],'public_log':{'version':2}}
 result=evaluate_public_game(game,b,Rules(True,initial_seer='none'),strategy)
 record={'cast':[n,w,m,s,h],'claims':claims,'model':mode,'strategy':strategy.__dict__,
         'initial_worlds':initial_worlds,'seconds':round(time.perf_counter()-started,4),
         'pending':result.reason if isinstance(result,FuturePending) else None,
         'village_win':None if isinstance(result,FuturePending) else str(result.village_win),
         'rows':0 if isinstance(result,FuturePending) else len(result.action_values)}
 records.append(record);print(json.dumps(record),flush=True)
Path('docs/model-a-root-benchmark.json').write_text(json.dumps({'method':'Windows root snapshots only; cold public/prior caches; exact complete rows or Pending; default 250000work/20sec. First ten preserve historical v0.4 no-seer-ability scope explicitly; last case exercises live seer/medium all. No general performance guarantee or full-history coverage.','cases':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
