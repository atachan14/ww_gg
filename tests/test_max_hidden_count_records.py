import unittest,json
from fractions import Fraction as F
from unittest.mock import patch
from time import perf_counter
from dev_previews.benchmark_player_counts import data,oracle
from werewolf.board_flow import BoardData
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree
from werewolf.navigation_current import NavigationCurrent
from werewolf.public_convergence import state_key
from werewolf.calculation_budget import calculation_budget

class MaxHiddenCountRecordsTests(unittest.TestCase):
 def document(self,n=7,wolves=2):
  game=data(n,'max',wolves=wolves).to_game();game['mediums']=1
  return NavigationDocument(BoardData.from_game(game),anonymous_owned=True)
 def leaves(self,stage):
  yield from stage.get('leaves',())
  for row in stage.get('branches',()):yield from self.leaves(row['children'])
 def test_original_seven_MAX_count_record_flow_no_ability_compile(self):
  with calculation_budget(4000000,max_seconds=60):
   doc=self.document();node=doc.game.node;e=node._Node__calculation._ClosedCalculation__engine;g=e.evaluation_graph
   self.assertEqual(node.forecast().village_win,oracle(7,2,'day'));self.assertEqual(node.forecast().village_win,F(8,35))
   self.assertFalse(g.supports(node.read())) # Day MAX retains its completed public choice-table contract.
   tree=NavigationTree(doc);root=tree.read(expand=True)
   self.assertEqual(len(root['actions']),1);self.assertEqual(root['actions'][0]['targets'],list(range(1,8)))
   self.assertEqual(root['actions'][0]['policy_probability'],'1');self.assertEqual(len(root['actions'][0]['branches']),1)
   key=root['actions'][0]['branches'][0]['node']
   with patch('werewolf.anonymous_role_night.compile_abilities',side_effect=AssertionError('MAX compiled hidden abilities')),patch('werewolf.anonymous_night.shared_night',side_effect=AssertionError('MAX rebuilt hidden stages')):
    night=tree.read(key,True)
   self.assertEqual(night['evaluation_trace']['owner'],'evaluator');self.assertEqual(night['evaluation_trace']['reduction'],'exchangeable-count-recurrence')
   self.assertEqual(night['night_stages']['method'],'evaluation-recorded-v1');self.assertEqual(night['stage_roles'],dict(seers=0,mediums=0,hunters=0))
   self.assertFalse(getattr(e,'anonymous_ability_programs',{}))
   with patch.object(e,'solve',side_effect=AssertionError('repeated MAX solve')),patch.object(e,'act',side_effect=AssertionError('repeated MAX action')),patch('werewolf.public_convergence.public_night_observations',side_effect=AssertionError('repeated public projection')):
    repeat=tree.read(key,True)
   self.assertEqual(repeat['village_win'],night['village_win'])
   nextkey=next(r['node'] for r in self.leaves(night['night_stages']) if not night['items'][r['node']]['winner'])
   day2=tree.read(nextkey,True);self.assertEqual(sum(F(a['policy_probability']) for a in day2['actions']),1)
   self.assertEqual(doc.game.node.forecast().village_win,F(8,35))
 def test_MAX_concrete_representative_Current_and_cold(self):
  with calculation_budget(4000000,max_seconds=60):
   doc=self.document(5,1);original=doc.game.node.forecast().village_win;doc.game.action(5);tree=NavigationTree(doc)
   shown=tree.read(tree.current_key(),True);self.assertEqual(shown['stage_roles'],dict(seers=0,mediums=0,hunters=0))
   key=next(r['node'] for r in self.leaves(shown['night_stages']) if not shown['items'][r['node']]['winner']);tree.select(key)
   source=NavigationCurrent(doc.game).source;self.assertNotIn(5,source.public.alive)
   cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())));self.assertTrue(state_key(NavigationCurrent(cold.game).source)==state_key(source),'MAX count Current cold Q/P differs')
   self.assertEqual(doc.game.history.state(doc.game.history.root).node.forecast().village_win,original)
   from werewolf.seer_acquisition import SeerReport
   alive=source.public.alive;actor,white,black=alive
   doc.game.public_input(['seer' if p==actor else 'latent' for p in range(1,6)],(SeerReport(1,2,actor,white,'white'),SeerReport(2,2,actor,black,'black')))
   self.assertEqual(doc.game.occurrence.selection_weight,0)
   self.assertEqual(doc.game.history.state(doc.game.history.root).node.forecast().village_win,original)


 def test_named_joint_QP_oracle_and_nonexchangeable_fallback(self):
  from dataclasses import replace
  from werewolf.information_set_forecast import InformationSetForecast
  from werewolf.actor_information import wolf_information_groups
  from werewolf.evaluation_branch import ActionInputs,physical_board
  from werewolf.action_flow import resolve_action
  from werewolf.public_convergence import public_transport,transport_source,public_key,mix
  from werewolf.seer_acquisition import normalize,public_worlds
  from werewolf.exact import replace_worlds
  with calculation_budget(4000000,max_seconds=60):
   for n,w in ((5,1),(6,2)):
    doc=self.document(n,w);doc.game.action(1);node=doc.game.node;s=node.read();e=node._Node__calculation._ClosedCalculation__engine;g=e.evaluation_graph
    record=node._evaluation_refinement();independent=InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False);independent.retain_joint_guard_history=True;buckets={}
    for info,mass,own in wolf_information_groups(s.private):
     policy=independent.wolf_policy(s.public,s.public_state,s.past,info.initial_roster,info.attacks)
     self.assertTrue(all(q==F(1,len(policy)) for t,q in policy),'exchangeable MAX tie weights differ')
     self.assertTrue(all(not info.initial_roster&(1<<(t-1)) for t,q in policy))
     for target,q in policy:
      payload=ActionInputs(s.public_state,s.past,own,None,physical_board(s.public,own,s.physical))
      acquired,outcomes=resolve_action(s.public,payload,target,independent.action_policy,terminal_payoffs=False)
      for outcome in outcomes:
       before=independent.action_policy.project(s.public,acquired,outcome,target)
       reports=((None,F(1),before),) if before.public.winner else independent.report_children(before)
       for public,p,after in reports:
        moved=transport_source(after,public_transport(s,after,node.groups));buckets.setdefault(public_key(moved),[]).append((mass*q*outcome.probability*p,moved))
    expected={state_key(mix(rows)):sum(q for q,source in rows) for rows in buckets.values()}
    self.assertTrue({state_key(edge.source):edge.probability for edge in record.edges}==expected,'complete named MAX joint Q/P law differs')
    self.assertEqual(sum(edge.probability for edge in record.edges),1)
    conditional=normalize(tuple(replace(h,mass=h.mass*(3 if (h.roles[0]&s.public.alive_mask).bit_count()==w else 1)) for h in s.private.hypotheses))
    observed=replace(s,private=replace(s.private,hypotheses=conditional),physical=physical_board(s.public,replace(s.private,hypotheses=conditional),s.physical))
    policies=dict(e.policies);g.refine(observed,node.groups)
    self.assertTrue(all(e.policies.get(key)==value for key,value in policies.items()),'private P changed a public MAX policy')
    biased=normalize(tuple(replace(h,mass=h.mass*(3 if h.roles[0]&(1<<1) else 1)) for h in s.public_state.hypotheses))
    asymmetric=replace(s,public=replace_worlds(s.public,public_worlds(biased)),public_state=replace(s.public_state,hypotheses=biased))
    self.assertFalse(g.supports(asymmetric))
    self.assertFalse(g.supports(replace(s,public=replace(s.public,claims=('seer',*['latent']*(n-1))))))

 def test_actual_seven_HTTP_MAX_no_ability_compilation(self):
  from tempfile import TemporaryDirectory
  from app import create_app
  with TemporaryDirectory() as directory,calculation_budget(4000000,max_seconds=60):
   app=create_app(dict(TESTING=True,SECRET_KEY='max-hidden-count-http',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True,NAVIGATION_DIRECTORY=directory));client=app.test_client()
   client.post('/start',data=dict(citizens=3,seers=1,mediums=1,wolves=2,day='max',night='max',fake_reports='max',win_cutoff=0))
   with patch('werewolf.anonymous_role_night.compile_abilities',side_effect=AssertionError('HTTP MAX ability compile')):
    root=client.get('/game-tree?expand=1');self.assertEqual(root.status_code,200);self.assertEqual(root.json['village_win'],'8/35')
    moved=client.post('/navigation/advance',json=dict(revision=0,target=6));self.assertEqual(moved.status_code,200,moved.get_data(as_text=True)[:200])
    night=client.get('/game-tree?node='+moved.json['current']['occurrence']+'~0&expand=1');self.assertEqual(night.status_code,200,night.get_data(as_text=True)[:200]);self.assertEqual(night.json['stage_roles'],dict(seers=0,mediums=0,hunters=0))
    key=next(r['node'] for r in self.leaves(night.json['night_stages']) if not night.json['items'][r['node']]['winner'])
    current=client.post('/game-tree/current',data=dict(snapshot=night.json['snapshot'],node=key,revision=moved.json['revision']));self.assertEqual(current.status_code,200,current.get_data(as_text=True)[:200])
    self.assertEqual(client.get('/main').status_code,200)
