"""Fresh-process public six-player transition and warm immutable-key timings."""
import hashlib,json,time,statistics
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.navigation_store import NavigationDocument
from werewolf.public_convergence import state_key
from werewolf.calculation_budget import calculation_budget

with calculation_budget(4000000,max_seconds=65):
 game=data(6,'random',wolves=2).to_game();game['hunters']=1
 game.update(claims=['seer',*['latent']*5],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
 start=time.perf_counter();doc=NavigationDocument(BoardData.from_game(game));root=doc.game.node;source=root.read()
 setup=time.perf_counter()-start
 start=time.perf_counter();doc.game.action(3);cold=time.perf_counter()-start
 graph=root._Node__calculation._ClosedCalculation__engine.evaluation_graph
 refinement=graph.refine(source,root.groups,3)
 warm=[]
 for _ in range(9):
  start=time.perf_counter();again=graph.refine(source,root.groups,3);warm.append(time.perf_counter()-start);assert again is refinement
 law=refinement.edges[0].source.private
 start=time.perf_counter()
 for _ in range(10000):hash(law)
 hashing=time.perf_counter()-start
 fingerprint=hashlib.sha256(repr(tuple((edge.probability,state_key(edge.source)) for edge in refinement.edges)).encode()).hexdigest()
 print(json.dumps(dict(setup_s=round(setup,4),cold_action_s=round(cold,4),warm_refinement_median_ms=round(statistics.median(warm)*1000,4),warm_10000_hashes_ms=round(hashing*1000,3),value=str(refinement.value),mass=str(sum(e.probability for e in refinement.edges)),law_sha=fingerprint,hypotheses=len(law.hypotheses))),flush=True)
