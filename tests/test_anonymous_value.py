import unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.anonymous_belief import Belief
from werewolf.anonymous_value import Evaluator
from werewolf.anonymous_materialization import expand
from werewolf.information_set_forecast import InformationSetForecast
from tests import test_anonymous_night as native

class AnonymousValueTests(unittest.TestCase):
 def test_full_game_random_and_MAX_match_existing_exact_named_solver(self):
  for seers,wolves,citizens in ((0,1,4),(1,1,3),(2,1,2),(1,2,3),(1,1,5)):
   for mode in ('random','max'):
    from app import create_app
    from werewolf.board_flow import BoardData
    from werewolf.board_future import SavedOrigin
    from werewolf.exact import Strategy
    from werewolf.calculation_budget import calculation_budget
    app=create_app({'TESTING':True,'SECRET_KEY':'anonymous-value-oracle'});client=app.test_client()
    client.post('/start',data=dict(citizens=str(citizens),wolves=str(wolves),seers=str(seers),mediums='0',hunters='0',day=mode,night=mode,fake_reports=mode))
    with client.session_transaction() as session:data=BoardData.from_game(session['game'])
    strategy=Strategy(**data.to_game()['policy'])
    b=Belief.initial((tuple(range(1,seers+wolves+citizens+1)),),dict(seer=seers,wolf=wolves,villager=citizens))
    solver=Evaluator(mode,mode)
    oracle=InformationSetForecast(data.game_data.rules,strategy,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True
    source=SavedOrigin(data,oracle.rules,strategy,project_public=False)()
    with calculation_budget(4000000):
     self.assertEqual(solver.value(b),oracle.solve(*source,physical=source.physical),(seers,wolves,citizens,mode))
 def test_scalar_projection_does_not_mutate_relational_tree_belief(self):
  b=Belief.initial(((1,2,3,4,5),),dict(wolf=1,seer=1,villager=3));snapshot=expand(b.p,b.groups)
  solver=Evaluator('max','max');solver.value(b)
  self.assertEqual(expand(b.p,b.groups),snapshot)
  self.assertTrue(any(a.population.scans for m,a in b.p.rows))

 def test_asymmetric_Q_and_private_P_do_not_change_public_or_actor_information(self):
  from werewolf.anonymous_belief import Law
  from werewolf.anonymous_value import information
  from werewolf.anonymous_materialization import source as materialize
  from werewolf.exact import Strategy
  from tests.test_anonymous_belief import AnonymousBeliefTests
  c,node,base=AnonymousBeliefTests().case()
  b=base.refine(((1,),(2,),(3,4,5)))
  q=Law.weighted((mass*(5 if information(atom,b.groups)[0] else 1),atom) for mass,atom in b.q.rows)[1]
  p=Law.weighted((mass*(4 if information(atom,b.groups)[1] else 1),atom) for mass,atom in b.p.rows)[1]
  b=replace(b,q=q,p=p);source=materialize(b,c.root.read());strategy=Strategy(day='max',night='max',fake_reports='max')
  oracle=InformationSetForecast(c.data.game_data.rules,strategy,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True
  solver=Evaluator('max','max')
  with c._ClosedCalculation__kernel():
   self.assertEqual(solver.value(b),oracle.solve(*source,physical=source.physical))
   expected=dict(oracle.day_scores(source.public,source.public_state,source.past))
   self.assertEqual({p:v for group,v in solver.day_scores(solver.scalar(b)) for p in group},expected)
  self.assertEqual(solver.day_scores(solver.scalar(b)),solver.day_scores(solver.scalar(replace(b,p=b.q))))
 def test_native_forecast_preserves_forced_action_and_by_dawn_metrics(self):
  from tests.test_anonymous_belief import AnonymousBeliefTests
  from werewolf.anonymous_materialization import source as materialize
  from werewolf.model_a_public import horizon_for_action
  c,node,b=AnonymousBeliefTests().case();e=c._ClosedCalculation__engine;solver=Evaluator()
  b=next(child for mass,key,child in b.execute(1) if key is None).refine(node.groups)
  source=node.read()
  with c._ClosedCalculation__kernel():
   result=solver.forecast(b)
   for target,value in result.action_values:
    self.assertEqual(value,e.act(source.public,source.public_state,source.past,target,source.private,None,physical=source.physical))
    self.assertEqual(dict(result.by_dawn_values)[target],horizon_for_action(e,source.public,source.public_state,source.past,target,source.private))
