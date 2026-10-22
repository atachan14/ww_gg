import unittest
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from werewolf.anonymous_belief import Belief,Law,Atom
from werewolf.anonymous_relations import Population,Person
from werewolf.anonymous_abilities import Memory
from werewolf.anonymous_materialization import expand,expand_laws,assignments,hypothesis
from werewolf.seer_acquisition import normalize
from werewolf.calculation_budget import calculation_budget

# Deliberately independent normalization: actual assignment count, rather than
# production's factorial slot formula or its multi-law weighted join.
def named_oracle(law,groups):
 rows=[]
 for mass,atom in law.rows:
  names=list(assignments(atom,groups))
  rows.extend(hypothesis(atom.population,ids,cells,mass/F(len(names))) for ids,cells in names)
 return normalize(tuple(rows))

class MaterializationJoinTests(unittest.TestCase):
 def case(self,n):
  b=Belief.initial((tuple(range(1,n+1)),),dict(wolf=1,seer=1,villager=n-2)).refine(((1,),tuple(range(2,n+1))))
  p=Law.weighted((mass*(2 if atom.population.people[dict(atom.pins)[1]].role=='wolf' else 1),atom) for mass,atom in b.q.rows)[1]
  return b,p
 def test_unequal_Q_P_masses_and_named_joint_histories_eight_nine(self):
  for n in (4,5,8,9):
   with self.subTest(n=n),calculation_budget(100000,max_seconds=10):
    b,p=self.case(n);q_rows,p_rows=expand_laws((b.q,p),b.groups)
    self.assertEqual(q_rows,named_oracle(b.q,b.groups));self.assertEqual(p_rows,named_oracle(p,b.groups))
    self.assertEqual(sum(h.mass for h in q_rows if h.roles[0]&1),F(1,n))
    self.assertEqual(sum(h.mass for h in p_rows if h.roles[0]&1),F(2,n+1))
    self.assertNotEqual(q_rows,p_rows);self.assertEqual(sum(h.mass for h in q_rows),1);self.assertEqual(sum(h.mass for h in p_rows),1)
 def test_equal_laws_reuse_once_and_separate_calls_remain_identical(self):
  b,p=self.case(8)
  import werewolf.anonymous_materialization as module
  with patch.object(module,'hypothesis',wraps=hypothesis) as generated:
   q,private=expand_laws((b.q,b.q),b.groups);calls=generated.call_count
  self.assertIs(q,private);self.assertEqual(q,expand(b.q,b.groups));self.assertEqual(calls,len(q))
 def test_shared_atom_names_are_generated_once_for_unequal_laws(self):
  b,p=self.case(9)
  import werewolf.anonymous_materialization as module
  with patch.object(module,'hypothesis',wraps=hypothesis) as generated:q,private=expand_laws((b.q,p),b.groups)
  self.assertEqual(generated.call_count,len(q));self.assertEqual(len(q),len(private))
 def test_different_guard_and_attack_memories_are_not_joined(self):
  people=(Person(0,'hunter'),Person(0,'villager'),Person(0,'villager'),Person(0,'wolf'))
  pins=tuple((i+1,i) for i in range(4));groups=((1,2,3,4),)
  def atom(target):return Atom(Population((),people,attacks=((1,target),),memories=(Memory('guard',1,0,(target,),None,(0,)),)),pins)
  a,b=atom(1),atom(2);q=Law(((F(1,3),a),(F(2,3),b)));p=Law(((F(3,4),a),(F(1,4),b)))
  qr,pr=expand_laws((q,p),groups)
  self.assertEqual(qr,named_oracle(q,groups));self.assertEqual(pr,named_oracle(p,groups))
  self.assertEqual({h.guards[-1].target:h.mass for h in qr},{2:F(1,3),3:F(2,3)})
  self.assertEqual({h.guards[-1].target:h.mass for h in pr},{2:F(3,4),3:F(1,4)})
  self.assertTrue(all(h.guards[-1].target==h.attacks[-1].target for h in (*qr,*pr)))

 def test_repeated_atom_entries_add_before_each_law_normalizes(self):
  b,p=self.case(4);a,c=b.q.rows[0][1],b.q.rows[-1][1]
  law=Law(((F(1,2),a),(F(1,4),a),(F(1,4),c)))
  self.assertEqual(expand_laws((law,b.q),b.groups)[0],named_oracle(law,b.groups))
