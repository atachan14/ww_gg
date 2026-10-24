"""Bounded public-only transition profile; no preview server or private view."""
import cProfile,json,pstats,time
from pathlib import Path
from unittest.mock import patch
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.navigation_store import NavigationDocument
from werewolf.calculation_budget import calculation_budget

with calculation_budget(4000000,max_seconds=70):
 game=data(6,'random',wolves=2).to_game();game['hunters']=1
 game.update(claims=['seer',*['latent']*5],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
 start=time.perf_counter();doc=NavigationDocument(BoardData.from_game(game));root=doc.game.node
 print(json.dumps(dict(phase='cold-document',seconds=round(time.perf_counter()-start,4))),flush=True)
 source=root.read();engine=root._Node__calculation._ClosedCalculation__engine;graph=engine.evaluation_graph
 start=time.perf_counter();q=root.selection_probability(3)
 print(json.dumps(dict(phase='selection',seconds=round(time.perf_counter()-start,4),probability=str(q))),flush=True)
 profiler=cProfile.Profile();start=time.perf_counter();profiler.enable()
 try:doc.game.action(3)
 finally:
  profiler.disable();profiler.dump_stats('.artifacts/public-transition-stage3.prof')
 print(json.dumps(dict(phase='cold-public-action3-profiled',seconds=round(time.perf_counter()-start,4),day=doc.game.node.read().public.day,phase_after=doc.game.node.read().public.phase)),flush=True)
 stats=pstats.Stats(profiler)
 rows=[]
 for (file,line,name),(primitive,total,selftime,cumulative,callers) in stats.stats.items():
  if 'werewolf' in Path(file).parts:
   rows.append(dict(file=Path(file).name,line=line,function=name,calls=total,self_seconds=round(selftime,4),inclusive_seconds=round(cumulative,4)))
 print(json.dumps(dict(phase='top-production-inclusive',rows=sorted(rows,key=lambda r:r['inclusive_seconds'],reverse=True)[:18])),flush=True)
 with patch.object(engine,'act',side_effect=AssertionError('warm refinement re-evaluated action')),patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('warm refinement replayed transitions')):
  start=time.perf_counter();refinement=graph.refine(source,root.groups,3);elapsed=time.perf_counter()-start
 print(json.dumps(dict(phase='warm-record-refinement',seconds=round(elapsed,6),value=str(refinement.value),mass=str(sum(edge.probability for edge in refinement.edges)),edges=len(refinement.edges))),flush=True)
