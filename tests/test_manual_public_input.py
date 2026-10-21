import unittest
from fractions import Fraction as F
from dataclasses import replace
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.manual_public_input import PublicInput,ContradictoryPublicInput,UnsupportedPublicInput
from werewolf.seer_acquisition import SeerReport

class ManualPublicInputTests(unittest.TestCase):
 def root(self):
  a=create_app({'TESTING':True,'SECRET_KEY':'manual-history'});c=a.test_client();c.post('/start',data=dict(citizens='3',seers='1',wolves='1',day='max',night='max',fake_reports='max'))
  with c.session_transaction() as ss:data=BoardData.from_game(ss['game'])
  return ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True).root
 def test_initial_simultaneous_reports_filter_actual_histories_and_cold_reconstruct(self):
  root=self.root();source=root.read();before=root.forecast()
  update=PublicInput(('seer','seer','latent','latent','latent'),(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,4,'white')))
  q,p,child=root.observe_public_input(update)
  self.assertGreater(q,0);self.assertGreater(p,0);self.assertEqual(child.read().public.role_probability(1,'wolf'),F(1,2))
  self.assertEqual(child.export_request().roles(),child.read());self.assertEqual(root.read(),source);self.assertEqual(root.forecast(),before)
  self.assertEqual(sum(h.mass for h in child.read().public_state.hypotheses),1);self.assertEqual(sum(h.mass for h in child.read().private.hypotheses),1)
  self.assertEqual(child.forecast().village_win,1)
 def test_repeated_input_keeps_earlier_evidence_and_distinguishes_unsupported_edit(self):
  root=self.root();first=PublicInput(('seer','latent','latent','latent','latent'),(SeerReport(1,1,1,3,'white'),))
  q,p,node=root.observe_public_input(first);q,p,second=node.observe_public_input(PublicInput(('seer','seer','latent','latent','latent'),(SeerReport(1,1,2,4,'white'),)))
  self.assertEqual(second.read().public.role_probability(1,'seer'),1);self.assertEqual(second.read().public.role_probability(2,'wolf'),1)
  self.assertEqual(second.export_request().roles(),second.read())
  with self.assertRaises(UnsupportedPublicInput):node.observe_public_input(PublicInput(first.claims,(SeerReport(1,1,1,4,'white'),)))
  with self.assertRaises(ContradictoryPublicInput):root.observe_public_input(PublicInput(first.claims,(SeerReport(1,1,1,3,'black'),)))

 def test_Q_and_P_are_conditioned_independently_without_fake_policy_likelihood(self):
  from werewolf.manual_public_input import condition_input
  from werewolf.exact import ClaimPolicy
  from werewolf.seer_acquisition import normalize
  from werewolf.evaluation_branch import physical_board
  root=self.root();source=root.read();p=replace(source.private,hypotheses=normalize(tuple(h for h in source.private.hypotheses if h.roles[2]&1)))
  source=replace(source,private=p,physical=physical_board(source.public,p,source.physical))
  evidence=PublicInput(('seer','seer','latent','latent','latent'),(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,4,'white')))
  child=condition_input(source,evidence,root.data.game_data.rules if hasattr(root,'data') else root._Node__calculation.data.game_data.rules,ClaimPolicy()).source
  self.assertEqual(child.public.role_probability(1,'seer'),F(1,2))
  self.assertEqual(sum(h.mass for h in child.private.hypotheses if h.roles[2]&1),1)

 def test_report_targets_refine_groups_before_future_evaluation(self):
  from werewolf.manual_public_input import PublicInput
  root=self.root()
  _,_,node=root.observe_public_input(PublicInput(('seer','latent','latent','latent','latent'),(SeerReport(1,1,1,3,'white'),)))
  self.assertFalse(any(3 in g and 4 in g for g in node.groups))
  from werewolf.information_set_forecast import InformationSetForecast
  engine=node._Node__calculation._ClosedCalculation__engine;s=node.read()
  oracle=InformationSetForecast(engine.rules,engine.strategy,exact_renaming=False,retire_uninformative_scans=False)
  oracle.retain_joint_guard_history=True
  with node._Node__calculation._ClosedCalculation__kernel(),engine.group_scope(node.groups):
   self.assertEqual(dict(engine.day_scores(s.public,s.public_state,s.past)),dict(oracle.day_scores(s.public,s.public_state,s.past)))
