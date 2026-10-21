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

 def test_real_main_and_Tree_use_shared_native_decisions_without_named_solver(self):
  from unittest.mock import patch
  from app import create_app
  app=create_app({'TESTING':True,'SECRET_KEY':'shared-native-route','GAME_TREE_PREVIEW':True,'ANONYMOUS_NIGHT_PREVIEW':True})
  client=app.test_client();client.post('/start',data=dict(citizens='3',seers='1',wolves='1',day='max',night='max',fake_reports='max'))
  with patch('werewolf.board_flow.RoleState.forecast',side_effect=AssertionError('legacy primary forecast used')),patch.object(InformationSetForecast,'solve',side_effect=AssertionError('named scalar used')),patch.object(InformationSetForecast,'wolf_policy',side_effect=AssertionError('named MAX policy used')):
   response=client.get('/main');self.assertEqual(response.status_code,200,response.data[:300]);self.assertIn('46.67%',response.get_data(as_text=True))
   root=client.get('/game-tree?expand=1').json
   key=next(b['node'] for a in root['actions'] for b in a['branches'] if not root['items'][b['node']]['winner'])
   response=client.get('/game-tree',query_string=dict(node=key,expand='1'));self.assertEqual(response.status_code,200,response.data[:300]);self.assertTrue(response.json['night_stages']['stats']['belief_owned'])
 def test_each_owned_outcome_continuation_matches_named_exact_oracle(self):
  from werewolf.closed_calculation import ClosedCalculation
  from werewolf.anonymous_night import compile_anonymous
  c,unused=native.AnonymousNightTests().case(seers=1,wolves=2,citizens=4,mode='max')
  owned=ClosedCalculation(c.data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  node=next(o.node for o in owned.root.action(1) if not o.node.read().public.winner);e=owned._ClosedCalculation__engine
  oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True
  with owned._ClosedCalculation__kernel(),e.group_scope(node.groups):
   program=compile_anonymous(e,node.read(),node.groups)
   for leaf in program.leaves:
    self.assertIsNotNone(leaf.belief)
    self.assertEqual(program.continuation(e,leaf),oracle.solve(*leaf.source,physical=leaf.source.physical))

 def test_mixed_live_wolf_counts_keep_forced_night_count_prior_and_horizon(self):
  from werewolf.closed_calculation import ClosedCalculation
  from werewolf.model_a_public import horizon_for_action
  c,unused=native.AnonymousNightTests().case(seers=1,wolves=2,citizens=4,mode='max')
  owned=ClosedCalculation(c.data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  node=next(o.node for o in owned.root.action(1) if not o.node.read().public.winner);e=owned._ClosedCalculation__engine;s=node.read();b=e.anonymous_beliefs[s]
  self.assertEqual(set(s.physical.wolf_count_distribution),{1,2})
  oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False);oracle.retain_joint_guard_history=True
  with owned._ClosedCalculation__kernel():
   result=e.anonymous_values.forecast(b)
   for target in (2,3):
    self.assertEqual(dict(result.action_values)[target],oracle.act(s.public,s.public_state,s.past,target,s.private,None,physical=s.physical))
    self.assertEqual(dict(result.by_dawn_values)[target],horizon_for_action(oracle,s.public,s.public_state,s.past,target,s.private))

 def test_terminal_public_belief_has_no_actions_or_further_abilities(self):
  b=Belief.initial(((1,2,3,4,5),),dict(wolf=1,seer=1,villager=3))
  won=next(child for mass,result,child in b.execute(1) if result=='village')
  forecast=Evaluator('max','max').forecast(won)
  self.assertEqual(forecast.village_win,1);self.assertEqual(forecast.action_values,());self.assertEqual(forecast.by_dawn_values,())
  with self.assertRaisesRegex(ValueError,'Terminal belief'):won.night()

 def test_saved_and_reporting_origins_keep_their_existing_exact_replay_path(self):
  from werewolf.anonymous_value import initial_forecast
  c,unused=native.AnonymousNightTests().case()
  self.assertIsNone(initial_forecast(c.data.updated(history=[{'target':1}])))
  game=c.data.to_game();claims=list(game['claims']);claims[0]='seer'
  self.assertIsNone(initial_forecast(c.data.updated(claims=claims)))
