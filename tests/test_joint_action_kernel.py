import unittest
from dataclasses import replace
from fractions import Fraction as F
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.actor_information import wolf_information_groups,PersonalInformation
from werewolf.evaluation_branch import ContinuationInputs,ActionInputs,physical_board
from werewolf.action_flow import resolve_action
from werewolf.exact import replace_worlds,legal_targets
from werewolf.seer_acquisition import normalize
from werewolf.joint_action_kernel import supported,compile_actions,group_outcomes,report_signature,compose,resolve_outcomes
from benchmarks.player_match_groups.cut_out_joint_night_forecast_fixture import moved_source


def fixture(mode='max',players=5):
 app=create_app({'TESTING':True,'SECRET_KEY':'joint-actions','GAME_TREE_PREVIEW':True})
 client=app.test_client();client.post('/start',data={'players':str(players),'seers':'1','day':mode,'night':mode,'fake_reports':mode})
 with client.session_transaction() as ss:
  game=ss['game'];game['claims'][0]='seer';game['seer_inputs']=[dict(day=1,reporter=1,target=2,color='white')];ss['game']=game;data=BoardData.from_game(game)
 calculation=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
 node=next(o.node for o in calculation.root.action(3) if o.node.read().public.winner is None)
 return calculation,node,client


def ordinary(engine,source,info,law,target):
 own=ContinuationInputs(source.public,source.public_state,source.past,law,source.observer,physical_board(source.public,law,source.physical))
 payload=ActionInputs(own.public_state,own.past,own.private,own.observer,own.physical)
 acquired,deaths=resolve_action(own.public,payload,target,engine.action_policy,terminal_payoffs=False)
 rows=[]
 for index,death in enumerate(deaths):
  child=engine.action_policy.project(own.public,acquired,death,target)
  reports=engine.report_children(child) if child.public.winner is None else ()
  for probability,c in (tuple((mass,c) for q,mass,c in reports) if reports else ((F(1),child),)):
   rows.append((death.probability*probability,c))
 return rows


