import copy,unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from tests.test_board_flow import game
from werewolf.board_flow import BoardData,GameData
from werewolf.game_runtime import GameRuntime,GameRuntimes
from werewolf.forecast_result import Forecast
from werewolf.seer_future_uniform import FuturePending

class GameEvaluationCacheTests(unittest.TestCase):
 def test_common_data_created_once_shared_without_rule_equality(self):
  runtime=GameRuntime.from_game(game());rules=runtime.data.rules
  with patch.object(GameData,'from_game',side_effect=AssertionError('common reloaded')),patch.object(type(rules),'__eq__',side_effect=AssertionError('rules compared')):
   root=BoardData.from_game(game(),runtime=runtime)
   changed=root.updated(selection=2)
   child=root.child(dict(target=5,policy=game()['policy']))
  self.assertIs(root.game_data,changed.game_data);self.assertIs(root.runtime,child.runtime)
  self.assertNotIn('rules',root.inputs)
  with self.assertRaises(ValueError):root.updated(rules=game()['rules'])
  with self.assertRaises(AttributeError):runtime.data=GameData.from_game(game())
 def test_public_complete_reuse_still_reconstructs_display_roles(self):
  import werewolf.board_roles as roles
  import werewolf.model_a_public as public
  runtime=GameRuntime.from_game(game());source=game()
  with patch.object(roles,'reconstruct_saved',wraps=roles.reconstruct_saved) as replay,patch.object(public,'evaluate_prepared_public',wraps=public.evaluate_prepared_public) as evaluate:
   first=BoardData.from_game(source,runtime=runtime).roles().forecast()
   count=replay.call_count
   second=BoardData.from_game(source,runtime=runtime).roles().forecast()
   self.assertGreater(replay.call_count,count);self.assertEqual(evaluate.call_count,1)
  self.assertEqual(first,second);self.assertEqual(first.village_win,F(7,15));self.assertEqual(runtime.info()['hits'],1)
 def test_games_and_common_changes_have_separate_lifetimes(self):
  registry=GameRuntimes(max_games=2)
  a=registry.get('A',game());a.put(('x',),Forecast(F(1),()))
  b=registry.get('B',game());self.assertFalse(b.get(('x',))[0])
  registry.discard('A');self.assertEqual(a.info()['entries'],0)
  changed=game(wolves=2);c=registry.get('C',changed)
  self.assertEqual(c.data.wolves,2);self.assertIsNot(a,c)
  self.assertFalse(c.get(('x',))[0])
 def test_input_history_policy_budget_dependencies_do_not_hit(self):
  import werewolf.model_a_public as public
  root=BoardData.from_game(game(mediums=1))
  variants=[root,root.updated(claims=['medium']+['latent']*4),root.updated(policy={**game()['policy'],'night':'random'}),root.child(dict(target=5,policy=game()['policy']))]
  with patch.object(public,'evaluate_prepared_public',return_value=Forecast(F(1,2),())) as evaluate:
   for board in variants:board.roles().forecast()
   self.assertEqual(evaluate.call_count,len(variants))
   variants[0].roles().forecast(max_work=250001);self.assertEqual(evaluate.call_count,len(variants)+1)
 def test_pending_and_partial_metrics_never_cached_and_lru_is_bounded(self):
  runtime=GameRuntime.from_game(game(),max_entries=2)
  runtime.put(('pending',),FuturePending('budget'));runtime.put(('partial',),Forecast(F(1,2),(),pending_metrics=('dawn',)))
  self.assertEqual(runtime.info()['entries'],0)
  for i in range(3):runtime.put((i,),Forecast(F(1,2),()))
  self.assertFalse(runtime.get((0,))[0]);self.assertEqual(runtime.info()['entries'],2)
 def test_private_key_isolated_and_cached_tables_are_defensive_copies(self):
  runtime=GameRuntime.from_game(game());state=BoardData.from_game(game(),runtime=runtime).roles()
  value={'players':[{'legal':True,'final':{'village':'1/3'},'dawn':{'village':'0','wolf':'0'}}],'reason':'complete'}
  with patch('werewolf.board_roles.prepare_private',return_value=(None,None)),patch('werewolf.private_adapter.evaluate_private_table',return_value=value) as evaluate:
   first=state.private('wolf',[1],[]);first['players'][0]['final']['village']='corrupted'
   again=state.private('wolf',[1],[])
   self.assertEqual(again['players'][0]['final']['village'],'1/3');self.assertEqual(evaluate.call_count,1)
   state.private('wolf',[2],[]);self.assertEqual(evaluate.call_count,2)
   state.forecast();self.assertEqual(evaluate.call_count,2)
 def test_reference_mode_bypasses_completed_results(self):
  from werewolf.board_future import reconstruction_kernel_reuse
  state=BoardData.from_game(game()).roles();state.forecast()
  with patch('werewolf.model_a_public.evaluate_prepared_public',return_value=Forecast(F(1,3),())) as evaluate:
   with reconstruction_kernel_reuse(False):reference=state.forecast()
   self.assertEqual(evaluate.call_count,1);self.assertEqual(reference.village_win,F(1,3))
  self.assertEqual(state.forecast().village_win,F(7,15))
 def test_cache_hit_enforces_outer_deadline_and_invalid_budgets(self):
  from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded
  from unittest.mock import patch
  state=BoardData.from_game(game()).roles();state.forecast()
  with self.assertRaises(ValueError):state.forecast(max_work=True)
  with calculation_budget(250000,max_seconds=20),patch('werewolf.calculation_budget.monotonic',return_value=float('inf')):
   self.assertIsInstance(state.forecast(),FuturePending)
 def test_new_setup_rotates_existing_game_identity_and_clears_old_results(self):
  from app import create_app
  app=create_app({'TESTING':True,'SECRET_KEY':'game-cache-test'});client=app.test_client()
  client.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
  client.get('/main')
  with client.session_transaction() as session:first=session['co_display_game'];source=copy.deepcopy(session['game'])
  registry=app.extensions['board_game_runtimes'];old=registry.get(first,source)
  self.assertGreater(old.info()['entries'],0)
  client.post('/start',data={'citizens':'3','wolves':'1','seers':'1','initial_seer':'none','day':'random','night':'random'})
  client.get('/main')
  with client.session_transaction() as session:second=session['co_display_game'];source=copy.deepcopy(session['game'])
  self.assertNotEqual(first,second);self.assertEqual(old.info()['entries'],0)
  self.assertEqual(registry.get(second,source).data.seers,1)
  self.assertEqual(registry.get(second,source).data.rules.initial_seer,'none')

