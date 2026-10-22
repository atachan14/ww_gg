import unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.manual_public_input import PublicInput,condition_input,UnsupportedPublicInput
from werewolf.seer_acquisition import SeerReport,normalize,publication_support
from werewolf.public_convergence import transport_source
from werewolf.exact import ClaimPolicy,condition_claims
from werewolf.navigation_store import NavigationDocument
from tests.test_manual_public_input import ManualPublicInputTests

class ManualRolePriorTests(unittest.TestCase):
 def fixture(self):
  doc=NavigationDocument(ManualPublicInputTests().root().data)
  doc.game.action(1);doc.game.action(2)
  source=transport_source(doc.game.node.read(),doc.game.occurrence.names.forward)
  evidence=PublicInput(('latent','latent','seer','latent','latent'),(SeerReport(1,2,3,4,'white'),SeerReport(2,2,3,5,'black')))
  return doc,source,evidence
 def apply(self,doc,source,evidence):
  return condition_input(source,evidence,doc.data.game_data.rules,ClaimPolicy())
 def marginal(self,law):
  return {r:sum(h.mass for h in law.hypotheses if h.roles==r) for r in {h.roles for h in law.hypotheses}}
 def test_reported_board_and_immutable_zero_edge(self):
  doc,source,evidence=self.fixture();before=doc.game.node.read();parent=doc.game.current;value=doc.game.node.forecast()
  result=self.apply(doc,source,evidence)
  self.assertEqual(result.public_mass,F(1,4));self.assertEqual(result.physical_mass,F(1,4))
  self.assertEqual(result.source.public.role_probability(3,'seer'),F(1,3))
  self.assertEqual(set(self.marginal(result.source.private).values()),{F(1,3)})
  row=doc.game.public_input(evidence.claims,evidence.seer_reports)
  self.assertEqual(row.selection_weight,0);self.assertEqual(doc.game.history.state(parent).source,before)
  self.assertEqual(doc.game.history.state(parent).node.forecast(),value)
  cold=NavigationDocument.restore(doc.export());self.assertEqual(cold.game.node.read(),doc.game.node.read())
 def test_unequal_priors_separate_Q_P_and_history_ratios(self):
  doc,s,e=self.fixture()
  def weighted(law,reverse=False):
   roles=sorted(self.marginal(law));weights={r:F((len(roles)-i if reverse else i+1)) for i,r in enumerate(roles)}
   return replace(law,hypotheses=normalize(tuple(replace(h,mass=h.mass*weights[h.roles]) for h in law.hypotheses)))
  s=replace(s,public_state=weighted(s.public_state),private=weighted(s.private,True))
  child=self.apply(doc,s,e).source
  allowed={r[:-1] for r in condition_claims(s.public,e.claims,ClaimPolicy()).worlds}
  for before,after in [(s.public_state,child.public_state),(s.private,child.private)]:
   kept=[h for h in publication_support(before.hypotheses,e.seer_reports) if h.roles in allowed]
   prior=self.marginal(before);survivors={h.roles for h in kept};z=sum(prior[r] for r in survivors)
   self.assertEqual(self.marginal(after),{r:prior[r]/z for r in survivors})
   for r in survivors:
    a=[h for h in after.hypotheses if h.roles==r];b=[h for h in kept if h.roles==r]
    self.assertEqual(normalize(a),normalize(b))
  self.assertNotEqual(self.marginal(child.public_state),self.marginal(child.private))
 def test_sequential_reports_equal_batch_and_future_oracle(self):
  doc,s,e=self.fixture();batch=self.apply(doc,s,e).source
  first=self.apply(doc,s,PublicInput(e.claims,e.seer_reports[:1])).source
  sequential=self.apply(doc,first,e).source
  self.assertEqual(batch,sequential)
  from werewolf.information_set_forecast import InformationSetForecast
  from werewolf.exact import Strategy
  engine=InformationSetForecast(doc.data.game_data.rules,Strategy(**doc.data.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False)
  engine.retain_joint_guard_history=True
  doc.game.public_input(e.claims,e.seer_reports)
  self.assertEqual(dict(doc.game.node.forecast().action_values),dict(engine.day_scores(batch.public,batch.public_state,batch.past)))
 def test_automatic_report_likelihood_is_unchanged(self):
  doc,s,e=self.fixture();claims=self.apply(doc,s,PublicInput(e.claims)).source
  from werewolf.morning_publications import future_publications
  branches=future_publications(claims.public_state,(),claims.public.alive,e.claims)
  self.assertEqual(sum(b.probability for b in branches),1)
  observed=next(b for b in branches if b.reports==e.seer_reports)
  self.assertEqual(observed.probability,F(25,312))
  self.assertEqual(sum(h.mass for h in observed.state.hypotheses if h.roles[2]&4),F(13,25))
 def test_public_support_without_physical_support_is_unsupported(self):
  doc,s,e=self.fixture()
  p=replace(s.private,hypotheses=normalize(tuple(h for h in s.private.hypotheses if h.roles[0]&8)))
  with self.assertRaises(UnsupportedPublicInput):self.apply(doc,replace(s,private=p),e)

 def test_multiple_seers_and_wolves_preserve_joint_assignment_weights(self):
  from werewolf.exact import initial_board,Rules
  from werewolf.seer_acquisition import from_board
  from werewolf.seer_future_uniform import TrueScanState,acquire_uniform
  from werewolf.evaluation_branch import ContinuationInputs
  b=initial_board(7,2,0,2);rules=Rules()
  state=acquire_uniform(TrueScanState(from_board(b),(),initial_rule='random_white'),b.alive)
  source=ContinuationInputs(b,state,(),state,None,b)
  e=PublicInput(('seer','seer')+('latent',)*5,(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,4,'white')))
  child=condition_input(source,e,rules,ClaimPolicy()).source
  prior=self.marginal(state);after=self.marginal(child.private)
  self.assertGreater(len(after),1);self.assertEqual(sum(after.values()),1)
  z=sum(prior[r] for r in after)
  self.assertEqual(after,{r:prior[r]/z for r in after})
  self.assertTrue(all(r[0].bit_count()==2 and r[2].bit_count()==2 for r in after))
