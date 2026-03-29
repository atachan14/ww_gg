import unittest

from app.game_tree import build_initial_node_state
from app.persistent_tree import build_stored_tree_record
from app.storage import InMemoryTreeStorage, StoredTreeRecord
from app.tree_state import advance_current_path, create_tree_session


class PersistentTreeTests(unittest.TestCase):
    def test_build_stored_tree_record_contains_current_and_root(self) -> None:
        role_counts = {
            "villager": 4,
            "seer": 0,
            "medium": 0,
            "hunter": 0,
            "wolf": 1,
            "madman": 0,
        }
        session = create_tree_session(build_initial_node_state(role_counts))
        advance_current_path(session)

        record = build_stored_tree_record(session)

        self.assertEqual(record.root_node_id, "")
        self.assertEqual(record.current_node_id, "0.0")
        self.assertIn("", record.nodes_by_id)
        self.assertIn("0.0", record.nodes_by_id)
        self.assertEqual(record.nodes_by_id[""].branch_meta["kind"], "choice")
        self.assertEqual(record.nodes_by_id["0.0"].branch_meta["kind"], "choice")

    def test_inmemory_storage_roundtrip(self) -> None:
        role_counts = {
            "villager": 2,
            "seer": 1,
            "medium": 0,
            "hunter": 0,
            "wolf": 1,
            "madman": 0,
        }
        session = create_tree_session(build_initial_node_state(role_counts))
        record = build_stored_tree_record(session)

        storage = InMemoryTreeStorage()
        storage.save_tree(record)
        loaded = storage.load_tree(record.tree_id)

        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertIsInstance(loaded, StoredTreeRecord)
        self.assertEqual(loaded.tree_id, record.tree_id)
        self.assertEqual(loaded.root_node_id, record.root_node_id)
        self.assertIn("1", loaded.player_configs)


if __name__ == "__main__":
    unittest.main()