class HypothesisIdentityTests(unittest.TestCase):
 def test_mass_free_keys_match_legacy_comparison_without_candidate_creation(self):
  from werewolf.seer_acquisition import Hypothesis
  from werewolf.board_future import identity,weighted_hypothesis
  from werewolf.guard_effect import GuardIntent
  from werewolf.night_knowledge import WolfAttack
  samples=[Hypothesis((1,0,2,4),(),F(1,2)),Hypothesis((1,0,2,4),(),F(1,3),guards=(GuardIntent(1,3,2),)),Hypothesis((1,0,2,4),(),F(1,4),attacks=(WolfAttack(1,2),))]
  samples += [replace(h,mass=F(1,7)) for h in samples]
  for a in samples:
   for b in samples:self.assertEqual(identity(a)==identity(b),replace(a,mass=F(1))==replace(b,mass=F(1)))
  with patch.object(Hypothesis,'__post_init__',side_effect=AssertionError('copy')):
   identity(samples[0]);self.assertIs(weighted_hypothesis(samples[0],samples[0].mass),samples[0])
 def test_subclass_compatibility_keeps_old_identity_behavior(self):
  from dataclasses import dataclass
  from werewolf.seer_acquisition import Hypothesis
  from werewolf.board_future import identity
  @dataclass(frozen=True)
  class Extra(Hypothesis):tag:int=1
  h=Extra((1,0,0,0),(),F(1,2))
  self.assertEqual(identity(h),replace(h,mass=F(1)))

 def test_equal_tuple_subclass_uses_same_key_and_compatibility_validation(self):
  from collections import namedtuple
  from werewolf.seer_acquisition import Hypothesis
  from werewolf.board_future import identity
  Roles=namedtuple('Roles','w m s h')
  left=Hypothesis((1,0,0,0),(),F(1,2));right=Hypothesis(Roles(1,0,0,0),(),F(1,3))
  self.assertEqual(identity(left),identity(right));self.assertEqual(hash(identity(left)),hash(identity(right)))
