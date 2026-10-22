import unittest
from fractions import Fraction as F
from collections import defaultdict
from tests import test_phase_compositions as phase_tests
from tests.test_joint_action_kernel import fixture
from werewolf.calculation_tree import CalculationTree
from werewolf.ability_factorization import signature,group_attacks

class AbilityFactorizationTests(unittest.TestCase):
 def latent(self,mode='max'):
  tree,client=phase_tests.PhaseCompositionTests().latent()
  if mode!='max':
   from werewolf.board_flow import BoardData
   game=tree.data.to_game();game['policy'].update(day=mode,night=mode,fake_reports=mode);data=BoardData.from_game(game);roles=data.roles();tree=CalculationTree(data,roles.board,roles.forecast())
  root=tree.read('0',True)
  night=next(b['node'] for a in root['actions'] for b in a['branches'] if not tree.nodes[b['node']]['node'].read().public.winner)
  key=next(c['node'] for c in tree.summary(night)['compositions'] if c['counts']['seers']==1)
  tree.expand(key);return tree,key,tree.nodes[key]['ability_choices'][0]
 def test_screenshot_transposition_full_laws_and_result_correlations(self):
  tree,key,scan=self.latent();self.assertEqual(scan['scans'],[[2,3]])
  self.assertEqual({tuple(a['targets']):F(a['policy_probability']) for a in scan['attacks']},{(2,):F(1,3),(3,):F(5,27),(4,5):F(13,27)})
  source=tree.nodes[key]['node'].read();swap=(1,2,3,5,4);identity=(1,2,3,4,5)
  self.assertEqual(signature(source,swap),signature(source,identity))
  results={r['label']:r for r in scan['results']}
  self.assertEqual({k:F(v['probability']) for k,v in results.items()},{'\u767d':F(5,9),'\u9ed2':F(4,9)})
  self.assertEqual({tuple(a['targets']):F(a['probability']) for a in results['\u767d']['attacks']},{(2,):F(1,3),(3,):F(1,3),(4,5):F(1,3)})
  self.assertEqual({tuple(a['targets']):F(a['probability']) for a in results['\u9ed2']['attacks']},{(2,):F(1,3),(4,5):F(2,3)})
  self.assertEqual(sum(F(r['probability']) for r in scan['results']),1)
  for r in scan['results']:
   self.assertEqual(sum(F(a['probability']) for a in r['attacks']),1)
   for a in r['attacks']:
    self.assertEqual(sum(F(b['probability']) for b in a['branches']),1)
    for member in a['members']:
     for b in member['branches']:
      child=tree.nodes[b['node']]['node'];state=child.read()
      self.assertEqual({x.color for h in state.private.hypotheses for x in h.acquisitions if x.day==2},{'white' if r['label']=='\u767d' else 'black'})
      self.assertEqual(child.export_request().roles(),state)
      self.assertEqual(tree.nodes[tree.restore(tree.route(b['node']))]['node'].read(),state)
      self.assertTrue(all(not h.roles[0]&(1<<(member['target']-1)) for h in state.private.hypotheses))
 def test_named_measure_unchanged_by_result_and_attack_factorization(self):
  for mode in ('max','random'):
   for latent in (False,True):
    if latent:tree,key,scan=self.latent(mode)
    else:
     calculation,node,client=fixture(mode);roles=calculation.data.roles();tree=CalculationTree(calculation.data,roles.board,roles.forecast());tree.expand('0')
     key=next(b['node'] for a in tree.nodes['0']['actions'] if 3 in a['targets'] for b in a['branches'] if not tree.nodes[b['node']]['node'].read().public.winner)
     tree.expand(key);scan=tree.nodes[key]['ability_choices'][0]
     self.assertTrue(all(a['multiplicity']==1 for a in scan['attacks']))
    before=defaultdict(F);after=defaultdict(F);value=F()
    for a in scan['attacks']:
     for m in a['members']:
      for b in m['branches']:before[tree.nodes[b['node']]['node'].read()]+=F(b['mass'])
    for r in scan['results']:
     for a in r['attacks']:
      for m in a['members']:
       for b in m['branches']:after[tree.nodes[b['node']]['node'].read()]+=F(b['mass'])
      for b in a['branches']:value+=F(scan['probability'])*F(r['probability'])*F(a['probability'])*F(b['probability'])*tree.value(b['node'])
    self.assertEqual(before,after);self.assertEqual(sum(after.values()),1);self.assertEqual(value,tree.value(key))
    self.assertTrue(all(r['private'] for r in scan['results']))
    # The unmodified legacy named enumeration independently conserves value.
    self.assertEqual(sum(F(a['policy_probability'])*sum(F(b['probability'])*tree.value(b['node']) for b in a['branches']) for a in tree.nodes[key]['actions']),tree.value(key))
 def test_equal_numbers_do_not_merge_distinct_scan_targets(self):
  tree,key,scan=self.latent();node=tree.nodes[key]['node']
  named=[{**a,'target':m['target'],'targets':[m['target']],'branches':m['branches']} for a in scan['attacks'] for m in a['members']]
  # Even replacing all displayed policy numbers with the same value cannot
  # create a full-law automorphism swapping actor 2 or scanned target 3.
  for a in named:a['policy_probability']='1/4'
  grouped=group_attacks(tree,node,scan['scans'],named)
  self.assertEqual([a['targets'] for a in grouped],[[2],[3],[4,5]])
 def test_absent_seer_has_no_invented_color(self):
  tree,client=phase_tests.PhaseCompositionTests().latent();root=tree.read('0',True)
  night=next(b['node'] for a in root['actions'] for b in a['branches'] if not tree.nodes[b['node']]['node'].read().public.winner)
  key=next(c['node'] for c in tree.summary(night)['compositions'] if c['counts']['seers']==0);tree.expand(key)
  self.assertEqual({r['label'] for s in tree.nodes[key]['ability_choices'] for r in s['results']},{'\u5360\u3044\u306a\u3057'})

 def test_grouped_named_Current_variant_roundtrip(self):
  tree,key,scan=self.latent();attack=next(a for r in scan['results'] for a in r['attacks'] if a['targets']==[4,5])
  for member in attack['members']:
   for b in member['branches']:
    selected=b['node'];restored=tree.restore(tree.route(selected));self.assertEqual(tree.nodes[restored]['node'].read(),tree.nodes[selected]['node'].read())
  rendered=tree.read(key,True)
  for b in attack['branches']:
   for v in b['variants']:self.assertIn(v['node'],rendered['items'])
 def test_result_display_does_not_change_source_information_or_wolf_policy(self):
  tree,key,scan=self.latent();node=tree.nodes[key]['node'];source=node.read();engine=tree.engine
  with tree.calculation._ClosedCalculation__kernel():
   policies={c.information:engine.wolf_policy(source.public,source.public_state,source.past,c.information.initial_roster,c.information.attacks) for c in node.wolf_choices()}
   tree.read(key,True)
   self.assertEqual(node.read(),source)
   for info,policy in policies.items():self.assertEqual(engine.wolf_policy(source.public,source.public_state,source.past,info.initial_roster,info.attacks),policy)
