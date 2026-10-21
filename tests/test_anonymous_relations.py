import unittest
from collections import defaultdict
from fractions import Fraction as F
from itertools import product
from dataclasses import replace
from werewolf.anonymous_relations import Cell,Person,Population,Scan,scans,attacks,person_label

# Independent named oracle. Name injection/enumeration exists only in tests.
def named_events(pop,day=2,include_self_bite=False,policy=None):
 roles=[p.role for p in pop.people];groups=[p.group for p in pop.people];alive=[p.alive for p in pop.people]
 for c in pop.cells:
  roles.extend([c.role]*c.count);groups.extend([c.group]*c.count);alive.extend([c.alive]*c.count)
 actors=[i for i,r in enumerate(roles) if r=='seer' and alive[i]]
 options=[tuple(i for i in range(len(roles)) if alive[i] and i!=a and i not in {s.target for s in pop.scans if s.actor==a}) for a in actors]
 legal=tuple(i for i in range(len(roles)) if alive[i] and (include_self_bite or roles[i]!='wolf'))
 out=defaultdict(F)
 for targets in product(*options):
  p=F(1)
  for choices in options:p/=len(choices)
  for victim in legal:
   names={i:i for i in range(len(pop.people))};fresh=[]
   def bind(name):
    if name not in names:names[name]=len(names);fresh.append((groups[name],roles[name]))
    return names[name]
   steps=[]
   for actor,target in zip(actors,targets):steps.extend((('seer_target',actor,bind(target)),('seer_result',actor,'black' if roles[target]=='wolf' else 'white')))
   steps.append(('wolf_target',None,bind(victim)))
   out[(tuple(steps),tuple(fresh))]+=p*(policy(victim,groups) if policy else F(1,len(legal)))
 return dict(out)

def anonymous_events(pop,policy=None,include_self_bite=False):
 out=defaultdict(F)
 for scan in scans(pop,2):
  for path in attacks(scan,1,policy=policy,include_self_bite=include_self_bite):
   key=(tuple((s.kind,s.actor,s.value) for s in path.steps),tuple((p.group,p.role) for p in path.population.people[len(pop.people):]))
   out[key]+=path.mass
 return dict(out)

class AnonymousRelationsTests(unittest.TestCase):
 def population(self,seers=1,wolves=1,citizens=3):
  return Population((Cell(0,'seer',seers),Cell(0,'wolf',wolves),Cell(0,'villager',citizens))).bind_seers()
 def test_exhaustive_named_agreement_multiple_seers_wolves(self):
  for seers,wolves,citizens in product((1,2),(1,2),(1,2,3)):
   with self.subTest(seers=seers,wolves=wolves,citizens=citizens):
    pop=self.population(seers,wolves,citizens)
    actual=anonymous_events(pop);self.assertEqual(actual,named_events(pop));self.assertEqual(sum(actual.values()),1)
 def test_no_named_assignment_growth_for_one_large_exchangeable_class(self):
  pop=Population((Cell(0,'villager',1000),), (Person(0,'seer'),))
  rows=scans(pop,2);self.assertEqual(len(rows),1);self.assertEqual(rows[0].multiplicity,1000);self.assertEqual(rows[0].mass,1)
  targets=attacks(rows[0],1);self.assertEqual(len(targets),3);self.assertEqual(sorted(p.multiplicity for p in targets),[1000,1000,999000]);self.assertEqual(sum(p.mass for p in targets),1)
 def test_previous_dead_excluded_but_same_night_victim_still_divined(self):
  pop=Population((Cell(0,'villager',2),Cell(1,'villager',1,False),Cell(0,'wolf',1)),(Person(0,'seer'),))
  self.assertEqual(anonymous_events(pop),named_events(pop))
  same=[]
  for scan in scans(pop,2):
   for path in attacks(scan,1):
    target=path.steps[0].value;victim=path.steps[-1].value
    if target==victim:same.append(path);self.assertTrue(any(s.target==victim and s.day==2 for s in path.population.scans))
    self.assertFalse(any(p.group==1 for p in path.population.people))
  self.assertTrue(same)
 def test_simultaneous_seer_death_retains_acquisition(self):
  pop=self.population()
  rows=[p for s in scans(pop,2) for p in attacks(s,1) if p.steps[-1].value==0]
  self.assertTrue(rows)
  for row in rows:self.assertFalse(row.population.people[0].alive);self.assertTrue(any(s.actor==0 and s.day==2 for s in row.population.scans))
 def test_distinguished_history_and_group_relations_are_not_counts_only(self):
  pop=Population((Cell(0,'wolf',1),Cell(0,'villager',2),Cell(1,'villager',1)),(Person(0,'seer'),Person(0,'villager')), (Scan(1,0,1,'white'),))
  self.assertEqual(anonymous_events(pop),named_events(pop));self.assertNotIn(1,{s.steps[0].value for s in scans(pop,2)})
  changed=replace(pop,scans=(Scan(1,0,0,'white'),))
  self.assertNotEqual(anonymous_events(pop),anonymous_events(changed))
 def test_white_black_and_equality_are_correlated_not_cross_product(self):
  pop=self.population();white=black=F()
  for scan in scans(pop,2):
   color=scan.steps[1].value
   for path in attacks(scan,1):
    if color=='black':black+=path.mass;self.assertNotEqual(path.steps[0].value,path.steps[-1].value)
    else:white+=path.mass
  self.assertEqual((white,black),(F(3,4),F(1,4)))
 def test_committed_nonuniform_policy_and_zero_policy_mass(self):
  pop=Population((Cell(0,'wolf',1),Cell(0,'villager',2),Cell(1,'villager',1)),(Person(0,'seer'),))
  policy=lambda choice:F(1,3) if choice.population.people[choice.target].group==0 else F(0)
  named=lambda target,groups:F(1,3) if groups[target]==0 else F(0)
  self.assertEqual(anonymous_events(pop,policy),named_events(pop,policy=named));self.assertEqual(sum(anonymous_events(pop,policy).values()),1)
 def test_collective_wolves_and_exact_alias_syntax(self):
  pop=self.population(2,2,2)
  self.assertEqual(person_label(pop,0,((2,3,4,5,6,7),)),'[2,3,4,5,6,7のa]')
  for scan in scans(pop,2):
   for path in attacks(scan,1):
    bound,unbound=path.steps[-1].wolves
    self.assertEqual(len(bound)+sum(n for index,n in unbound),2)
 def test_self_bite_option_oracle(self):
  pop=self.population();self.assertEqual(anonymous_events(pop,include_self_bite=True),named_events(pop,include_self_bite=True))
