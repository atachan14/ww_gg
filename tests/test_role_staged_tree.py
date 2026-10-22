import unittest,json
from fractions import Fraction as F
from dataclasses import replace
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree
from werewolf.navigation_current import NavigationCurrent
from werewolf.calculation_budget import calculation_budget
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.root_secret_flow import RootSecretEngine
from werewolf.exact import Strategy

class RoleStagedTreeTests(unittest.TestCase):
 def doc(self,kind,policy='random'):
  g=data(5 if kind=='medium' else 4,policy).to_game()
  if kind=='medium':g.update(mediums=1,claims=['seer','medium','latent','latent','latent'],seer_inputs=[dict(day=1,reporter=1,target=3,color='white')])
  else:g.update(seers=0,hunters=1,seer_mode='');g.pop('seer_options',None)
  return NavigationDocument(BoardData.from_game(g))
 def leaves(self,stage,mass=F(1),path=()):
  rows=[(mass*F(r['probability']),r,path) for r in stage.get('leaves',())]
  for b in stage.get('branches',()):rows+=self.leaves(b['children'],mass*F(b['probability']),(*path,b))
  return rows
 def test_hunter_footer_summary_includes_terminal_counterfactual_values(self):
  import tempfile
  from app import create_app
  with tempfile.TemporaryDirectory() as directory:
   app=create_app(dict(TESTING=True,GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
   c=app.test_client();c.post('/start',data=dict(citizens=2,seers=0,hunters=1,wolves=1,day='random',night='random',fake_reports='random',win_cutoff=0))
   r=c.post('/navigation/advance',json=dict(revision=0,target=3));self.assertEqual(r.status_code,200,r.json)
   self.assertEqual(r.json['board']['phase'],'night');self.assertEqual(r.json['village_win'],'7/24')
 def test_medium_result_seer_attack_death_then_public_update(self):
  with calculation_budget(250000,max_seconds=20):
   doc=self.doc('medium');doc.game.action(3);view=NavigationTree(doc);shown=view.read(view.current_key(),True);source=doc.game.node.read();rows=self.leaves(shown['night_stages'])
   self.assertEqual(shown['night_stages']['method'],'anonymous-relational-v1');self.assertEqual(sum(p for p,r,path in rows),1)
   for mass,row,path in rows:
    kinds=[b['kind'] for b in path];self.assertEqual(kinds[:3],['medium_result','seer_target','seer_result']);self.assertEqual(kinds[-3:],['wolf_target','death_notice','publication'])
    self.assertEqual([b['stage_column'] for b in path],[0,1,2,3,4,5]);self.assertTrue(path[0]['private']);self.assertEqual(tuple(path[0]['symbols']['actor']['members']),(2,));self.assertTrue(path[-2]['public_observation'])
   engine=InformationSetForecast(doc.data.game_data.rules,Strategy(**doc.data.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False);engine.retain_joint_guard_history=True
   self.assertEqual(doc.game.node.forecast().village_win,engine.solve(*source,physical=source.physical))
   for mass,row,path in rows:
    bite=next(b['value'] for b in path if b['kind']=='wolf_target')
    if bite==2:
     owner,local,tree,names=view.parse(row['node']);destination=tree.nodes[local]['node'].read();self.assertFalse(any(r.reporter==2 and r.day==2 for r in destination.public.reports))
   updates=[(k,d) for k,d in shown['items'].items() if d.get('day_start') and d.get('public_updates')]
   self.assertTrue(updates)
   start,summary=updates[0];view.select(start);self.assertFalse(doc.game.node.read().public.reports)
   update=summary['public_updates'][0]['node'];view.select(update)
   self.assertTrue(doc.game.node.read().public.reports or doc.game.node.read().past)
   current=NavigationCurrent(doc.game);medium=[e for b in current.public_log for e in b['events'] if e['kind']=='medium']
   if doc.game.node.read().public.reports:self.assertTrue(medium)
   cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())));self.assertEqual(cold.game.node.read(),doc.game.node.read())
 def test_medium_black_white_results_do_not_change_actor_information(self):
  with calculation_budget(250000,max_seconds=20):
   g=data(6,'random',wolves=2).to_game();g.update(mediums=1,claims=['seer','medium']+['latent']*4,seer_inputs=[dict(day=1,reporter=1,target=3,color='white')])
   doc=NavigationDocument(BoardData.from_game(g));doc.game.action(4);program=doc.game.node._night_program()
   branches=program.root.branches();self.assertEqual({b.step.value[1]:b.probability for b in branches},{'black':F(2,3),'white':F(1,3)})
   def check(stage):
    self.assertEqual(stage.public,program.source.public_state)
    for branch in stage.branches():check(branch.state)
   check(program.root)
   e=doc.game.node._Node__calculation._ClosedCalculation__engine
   with e.group_scope(doc.game.node.groups):self.assertEqual(program.root.value(e),doc.game.node.forecast().village_win)
 def test_medium_MAX_uses_existing_named_strategy_values(self):
  with calculation_budget(250000,max_seconds=20):
   doc=self.doc('medium','max');self.assertEqual(doc.game.node.forecast().village_win,1)
   doc.game.action(3);s=doc.game.node.read();e=InformationSetForecast(doc.data.game_data.rules,Strategy(**doc.data.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
   self.assertEqual(doc.game.node.forecast().village_win,e.solve(*s,physical=s.physical))
   self.assertEqual(sum(p for p,r,path in self.leaves(NavigationTree(doc).read(NavigationTree(doc).current_key(),True)['night_stages'])),1)
 def test_existing_true_fake_medium_joint_reports_stay_exact(self):
  with calculation_budget(250000,max_seconds=20):
   g=data(5,'random').to_game();g.update(mediums=1,claims=['seer','medium','medium','latent','latent'],seer_inputs=[dict(day=1,reporter=1,target=4,color='white')])
   doc=NavigationDocument(BoardData.from_game(g));doc.game.action(4);view=NavigationTree(doc);shown=view.read(view.current_key(),True)
   self.assertEqual(sum(p for p,r,path in self.leaves(shown['night_stages'])),1)
   self.assertEqual({p for b in shown['night_stages']['branches'] for p in b['symbols']['actor']['members']},{2,3})
 def test_guard_success_merges_all_hidden_attacks_and_Current_replays(self):
  with calculation_budget(250000,max_seconds=20):
   doc=self.doc('guard');self.assertEqual(doc.game.node.forecast().village_win,F(7,24));doc.game.action(3);view=NavigationTree(doc);shown=view.read(view.current_key(),True);rows=self.leaves(shown['night_stages'])
   self.assertEqual(sum(p for p,r,path in rows),1)
   self.assertTrue(any(path[0]['kind']=='guard_target' for p,r,path in rows));self.assertTrue(any(path[0]['kind']=='wolf_target' for p,r,path in rows))
   ongoing={r['node'] for p,r,path in rows if shown['items'][r['node']]['winner'] is None}
   self.assertEqual(len(ongoing),1);key=ongoing.pop();self.assertEqual(sum(p for p,r,path in rows if r['node']==key),F(1,6))
   for p,r,path in rows:
    if r['node']==key:self.assertEqual(path[-1]['kind'],'death_notice');self.assertIsNone(path[-1]['value'])
   self.assertEqual((shown['items'][key]['column_day'],shown['items'][key]['column_phase']),(2,'day'))
   view.select(key);s=doc.game.node.read();self.assertEqual(s.public.day,2);self.assertFalse(any(e.phase=='night' and e.day==1 for e in s.public.history))
   # No-death reveals neither the target nor the private guard/attack relation.
   self.assertEqual({h.attacks[-1].target for h in NavigationCurrent(doc.game).source.private.hypotheses},{1,2,4})
   self.assertTrue(all(h.guards[-1].target==h.attacks[-1].target for h in s.private.hypotheses))
   self.assertEqual(sum(h.mass for h in s.private.hypotheses),1);self.assertEqual(doc.game.node.forecast().village_win,F(1,3))
   self.assertEqual(NavigationCurrent(doc.game).source.public.history[-1].target,3)
   cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())));self.assertEqual(cold.game.node.read(),s)
 def test_unsupported_guard_policies_and_multiplicity_remain_explicit(self):
  from werewolf.closed_calculation import ClosedCalculation
  g=data(5).to_game();g['hunters']=1
  with self.assertRaises(Pending) as error:ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  self.assertEqual(error.exception.reason,'closed_guard_stage_policy_unimplemented')
  from werewolf.calculation_tree import explain_unavailable
  self.assertTrue(any('MAX' in issue and '狩人' in issue for issue in explain_unavailable(g,error.exception.reason)['issues']))
  g['hunters']=2
  with self.assertRaises(Pending) as error:ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  self.assertEqual(error.exception.reason,'guard_multiple_hunters_unimplemented')
