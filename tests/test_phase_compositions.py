import unittest
from fractions import Fraction as F
from app import create_app
from werewolf.calculation_tree import CalculationTree
from werewolf.board_flow import BoardData
from werewolf.physical_selection import counts
from tests.test_joint_action_kernel import fixture

class PhaseCompositionTests(unittest.TestCase):
 def latent(self):
  app=create_app({'TESTING':True,'SECRET_KEY':'phase-tests','GAME_TREE_PREVIEW':True});client=app.test_client();client.post('/start',data={'players':'5','seers':'1','day':'max','night':'max'})
  with client.session_transaction() as ss:data=BoardData.from_game(ss['game'])
  roles=data.roles();tree=CalculationTree(data,roles.board,roles.forecast());return tree,client
 def test_initial_latent_compositions_terminal_and_probability_conservation(self):
  tree,client=self.latent();root=tree.read('0',True);self.assertEqual(root['compositions'][0]['label'],'占い1市民3狼1')
  labels={};total=F()
  for action in root['actions']:
   for branch in action['branches']:
    child=tree.summary(branch['node']);source=tree.nodes[child['node']]['node'].read()
    for composition in child['compositions']:
     probability=F(action['policy_probability'])*F(branch['probability'])*F(composition['probability'])
     labels[composition['label']]=labels.get(composition['label'],F())+probability;total+=probability
     node=tree.nodes[composition['node']]['node'];state=node.read()
     self.assertEqual(state.public_state,source.public_state);self.assertEqual(state.public,source.public)
     self.assertEqual(node.export_request().roles(),state)
     self.assertEqual({counts(h,state.public.alive) for h in state.private.hypotheses},{tuple(composition['counts'][k] for k in ('wolves','mediums','seers','hunters','citizens'))})
     if composition['counts']['wolves']==0:
      tree.expand(composition['node']);self.assertEqual(tree.nodes[composition['node']]['actions'],[]);self.assertEqual(tree.value(composition['node']),1)
    self.assertEqual(sum(F(c['probability']) for c in child['compositions']),1)
    self.assertEqual(sum(F(c['probability'])*tree.value(c['node']) for c in child['compositions']),tree.value(child['node']))
  self.assertEqual(total,1);self.assertEqual(labels,{'占い1市民3狼0':F(1,5),'占い0市民3狼1':F(1,5),'占い1市民2狼1':F(3,5)})
 def test_hidden_composition_never_conditions_public_wolf_policy(self):
  tree,client=self.latent();root=tree.read('0',True)
  night=next(b['node'] for a in root['actions'] for b in a['branches'] if tree.nodes[b['node']]['node'].read().public.winner is None)
  source=tree.nodes[night]['node'].read();e=tree.engine
  with tree.calculation._ClosedCalculation__kernel():
   for c in tree.summary(night)['compositions']:
    node=tree.nodes[c['node']]['node'];child=node.read()
    self.assertEqual(child.public_state,source.public_state)
    for choice in node.wolf_choices():
     i=choice.information
     self.assertEqual(e.wolf_policy(source.public,source.public_state,source.past,i.initial_roster,i.attacks),e.wolf_policy(child.public,child.public_state,child.past,i.initial_roster,i.attacks))
 def test_canonical_scan_then_legal_bites_are_same_simultaneous_measure(self):
  for mode in ('max','random'):
   calculation,node,client=fixture(mode);roles=calculation.data.roles();tree=CalculationTree(calculation.data,roles.board,roles.forecast());tree.expand('0')
   night=next(b['node'] for a in tree.nodes['0']['actions'] if a['targets']==[3,4,5] for b in a['branches'] if tree.nodes[b['node']]['node'].read().public.winner is None)
   tree.expand(night);selections=tree.nodes[night]['ability_choices'];self.assertEqual(len(selections),1)
   scan=selections[0];self.assertEqual(scan['label'],'1が[(4),5]から占い');self.assertEqual(scan['scans'],[[1,4]]);self.assertTrue(scan['simultaneous'])
   self.assertEqual(F(scan['probability']),1);self.assertEqual(sum(F(a['policy_probability']) for a in scan['attacks']),1)
   actual=F()
   for attack in scan['attacks']:
    self.assertEqual(sum(F(b['probability']) for b in attack['branches']),1)
    for branch in attack['branches']:
     child=tree.nodes[branch['node']]['node'];state=child.read()
     self.assertEqual(state.public.history[-1].target,attack['target'])
     self.assertTrue(all(not h.roles[0]&(1<<(attack['target']-1)) for h in state.private.hypotheses))
     self.assertTrue(all(tuple((a.player,a.target) for a in h.acquisitions if a.day==2)==((1,4),) for h in state.private.hypotheses))
     self.assertEqual(child.export_request().roles(),state)
     restored=tree.restore(tree.route(branch['node']));self.assertEqual(tree.nodes[restored]['node'].read(),state)
     actual+=F(attack['policy_probability'])*F(branch['probability'])*tree.value(branch['node'])
    if attack['target'] in (4,5):
     self.assertEqual(attack['conditional_probability'],'1/2');self.assertEqual(len(attack['branches']),1)
     state=tree.nodes[attack['branches'][0]['node']]['node'].read()
     self.assertEqual({a.color for h in state.private.hypotheses for a in h.acquisitions if a.day==2},{'white' if attack['target']==4 else 'black'})
     if mode=='max':self.assertEqual(attack['policy_probability'],'0')
   self.assertEqual(actual,tree.value(night))
 def test_latent_composition_split_actions_conserve_value_and_replay(self):
  tree,client=self.latent();root=tree.read('0',True)
  night=next(b['node'] for a in root['actions'] for b in a['branches'] if not tree.nodes[b['node']]['node'].read().public.winner)
  for composition in tree.summary(night)['compositions']:
   key=composition['node'];tree.expand(key);choices=tree.nodes[key]['ability_choices'];total=F()
   self.assertEqual(sum(F(s['probability']) for s in choices),1)
   for scan in choices:
    self.assertEqual(sum(F(a['policy_probability']) for a in scan['attacks']),1)
    for attack in scan['attacks']:
     self.assertEqual(sum(F(b['probability']) for b in attack['branches']),1)
     for branch in attack['branches']:
      node=tree.nodes[branch['node']]['node'];self.assertEqual(node.export_request().roles(),node.read())
      restored=tree.restore(tree.route(branch['node']));self.assertEqual(tree.nodes[restored]['node'].read(),node.read())
      total+=F(scan['probability'])*F(attack['policy_probability'])*F(branch['probability'])*tree.value(branch['node'])
   self.assertEqual(total,tree.value(key))

 def test_split_joint_Current_and_tree_reload(self):
  calculation,node,client=fixture('max');root=client.get('/game-tree?expand=1').json
  orbit=next(a for a in root['actions'] if a['targets']==[3,4,5])
  night=next(b['node'] for b in orbit['branches'] if not root['items'][b['node']]['winner'])
  expanded=client.get('/game-tree',query_string={'node':night,'expand':'1'}).json
  attack=next(a for a in expanded['ability_choices'][0]['attacks'] if a['target']==4)
  result=client.post('/game-tree/current',data={'snapshot':root['snapshot'],'node':attack['branches'][0]['node']})
  self.assertEqual(result.status_code,200,result.data);self.assertEqual(client.get(result.json['url']).status_code,200)
  from urllib.parse import urlparse,parse_qs
  token=parse_qs(urlparse(result.json['url']).query)['current'][0]
  reloaded=client.get('/game-tree',query_string={'current':token,'expand':'1'})
  self.assertEqual(reloaded.status_code,200,reloaded.data)
  self.assertEqual(reloaded.json['current_node'],attack['branches'][0]['node'])

 def test_incomplete_latent_history_keeps_exact_existing_action_fallback(self):
  calculation,node,client=fixture();game=calculation.data.to_game();game['claim_policy']['seer']='none'
  data=BoardData.from_game(game);roles=data.roles();tree=CalculationTree(data,roles.board,roles.forecast());tree.expand('0')
  action=next(a for a in tree.nodes['0']['actions'] if 3 in a['targets'])
  key=next(b['node'] for b in action['branches'] if not tree.nodes[b['node']]['node'].read().public.winner)
  value=tree.value(key);tree.expand(key)
  self.assertTrue(tree.nodes[key]['actions']);self.assertIsNone(tree.nodes[key].get('ability_choices'))
  self.assertIn('完全な占い履歴',tree.nodes[key]['ability_pending']);self.assertEqual(tree.value(key),value)

 def test_composition_Current_roundtrip_and_no_saved_input_edits(self):
  tree,client=self.latent();root=client.get('/game-tree?expand=1').json
  night=next(root['items'][b['node']] for a in root['actions'] for b in a['branches'] if not root['items'][b['node']]['winner'])
  composition=next(c for c in night['compositions'] if c['counts']['seers']==0)
  with client.session_transaction() as ss:before=ss['game'].copy()
  result=client.post('/game-tree/current',data={'snapshot':root['snapshot'],'node':composition['node']})
  self.assertEqual(result.status_code,200,result.data);self.assertEqual(client.get(result.json['url']).status_code,200)
  with client.session_transaction() as ss:self.assertEqual(ss['game'],before)
