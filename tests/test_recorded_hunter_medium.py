import unittest
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.root_secret_flow import RootSecretEngine,prepare_root_secrets,step_root_action
from werewolf.evaluation_graph import EvaluationGraph
from werewolf.evaluation_branch import ContinuationInputs
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy
from werewolf.calculation_tree import CalculationTree
from werewolf.public_convergence import public_night_observations,state_key
from werewolf.calculation_budget import calculation_budget

class RecordedHunterMediumTests(unittest.TestCase):
 def case(self):
  g=data(5,'random').to_game();g.update(seers=0,seer_mode='',hunters=1,mediums=1,claims=['medium','latent','latent','latent','latent']);g.pop('seer_options',None)
  c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  n=next(o.node for o in c.root.action(3) if not o.node.read().public.winner)
  return c,n
 def test_actual_medium_results_and_reductions_preserve_joint_law(self):
  with calculation_budget(4000000,max_seconds=60):
   c,node=self.case();e=c._ClosedCalculation__engine;s=node.read();value=node.forecast().village_win
   with patch.object(e,'solve',side_effect=AssertionError('factor evaluated')),patch.object(e,'wolf_policy',side_effect=AssertionError('factor selected policy')),patch('werewolf.anonymous_night.shared_night',side_effect=AssertionError('factor generated ability')):
    record=e.evaluation_graph.evaluated_program(s,node.groups)
   self.assertIsNotNone(record);p=record.program;self.assertGreater(p.stats['medium_results_recorded'],0);self.assertGreater(p.stats['medium_results_reduced'],0)
   self.assertEqual(sum(leaf.mass for leaf in p.leaves),1)
   for leaf in p.leaves:
    names=dict(leaf.correspondence);h=leaf.source.private.hypotheses[0]
    for step in leaf.steps:
     if step.kind=='medium_result':
      actor,target=names[step.actor.index],names[step.target.index]
      self.assertTrue(h.roles[1]&(1<<(actor-1)))
      self.assertTrue(any(r.reporter==actor and r.target==target and r.color==step.public_fact and r.day==s.public.day+1 for r in leaf.source.public.reports))
     elif step.kind=='ability_reduced':
      self.assertEqual(step.value,'medium_result');self.assertEqual(step.public_fact,'unretained-private-result');self.assertEqual(step.label(),'\u7701\u7565')
   self.assertEqual(p.root.value(e),value)
   oracle=RootSecretEngine(e.rules,e.strategy,exact_renaming=False)
   projection=e.evaluation_graph.public_projection(s,node.groups)
   for publish,rows in ((True,projection.edges),(False,projection.arrivals)):
    named=public_night_observations(oracle,s,node.groups,publish=publish)
    self.assertTrue({state_key(r.source):r.probability for r in rows}=={state_key(after):q for q,after,t in named if publish or not after.public.winner},'medium/hunter full Q/P differs')
   tree=CalculationTree.from_node(node)
   with patch('werewolf.anonymous_night.shared_night',side_effect=AssertionError('Tree regenerated abilities')),patch('werewolf.public_convergence.public_night_observations',side_effect=AssertionError('Tree replayed public events')):shown=tree.read('0',True)
   self.assertEqual(shown['evaluation_trace']['ability_program'],'factored-evaluated-flow')
   def walk(stage):
    for branch in stage.get('branches',()):
     if branch['kind'] in ('medium_result','ability_reduced'):self.assertEqual(branch['stage_column'],0)
     yield branch;yield from walk(branch['children'])
   self.assertTrue(any(b['kind']=='ability_reduced' for b in walk(shown['night_stages'])))
 def test_true_black_and_white_read_from_actual_known_world_reports(self):
  for victim,color in ((1,'black'),(7,'white')):
   with self.subTest(victim=victim),calculation_budget(4000000,max_seconds=60):
    rules=Rules();strategy=Strategy('random','random',fake_reports='random',win_cutoff=False)
    board=replace_worlds(initial_board(7,2,1,0,1),((3,4,0,8,F(1)),));board=replace(board,claims=('latent','latent','medium','latent','latent','latent','latent'))
    root=prepare_root_secrets(board,rules);night=next(child for q,child in step_root_action(root,victim,rules,strategy) if not child.public.winner)
    source=ContinuationInputs(night.public,night.public_law,night.past,night.physical_law,None,night.physical)
    e=RootSecretEngine(rules,strategy,exact_renaming=False);e.evaluation_graph=EvaluationGraph(e);value=e.solve(*source,physical=source.physical)
    groups=tuple((p,) for p in range(1,8));record=e.evaluation_graph.evaluated_program(source,groups);self.assertIsNotNone(record)
    results=[step for leaf in record.program.leaves for step in leaf.steps if step.kind=='medium_result']
    self.assertTrue(results);self.assertEqual({step.public_fact for step in results},{color});self.assertEqual(record.value,value)

 def test_globally_unretained_medium_column_is_omitted(self):
  with calculation_budget(4000000,max_seconds=60):
   g=data(5,'random').to_game();g.update(hunters=1,mediums=1,claims=['seer','latent','latent','latent','latent'],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
   c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
   node=next(o.node for o in c.root.action(3) if not o.node.read().public.winner);node.forecast();tree=CalculationTree.from_node(node);tree.read('0');shown=tree.read('0',True)
   self.assertTrue(shown['night_stages']['stats']['medium_stage_omitted']);self.assertEqual(shown['stage_roles']['mediums'],0)
   for item in shown['items'].values():
    if item['day']==1 and item['phase']=='night':self.assertEqual(item['stage_roles']['mediums'],0)
   def walk(stage):
    for b in stage.get('branches',()):yield b;yield from walk(b['children'])
   self.assertFalse(any(b['kind']=='medium_result' or b['kind'] in ('ability_reduced','ability_dead') and b['value']=='medium_result' for b in walk(shown['night_stages'])))
 def test_medium_hunter_Current_report_deathless_and_cold_history(self):
  from werewolf.navigation_store import NavigationDocument
  from werewolf.navigation_tree import NavigationTree
  from werewolf.navigation_current import NavigationCurrent
  import json
  with calculation_budget(4000000,max_seconds=60):
   c,_=self.case();doc=NavigationDocument(c.data);doc.game.action(3);view=NavigationTree(doc);shown=view.read(view.current_key(),True)
   def report_count(key):
    owner,local,tree,names=view.parse(key);return len(tree.nodes[local]['node'].read().public.reports)
   before,arrival=next((k,r) for k,r in shown['items'].items() if r.get('day_start') and len(r['alive'])==4 and any(report_count(u['node'])>report_count(k) for u in r.get('public_updates') or ()))
   update=next(u['node'] for u in arrival['public_updates'] if report_count(u['node'])>report_count(before))
   view.select(before);self.assertEqual(NavigationCurrent(doc.game).data.facts.day,2)
   view.select(update);current=NavigationCurrent(doc.game);self.assertTrue(current.source.public.reports)
   self.assertEqual(current.data.facts.day,2)
   cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
   self.assertTrue(state_key(NavigationCurrent(cold.game).source)==state_key(current.source),'medium/hunter cold P/Q differs')
   ordinary=next(k for k,r in shown['items'].items() if r.get('day_start') and len(r['alive'])==3)
   view.select(ordinary);current=NavigationCurrent(doc.game)
   self.assertEqual(current.data.facts.day,2);self.assertEqual(len(current.source.public.alive),3)
