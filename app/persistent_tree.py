from __future__ import annotations

from app.storage import StoredNodeRecord, StoredTreeRecord
from app.modes.parallel.tree_state import TreeNode, TreeSessionState, build_tree


def build_stored_tree_record(
    session: TreeSessionState,
    *,
    role_counts: dict[str, int] | None = None,
    rules: dict[str, str] | None = None,
    ui_state: dict[str, object] | None = None,
) -> StoredTreeRecord:
    root = build_tree(session)
    if root is None:
        return StoredTreeRecord(
            tree_id=session.tree_id,
            current_node_id=session.current_node_id,
            root_node_id=session.root_node_id,
            player_configs=_build_player_configs(session),
            nodes_by_id={},
            role_counts=dict(role_counts or {}),
            rules=dict(rules or {}),
            ui_state=dict(ui_state or {}),
        )

    nodes_by_id: dict[str, StoredNodeRecord] = {}

    def walk(node: TreeNode, parent_node_id: str | None) -> None:
        child_node_ids = [child.node_id for child in node.children]
        nodes_by_id[node.node_id] = StoredNodeRecord(
            node_id=node.node_id,
            parent_node_id=parent_node_id,
            child_node_ids=child_node_ids,
            state=node.node_state,
            analysis={
                "white_alive_count": node.white_alive_count,
                "wolf_alive_count": node.wolf_alive_count,
                "terminal_winner": node.terminal_winner,
                "result_text": node.result_text,
                "cumulative_probability": node.cumulative_probability,
            },
            player_probabilities={},
            branch_meta={
                "kind": node.kind,
                "label": node.label,
                "selected_target": node.selected_target,
                "probability_text": node.probability_text,
            },
        )
        for child in node.children:
            walk(child, node.node_id)

    walk(root, None)

    return StoredTreeRecord(
        tree_id=session.tree_id,
        current_node_id=session.current_node_id,
        root_node_id=root.node_id,
        player_configs=_build_player_configs(session),
        nodes_by_id=nodes_by_id,
        role_counts=dict(role_counts or {}),
        rules=dict(rules or {}),
        ui_state=dict(ui_state or {}),
    )


def _build_player_configs(session: TreeSessionState) -> dict[str, dict[str, object]]:
    return {
        str(player.index): {
            "index": player.index,
            "name": player.name,
        }
        for player in session.root_state.players
    }
