import unittest
from fractions import Fraction as F
from copy import deepcopy
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.public_relation_orbits import initial_orbits
from werewolf.anonymous_night import Symbol,SymbolStep

class PublicRelationOrbitTests(unittest.TestCase):
 def game(self,mode='max'):
  app=create_app({'TESTING':True,'SECRET_KEY':'relation-test'})
  client=app.test_client();client.post('/start',data={'citizens':'3','wolves':'1','seers':'1','day':mode,'night':mode,'fake_reports':mode})
  with client.session_transaction() as ss:g=deepcopy(ss['game'])
  g['claims']=['seer','seer','latent','latent','latent']
  g['seer_inputs']=[dict(day=1,reporter=1,target=3,color='white'),dict(day=1,reporter=2,target=4,color='white')]
  return g
 def test_coupled_report_forest_not_independent_population(self):
  g=self.game();self.assertEqual(initial_orbits(g),((1,2),(3,4),(5,)))
  c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  self.assertEqual(c.root.groups,((1,),(2,),(3,),(4,),(5,)))
  child=next(b.node for b in c.root.action(1) if not b.node.read().public.winner)
  self.assertFalse(any(3 in group and 4 in group for group in child.groups))
  self.assertNotIn((child.read().public,child.read().public_state,child.read().past),c._ClosedCalculation__engine.public_action_orbits)
 def test_asymmetric_reports_and_sequential_batches_split(self):
  g=self.game();g['seer_inputs'][1]['color']='black';self.assertEqual(initial_orbits(g),tuple((p,) for p in range(1,6)))
  g=self.game();g['public_log']={'batches':[dict(slot=0,mode='single',events=[dict(kind='co',player=1,role='seer')]),dict(slot=0,mode='single',events=[dict(kind='co',player=2,role='seer')])]}
  self.assertEqual(initial_orbits(g),tuple((p,) for p in range(1,6)))
 def test_initial_scores_and_P_Q_match_independent_named_oracle(self):
  for mode in ('random','max'):
   c=ClosedCalculation(BoardData.from_game(self.game(mode)),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
   s=c.root.read();e=c._ClosedCalculation__engine
   before=(s.public_state,s.private,s.past)
   oracle=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True
   with c._ClosedCalculation__kernel(),e.group_scope(c.root.groups):
    expected=dict(oracle.day_scores(s.public,s.public_state,s.past));actual=dict(e.day_scores(s.public,s.public_state,s.past))
    self.assertEqual(actual,expected);self.assertEqual(actual[1],actual[2]);self.assertEqual(actual[3],actual[4])
    for target in (1,3,5):self.assertEqual(sum(row.probability for row in c.root.action(target)),1)
   self.assertEqual(before,(s.public_state,s.private,s.past))
 def test_singleton_display_retains_internal_alias_identity(self):
  a,b=Symbol(0,(2,)),Symbol(1,(3,));self.assertEqual(SymbolStep('wolf_target',None,b,(a,)).label(),'2が3を襲撃')
  self.assertEqual((a.index,b.index),(0,1));self.assertEqual(Symbol(0,(3,4)).label(),'[3,4のa]')

 def test_real_tree_groups_actions_and_preserves_joint_outcomes(self):
  from werewolf.calculation_tree import CalculationTree
  data=BoardData.from_game(self.game());roles=data.roles();tree=CalculationTree(data,roles.board,roles.forecast(),anonymous=True)
  root=tree.read(tree.root,True);self.assertEqual([a['targets'] for a in root['actions']],[[1,2],[3,4],[5]])
  self.assertEqual(sum(F(a['policy_probability']) for a in root['actions']),1)
  for action in root['actions']:
   self.assertEqual(sum(F(b['probability']) for b in action['branches']),1)
   for branch in action['branches']:
    child=tree.nodes[branch['node']]['node'].read()
    cold=CalculationTree(data,roles.board,roles.forecast(),anonymous=True)
    key=cold.restore(tree.route(branch['node']));self.assertEqual(cold.nodes[key]['node'].read(),child)
  action=root['actions'][0]
  night=next(b['node'] for b in action['branches'] if not root['items'][b['node']]['winner'])
  staged=tree.read(night,True)['night_stages']
  def labels(stage):
   return [b['label'] for b in stage.get('branches',[])]+[v for b in stage.get('branches',[]) for v in labels(b['children'])]
  text=labels(staged);self.assertTrue(any('2が3を襲撃'==label for label in text));self.assertFalse(any('[2の' in label or '[3の' in label for label in text))
