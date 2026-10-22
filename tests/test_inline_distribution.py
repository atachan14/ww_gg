import unittest
from fractions import Fraction as F
from tests import test_public_convergence_api as public_tests

class InlineDistributionTests(unittest.TestCase):
 def test_conditional_hierarchy_conserves_mass_and_does_not_change_public_mixture(self):
  helper=public_tests.PublicConvergenceAPITests();tree=helper.tree();night,data=helper.night(tree)
  public=helper.leaves(data['night_stages'])[0]['node']
  for key in (night,public):
   source=tree.nodes[key]['node'].read();before=tuple(source)
   rows=tree.distribution(key);self.assertTrue(rows)
   def check(children):
    self.assertEqual(sum(F(row['probability']) for row in children),1)
    for row in children:
     self.assertNotIn('node',row)
     if row['children']:check(row['children'])
   check(rows);self.assertEqual(tuple(tree.nodes[key]['node'].read()),before)
   self.assertTrue(all('village_win' in row for row in rows))
  after=tree.distribution(public)
  self.assertEqual({r['label']:F(r['probability']) for r in after},{'市民2占い0人狼1':F(1,2),'市民1占い1人狼1':F(1,2)})
 def test_secret_contexts_are_not_new_Current_navigation_targets(self):
  helper=public_tests.PublicConvergenceAPITests();tree=helper.tree();night,data=helper.night(tree)
  leaves=helper.leaves(data['night_stages']);self.assertTrue(tree.public_current(leaves[0]['node']))
  contexts={leaf['context_node'] for leaf in leaves if leaf['context_node']!=leaf['node']}
  self.assertTrue(contexts)
  for key in contexts:self.assertFalse(tree.public_current(key))
  self.assertTrue(tree.public_current(tree.root))

 def test_actual_API_returns_analysis_without_navigation_and_rejects_secret_Current(self):
  from app import create_app
  app=create_app({'TESTING':True,'SECRET_KEY':'inline-api','GAME_TREE_PREVIEW':True,'ANONYMOUS_NIGHT_PREVIEW':True})
  client=app.test_client();client.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'random','night':'random','fake_reports':'random'})
  root=client.get('/game-tree?expand=1').json
  night=next(b['node'] for a in root['actions'] for b in a['branches'] if not root['items'][b['node']]['winner'])
  data=client.get('/game-tree',query_string=dict(node=night,expand='1')).json
  helper=public_tests.PublicConvergenceAPITests();leaves=helper.leaves(data['night_stages'])
  public=leaves[0]['node'];context=next(leaf['context_node'] for leaf in leaves if leaf['context_node']!=leaf['node'])
  response=client.get('/game-tree',query_string=dict(node=public,analysis='1'));self.assertEqual(response.status_code,200)
  self.assertTrue(response.json['distribution']);self.assertNotIn('node',str(response.json['distribution']))
  denied=client.post('/game-tree/current',data=dict(snapshot=root['snapshot'],node=context));self.assertEqual(denied.status_code,409)
  accepted=client.post('/game-tree/current',data=dict(snapshot=root['snapshot'],node=public));self.assertEqual(accepted.status_code,200)
