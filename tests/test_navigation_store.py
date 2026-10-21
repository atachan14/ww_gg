import json,tempfile,unittest
from tests import test_manual_public_input as fixtures
from werewolf.navigation_store import NavigationStore,StaleNavigation

class NavigationStoreTests(unittest.TestCase):
 def test_fresh_process_restores_recipes_and_cursor_without_evaluation_snapshot(self):
  root=fixtures.ManualPublicInputTests().root();data=root.data
  with tempfile.TemporaryDirectory() as directory:
   store=NavigationStore(directory);doc,row=store.apply('test-game',data,0,lambda game:game.action(3))
   before=doc.game.node.read();record=doc.export();self.assertNotIn('hypotheses',json.dumps(record));self.assertNotIn('private',record)
   restored=NavigationStore(directory).get('test-game',data)
   self.assertEqual(restored.game.node.read(),before);self.assertEqual(restored.game.current,row.key);self.assertEqual(restored.export(),record)
   with self.assertRaises(StaleNavigation):store.apply('test-game',data,0,lambda game:game.back())
   self.assertEqual(doc.game.current,row.key)

 def test_failed_persistence_restores_cursor_and_occurrences(self):
  from unittest.mock import patch
  data=fixtures.ManualPublicInputTests().root().data
  with tempfile.TemporaryDirectory() as directory:
   store=NavigationStore(directory);doc=store.get('test-game',data);before=doc.export()
   with patch.object(store,'save',side_effect=OSError('disk unavailable')):
    with self.assertRaises(OSError):store.apply('test-game',data,0,lambda game:game.action(3))
   self.assertEqual(doc.export(),before)
   doc,row=store.apply('test-game',data,0,lambda game:game.action(3))
   self.assertEqual(doc.revision,1);self.assertEqual(row.key,'h1')
