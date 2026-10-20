import unittest
from fractions import Fraction as F
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.calculation_tree import CalculationTree
from werewolf.closed_calculation import ClosedCalculation
from werewolf.evaluation_branch import physical_board
from werewolf.seer_future_uniform import candidates

class OneCOGameTreeSemantics(unittest.TestCase):
 def setUp(self):
  app=create_app({'TESTING':True,'SECRET_KEY':'one-co-proof'});c=app.test_client();c.post('/start',data={'players':'5','seers':'1','day':'max','night':'max'})
  with c.session_transaction() as ss:g=ss['game'];g['claims'][0]='seer';g['seer_inputs']=[dict(day=1,reporter=1,target=2,color='white')];self.data=BoardData.from_game(g)
 def test_parent_execution_orbit_and_conditional_named_joint_choices(self):
  roles=self.data.roles();tree=CalculationTree(self.data,roles.board,roles.forecast());tree.expand('0')
  action=next(a for a in tree.nodes['0']['actions'] if a['targets']==[3,4,5]);branch=next(b for b in action['branches'] if tree.nodes[b['node']]['node'].read().public.winner is None)
  actors=set();raw=0;positive=0
  for variant in branch['variants']:
   key=variant['node'];tree.expand(key);source=tree.nodes[key]['node'].read();executed=source.public.history[-1].target
   self.assertNotIn(executed,source.public.alive)
   rows=[(a,t,m) for a in tree.nodes[key]['actions'] for b in a['branches'] for t in b['joint_actions'] for m in t['members']]
   self.assertEqual(len(rows),12)
   for a in tree.nodes[key]['actions']:
    self.assertEqual(sum(F(b['probability']) for b in a['branches']),1)
    for b in a['branches']:
     self.assertEqual(sum(F(t['probability']) for t in b['joint_actions']),F(b['probability']))
     for t in b['joint_actions']:self.assertEqual(sum(F(m['probability']) for m in t['members']),F(t['probability']))
   for a,t,m in rows:
    wolf=m['wolves'][0];actors.add(wolf);raw+=1
    self.assertTrue(all(scan[1] in source.public.alive for scan in m['scans']));self.assertNotEqual(wolf,executed);self.assertNotEqual(wolf,m['target']);self.assertIn(m['target'],source.public.alive)
    if F(a['policy_probability']):positive+=1;self.assertEqual(m['target'],1)
   if executed==3:
    self.assertEqual({m['wolves'][0] for a,t,m in rows},{4,5})
    self.assertEqual({m['scans'][0][1] for a,t,m in rows},{4,5})
    self.assertEqual(sum(len(b['joint_actions']) for a in tree.nodes[key]['actions'] for b in a['branches']),6)
  self.assertEqual((actors,raw,positive),({3,4,5},36,12))
 def test_dead_target_excluded_and_solver_still_compresses_actor_cells(self):
  c=ClosedCalculation(self.data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
  self.assertEqual(c.root.forecast().village_win,F(2,3))
  n=next(o.node for o in c.root.action(3) if o.node.read().public.winner is None);s=n.read();e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(n.groups):
   cells=e.wolf_cells(s.private);self.assertEqual(len(cells),1)
   info,mass,p=cells[0];self.assertEqual((info.initial_roster,mass),(8,F(1)))
   self.assertEqual(candidates(p.hypotheses[0],1,s.public.alive),(4,5))
   q=info.condition_public(s.public_state)
   with e.actor_scope(info):
    scores={t:e.act(s.public,s.public_state,s.past,t,q,None,physical=physical_board(s.public,q)) for t in (1,2,5)}
   self.assertEqual(scores,{1:F(1,2),2:F(1),5:F(1)})
   self.assertEqual(len(e.acquire(s.public,s.public_state).hypotheses),4)
   self.assertEqual(len(e.acquire(s.public,p).hypotheses),2)

 def test_named_max_kernel_matches_representative_with_separate_cache(self):
  grouped=ClosedCalculation(self.data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
  named=ClosedCalculation(self.data,grouped=True,aggregate_reports=True)
  e=named._ClosedCalculation__engine;s=named.root.read()
  with named._ClosedCalculation__kernel(),e.group_scope(()):
   value=e.solve(*s,physical=s.physical)
   actions={p:e.act(*s[:3],p,s.private,s.observer,physical=s.physical) for p in s.public.alive}
  forecast=grouped.root.forecast()
  self.assertEqual(value,forecast.village_win)
  self.assertEqual(actions,dict(forecast.action_values))

if __name__=='__main__':unittest.main()
