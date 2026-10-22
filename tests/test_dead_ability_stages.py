import unittest
from fractions import Fraction as F
from dataclasses import replace
from werewolf.anonymous_relations import Population,Person,Cell
from werewolf.anonymous_abilities import Context,run
from werewolf.ability_adapters import Medium,Divination,Guard
from werewolf.anonymous_night import symbolic_steps
from tests import test_day_action_quotient as quotient
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree
from werewolf.calculation_budget import calculation_budget

class DeadAbilityStagesTests(unittest.TestCase):
 def test_common_dead_absent_live_and_multiple_holders(self):
  for ability,role in ((Medium(),'medium'),(Divination(),'seer'),(Guard(),'hunter')):
   with self.subTest(role=role):
    pop=Population((Cell(0,'villager',2),),(Person(0,role,False),Person(0,'villager',False)))
    rows=run(pop,(ability,),Context(1,2,execution=1))
    self.assertEqual(len(rows),1);self.assertEqual(rows[0].mass,1)
    self.assertEqual(tuple(s.value for s in rows[0].steps),ability.stages)
    symbols,_=symbolic_steps(rows[0],((1,2,3,4),));self.assertTrue(all(s.label()=='死亡済み' and s.visible_to==() for s in symbols))
    absent=replace(pop,people=(Person(0,'villager',False),Person(0,'villager',False)))
    self.assertEqual(run(absent,(ability,),Context(1,2,execution=1))[0].steps,())
    live=replace(pop,people=(*pop.people,Person(0,role)))
    self.assertTrue(all(not any(s.kind=='ability_dead' for s in row.steps) for row in run(live,(ability,),Context(1,2,execution=1))))
    if role=='medium':self.assertEqual(run(live,(ability,),Context(1,2))[0].steps,())
 def test_real_tree_dead_holder_columns_and_mass(self):
  for role,counts,stages,columns in [('medium',(1,0,0),('medium_result',),(0,)),('seer',(0,0,1),('seer_target','seer_result'),(0,1)),('hunter',(0,1,0),('guard_target',),(0,))]:
   with self.subTest(role=role),calculation_budget(400000,max_seconds=35):
    m,h,s=counts;doc=NavigationDocument(quotient.DayActionQuotientTests().data(5,m,h,s,1));doc.game.action(1);view=NavigationTree(doc);shown=view.read(view.current_key(),True)
    dead=next(b for b in shown['night_stages']['branches'] if b['kind']=='ability_dead')
    self.assertEqual(F(dead['probability']),F(1,4))
    for stage,column in zip(stages,columns):
     self.assertEqual((dead['value'],dead['stage_column'],dead['label']),(stage,column,'死亡済み'))
     self.assertFalse(dead['public_observation']);self.assertEqual(dead['visible_to'],[])
     if stage!=stages[-1]:dead=dead['children']['branches'][0];self.assertEqual(dead['probability'],'1')
