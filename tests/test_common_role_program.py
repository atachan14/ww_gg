import unittest,json
from dataclasses import replace
from fractions import Fraction as F
from collections import defaultdict
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.calculation_budget import calculation_budget
from werewolf.night_program import compile_night
from werewolf.root_secret_flow import RootSecretEngine
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.anonymous_night import ingest
from werewolf.anonymous_materialization import hypothesis
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree

class CommonRoleProgramTests(unittest.TestCase):
 def node(self,n,role,mode='random',repeat=True):
  g=data(n,mode).to_game();g.update(seers=0,seer_mode='',**{role:1});g.pop('seer_options',None);g['rules']['allow_repeat_guard']=repeat
  c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  node=next(o.node for o in c.root.action(n) if not o.node.read().public.winner)
  return c,node
 def invariants(self,program):
  result=defaultdict(F)
  for leaf in program.leaves:
   for h in leaf.source.private.hypotheses:
    b=leaf.source.public;alive=sum(1<<(p-1) for p in b.alive)
    comp=tuple((m&alive).bit_count() for m in h.roles)
    scans=tuple(sorted((a.day,a.color,bool(h.roles[2]&(1<<(a.target-1)))) for a in h.acquisitions))
    guard=h.guards[-1] if h.guards else None;bite=h.attacks[-1] if h.attacks else None
    key=(len(b.alive),leaf.source.physical.winner,comp,scans,bool(guard and bite and guard.night==bite.night and guard.target==bite.target))
    result[key]+=leaf.mass*h.mass
  return dict(result)
 def test_shared_program_matches_named_transition_law_and_values(self):
  for role,n in [('mediums',4),('mediums',5),('hunters',4),('hunters',5),('hunters',6)]:
   with self.subTest(role=role,n=n),calculation_budget(1000000,max_seconds=35):
    c,node=self.node(n,role);e=c._ClosedCalculation__engine;s=node.read()
    with e.group_scope(node.groups):
     common=node._night_program();named=compile_night(e,s,node.groups)
     self.assertEqual(common.method,'anonymous-relational-v1');self.assertTrue(common.stats['ability_adapters'])
     self.assertLess(common.stats['relational_families'],common.stats['named_prior_atoms']);self.assertEqual(common.stats['permutation_checks'],0)
     self.assertEqual(sum(l.mass for l in common.leaves),1);self.assertEqual(sum(l.counter for l in common.leaves),1)
     self.assertEqual(self.invariants(common),self.invariants(named))
     oracle=(RootSecretEngine if role=='hunters' else InformationSetForecast)(e.rules,e.strategy,exact_renaming=False);oracle.retain_joint_guard_history=True
     self.assertEqual(common.root.value(e),oracle.solve(*s,physical=s.physical))
 def test_two_seers_and_medium_keep_joint_private_relations(self):
  with calculation_budget(1000000,max_seconds=35):
   g=data(5,'random').to_game();g.update(seers=2,mediums=1,claims=['seer','seer','medium','latent','latent'],seer_inputs=[dict(day=1,reporter=1,target=4,color='white'),dict(day=1,reporter=2,target=4,color='white')])
   c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
   node=next(o.node for o in c.root.action(4) if not o.node.read().public.winner);e=c._ClosedCalculation__engine;s=node.read()
   with e.group_scope(node.groups):
    common=node._night_program();named=compile_night(e,s,node.groups)
    self.assertEqual(self.invariants(common),self.invariants(named));self.assertEqual(sum(l.mass for l in common.leaves),1)
    for leaf in common.leaves:
     order=[step.kind for step in leaf.steps]
     self.assertEqual(order[0],'medium_result')
     self.assertEqual(order[1:5],['seer_target','seer_result','seer_target','seer_result'])
    self.assertIs(common.root.public,s.public_state)
 def test_guard_history_transport_and_renaming_round_trip(self):
  with calculation_budget(1000000,max_seconds=35):
   c,node=self.node(5,'hunters',repeat=False);e=c._ClosedCalculation__engine
   with e.group_scope(node.groups):program=node._night_program()
   guarded=next(l.source for l in program.leaves if len(l.source.public.alive)==4)
   for h in guarded.private.hypotheses:
    pop,transport=ingest(h,node.groups,guarded.public.alive,guarded.public.history)
    cells={p:cell.role for cell,free in zip(pop.cells,transport.free) for p in free};names=dict(enumerate(transport.people))
    restored=hypothesis(pop,names,cells)
    self.assertEqual(restored.roles,h.roles);self.assertEqual(restored.acquisitions,h.acquisitions);self.assertEqual(restored.guards,h.guards);self.assertEqual(restored.attacks,h.attacks)
 def test_no_repeat_second_night_and_cold_history(self):
  with calculation_budget(1000000,max_seconds=35):
   g=data(5,'random').to_game();g.update(seers=0,hunters=1,seer_mode='');g.pop('seer_options',None);g['rules']['allow_repeat_guard']=False
   doc=NavigationDocument(BoardData.from_game(g));doc.game.action(5);view=NavigationTree(doc);shown=view.read(view.current_key(),True)
   keys={k for k,d in shown['items'].items() if d['day']==2 and len(d['alive'])==4 and d['winner'] is None}
   self.assertTrue(keys);view.select(next(iter(keys)));doc.game.action(4)
   self.assertEqual(doc.game.node.read().public.phase,'night');program=doc.game.node._night_program()
   for leaf in program.leaves:
    for h in leaf.source.private.hypotheses:
     by_actor={}
     for intent in h.guards:by_actor.setdefault(intent.actor,[]).append(intent)
     for records in by_actor.values():
      if len(records)>1:self.assertNotEqual(records[-1].target,records[-2].target)
   cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())));self.assertEqual(cold.game.node.read(),doc.game.node.read())
