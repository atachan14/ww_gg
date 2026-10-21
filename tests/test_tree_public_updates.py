import unittest
from copy import deepcopy
from fractions import Fraction as F
from tests import test_public_relation_orbits as relation_tests
from tests.test_joint_action_kernel import fixture
from werewolf.tree_public_updates import input_timeline
from werewolf.board_flow import BoardData
from werewolf.calculation_tree import CalculationTree
from werewolf.exact import ROLES

class TreePublicUpdateTests(unittest.TestCase):
 def data(self,separate=False):
  g=relation_tests.PublicRelationOrbitTests().game()
  events=[[dict(kind='co',player=p,role='seer'),dict(kind='seer',player=p,day=1,target=t,color='white')] for p,t in ((1,3),(2,4))]
  groups=events if separate else [sum(events,[])]
  g['public_log']=dict(version=1,legacy=False,base_claims=[['latent']*5],base_seer=[],base_medium=[],batches=[dict(id=i+1,slot=0,mode='simultaneous',events=group) for i,group in enumerate(groups)],next_id=len(groups)+1)
  return BoardData.from_game(g)
 def test_recorded_simultaneous_and_separate_input_snapshots_have_no_likelihood(self):
  for separate in (False,True):
   data=self.data(separate);before=data.inputs;timeline=input_timeline(data,ROLES)
   self.assertEqual(len(timeline['updates']),2 if separate else 1)
   self.assertEqual(timeline['before']['public_claims'],['latent']*5)
   self.assertTrue(all(update['probability'] is None for update in timeline['updates']))
   self.assertTrue(all(update['state']['snapshot_only'] and not update['state']['public_current'] for update in timeline['updates']))
   self.assertEqual(timeline['updates'][0]['state']['public_claims'][:2],['seer','latent'] if separate else ['seer','seer'])
   self.assertEqual(data.inputs,before)
 def test_real_API_root_keeps_post_update_Current_and_adds_input_timeline(self):
  data=self.data();roles=data.roles();tree=CalculationTree(data,roles.board,roles.forecast(),anonymous=True)
  root=tree.read(tree.root,True)
  self.assertTrue(root['public_current']);self.assertEqual(root['public_claims'][:2],['seer','seer'])
  self.assertEqual(root['input_timeline']['before']['public_claims'],['latent']*5)
  self.assertEqual([a['targets'] for a in root['actions']],[[1,2],[3,4],[5]])
 def test_generated_arrival_is_pre_report_and_updates_conserve_joint_mass(self):
  c,night,client=fixture('random');data=c.data;roles=data.roles();tree=CalculationTree(data,roles.board,roles.forecast(),anonymous=True)
  root=tree.read(tree.root,True);action=next(a for a in root['actions'] if 3 in a['targets'])
  key=next(b['node'] for b in action['branches'] if not root['items'][b['node']]['winner'])
  staged=tree.read(key,True);bundles=tree.nodes[key]['public_bundles'];arrivals=tree.nodes[key]['day_arrivals']
  self.assertTrue(arrivals)
  for arrival in arrivals.values():
   before=tree.nodes[key]['arrival_sources'][arrival['id']]
   self.assertEqual(sum(h.mass for h in before.public_state.hypotheses),1)
   self.assertEqual(sum(h.mass for h in before.private.hypotheses),1)
   self.assertFalse(any(r.acquired_day==2 for r in before.past))
   state=arrival['state'];self.assertTrue(state['snapshot_only']);self.assertFalse(state['public_current'])
   self.assertTrue(all(r['acquired_day']==1 for r in state['public_seer_reports']))
   self.assertEqual(sum(F(u['probability']) for u in arrival['updates']),1)
   self.assertEqual(sum(F(row['probability']) for row in state['distribution']),1)
   self.assertEqual(F(state['village_win']),sum(F(u['probability'])*tree.value(u['node']) for u in arrival['updates']))
   for update in arrival['updates']:
    after=tree.nodes[update['node']]['node'].read()
    self.assertTrue(all(r.acquired_day==1 for r in tree.nodes[key]['node'].read().past))
    self.assertEqual(state['alive'],list(after.public.alive))
    from werewolf.generated_current import GeneratedCurrent
    self.assertEqual(GeneratedCurrent(tree,update['node']).source,after)
  # A bite killing the known true seer emits no new report from that dead actor.
  killed=[arrival for arrival in arrivals.values() if 1 not in arrival['state']['alive']]
  self.assertTrue(killed)
  self.assertTrue(all(u['label']=='更新なし' for arrival in killed for u in arrival['updates']))
  for entry in bundles.values():
   after=tree.nodes[entry['node']]['node'].read()
   if 1 not in after.public.alive:self.assertFalse(any(r.player==1 and r.acquired_day==2 for r in after.past))
