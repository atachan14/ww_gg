"""Reproduce the fixed seven-player full-disclosure budget case locally."""
import json,sys,time,platform
from pathlib import Path
from collections import Counter
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from werewolf.exact import initial_board,condition_claims,ClaimPolicy,Rules,Strategy
from werewolf.public_prior import prepare_public_prior,clear_public_prior_cache
from werewolf.model_a_public import public_forecast
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.seer_future_uniform import FuturePending
from werewolf.calculation_budget import _current
from werewolf.joint_value_key import renamings


def run(optimized):
    clear_public_prior_cache();renamings.cache_clear()
    b=condition_claims(initial_board(7,2,2,1),('seer','medium','medium')+('latent',)*4,
                       ClaimPolicy(medium='none',seer='none'))
    game={'players':7,'rules':{'initial_seer':'none'},'seer_options':{'initial_rule':'none'},
          'seer_inputs':[],'public_log':{'version':2}}
    rules=Rules(initial_seer='none');s,past=prepare_public_prior(game,b,rules)
    counts=Counter();unique={k:set() for k in ('act','morning','publications')};engines=[];work=[0]
    class Diagnostic(InformationSetForecast):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs,memoize_flows=optimized,retire_uninformative_scans=optimized,trace={})
            if not optimized:self.equivalent_targets=lambda *args:False
            engines.append(self)
        def scalar(self,*args):
            try:return super().scalar(*args)
            finally:
                state=_current.get()
                if state:work[0]=max(work[0],state[1])
        def act(self,b,s,past,target,private,observer):
            counts['act']+=1;unique['act'].add((b,s,past,target,private,observer))
            try:return super().act(b,s,past,target,private,observer)
            finally:
                state=_current.get()
                if state:work[0]=max(work[0],state[1])
        def morning(self,b,s,past):
            counts['morning']+=1;unique['morning'].add((b,s,past))
            return super().morning(b,s,past)
        def publications(self,b,s,past):
            counts['publications']+=1;unique['publications'].add((b,s,past))
            return super().publications(b,s,past)
    started=time.perf_counter()
    with patch('werewolf.model_a_public.InformationSetForecast',Diagnostic):
        if optimized:result=public_forecast(b,s,past,rules,Strategy())
        else:
            with patch('werewolf.model_a_public.project_evaluation',side_effect=lambda b,s,p:(b,s)):
                result=public_forecast(b,s,past,rules,Strategy())
    engine=engines[0]
    return {'mode':'optimized' if optimized else 'uncompressed_reference','seconds':time.perf_counter()-started,
            'work':work[0],'initial_hypotheses':len(s.hypotheses),'calls':dict(counts),
            'unique_inputs':{k:len(v) for k,v in unique.items()},'memo':engine.trace.get('flow_memo',{}),
            'cache_sizes':{k:len(getattr(engine,k)) for k in ('values','scores','policies','acquired','action_values','mornings','publication_values','joint_descriptors')},
            'pending':result.reason if isinstance(result,FuturePending) else None,
            'village_win':None if isinstance(result,FuturePending) else str(result.village_win),
            'actions':None if isinstance(result,FuturePending) else {str(p):str(v) for p,v in result.action_values},
            'horizon':None if isinstance(result,FuturePending) else {str(p):[str(v.village_win),str(v.wolf_win)] for p,v in result.by_dawn_values}}


if __name__=='__main__':
    records=[]
    for mode in (False,True):
        result=run(mode);records.append(result);print(json.dumps(result),flush=True)
    Path('docs/mixed-model-a-benchmark.json').write_text(json.dumps({'python':platform.python_version(),
        'method':'Fixed cast 7/wolf2/medium2/seer1; CO seer1 medium2 medium3; no initial scan; fixed CO/all; max/max/max; both use production 250000work/20sec. Cold request-local caches and label tables. Counting instrumentation affects wall time. Reference Pending is not an independent full seven-player equality proof.',
        'cases':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
