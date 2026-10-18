"""Bounded root7 history comparison, original vs existing-key construction only."""
import json,time,threading
from pathlib import Path
from dataclasses import asdict
from unittest.mock import patch
from werewolf.exact import Rules,Strategy
from werewolf.seer_manual import migrate_game,replay
from werewolf.root_secret_flow import prepare_root_entry,root_branch_forecast,RootSecretEngine
from werewolf.seer_future_uniform import FuturePending
from werewolf.calculation_budget import calculation_budget,cancellation_scope
from benchmarks.board_b_benchmark import process_memory_peak
from .checkpoint_audit import encode
from .local_root import LocalRootEngine


def game(repeat=True):
    saved=asdict(Strategy(day='random',night='random',fake_reports='random',disclosure_common='none'))
    current={**saved,'night':'max'};claims=['hunter']+['latent']*6
    history=[]
    for target,deaths in ((7,[6]),(5,[])):
        history.append(dict(target=target,claims=claims,claim_policy={'hunter':'none'},policy=saved))
        history.append(dict(target=deaths[0] if deaths else None,claims=claims,claim_policy={'hunter':'none'},policy=saved,observation='night-deaths-v1',deaths=deaths))
    history.append(dict(target=4,claims=claims,claim_policy={'hunter':'none'},policy=saved))
    return migrate_game(dict(players=7,wolves=1,mediums=0,seers=0,hunters=1,claims=claims,claim_policy={'hunter':'none'},policy=current,rules=asdict(Rules(allow_repeat_guard=repeat)),seer_mode='information-fixed-v1',seer_inputs=[],history=history))


def run():
    result=[];done=threading.Event();cancel=threading.Event()
    def monitor():
        while not done.wait(.1):
            m=process_memory_peak()
            if max(m['peak_working_set_bytes'],m['peak_process_commit_bytes'])>=1500000000:cancel.set()
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    try:
        with cancellation_scope(cancel):
            for repeat in(True,False):
                g=game(repeat)
                with calculation_budget(4000000,max_seconds=20):
                    rules,p=replay(g);strategy=Strategy(**g['policy']);branch=prepare_root_entry(g,p.board,rules,strategy,max_seconds=20)
                if isinstance(branch,FuturePending):raise AssertionError(branch)
                rows=[]
                for cls in(RootSecretEngine,LocalRootEngine):
                    engines=[]
                    def factory(original,board,rules,strategy,**kwargs):
                        e=cls(rules,strategy,**kwargs);engines.append(e);return e
                    started=time.perf_counter()
                    with patch('werewolf.local_reuse.make_root_engine',factory):value=root_branch_forecast(branch,rules,strategy,max_seconds=20)
                    rows.append(dict(engine=cls.__name__,seconds=time.perf_counter()-started,complete=not isinstance(value,FuturePending),forecast=encode(value),key_calls=getattr(engines[0],'local_key_calls',None),mask_stats=getattr(engines[0],'local_mask_stats',None)))
                    print(repeat,cls.__name__,rows[-1]['complete'],rows[-1]['seconds'],flush=True)
                assert rows[0]['complete'] and rows[1]['complete']
                assert rows[0]['forecast']==rows[1]['forecast']
                result.append(dict(repeat=repeat,game=g,alive=branch.public.alive,public_hypotheses=len(branch.public_law.hypotheses),physical_hypotheses=len(branch.physical_law.hypotheses),rows=rows,exact_equal=True))
        return dict(cases=result,memory=process_memory_peak(),scope='constructor acceleration only; no new retirement, physical caching or policy changes')
    finally:done.set();thread.join()
if __name__=='__main__':
    r=run();Path('benchmarks/player_match_groups/root7-history-results.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