class JointActionKernelTests(unittest.TestCase):
 def compare(self,calculation,node,source=None,groups=None):
  source=source or node.read();groups=node.groups if groups is None else groups
  engine=calculation._ClosedCalculation__engine
  named=InformationSetForecast(engine.rules,engine.strategy,exact_renaming=False,retire_uninformative_scans=False);named.retain_joint_guard_history=True
  with calculation._ClosedCalculation__kernel(),engine.group_scope(groups):
   self.assertTrue(supported(engine,source))
   actions=compile_actions(engine,source,groups)
   self.assertEqual(sum(a.policy_mass for a in actions),1)
   reference={};policies={}
   for info,mass,law in wolf_information_groups(source.private):
    policies[info]=dict(named.wolf_policy(source.public,source.public_state,source.past,info.initial_roster,info.attacks))
    for target in legal_targets(physical_board(source.public,law,source.physical),engine.rules,engine.strategy):
     reference[info,target]=ordinary(named,source,info,law,target)
   visited=set()
   for action in actions:
    packets=group_outcomes(engine,action)
    self.assertEqual(sum(weight*outcome.probability for plan,weight,outcome in packets),1)
    for plan,weight,outcome in packets:
     self.assertEqual(sum(q for q,m,i in outcome.images),1)
     for member in plan.members:
      info=member.information
      owner_mass=sum(h.mass for h in source.private.hypotheses if h.roles[0]==info.initial_roster and h.attacks==info.attacks)
      self.assertEqual(member.policy_mass,owner_mass*policies[info].get(member.target,F()))
      self.assertFalse(info.initial_roster&(1<<(member.target-1)))
      for image_mass,mapping,report_index in outcome.images:
       moved=moved_source(outcome.source,compose(mapping,member.mapping))
       matches=[(p,c) for p,c in reference[info,member.target] if c==moved]
       self.assertEqual(len(matches),1)
       self.assertEqual(matches[0][0],outcome.probability*image_mass)
       visited.add((info,member.target,repr(report_signature(moved))))
   family=lambda target:next((g for g in groups if target in g),(target,))
   family_mass={}
   for info,mass,law in wolf_information_groups(source.private):
    for target,probability in policies[info].items():family_mass[family(target)]=family_mass.get(family(target),F())+mass*probability
   expected=sum(len(rows) for (info,target),rows in reference.items() if policies[info].get(target,F()) or not family_mass.get(family(target),F()))
   self.assertEqual(len(visited),expected)
   want=named.solve(*source,physical=source.physical)
   self.assertEqual(engine.solve(*source,physical=source.physical),want)
  return engine,actions

 def test_random_and_max_match_independent_named_full_Q_P_histories_and_mass(self):
  for mode in ('random','max'):
   with self.subTest(mode=mode):
    calculation,node,client=fixture(mode)
    engine,actions=self.compare(calculation,node)
    attack=next(a for a in actions if a.targets==(4,5))
    self.assertEqual(attack.policy_mass,F(1,3) if mode=='random' else 0)
    packets=group_outcomes(engine,attack)
    self.assertEqual([weight*o.probability for p,weight,o in packets],[F(1,2)]*2)
    self.assertEqual({o.source.past[-1].color for p,w,o in packets},{'white','black'})
    for plan,weight,outcome in packets:
     target=outcome.source.past[-1].target;victim=outcome.source.public.history[-1].target
     self.assertEqual(target==victim,outcome.source.past[-1].color=='white')
    self.assertEqual(sum(len(a.plans) for a in actions),3)
    self.assertEqual(sum(len(p.members) for a in actions for p in a.plans),6)

 def test_more_candidates_skip_actor_target_generation_and_equivalent_outcome_evaluation(self):
  calculation,node,client=fixture('random',6)
  engine,actions=self.compare(calculation,node)
  self.assertLess(sum(len(a.plans) for a in actions),sum(len(p.members) for a in actions for p in a.plans))
  packets=[o for a in actions for p,w,o in group_outcomes(engine,a)]
  self.assertTrue(any(len(o.images)>1 for o in packets))
  reference=InformationSetForecast(engine.rules,engine.strategy,exact_renaming=False,retire_uninformative_scans=False);reference.retain_joint_guard_history=True
  from werewolf.night_program import compile_night
  with calculation._ClosedCalculation__kernel(),engine.group_scope(node.groups):program=compile_night(engine,node.read(),node.groups)
  program.values.clear()
  calls=[];original=engine.solve
  def evaluate(*args,physical=None):calls.append(args);return reference.solve(*args,physical=physical)
  engine.solve=evaluate
  try:
   with calculation._ClosedCalculation__kernel(),engine.group_scope(node.groups):engine.joint_night_value(node.read())
  finally:engine.solve=original
  self.assertGreater(len(calls),0)
  self.assertLess(len(calls),len(program.leaves))
  self.assertEqual(len(calls),len(program.values))

 def test_asymmetric_public_and_private_masses_do_not_authorize_swapping(self):
  calculation,node,client=fixture('max');source=node.read()
  public=replace(source.public_state,hypotheses=normalize(tuple(replace(h,mass=h.mass*(7 if h.roles[0]==8 else 3)) for h in source.public_state.hypotheses)))
  private=replace(source.private,hypotheses=normalize(tuple(replace(h,mass=h.mass*(2 if h.roles[0]==8 else 8)) for h in source.private.hypotheses)))
  board=replace_worlds(source.public,public.public_roles)
  asymmetric=ContinuationInputs(board,public,source.past,private,None,physical_board(board,private))
  engine,actions=self.compare(calculation,node,asymmetric,tuple((p,) for p in range(1,6)))
  self.assertTrue(all(len(p.members)==1 for a in actions for p in a.plans))
  self.assertTrue(all(len(o.images)==1 for a in actions for p,w,o in group_outcomes(engine,a)))
  self.assertFalse(supported(engine,replace(asymmetric,observer=PersonalInformation(1,'seer'))))

 def test_tree_uses_same_packets_and_all_named_transports_reconstruct_Current(self):
  from werewolf.calculation_tree import CalculationTree,DeferredNode
  calculation,node,client=fixture('max');data=calculation.data;roles=data.roles()
  tree=CalculationTree(data,roles.board,roles.forecast());tree.expand('0')
  root=next(a for a in tree.nodes['0']['actions'] if a['targets']==[3,4,5])
  key=next(b['node'] for b in root['branches'] if tree.nodes[b['node']]['node'].read().public.winner is None)
  tree.expand(key);actions=tree.nodes[key]['actions']
  self.assertEqual(len(actions),3);self.assertTrue(all(a['grouped'] for a in actions))
  self.assertEqual({a['label'] for a in actions},{'1が[(4),5]から占い｜狼が1を襲撃','1が[(4),5]から占い｜狼が2を襲撃','1が[(4),5]から占い｜狼が[(4),5]から襲撃'})
  candidate=next(a for a in actions if a['targets']==[4,5])
  self.assertEqual(candidate['policy_probability'],'0')
  self.assertEqual([b['probability'] for b in candidate['branches']],['1/2','1/2'])
  self.assertEqual({b['outcome_label'] for b in candidate['branches']},{'黒・別の対象が死亡','白・占い先が死亡'})
  lazy=[v for b in candidate['branches'] for v in b['variants'] if v['transport']!=list(range(1,6))]
  self.assertTrue(all(isinstance(tree.nodes[v['node']]['node'],DeferredNode) for v in lazy))
  self.assertTrue(any(tree.nodes[v['node']]['node'].node is None for v in lazy)) # Only new scan representatives are materialized.
  for branch in candidate['branches']:
   representative=tree.nodes[branch['node']]['node'].read()
   for variant in branch['variants']:
    child=tree.nodes[variant['node']]['node'];actual=child.read()
    self.assertEqual(actual,moved_source(representative,tuple(variant['transport'])))
    self.assertEqual(child.export_request().roles(),actual)
    restored=tree.restore(tree.route(variant['node']))
    self.assertEqual(tree.nodes[restored]['node'].read(),actual)
  root_api=client.get('/game-tree?expand=1').json
  orbit=next(a for a in root_api['actions'] if a['targets']==[3,4,5])
  night=next(b['node'] for b in orbit['branches'] if not root_api['items'][b['node']]['winner'])
  expanded=client.get('/game-tree',query_string={'node':night,'expand':'1'}).json
  family=next(a for a in expanded['actions'] if a['targets']==[4,5])
  other=next(v['node'] for b in family['branches'] for v in b['variants'] if v['transport']!=list(range(1,6)))
  result=client.post('/game-tree/current',data={'snapshot':expanded['snapshot'],'node':other})
  self.assertEqual(result.status_code,409,result.data) # Cold transport above is retained; secret Current UI is removed.
