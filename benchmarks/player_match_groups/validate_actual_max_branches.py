"""Bounded original actual-max branch audit; no count-law reference."""
import json,time,threading
from pathlib import Path
from unittest.mock import patch
from .extension_cases import prepare_game
from .extension_reuse import ExtensionForecast
from .checkpoint_audit import digest,engine_version
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.model_a_public import public_forecast
from werewolf.calculation_budget import calculation_budget,cancellation_scope
from werewolf.seer_future_uniform import FuturePending
from benchmarks.board_b_benchmark import process_memory_peak


class OriginalRecorder(InformationSetForecast):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.completed={}
    def uncached_act(self,b,s,past,target,private,observer,*,physical=None):
        value=super().uncached_act(b,s,past,target,private,observer,physical=physical)
        if len(self.completed)<128 and len(b.alive)>=4 and 0<value<1:
            inputs=(b,s,past,target,private,observer,physical);signature=digest(inputs)
            self.completed.setdefault(signature,(inputs,value))
        return value


def run():
    source=json.loads(Path('benchmarks/player_match_groups/actual-seven-extended-retirement.json').read_text())
    game=source['game'];_,_,b,s,past,rules,strategy,_=prepare_game(game)
    engines=[];done=threading.Event();cancel=threading.Event()
    def factory(*args,**kwargs):
        e=OriginalRecorder(*args,**kwargs);engines.append(e);return e
    def monitor():
        while not done.wait(.1):
            peak=process_memory_peak()
            if max(peak['peak_working_set_bytes'],peak['peak_process_commit_bytes'])>=1500000000:cancel.set()
    thread=threading.Thread(target=monitor,daemon=True);thread.start();started=time.perf_counter()
    try:
        with patch('werewolf.model_a_public.InformationSetForecast',factory),cancellation_scope(cancel):
            original=public_forecast(b,s,past,rules,strategy,max_work=4000000,max_seconds=25)
        elapsed=time.perf_counter()-started;recorded=engines[0].completed
        trial=ExtensionForecast(rules,strategy,future_reuse=True,physical_reuse=True,retired_reuse=True,compact_keys=True,fast_parts=True,combined_reuse=True,retirement_proof=True,extended_retirement=True)
        rows=[]
        with calculation_budget(4000000,max_seconds=30),cancellation_scope(cancel):
            for signature,(inputs,expected) in recorded.items():
                child,public,history,target,private,observer,physical=inputs
                actual=trial.act(child,public,history,target,private,observer,physical=physical)
                assert actual==expected,(signature,actual,expected)
                rows.append(dict(input=signature,value=str(actual),alive=len(child.alive),private_hypotheses=len(private.hypotheses),public_hypotheses=len(public.hypotheses)))
        assert rows
        return dict(input=digest(game),frozen_core=engine_version(),original_full_complete=not isinstance(original,FuturePending),original_seconds=elapsed,original_recorded_nontrivial=len(recorded),verified=len(rows),all_equal=True,reference='original InformationSetForecast completed nontrivial act calls; exact full arguments/physical/private evidence passed unchanged',rows=rows,seconds=time.perf_counter()-started,memory=process_memory_peak())
    finally:done.set();thread.join()

if __name__=='__main__':
    result=run();Path('benchmarks/player_match_groups/actual-max-branch-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='rows'}),flush=True)
