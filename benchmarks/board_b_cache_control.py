"""Warm-cache control: both revisions use existing completed-result public facade.

Diagnostic only. Cold origin wiring differs from native B and is not used to
attribute native cold overhead. Product RoleState is not edited on disk.
"""
import sys,time,json
from pathlib import Path
import board_b_benchmark as bench
original_worker=bench.worker

def worker(args):
    sys.path.insert(0,args.tree)
    from contextlib import nullcontext
    scope=nullcontext();started=time.perf_counter()
    if args.version=='new':
        from unittest.mock import patch
        from werewolf.board_flow import RoleState
        from werewolf.model_a_public import evaluate_public_game
        from werewolf.exact import Strategy
        def cached(self,*,max_work=250000,max_seconds=20):
            game=self.owner.to_game()
            return evaluate_public_game(game,self.board,self.rules,Strategy(**game['policy']),max_work=max_work,max_seconds=max_seconds)
        scope=patch.object(RoleState,'forecast',cached)
    setup=time.perf_counter()-started
    with scope:original_worker(args)
    path=Path(args.output);r=json.loads(path.read_text(encoding='utf-8'))
    r['cache_control']='Both revisions use existing evaluate_public_game completed-Forecast LRU; B root marginals still reconstructed. Diagnostic only; native B miss-origin wiring differs.'
    r['cache_control_extra_setup_seconds']=setup
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')

bench.worker=worker;bench.__file__=__file__
if __name__=='__main__':bench.main()
