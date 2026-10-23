"""Cold actual six-person NavigationDocument path, no fixture shortcuts."""
from time import perf_counter
import json
from fractions import Fraction as F
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.navigation_store import NavigationDocument
from werewolf.wolf_view_document import WolfViewDocument
from werewolf.calculation_budget import calculation_budget
start=perf_counter()
def mark(phase):
 global start
 now=perf_counter();print(json.dumps(dict(phase=phase,seconds=round(now-start,3))),flush=True);start=now
with calculation_budget(4000000,max_seconds=90):
 game=data(6,'random',wolves=2).to_game();game['hunters']=1
 game.update(claims=['seer',*['latent']*5],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
 public=NavigationDocument(BoardData.from_game(game));mark('cold-document')
 assert public.game.node.selection_probability(3)==F(1,6);mark('uniform-selection')
 public.game.action(3);mark('actual-cold-navigation-action3')
 for pack,other in (((4,5),6),((4,6),5)):
  view=WolfViewDocument(public,public.game.current,pack,[]);result=view.result();mark('private-result-'+str(pack))
  actual={p['id']:F(p['final']['village']) for p in result['players'] if p.get('final')}
  assert actual=={1:F(7,324),2:F(7,648),other:F(7,648)},actual
  assert view.root.forecast().village_win==F(7,486)
  tree=view.tree();shown=tree.read(tree.current_key(),True);mark('first-tree-'+str(pack))
  assert shown['evaluation_trace']['owner']=='evaluator'
  projection=view.root._Node__calculation._ClosedCalculation__engine.evaluation_graph.personal_projection(view.root.read(),view.root.groups)
  assert sum(r.probability for r in projection.edges)==1
  assert all(len(h.attacks)==1 for r in projection.edges for h in r.source.private.hypotheses)
  tree.read(tree.current_key(),True);mark('repeat-tree-'+str(pack))
 print('PASS full cold six-person navigation, two living wolves, exact independent values and recorded Trees',flush=True)
