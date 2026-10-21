import unittest
from fractions import Fraction as F
from werewolf.navigation_history import NavigationHistory,NameMap
from tests import test_joint_action_kernel as fixture_tests

class NavigationHistoryTests(unittest.TestCase):
 def test_reconverged_state_keeps_distinct_parents_and_cold_routes(self):
  c,night,client=fixture_tests.fixture('random');root=c.root;h=NavigationHistory(root)
  branch=next((i,b) for i,b in enumerate(root.action(3)) if not b.node.read().public.winner);index,child=branch
  a=h.append(h.root,child.node,dict(target=3,outcome=index),selection_weight=F(1,3))
  b=h.append(h.root,child.node,dict(target=3,outcome=index),names=NameMap((1,2,4,3,5)),selection_weight=F(1,3))
  self.assertEqual(a.state,b.state);self.assertNotEqual(a.key,b.key);self.assertNotEqual(a.names,b.names)
  repeat=h.append(a.key,child.node,dict(keep=True),kind='manual_public',selection_weight=0)
  self.assertEqual(repeat.state,a.state);self.assertEqual(h.path(repeat.key)[-2],a)
  rebuilt=NavigationHistory.restore(root,h.export(),lambda node,s:node if s.get('keep') else node.action(s['target'])[s['outcome']].node)
  self.assertEqual(rebuilt.export(),h.export());self.assertEqual(rebuilt.state(b.key).cold(),child.node.read())
 def test_manual_edge_does_not_change_source_value_or_old_continuations(self):
  c,night,client=fixture_tests.fixture('random');h=NavigationHistory(c.root);before=c.root.forecast();child=c.root.action(3)[0].node
  old=h.append(h.root,child,dict(target=3,outcome=0),selection_weight=F(1,3))
  manual=h.append(h.root,child,dict(target=3,outcome=0),kind='manual_public',selection_weight=0)
  self.assertEqual(c.root.forecast(),before);self.assertEqual(h.children(h.root),(old,manual));self.assertEqual(manual.selection_weight,0)
  with self.assertRaises(ValueError):h.append(h.root,child,None,kind='manual_public',selection_weight=1)
 def test_bijection_round_trip_and_composition(self):
  a=NameMap((1,3,2,4,5));b=NameMap((2,1,3,5,4))
  for p in range(1,6):self.assertEqual(a.canonical(a.display(p)),p);self.assertEqual(a.then(b).display(p),b.display(a.display(p)))
  with self.assertRaises(ValueError):NameMap((1,1,3))

 def test_selector_is_immutable_and_policy_is_part_of_solver_state_identity(self):
  c,night,client=fixture_tests.fixture('random');other,unused,unused_client=fixture_tests.fixture('max')
  h=NavigationHistory(c.root);selector=dict(example=[1,2]);a=h.append(h.root,c.root,selector)
  selector['example'].append(3);self.assertEqual(a.selector,dict(example=[1,2]))
  read=a.selector;read['example'].append(4);self.assertEqual(a.selector,dict(example=[1,2]))
  b=h.append(h.root,other.root,dict(example=[]));self.assertNotEqual(a.state,b.state)
