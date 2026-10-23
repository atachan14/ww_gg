import json,unittest
from dataclasses import replace
from collections import defaultdict
from fractions import Fraction as F
from types import SimpleNamespace
from unittest.mock import patch
from tests import test_personal_evaluated_records as fixture
from werewolf.root_secret_flow import RootSecretEngine
from werewolf.actor_information import wolf_information_groups,PersonalInformation
from werewolf.seer_intervention import SeerObserver
from werewolf.evaluation_branch import ActionInputs,physical_board
from werewolf.action_flow import resolve_action
from werewolf.public_convergence import state_key,digest,transport_source as public_transport_source
from werewolf.personal_convergence import public_transport,transport_source,mix,observation_key
from werewolf.calculation_tree import CalculationTree
from werewolf.navigation_game import NavigationGame
from werewolf.navigation_tree import NavigationTree
from werewolf.navigation_current import NavigationCurrent
from werewolf.navigation_history import NavigationHistory,NameMap
from werewolf.calculation_budget import calculation_budget

class PersonalRecordedProjectionTests(unittest.TestCase):
 def case(self,kind='intervention'):
  c,public,node,mass=fixture.PersonalEvaluatedRecordTests().personal(kind)
  e=c._ClosedCalculation__engine;s=node.read();value=e.solve(*s,physical=s.physical)
  e.evaluation_graph.personal_program(s,node.groups)
  return c,node,e,value
 def oracle(self,e,s,groups,publish):
  oracle=RootSecretEngine(e.rules,e.strategy,exact_renaming=False);buckets={}
  for info,mass,own in wolf_information_groups(s.private):
   for target,q in oracle.wolf_policy(s.public,s.public_state,s.past,info.initial_roster,info.attacks):
    if not q:continue
    payload=ActionInputs(s.public_state,s.past,own,s.observer,physical_board(s.public,own,s.physical))
    acquired,outcomes=resolve_action(s.public,payload,target,oracle.action_policy,terminal_payoffs=True)
    for outcome in outcomes:
     before=oracle.action_policy.project(s.public,acquired,outcome,target)
     rows=tuple((p,after) for public,p,after in oracle.report_children(before)) if publish else ((F(1),before),)
     for p,after in rows:
      moved=transport_source(after,public_transport(s,after,groups));weight=mass*q*outcome.probability*p
      buckets.setdefault(observation_key(moved),[]).append((weight,moved))
  return {state_key(mix(rows)):sum(w for w,s in rows) for rows in buckets.values()}
 def test_projection_reuses_records_and_matches_full_named_view_laws(self):
  for kind in ('seer','villager','medium','intervention','black-intervention'):
   with self.subTest(kind=kind),calculation_budget(4000000,max_seconds=75):
    c,node,e,value=self.case(kind);s=node.read();g=e.evaluation_graph
    expected={publish:self.oracle(e,s,node.groups,publish) for publish in (False,True)}
    with patch.object(e,'solve',side_effect=AssertionError('projection solved')),patch.object(e,'wolf_policy',side_effect=AssertionError('projection chose policy')),patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('projection simulated')):
     projection=g.personal_projection(s,node.groups);self.assertIsNotNone(projection)
     self.assertIs(projection,g.personal_projection(s,node.groups,counter=True))
    self.assertEqual(projection.value,value);self.assertEqual(projection.reason,'evaluated-personal-mixture')
    for publish,rows in ((True,projection.edges),(False,projection.arrivals)):
     self.assertTrue({state_key(r.source):r.probability for r in rows}==expected[publish],'complete observer Q/P projection differs')
     self.assertEqual(sum(r.probability for r in rows),1)
     self.assertTrue(all(r.source.observer==s.observer for r in rows))
    for r in projection.arrivals:
     self.assertEqual(sum(u.probability for u in r.updates),1)
     self.assertEqual(sum(u.probability*g.values[u.source].value for u in r.updates),r.value)
    self.assertIsNone(g.public_projection(s,node.groups))
 def test_typed_bijection_and_view_identity_isolation(self):
  with calculation_budget(4000000,max_seconds=75):
   c,node,e,value=self.case();s=node.read();projection=e.evaluation_graph.personal_projection(s,node.groups)
   mapping=(2,1,4,3,5)
   for source in (s,*(r.source for r in projection.edges)):
    moved=transport_source(source,mapping)
    self.assertTrue(state_key(transport_source(moved,mapping))==state_key(source),'full observer/map roundtrip differs')
    self.assertEqual(moved.observer.actor,2);self.assertEqual(moved.observer.target,3)
    with self.assertRaises(ValueError):public_transport_source(source,mapping)
   other=replace(s,observer=SeerObserver(1,s.observer.acquisitions,2,2))
   with self.assertRaises(ValueError):mix(((F(1,2),s),(F(1,2),other)))
   self.assertNotEqual(digest(s),digest(other))
   _,black=node.personal(SeerObserver(1,s.observer.acquisitions,2,2))
   self.assertNotEqual(CalculationTree.from_node(node).snapshot,CalculationTree.from_node(black).snapshot)
   a=NavigationGame(node);b=NavigationGame(black)
   self.assertNotEqual(NavigationCurrent(a).identity,NavigationCurrent(b).identity)
 def test_tree_Current_and_cold_recipes_keep_observer_without_replay(self):
  with calculation_budget(4000000,max_seconds=75):
   c,node,e,value=self.case();g=e.evaluation_graph;s=node.read();tree=CalculationTree.from_node(node)
   with patch.object(e,'solve',side_effect=AssertionError('Tree solved')),patch('werewolf.public_convergence.public_night_observations',side_effect=AssertionError('Tree replayed public flow')),patch('werewolf.anonymous_night.shared_night',side_effect=AssertionError('Tree generated hidden flow')):
    shown=tree.read('0',True)
   self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
   self.assertEqual(shown['evaluation_trace']['public_projection'],'evaluated')
   self.assertEqual(shown['evaluation_trace']['ability_program'],'factored-evaluated-flow')
   candidates=[(key,row) for key,row in tree.nodes.items() if row.get('public_bundle')]
   self.assertTrue(candidates)
   for key,row in candidates[:4]:
    source=row['node'].read();self.assertEqual(source.observer,s.observer)
    self.assertTrue(state_key(row['node'].export_request().roles())==state_key(source),'cold personal observation source differs')
    cold=CalculationTree.from_node(node);restored=cold.restore(tree.route(key))
    self.assertTrue(state_key(cold.nodes[restored]['node'].read())==state_key(source),'Tree path restoration differs')
 def test_scoped_navigation_deathless_updates_and_cold_history(self):
  with calculation_budget(4000000,max_seconds=75):
   c,node,e,value=self.case();game=NavigationGame(node);document=SimpleNamespace(game=game,data=c.data,revision=0);view=NavigationTree(document)
   shown=view.read(view.current_key(),True)
   before,arrival=next((k,r) for k,r in shown['items'].items() if r.get('day_start') and len(r['alive'])==4 and r.get('public_updates'))
   update=arrival['public_updates'][0]['node']
   view.select(before);a=NavigationCurrent(game);self.assertEqual(a.source.observer,node.read().observer)
   view.select(update);b=NavigationCurrent(game);self.assertEqual(b.source.public.day,2);self.assertEqual(len(b.source.public.alive),4)
   self.assertEqual(b.source.observer,node.read().observer)
   here=game.current;game.back();game.forward();self.assertEqual(game.current,here)
   restored=NavigationGame.restore(node,json.loads(json.dumps(game.export())))
   self.assertTrue(state_key(NavigationCurrent(restored).source)==state_key(b.source),'cold scoped Current differs')
   ordinary=next(k for k,r in shown['items'].items() if r.get('day_start') and len(r['alive'])==3)
   view.select(ordinary);self.assertEqual(len(NavigationCurrent(game).source.public.alive),3)

 def test_nonrepresentative_choice_keeps_owner_and_full_named_history(self):
  from dev_previews.benchmark_player_counts import data
  from werewolf.board_flow import BoardData
  from werewolf.closed_calculation import ClosedCalculation
  with calculation_budget(4000000,max_seconds=75):
   g=data(5,'random').to_game();g['hunters']=1
   c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
   _,root=c.root.personal(PersonalInformation(1,'villager'))
   game=NavigationGame(root);row=game.action(5)
   self.assertEqual(row.selector['requested'],5);self.assertNotEqual(row.selector['target'],5)
   current=NavigationCurrent(game);self.assertNotIn(5,current.source.public.alive)
   self.assertEqual(current.source.observer,root.read().observer)
   literal=next(r.node.read() for r in root.action(5) if not r.node.read().public.winner)
   self.assertTrue(state_key(current.source)==state_key(literal),'representative display map differs from named choice')
   cold=NavigationGame.restore(root,json.loads(json.dumps(game.export())))
   self.assertTrue(state_key(NavigationCurrent(cold).source)==state_key(literal),'cold nonrepresentative choice changed owner/history')
