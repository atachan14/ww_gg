import unittest,json
from fractions import Fraction as F
from dataclasses import replace
from werewolf.anonymous_relations import Population,Person,Cell,Scan
from werewolf.anonymous_abilities import Context,Memory,run,resolve
from werewolf.ability_adapters import Divination,Guard,WolfAttack
from werewolf.calculation_budget import calculation_budget
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree
from werewolf.board_flow import BoardData
from werewolf.root_secret_flow import RootSecretEngine
from werewolf.exact import Strategy
from dev_previews.benchmark_player_counts import data

class OvernightRegressions(unittest.TestCase):
 def test_equal_role_counts_different_relational_memories_change_joint_choices(self):
  people=(Person(0,'hunter'),Person(0,'seer'),Person(0,'villager'),Person(0,'villager'),Person(0,'wolf'))
  base=Population((),people,scans=(Scan(1,1,2,'white'),),memories=(Memory('divination',1,1,(2,),'white',(1,)),))
  def probability(previous):
   pop=replace(base,memories=(*base.memories,Memory('guard',1,0,(previous,),None,(0,))))
   rows=run(pop,(Divination(),Guard()),Context(2,3,allow_repeat_guard=False))
   self.assertEqual(sum(p.mass for p in rows),1)
   return sum((p.mass for p in rows if next(s.value for s in p.steps if s.kind=='seer_target')==next(s.value for s in p.steps if s.kind=='guard_target')),F())
  self.assertEqual(probability(2),F(2,9));self.assertEqual(probability(3),F(1,9))
 def test_zero_policy_keeps_counterfactual_guard_attack_relations(self):
  pop=Population((Cell(0,'wolf',1),Cell(0,'villager',2)),(Person(0,'hunter'),))
  factory=lambda ability,actor,initial:(lambda choice,bindings:F()) if ability.key=='attack' else None
  ctx=Context(1,2);rows=run(pop,(Guard(),WolfAttack()),ctx,factory)
  self.assertTrue(rows);self.assertEqual(sum(r.mass for r in rows),0);self.assertEqual(sum(r.counter for r in rows),1)
  self.assertEqual(sum((r.counter for r in rows if not resolve(r,ctx)[1]),F()),F(2,9))
  self.assertTrue(all(next(s.value for s in r.steps if s.kind=='guard_target')!=0 for r in rows))
 def test_guard_success_manual_CO_alternatives_do_not_mutate_parent_or_history(self):
  with calculation_budget(500000,max_seconds=30):
   g=data(4,'random').to_game();g.update(seers=0,hunters=1,seer_mode='');g.pop('seer_options',None);g['rules']['allow_repeat_guard']=False
   doc=NavigationDocument(BoardData.from_game(g));doc.game.action(4);view=NavigationTree(doc);shown=view.read(view.current_key(),True)
   keys={k for k,d in shown['items'].items() if d['day']==2 and len(d['alive'])==3 and d['winner'] is None};self.assertTrue(keys)
   view.select(next(iter(keys)));parent=doc.game.current;source=doc.game.node.read();value=doc.game.node.forecast().village_win
   children=[]
   for actor in (1,2):
    doc.game.move(parent);claims=tuple('hunter' if p==actor else 'latent' for p in range(1,5));row=doc.game.public_input(claims,())
    self.assertEqual(row.selection_weight,0);children.append(row.key);current=doc.game.node.read()
    self.assertEqual(sum(h.mass for h in current.private.hypotheses),1);self.assertEqual(sum(h.mass for h in current.public_state.hypotheses),1)
    self.assertTrue(all(h.guards[-1].target==h.attacks[-1].target for h in current.private.hypotheses))
    e=RootSecretEngine(doc.data.game_data.rules,Strategy(**doc.data.to_game()['policy']),exact_renaming=False);e.retain_joint_guard_history=True
    self.assertEqual(doc.game.node.forecast().village_win,e.solve(*current,physical=current.physical))
    cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())));self.assertEqual(cold.game.node.read(),current)
   self.assertNotEqual(children[0],children[1]);self.assertEqual(doc.game.history.state(parent).source,source)
   doc.game.move(parent);self.assertEqual(doc.game.node.forecast().village_win,value)
   for child in children:doc.game.move(child);self.assertEqual(doc.game.history.occurrence(child).parent,parent)

 def test_eight_nine_hunter_structural_kernel_with_exact_guard_success_mass(self):
  from tests.test_common_role_program import CommonRoleProgramTests
  for n in (8,9):
   with self.subTest(n=n),calculation_budget(500000,max_seconds=20):
    c,node=CommonRoleProgramTests().node(n,'hunters');e=c._ClosedCalculation__engine
    with e.group_scope(node.groups):program=node._night_program()
    self.assertEqual(program.stats['structural_joint_paths'],6);self.assertEqual(program.stats['permutation_checks'],0)
    self.assertEqual(sum(l.mass for l in program.leaves),1)
    success=sum((l.mass for l in program.leaves if len(l.source.public.alive)==n-1),F())
    self.assertEqual(success,F(n-3,(n-2)*(n-1)))
    self.assertIs(program.root.public,node.read().public_state)
