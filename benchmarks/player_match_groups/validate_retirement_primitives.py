"""Validate new retirement/scalar sharing against frozen original primitives."""
import json,time,threading
from pathlib import Path
from fractions import Fraction as F
from . import checkpoint_audit as base
from .primitive_checkpoint import fields
from .retirement_proof import RetirementProofForecast
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.evaluation_projection import project_evaluation
from werewolf.calculation_budget import calculation_budget,cancellation_scope
from benchmarks.board_b_benchmark import process_memory_peak


def run():
    source=base.read(Path('benchmarks/player_match_groups/primitive-seven-assessment.json'))
    saved=base.read(base.CACHE/source['identity']/'summary.json')
    game=base.read(Path('benchmarks/player_match_groups/checkpoint-seven-input.json'))
    assert base.engine_version()==source['engine']==saved['engine']
    assert base.digest(game)==source['input']==saved['input']
    prepared=list(base.prepared_game(game));prepared[2],prepared[3]=project_evaluation(prepared[2],prepared[3],prepared[6])
    trial=RetirementProofForecast(prepared[5],prepared[6],future_reuse=True,physical_reuse=True,retired_reuse=True,compact_keys=True,fast_parts=True,retirement_proof=True,max_work=4000000)
    terms={};rows=[];started=time.perf_counter();cancel=threading.Event();done=threading.Event()
    def monitor():
        while not done.wait(.1):
            peak=process_memory_peak()
            if max(peak['peak_working_set_bytes'],peak['peak_process_commit_bytes'])>=1500000000:cancel.set()
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    try:
        with calculation_budget(4000000,max_seconds=90),cancellation_scope(cancel):
            for root in range(1,8):
                old,metadata=base.night_plan(prepared,InformationSetForecast(prepared[5],prepared[6]),root)
                assert metadata==saved['plans'][str(root)]
                new,_=base.night_plan(prepared,trial,root)
                assert len(old)==len(new)
                for a,b in zip(old,new):
                    assert a['weight']==b['weight'] and a['bite']==b['bite']
                    ai,bi=a['inputs'],b['inputs']
                    assert ai[:2]+ai[3:]==bi[:2]+bi[3:]
                    if ai[2]!=bi[2]:
                        assert not ai[2] and bi[2]==prepared[4] and ai[0].initial_seer_count==0
                    terms[(root,a['bite'],a['signature'])]=b
            for key,row in sorted(saved['parts']['oracle'].items()):
                if row['status']!='complete':continue
                assert row['checksum']==base.digest(fields(row))
                assert (row['engine'],row['input'])==(source['engine'],source['input'])
                term=terms[row['root'],row['bite'],row['signature']]
                assert str(term['weight'])==row['weight']
                child,public,history,group,observer,actual,fixed=term['inputs']
                value=trial.act(child,public,history,fixed,group,observer,physical=actual)
                assert value==F(row['value']),(key,value,row['value'])
                rows.append(dict(key=key,value=str(value),original_signature=row['signature'],original_checksum=row['checksum']))
    finally:done.set();thread.join()
    return dict(frozen_engine=source['engine'],input=source['input'],original_plan_and_coefficients_verified=True,original_private_and_physical_laws_verified=True,verified_original_oracle_primitives=len(rows),seconds=time.perf_counter()-started,memory=process_memory_peak(),rows=rows)

if __name__=='__main__':
    result=run();Path('benchmarks/player_match_groups/retirement-proof-primitive-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='rows'}),flush=True)
