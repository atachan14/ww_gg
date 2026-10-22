import unittest
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from collections import defaultdict
from werewolf.anonymous_relations import Population,Person,Cell
from werewolf.anonymous_abilities import Context,Memory,run,resolve
from werewolf.ability_adapters import Medium,Divination,Guard,WolfAttack

class CommonAbilitiesTests(unittest.TestCase):
 def population(self,citizens):
  return Population((Cell(0,'wolf',1),Cell(0,'villager',citizens)),(Person(0,'seer'),Person(0,'hunter'),Person(0,'medium'),Person(1,'villager',False)))
 def signature(self,roles,scan,guard,bite):
  dead=() if guard==bite else (bite,)
  return (roles[scan],roles[guard],roles[bite],scan==guard,scan==bite,guard==bite,0 in dead,1 in dead,2 in dead)
 def test_exhaustive_joint_relations_against_independent_named_choices(self):
  for citizens in (1,2,3):
   pop=self.population(citizens);actual=defaultdict(F);expected=defaultdict(F)
   ctx=Context(1,2,execution=3)
   for row in run(pop,(Medium(),Divination(),Guard(),WolfAttack()),ctx):
    final,dead=resolve(row,ctx);steps=row.steps
    scan=next(s.value for s in steps if s.kind=='seer_target');guard=next(s.value for s in steps if s.kind=='guard_target');bite=next(s.value for s in steps if s.kind=='wolf_target')
    roles={i:p.role for i,p in enumerate(row.population.people)}
    actual[self.signature(roles,scan,guard,bite)]+=row.mass
    self.assertEqual(set(dead),set() if guard==bite else {bite})
    self.assertTrue(any(m.kind=='medium' and m.participants==(3,) and m.value=='white' and m.visible_to==(2,) for m in row.population.memories))
    self.assertEqual(len(final.population.effects),0)
   # Explicit named actors 0/1/2, dead3, wolf4, remaining citizens.
   roles={0:'seer',1:'hunter',2:'medium',3:'villager',4:'wolf',**{i:'villager' for i in range(5,5+citizens)}}
   alive=tuple(i for i in roles if i!=3)
   targets=lambda actor:tuple(i for i in alive if i!=actor)
   bites=tuple(i for i in alive if roles[i]!='wolf')
   for scan,guard,bite in product(targets(0),targets(1),bites):expected[self.signature(roles,scan,guard,bite)]+=F(1,len(targets(0))*len(targets(1))*len(bites))
   self.assertEqual(dict(actual),dict(expected));self.assertEqual(sum(actual.values()),1)
 def test_guard_memory_refines_legality_and_joint_identity(self):
  pop=self.population(2);pop=replace(pop,memories=(Memory('guard',1,1,(0,),None,(1,)),))
  rows=run(pop,(Medium(),Divination(),Guard(),WolfAttack()),Context(2,3,execution=3,allow_repeat_guard=False))
  self.assertTrue(rows)
  for row in rows:
   self.assertNotEqual(next(s.value for s in row.steps if s.kind=='guard_target'),0)
   self.assertIn(pop.memories[0],row.population.memories)
  different=replace(pop,memories=(Memory('guard',1,1,(2,),None,(1,)),))
  self.assertNotEqual(pop,different)
  other=run(different,(Guard(),),Context(2,3,allow_repeat_guard=False))
  self.assertTrue(any(r.steps[-1].value==0 for r in other));self.assertFalse(any(r.steps[-1].value==2 for r in other))
 def test_policy_commit_precedes_other_private_results_and_death(self):
  pop=self.population(1);seen=[]
  def factory(ability,actor,initial):
   seen.append((ability.key,initial.memories));return None
  rows=run(pop,(Medium(),Divination(),Guard(),WolfAttack()),Context(1,2,execution=3),factory)
  self.assertTrue(all(memory==() for key,memory in seen))
  killed=[resolve(r,Context(1,2))[0] for r in rows if r.steps[-1].value==0 and next(s.value for s in r.steps if s.kind=='guard_target')!=0]
  self.assertTrue(killed);self.assertTrue(all(not r.population.people[0].alive and any(m.actor==0 and m.kind=='divination' for m in r.population.memories) for r in killed))
 def test_no_repeat_requires_prior_and_no_false_role_memory_equivalence(self):
  pop=self.population(1)
  with self.assertRaisesRegex(ValueError,'Previous guard'):run(pop,(Guard(),),Context(2,3,allow_repeat_guard=False))
  a=replace(pop,memories=(Memory('medium',2,2,(3,),'white',(2,)),))
  b=replace(pop,memories=(Memory('medium',2,2,(0,),'white',(2,)),))
  self.assertNotEqual(a,b)

 def test_ingestion_does_not_invent_result_for_executed_medium(self):
  from werewolf.anonymous_night import ingest
  from werewolf.seer_acquisition import Hypothesis
  from werewolf.exact import PublicEvent
  h=Hypothesis((4,1,0,0),(),F(1))
  pop,transport=ingest(h,((1,),(2,3)),(2,3),(PublicEvent(1,'day',1),))
  self.assertFalse(any(m.kind=='medium' for m in pop.memories))
