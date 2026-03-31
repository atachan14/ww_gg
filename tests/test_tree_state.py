import unittest

from app.core.game_tree import build_initial_node_state
from app.modes.parallel.tree_state import (
    advance_current_path,
    create_tree_session,
    deserialize_tree_session,
    fork_current_node_with_claims,
    fork_current_node_with_tactics,
    get_current_node,
    serialize_tree_session,
    set_node_claims,
    set_node_tactics,
)


ROLE_COUNTS = {
    "villager": 2,
    "seer": 1,
    "medium": 0,
    "hunter": 0,
    "wolf": 1,
    "madman": 0,
}


class TreeStateTests(unittest.TestCase):
    def test_serialize_roundtrip_preserves_overrides(self) -> None:
        session = create_tree_session(build_initial_node_state(ROLE_COUNTS))
        set_node_tactics(session, "", {"village_no_counter": "all_true"})
        set_node_claims(session, "", {1: ["seer"], 2: ["villager"]})

        restored = deserialize_tree_session(serialize_tree_session(session), ROLE_COUNTS)
        current = get_current_node(restored)

        self.assertIsNotNone(current)
        assert current is not None
        self.assertEqual(current.node_state.tactics["village_no_counter"], "all_true")
        self.assertEqual(current.node_state.players[0].claim_role_keys, ["seer"])
        self.assertEqual(current.node_state.players[1].claim_role_keys, ["villager"])

    def test_advance_moves_to_next_choice_node(self) -> None:
        role_counts = {
            "villager": 4,
            "seer": 0,
            "medium": 0,
            "hunter": 0,
            "wolf": 1,
            "madman": 0,
        }
        session = create_tree_session(build_initial_node_state(role_counts))

        current_before = get_current_node(session)
        self.assertIsNotNone(current_before)
        assert current_before is not None
        self.assertEqual(current_before.node_id, "")
        self.assertEqual(current_before.kind, "choice")
        self.assertEqual(current_before.selected_target, 1)

        advance_current_path(session)
        current_after = get_current_node(session)
        self.assertIsNotNone(current_after)
        assert current_after is not None
        self.assertEqual(session.current_node_id, "0.0")
        self.assertEqual(current_after.node_id, "0.0")
        self.assertEqual(current_after.kind, "choice")
        self.assertEqual(current_after.selected_target, 2)

    def test_fork_with_tactics_creates_child_node(self) -> None:
        session = create_tree_session(build_initial_node_state(ROLE_COUNTS))

        forked_node_id = fork_current_node_with_tactics(session, {"village_no_counter": "filled_true"})
        current = get_current_node(session)

        self.assertEqual(forked_node_id, "f1")
        self.assertEqual(session.current_node_id, "f1")
        self.assertIsNotNone(current)
        assert current is not None
        self.assertEqual(current.node_id, "f1")
        self.assertEqual(current.node_state.tactics["village_no_counter"], "filled_true")

    def test_fork_with_claims_creates_child_node(self) -> None:
        session = create_tree_session(build_initial_node_state(ROLE_COUNTS))

        forked_node_id = fork_current_node_with_claims(session, {1: ["seer"], 2: ["villager"]})
        current = get_current_node(session)

        self.assertEqual(forked_node_id, "f1")
        self.assertIsNotNone(current)
        assert current is not None
        self.assertEqual(current.node_state.players[0].claim_role_keys, ["seer"])
        self.assertEqual(current.node_state.players[1].claim_role_keys, ["villager"])


if __name__ == "__main__":
    unittest.main()
