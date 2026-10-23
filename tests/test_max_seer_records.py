import unittest
from fractions import Fraction as F
from unittest.mock import patch
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.actor_information import PersonalInformation
from werewolf.seer_acquisition import Acquisition
from werewolf.evaluation_branch import ActionInputs
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.action_flow import resolve_action
from werewolf.public_convergence import state_key
from werewolf.calculation_budget import calculation_budget

class MaxSeerRecordTests(unittest.TestCase):
 def case(self):
  game=data(5,'max').to_game()
  game.update(claims=['seer','seer','latent','latent','latent'],seer_inputs=[dict(day=1,reporter=1,target=3,color='white'),dict(day=1,reporter=2,target=4,color='white')])
  c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  return c,c.root
 def test_private_day_records_keep_public_MAX_ties_and_zero_choices(self):
  with calculation_budget(4000000,max_seconds=90):
   c,public=self.case();e=c._ClosedCalculation__engine;g=e.evaluation_graph
   public_value=e.solve(*public.read(),physical=public.read().physical)
   nodes=[public.personal(PersonalInformation(actor,'seer',(Acquisition(1,actor,target,'white'),)))[1] for actor,target in ((1,3),(2,4))]
   decision=None
   for node in nodes:
    s=node.read();oracle=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False)
    self.assertIs(s.public_state,public.read().public_state)
    self.assertTrue(s.private!=s.public_state,'fixture must retain distinct private P')
    value=e.solve(*s,physical=s.physical);self.assertEqual(value,oracle.solve(*s,physical=s.physical))
    selected=g.day_decision(s,evaluate=True)
    if decision is None:decision=selected
    else:self.assertEqual(selected,decision)
    self.assertEqual(sum(q for t,q in selected.policy),1)
    self.assertGreater(sum(q>0 for t,q in selected.policy),1)
    self.assertTrue(any(q==0 for t,q in selected.policy))
    for target,q in selected.policy:
     payload=ActionInputs(s.public_state,s.past,s.private,s.observer,s.physical)
     e.act(*s[:3],target,s.private,s.observer,physical=s.physical)
     self.assertIsNotNone(g.recorded_action(s.public,payload,target))
     acquired,outcomes=resolve_action(s.public,payload,target,oracle.action_policy)
     expected={state_key(oracle.action_policy.project(s.public,acquired,o,target)):o.probability for o in outcomes}
     with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('recorded private day replayed')),patch.object(e,'solve',side_effect=AssertionError('recorded private day solved')):
      result=g.refine(s,node.groups,target)
     self.assertTrue({state_key(r.source):r.probability for r in result.edges}==expected,'private P child law differs')
     self.assertEqual(result.selection_probability,q)
     self.assertEqual(result.value,oracle.act(*s[:3],target,s.private,s.observer,physical=s.physical))
     self.assertTrue(all(r.source.observer==s.observer for r in result.edges))
   self.assertEqual(e.solve(*public.read(),physical=public.read().physical),public_value)

 def night(self):
  game=data(6,'max').to_game();game.update(claims=['seer',*['latent']*5],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
  c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  node=next(r.node for r in c.root.action(3) if not r.node.read().public.winner)
  from werewolf.seer_intervention import SeerObserver
  _,node=node.personal(SeerObserver(1,(Acquisition(1,1,2,'white'),),2,4))
  return c,node
 def named_night(self,e,s,groups,counter):
  from werewolf.actor_information import wolf_information_groups
  from werewolf.evaluation_branch import physical_board
  from werewolf.exact import legal_targets
  from werewolf.personal_convergence import public_transport,transport_source,mix,observation_key
  oracle=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True;buckets={}
  for info,mass,own in wolf_information_groups(s.private):
   payload=ActionInputs(s.public_state,s.past,own,s.observer,physical_board(s.public,own,s.physical))
   targets=legal_targets(payload.physical,e.rules,e.strategy)
   policy=tuple((t,F(1,len(targets))) for t in targets) if counter else oracle.wolf_policy(s.public,s.public_state,s.past,info.initial_roster,info.attacks)
   for target,q in policy:
    if not q:continue
    acquired,outcomes=resolve_action(s.public,payload,target,oracle.action_policy,terminal_payoffs=False)
    for outcome in outcomes:
     before=oracle.action_policy.project(s.public,acquired,outcome,target)
     branches=((None,F(1),before),) if before.public.winner else oracle.report_children(before)
     for public,p,after in branches:
      moved=transport_source(after,public_transport(s,after,groups));weight=mass*q*outcome.probability*p
      buckets.setdefault(observation_key(moved),[]).append((weight,moved))
  return {state_key(mix(rows)):sum(w for w,s in rows) for rows in buckets.values()}
 def test_night_selected_and_inspection_measures_are_distinct_actual_records(self):
  with calculation_budget(4000000,max_seconds=90):
   c,node=self.night();s=node.read();e=c._ClosedCalculation__engine;g=e.evaluation_graph
   with e.group_scope(node.groups),node.relation_scope():
    value=e.solve(*s,physical=s.physical)
    program=g.personal_program(s,node.groups,evaluate=True)
   self.assertIsNotNone(program)
   self.assertEqual(program.value,value)
   self.assertEqual(program.program.root.value(e),value)
   self.assertEqual(sum(leaf.mass for leaf in program.program.leaves),1)
   self.assertEqual(sum(leaf.counter for leaf in program.program.leaves),1)
   self.assertTrue(any(leaf.mass==0 and leaf.counter>0 for leaf in program.program.leaves))
   expected={counter:self.named_night(e,s,node.groups,counter) for counter in (False,True)}
   with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('recorded night replayed')),patch.object(e,'solve',side_effect=AssertionError('recorded night solved')),patch.object(e,'wolf_policy',side_effect=AssertionError('recorded night reselected')):
    for counter in (False,True):
     projection=g.personal_projection(s,node.groups,counter=counter)
     self.assertIsNotNone(projection)
     self.assertTrue({state_key(r.source):r.probability for r in projection.edges}==expected[counter],'named MAX selected/inspection law differs')
     self.assertEqual(sum(r.probability for r in projection.edges),1)
   self.assertTrue(expected[False]!=expected[True],'selected and inspection laws unexpectedly coincide')
   from dataclasses import replace
   public_policy={k:v for k,v in e.policies.items() if k[:3]==(s.public,s.public_state,s.past)}
   alternative=replace(s,observer=replace(s.observer,target=5))
   with e.group_scope(node.groups),node.relation_scope():e.solve(*alternative,physical=alternative.physical)
   self.assertTrue(public_policy=={k:v for k,v in e.policies.items() if k[:3]==(s.public,s.public_state,s.past)},'observer intervention changed public wolf policy')

 def test_Table_MAX_current_and_counter_cold_sources_do_not_cross(self):
  import json
  from werewolf.navigation_store import NavigationDocument
  from werewolf.seer_view_document import SeerViewDocument
  from werewolf.calculation_tree import CalculationTree
  with calculation_budget(4000000,max_seconds=90):
   c,node=self.night();public=NavigationDocument(c.data);public.game.action(3);before=public.export()
   view=SeerViewDocument(public,public.game.current,[1],[dict(day=1,target=2,color='white')]);result=view.result()
   e=view.root._Node__calculation._ClosedCalculation__engine;s=view.root.read()
   oracle=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False)
   for player in result['players']:
    if player.get('final'):
     selected=SeerViewDocument(public,public.game.current,[1],[dict(day=1,target=2,color='white')],target=player['id']).root.read()
     self.assertEqual(F(player['final']['village']),oracle.solve(*selected,physical=selected.physical))
   tree=view.tree();shown=tree.read(tree.current_key(),True)
   self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
   raw,_=tree.view('h0')
   checked=0
   for key,row in tuple(raw.nodes.items()):
    if not row.get('public_bundle'):continue
    source=row['node'].read();cold=CalculationTree.from_node(view.root);restored=cold.restore(raw.route(key))
    self.assertTrue(state_key(cold.nodes[restored]['node'].read())==state_key(source),'selected/inspection cold source differs')
    checked+=1
   self.assertGreater(checked,1)
   target=next(k for k,r in shown['items'].items() if r.get('day_start') and not r.get('counterfactual'))
   tree.select(target);current=view.game.node.read()
   saved=json.loads(json.dumps(view.export()));cold=SeerViewDocument.restore(NavigationDocument.restore(json.loads(json.dumps(public.export()))),saved)
   self.assertTrue(state_key(cold.game.node.read())==state_key(current),'MAX personal Current restore differs')
   self.assertEqual(public.export(),before)

 def test_five_player_terminal_report_reduction_gets_only_requested_detail(self):
  from werewolf.navigation_store import NavigationDocument
  from werewolf.seer_view_document import SeerViewDocument
  game=data(5,'max').to_game();game.update(claims=['seer',*['latent']*4],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
  public=NavigationDocument(BoardData.from_game(game));public.game.action(3)
  view=SeerViewDocument(public,public.game.current,[1],[dict(day=1,target=2,color='white')]);result=view.result()
  self.assertEqual({p['id']:F(p['final']['village']) for p in result['players'] if p.get('final')},{4:F(1,2),5:F(1,2)})
  s=view.root.read();e=view.root._Node__calculation._ClosedCalculation__engine;g=e.evaluation_graph
  self.assertIsNone(g.personal_program(s,view.root.groups))
  shown=view.tree().read(view.tree().current_key(),True)
  self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
  self.assertEqual(F(shown['village_win']),F(1,2))
