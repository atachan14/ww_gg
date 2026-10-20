import unittest
from collections import defaultdict
from fractions import Fraction as F
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.calculation_tree import CalculationTree
from werewolf.action_tree_trace import trace_source

class ActionColumnTraceTests(unittest.TestCase):
 def setUp(self):
  app=create_app({'TESTING':True,'SECRET_KEY':'action-trace'})
  c=app.test_client();c.post('/start',data={'players':'5','seers':'1','day':'max','night':'max'})
  with c.session_transaction() as session:data=BoardData.from_game(session['game'])
  roles=data.roles();self.tree=CalculationTree(data,roles.board,roles.forecast());self.tree.expand('0')
 def test_night_joint_mass_matches_independent_roles_initial_white_and_unvisited_enumeration(self):
  expected=defaultdict(F)
  # Independently enumerate wolf, victim, true seer, initial random-white and
  # next own-unvisited target. Night1 scans occur before its victim dies.
  for wolf in (2,3,4,5):
   for victim in (p for p in (2,3,4,5) if p!=wolf):
    for seer in (p for p in range(1,6) if p!=wolf):
     if seer==1:expected[((wolf,),(),victim)]+=F(1,4*3*4);continue
     for white in (p for p in range(1,6) if p not in (wolf,seer)):
      for target in (p for p in range(1,6) if p not in (seer,white)):
       expected[((wolf,),((seer,target),),victim)]+=F(1,4*3*4*3*3)
  before=self.tree.nodes['2']['node'].read();self.tree.expand('2');actual=defaultdict(F);groups=[]
  for choice in self.tree.nodes['2']['actions']:
   for branch in choice['branches']:
    self.assertIsNone(branch['trace_pending']);self.assertEqual(sum(F(t['probability']) for t in branch['joint_actions']),F(branch['probability']))
    for trace in branch['joint_actions']:
     groups.append(trace)
     self.assertEqual(sum(F(m['probability']) for m in trace['members']),F(trace['probability']))
     self.assertIn(trace['label'],[m['label'] for m in trace['members']])
     for m in trace['members']:
      self.assertTrue(all(scan[0] not in m['wolves'] for scan in m['scans']))
      self.assertEqual(len(m['wolves']),1)
      actual[(tuple(m['wolves']),tuple(map(tuple,m['scans'])),m['target'])]+=F(m['probability'])
  self.assertEqual(actual,expected);self.assertEqual(sum(actual.values()),1)
  self.assertEqual(sum(p for (w,scans,t),p in actual.items() if not scans),F(1,4))
  self.assertTrue(any(scans and scans[0][0]==target for (wolves,scans,target) in actual))
  self.assertEqual(self.tree.nodes['2']['node'].read(),before)
  self.assertEqual(before.private.tracked,())
  self.assertEqual(self.tree.value('0'),F(7,15));self.assertEqual(self.tree.value('2'),F(1,3))
 def test_trace_restoration_only_reintroduces_marginalized_records(self):
  self.tree.expand('2')
  for choice in self.tree.nodes['2']['actions']:
   for branch in choice['branches']:
    for member in branch['variants']:
     node=self.tree.nodes[member['node']]['node'];original=node.read();full,pending=trace_source(node)
     self.assertIsNone(pending);self.assertEqual(full.public,original.public)
     self.assertEqual(full.public_state.public_roles,original.public_state.public_roles)
     self.assertEqual(full.private.public_roles,original.private.public_roles)
     self.assertEqual(full.physical,original.physical)
     self.assertTrue(any(a.day==2 for h in full.private.hypotheses for a in h.acquisitions))

if __name__=='__main__':unittest.main()
