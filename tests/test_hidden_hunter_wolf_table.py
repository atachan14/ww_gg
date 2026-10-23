"""Claimless random-hunter pack Table consumes existing evaluated records."""
import json,unittest
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.navigation_store import NavigationDocument
from werewolf.wolf_view_document import WolfViewDocument
from werewolf.public_convergence import state_key
from werewolf.calculation_budget import calculation_budget

class HiddenHunterWolfTableTests(unittest.TestCase):
 def document(self,repeat=True):
  from tests.test_hunter_evaluated_flow_record import HunterEvaluatedFlowRecordTests
  c,_=HunterEvaluatedFlowRecordTests().case(repeat=repeat,co=False)
  public=NavigationDocument(c.data);public.game.action(3)
  return public
 def test_existing_named_values_QP_and_guard_joint_law_without_replay(self):
  from werewolf.root_secret_flow import RootSecretBranch,root_wolf_forecast
  from werewolf.calculation_tree import CalculationTree
  with calculation_budget(4000000,max_seconds=60):
   public=self.document();before=public.export();base=public.game.node.read()
   self.assertTrue(WolfViewDocument.supports(public,[4]))
   self.assertEqual(set(base.public.claims),{'latent'})
   view=WolfViewDocument(public,public.game.current,[4],[]);result=view.result()
   e=view.root._Node__calculation._ClosedCalculation__engine;s=view.root.read();g=e.evaluation_graph
   self.assertIs(s.public_state,base.public_state)
   self.assertTrue(all(h.roles[0]==1<<3 for h in s.private.hypotheses))
   self.assertLess(s.public.role_probability(4,'wolf'),1)
   expected=root_wolf_forecast(RootSecretBranch(base.public,base.public_state,base.physical,base.private,base.past),(4,),(),e.rules,e.strategy)
   self.assertIsInstance(expected,tuple)
   self.assertEqual({p['id']:F(p['final']['village']) for p in result['players'] if p.get('final')},{view.names.display(p):value for p,value in expected[0]})
   value=view.root.forecast().village_win
   # Complete remaining small game: after a prevented bite, next day wins
   # on wolf execution1/4 or a citizen execution2/4 followed by another
   # prevented bite1/4 and the final execution1/3.
   last_day=F(1,3);protected_day=F(1,4)+F(2,4)*F(1,4)*last_day
   independent=F(1,6)*protected_day+F(5,6)*last_day
   self.assertEqual(independent,F(47,144));self.assertEqual(value,independent)
   record=g.personal_program(s,view.root.groups);self.assertIsNotNone(record)
   with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('consumer reran transition')),patch.object(e,'solve',side_effect=AssertionError('consumer solved')),patch.object(e,'wolf_policy',side_effect=AssertionError('consumer reselected')):
    projection=g.personal_projection(s,view.root.groups)
    shown=CalculationTree.from_node(view.root).read('0',True)
   from tests.test_personal_recorded_projection import PersonalRecordedProjectionTests
   for publish,rows in ((True,projection.edges),(False,projection.arrivals)):
    expected_law=PersonalRecordedProjectionTests().oracle(e,s,view.root.groups,publish)
    self.assertTrue({state_key(r.source):r.probability for r in rows}==expected_law,'full named observer Q/P law differs')
   self.assertEqual(sum(r.probability for r in projection.edges),1)
   # Hunter alive3/4; bite avoids that hunter2/3; guard hits victim1/3.
   self.assertEqual(sum(r.probability for r in projection.edges if len(r.source.public.alive)==4),F(3,4)*F(2,3)*F(1,3))
   self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
   self.assertEqual(public.export(),before)
   self.assertTrue(any(h.guards for edge in projection.edges for h in edge.source.private.hypotheses))
   self.assertTrue(all(h.attacks for edge in projection.edges for h in edge.source.private.hypotheses))

 def test_deathless_Current_mapping_restore_and_public_manual_sibling(self):
  from werewolf.seer_acquisition import SeerReport
  with calculation_budget(4000000,max_seconds=60):
   public=self.document(repeat=False);rootvalue=public.game.history.state('h0').node.forecast().village_win
   view=WolfViewDocument(public,public.game.current,[4],[]);view.result();tree=view.tree();shown=tree.read(tree.current_key(),True)
   choice=next(k for k,row in shown['items'].items() if row.get('public_current') and row['column_day']==2 and row['column_phase']=='day' and len(row['alive'])==4)
   tree.select(choice);current=view.game.node.read()
   self.assertEqual(current.public.day,2);self.assertEqual(len(current.public.alive),4)
   self.assertTrue(all(h.roles[0]==1<<3 and h.attacks for h in current.private.hypotheses))
   restored=WolfViewDocument.restore(NavigationDocument.restore(json.loads(json.dumps(public.export()))),json.loads(json.dumps(view.export())))
   self.assertTrue(state_key(restored.game.node.read())==state_key(current),'private cold law/mapping changed')
   self.assertEqual(restored.game.occurrence.names,view.game.occurrence.names)
   view.game.back();view.game.forward();self.assertTrue(state_key(view.game.node.read())==state_key(current))
   # A separate public input remains a zero-weight alternative, never a new
   # conditioning fact in the already-open private history.
   public.game.move('h0')
   public.game.public_input(('seer','latent','latent','latent','latent'),(SeerReport(1,1,1,2,'white'),))
   self.assertEqual(public.game.occurrence.selection_weight,0)
   self.assertEqual(public.game.history.state('h0').node.forecast().village_win,rootvalue)
   self.assertTrue(state_key(view.game.node.read())==state_key(current))

 def test_full_pack_includes_dead_member_in_claimless_guard_records(self):
  from dev_previews.benchmark_player_counts import data
  from werewolf.board_flow import BoardData
  with calculation_budget(4000000,max_seconds=60):
   game=data(5,'random',wolves=2).to_game();game['hunters']=1
   public=NavigationDocument(BoardData.from_game(game));public.game.action(3)
   view=WolfViewDocument(public,public.game.current,[3,4],[]);view.result()
   mask=sum(1<<(view.names.canonical(p)-1) for p in (3,4))
   self.assertEqual(view.root.read().observer.initial_roster,mask)
   self.assertEqual({view.names.display(p) for p in range(1,6) if mask&(1<<(p-1))},{3,4})
   self.assertFalse({3,4}&set(view.targets()))
   self.assertTrue(all(h.roles[0]==mask for h in view.root.read().private.hypotheses))
   # Executed teammate3 means the hunter is certainly still alive. Guard
   # success2/9 replaces1/6; the remaining complete small-game values agree.
   protected_day=F(1,4)+F(2,4)*F(1,4)*F(1,3)
   self.assertEqual(view.root.forecast().village_win,F(2,9)*protected_day+F(7,9)*F(1,3))
   s=view.root.read();e=view.root._Node__calculation._ClosedCalculation__engine
   projection=e.evaluation_graph.personal_projection(s,view.root.groups)
   self.assertEqual(sum(r.probability for r in projection.edges if len(r.source.public.alive)==4),F(2,9))

 def test_no_hunter_value_only_and_unsupported_policy_boundaries_remain(self):
  from dev_previews.benchmark_player_counts import data
  from werewolf.board_flow import BoardData
  from types import SimpleNamespace
  from dataclasses import replace
  public=NavigationDocument(BoardData.from_game(data(5,'random').to_game()));public.game.action(3)
  self.assertFalse(WolfViewDocument.supports(public,[4]))
  hidden=self.document();e=hidden.game.node._Node__calculation._ClosedCalculation__engine;b=hidden.game.node.read().public
  self.assertFalse(WolfViewDocument.policy_scope(b,SimpleNamespace(strategy=replace(e.strategy,day='max'))))
  self.assertFalse(WolfViewDocument.policy_scope(SimpleNamespace(initial_hunter_count=2),e))

if __name__=='__main__':unittest.main()
