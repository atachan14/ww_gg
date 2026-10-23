"""Hidden seer Table reuses established random guard evaluator records."""
import json,unittest
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.seer_view_document import SeerViewDocument
from werewolf.navigation_store import NavigationDocument
from werewolf.public_convergence import state_key
from werewolf.calculation_budget import calculation_budget
from tests import test_hidden_hunter_wolf_table as wolf_fixture

class HiddenHunterSeerTableTests(unittest.TestCase):
 def document(self,repeat=True):return wolf_fixture.HiddenHunterWolfTableTests().document(repeat)
 def view(self,public,target=None):return SeerViewDocument(public,public.game.current,[2],[dict(day=1,target=4,color='white')],target=target)
 def test_named_values_full_laws_and_existing_records_without_recompute(self):
  from werewolf.root_secret_flow import RootSecretBranch,root_seer_forecast
  from werewolf.calculation_tree import CalculationTree
  from tests.test_personal_recorded_projection import PersonalRecordedProjectionTests
  with calculation_budget(4000000,max_seconds=75):
   public=self.document();before=public.export();base=public.game.node.read()
   self.assertTrue(SeerViewDocument.supports(public,[2]))
   view=self.view(public);result=view.result();s=view.root.read();e=view.root._Node__calculation._ClosedCalculation__engine;g=e.evaluation_graph
   self.assertIs(s.public_state,base.public_state)
   self.assertLess(s.public.role_probability(view.names.canonical(2),'seer'),1)
   self.assertTrue(all(h.roles[2]&(1<<(view.names.canonical(2)-1)) for h in s.private.hypotheses))
   self.assertEqual({view.names.display(p) for p in s.public.alive},{1,2,4,5})
   self.assertEqual(set(view.targets()),{1,5})
   branch=RootSecretBranch(base.public,base.public_state,base.physical,base.private,base.past)
   expected=root_seer_forecast(branch,view.names.canonical(2),view.acquisitions,e.rules,e.strategy)
   self.assertIsInstance(expected,tuple)
   actual={p['id']:F(p['final']['village']) for p in result['players'] if p.get('final')}
   self.assertEqual(actual,{view.names.display(p):v for p,v in expected})
   # Known seer2 cannot guard; hunter survived2/3, avoids bite2/3,
   # and guards the chosen victim1/3. Complete future game after success:
   # random wolf execution1/4 or citizen execution2/4, then guard1/4,
   # then final random execution1/3. No seer ever publicly reports here.
   success=F(2,3)*F(2,3)*F(1,3)
   protected_day=F(1,4)+F(2,4)*F(1,4)*F(1,3)
   independent=success*protected_day+(1-success)*F(1,3)
   self.assertEqual(independent,F(53,162))
   self.assertEqual(set(actual.values()),{independent})
   self.assertEqual(set(result['recorded_scans'].values()),{'evaluated'})
   self.assertIsNotNone(g.personal_program(s,view.root.groups))
   with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('seer Tree reran transition')),patch.object(e,'solve',side_effect=AssertionError('seer Tree solved')),patch.object(e,'wolf_policy',side_effect=AssertionError('seer Tree reselected')):
    projection=g.personal_projection(s,view.root.groups)
    shown=CalculationTree.from_node(view.root).read('0',True)
   self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
   self.assertEqual(sum(r.probability for r in projection.edges),1)
   self.assertEqual(sum(r.probability for r in projection.edges if len(r.source.public.alive)==4),success)
   for publish,rows in ((False,projection.arrivals),(True,projection.edges)):
    law=PersonalRecordedProjectionTests().oracle(e,s,view.root.groups,publish)
    self.assertTrue({state_key(r.source):r.probability for r in rows}==law,'hidden seer full Q/P law differs')
   self.assertEqual(public.export(),before)

 def test_intervention_acquisition_Current_and_cold_keep_joint_private_history(self):
  from werewolf.navigation_current import NavigationCurrent
  with calculation_budget(4000000,max_seconds=75):
   public=self.document(repeat=False);before=public.export()
   view=self.view(public,target=1);view.result();s=view.root.read();actor=s.observer.actor;target=view.names.canonical(1)
   self.assertEqual(s.observer.target,target)
   tree=view.tree();shown=tree.read(tree.current_key(),True)
   candidates=[k for k,row in shown['items'].items() if row.get('public_current') and row['column_day']==2 and row['column_phase']=='day' and len(row['alive'])==4]
   self.assertTrue(candidates)
   tree.select(candidates[0]);current=view.game.node.read()
   for h in current.private.hypotheses:
    own=[a for a in h.acquisitions if a.player==actor]
    self.assertTrue(any(a.day==1 and a.target==view.names.canonical(4) and a.color=='white' for a in own))
    self.assertTrue(any(a.day==2 and a.target==target for a in own))
    self.assertTrue(h.guards and h.attacks)
   projection=NavigationCurrent(view.game)
   self.assertEqual(projection.source.public.claims,('latent',)*5)
   cold=SeerViewDocument.restore(NavigationDocument.restore(json.loads(json.dumps(public.export()))),json.loads(json.dumps(view.export())))
   self.assertTrue(state_key(cold.game.node.read())==state_key(current),'hidden seer cold private law changed')
   self.assertEqual(cold.game.occurrence.names,view.game.occurrence.names)
   view.game.back();view.game.forward();self.assertTrue(state_key(view.game.node.read())==state_key(current))
   for victim in (1,2):
    view.game.move(view.game.history.root)
    death=next(k for k,row in shown['items'].items() if row.get('public_current') and row['column_day']==2 and row['column_phase']=='day' and len(row['alive'])==3 and victim not in row['alive'])
    tree.select(death);dead=view.game.node.read();named=view.game.occurrence.names
    for h in dead.private.hypotheses:
     acquired=[a for a in h.acquisitions if a.player==named.canonical(2) and a.day==2]
     self.assertEqual(len(acquired),1)
     self.assertEqual(acquired[0].target,named.canonical(1))
     if victim==1:self.assertEqual(acquired[0].color,'white')
    self.assertEqual(dead.past,())  # no publication, including simultaneous seer death
   self.assertEqual(public.export(),before)

 def test_unresolved_history_dead_actor_and_unsupported_MAX_remain_rejected(self):
  from werewolf.board_flow import BoardData
  from werewolf.information_set_forecast import Pending
  public=self.document()
  with self.assertRaisesRegex(Pending,'seer_view_past_private_history_unresolved'):
   SeerViewDocument(public,public.game.current,[2],[])
  with self.assertRaisesRegex(ValueError,'alive'):
   SeerViewDocument(public,public.game.current,[3],[])
  with self.assertRaisesRegex(ValueError,'Illegal own scan target'):
   self.view(public,target=3)
  game=public.data.to_game();game['policy'].update(day='max',night='max',fake_reports='max')
  with self.assertRaisesRegex(Pending,'closed_guard_stage_policy_unimplemented'):
   NavigationDocument(BoardData.from_game(game))

 def test_alternative_initial_private_results_keep_separate_views_and_same_public_Q(self):
  with calculation_budget(4000000,max_seconds=60):
   public=self.document();first=self.view(public)
   other=SeerViewDocument(public,public.game.current,[2],[dict(day=1,target=5,color='white')])
   self.assertIs(first.root.read().public_state,other.root.read().public_state)
   self.assertNotEqual(first.root.read().private,other.root.read().private)
   self.assertNotEqual(first.tree().snapshot,other.tree().snapshot)
   self.assertEqual(first.root.read().public.claims,('latent',)*5)

if __name__=='__main__':unittest.main()
