import unittest
from dataclasses import replace
from collections import defaultdict
from fractions import Fraction as F
from unittest.mock import patch
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.actor_information import PersonalInformation,wolf_information_groups
from werewolf.seer_intervention import SeerObserver
from werewolf.root_secret_flow import RootSecretEngine
from werewolf.evaluation_branch import ActionInputs,physical_board
from werewolf.action_flow import resolve_action
from werewolf.public_convergence import state_key
from werewolf.calculation_budget import calculation_budget
from werewolf.information_set_forecast import Pending

class PersonalEvaluatedRecordTests(unittest.TestCase):
 def personal(self,kind):
  g=data(5,'random').to_game();g['hunters']=1
  if kind=='medium':
   g.update(seers=0,seer_mode='',mediums=1,claims=['medium','medium','latent','latent','latent']);g.pop('seer_options',None)
  else:g.update(claims=['seer','seer','latent','latent','latent'],seer_inputs=[dict(day=1,reporter=1,target=3,color='white'),dict(day=1,reporter=2,target=4,color='white')])
  c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  n=next(o.node for o in c.root.action(5) if not o.node.read().public.winner)
  if kind=='medium':information=PersonalInformation(1,'medium')
  elif kind=='villager':information=PersonalInformation(4,'villager')
  else:
   h=next(h for h in n.read().private.hypotheses if h.roles[2]&1)
   known=tuple(a for a in h.acquisitions if a.player==1)
   information=SeerObserver(1,known,2,2 if kind=='black-intervention' else 4) if kind.endswith('intervention') else PersonalInformation(1,'seer',known)
  mass,own=n.personal(information);return c,n,own,mass
 def named(self,e,s):
  oracle=RootSecretEngine(e.rules,e.strategy,exact_renaming=False)
  law=defaultdict(F);weighted=F()
  for info,mass,own in wolf_information_groups(s.private):
   policy=oracle.wolf_policy(s.public,s.public_state,s.past,info.initial_roster,info.attacks)
   for target,q in policy:
    if not q:continue
    payload=ActionInputs(s.public_state,s.past,own,s.observer,physical_board(s.public,own,s.physical))
    acquired,outcomes=resolve_action(s.public,payload,target,oracle.action_policy,terminal_payoffs=True)
    for outcome in outcomes:
     self.assertIsNone(outcome.board.winner,'fixture requires retained continuing Boards')
     before=oracle.action_policy.project(s.public,acquired,outcome,target)
     for public,p,after in oracle.report_children(before):
      weight=mass*q*outcome.probability*p
      law[state_key(after)]+=weight
      weighted+=weight*oracle.solve(*after,physical=after.physical)
  return oracle,dict(law),weighted
 def test_supported_typed_personal_joint_outputs_match_named(self):
  for kind in ('seer','villager','medium','intervention','black-intervention'):
   with self.subTest(kind=kind),calculation_budget(4000000,max_seconds=75):
    c,public,node,mass=self.personal(kind);e=c._ClosedCalculation__engine;s=node.read()
    self.assertGreater(mass,0);self.assertIs(s.public_state,public.read().public_state)
    self.assertTrue(s.private!=s.public_state,'fixture should carry genuinely private evidence')
    value=e.solve(*s,physical=s.physical);graph=e.evaluation_graph
    oracle,named,want=self.named(e,s);self.assertEqual(value,want)
    with patch.object(e,'solve',side_effect=AssertionError('reader evaluated')),patch.object(e,'wolf_policy',side_effect=AssertionError('reader chose policy')),patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('reader simulated')):
     record=graph.personal_program(s,node.groups)
     self.assertIsNotNone(record);self.assertEqual(record.value,value);self.assertEqual(record.reason,'factored-evaluated-personal-action-flow')
     self.assertIs(graph.personal_program(s,node.groups),record)
     if all(leaf.source in record.program.values for leaf in record.program.leaves):self.assertEqual(record.program.root.value(e),value)
     else:
      with self.assertRaises(Pending) as pending:record.program.root.value(e)
      self.assertEqual(pending.exception.reason,'evaluated_continuation_detail_not_retained')
    actual=defaultdict(F)
    for row in graph.hunter_rows(s)[0]:actual[state_key(row[2])]+=row[0]
    self.assertTrue(dict(actual)==named,'observer-conditioned full Q/P joint law differs')
    self.assertEqual(sum(actual.values()),1)
    for leaf in record.program.leaves:
     self.assertEqual(leaf.source.observer,s.observer)
     self.assertEqual(leaf.source.private.hypotheses[0].mass,1)
     self.assertTrue(all(s.observer(h,leaf.source.private) for h in leaf.source.private.hypotheses),'private fact lost')
     for step in leaf.steps:
      if step.kind=='seer_target' and kind.endswith('intervention') and dict(leaf.correspondence)[step.actor.index]==1:self.assertEqual(dict(leaf.correspondence)[step.target.index],s.observer.target)
    for info,policy in record.policies:
     self.assertEqual(policy,oracle.wolf_policy(s.public,s.public_state,s.past,info.initial_roster,info.attacks))
    self.assertIsNone(graph.evaluated_program(s,node.groups))
    self.assertIsNone(graph.public_projection(s,node.groups))
 def test_missing_detail_and_public_policy_cache_are_not_replaced(self):
  with calculation_budget(4000000,max_seconds=75):
   c,public,node,mass=self.personal('seer');e=c._ClosedCalculation__engine;s=node.read();g=e.evaluation_graph
   self.assertIsNone(g.personal_program(s,node.groups));self.assertFalse(any(k[1].observer==s.observer for k in g.actions))
   public.forecast()
   before={info:e.policies[s.public,s.public_state,s.past,info] for info,m,own in wolf_information_groups(s.private)}
   value=e.solve(*s,physical=s.physical);record=g.personal_program(s,node.groups);self.assertIsNotNone(record)
   for info,policy in before.items():self.assertIs(e.policies[s.public,s.public_state,s.past,info],policy)
   self.assertTrue(all(key[1].public_state.public_roles==tuple(sorted(key[0].worlds)) for key in g.actions),'Q replaced by personal P')
   e.anonymous_beliefs[s]=object()
   self.assertIsNone(g.personal_program(s,node.groups));e.anonymous_beliefs.pop(s)
   self.assertIsNone(g.personal_program(replace(s,observer=object()),node.groups))
 def test_personal_history_roundtrip_and_owner_pins(self):
  for kind in ('seer','villager','medium','intervention','black-intervention'):
   with self.subTest(kind=kind),calculation_budget(4000000,max_seconds=75):
    c,public,node,mass=self.personal(kind);s=node.read()
    self.assertTrue(state_key(node.export_request().roles())==state_key(s),'cold owner source differs')
    actor=s.observer.actor;self.assertIn((actor,),node.groups)
    if kind.endswith('intervention'):self.assertIn((s.observer.target,),node.groups)
    target=actor # Same-night death still preserves already acquired owner information.
    for branch in node.action(target):
     self.assertTrue(state_key(branch.node.export_request().roles())==state_key(branch.node.read()),'cold action/owner source differs')
     self.assertEqual(branch.node.read().observer,s.observer)

 def test_white_black_owner_interventions_share_public_policy_not_private_outputs(self):
  with calculation_budget(4000000,max_seconds=75):
   c,public,white,mass=self.personal('intervention');e=c._ClosedCalculation__engine;s=white.read()
   _,black=public.personal(SeerObserver(1,s.observer.acquisitions,2,2))
   records=[]
   for node,color in ((white,'white'),(black,'black')):
    source=node.read();e.solve(*source,physical=source.physical)
    record=e.evaluation_graph.personal_program(source,node.groups);self.assertIsNotNone(record);records.append(record)
    self.assertTrue(all(any(a.player==1 and a.day==2 and a.target==source.observer.target and a.color==color for a in h.acquisitions) for leaf in record.program.leaves for h in leaf.source.private.hypotheses),'owner result correlation changed')
   self.assertIsNot(records[0],records[1]);self.assertTrue(records[0].program.source.public_state is records[1].program.source.public_state)
   self.assertEqual(records[0].policies,records[1].policies)
