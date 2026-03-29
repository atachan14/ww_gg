from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.game_tree import NodeState, deserialize_node_state, serialize_node_state
from app.runtime_config import RuntimeConfig


@dataclass
class StoredNodeRecord:
    node_id: str
    parent_node_id: str | None
    child_node_ids: list[str]
    state: NodeState
    analysis: dict[str, object] = field(default_factory=dict)
    player_probabilities: dict[str, object] = field(default_factory=dict)
    branch_meta: dict[str, object] = field(default_factory=dict)

    def serialize(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "parent_node_id": self.parent_node_id,
            "child_node_ids": self.child_node_ids.copy(),
            "state": serialize_node_state(self.state),
            "analysis": self.analysis.copy(),
            "player_probabilities": self.player_probabilities.copy(),
            "branch_meta": self.branch_meta.copy(),
        }

    @classmethod
    def deserialize(cls, data: dict[str, object], fallback_role_counts: dict[str, int]) -> "StoredNodeRecord":
        return cls(
            node_id=str(data.get("node_id", "")),
            parent_node_id=(str(data["parent_node_id"]) if data.get("parent_node_id") is not None else None),
            child_node_ids=[str(child_id) for child_id in data.get("child_node_ids", []) if isinstance(child_id, str)],
            state=deserialize_node_state(data.get("state"), fallback_role_counts),
            analysis=dict(data.get("analysis", {})),
            player_probabilities=dict(data.get("player_probabilities", {})),
            branch_meta=dict(data.get("branch_meta", {})),
        )


@dataclass
class StoredTreeRecord:
    tree_id: str
    current_node_id: str
    root_node_id: str
    player_configs: dict[str, dict[str, object]] = field(default_factory=dict)
    nodes_by_id: dict[str, StoredNodeRecord] = field(default_factory=dict)
    role_counts: dict[str, int] = field(default_factory=dict)
    rules: dict[str, str] = field(default_factory=dict)
    ui_state: dict[str, object] = field(default_factory=dict)

    def serialize(self) -> dict[str, object]:
        return {
            "tree_id": self.tree_id,
            "current_node_id": self.current_node_id,
            "root_node_id": self.root_node_id,
            "player_configs": {
                str(player_index): dict(player_config)
                for player_index, player_config in self.player_configs.items()
            },
            "nodes_by_id": {
                node_id: node.serialize()
                for node_id, node in self.nodes_by_id.items()
            },
            "role_counts": self.role_counts.copy(),
            "rules": self.rules.copy(),
            "ui_state": self.ui_state.copy(),
        }

    @classmethod
    def deserialize(cls, data: dict[str, object], fallback_role_counts: dict[str, int]) -> "StoredTreeRecord":
        raw_nodes = dict(data.get("nodes_by_id", {}))
        return cls(
            tree_id=str(data.get("tree_id", "")),
            current_node_id=str(data.get("current_node_id", "")),
            root_node_id=str(data.get("root_node_id", "")),
            player_configs={
                str(player_index): dict(player_config)
                for player_index, player_config in dict(data.get("player_configs", {})).items()
                if isinstance(player_config, dict)
            },
            nodes_by_id={
                str(node_id): StoredNodeRecord.deserialize(node_data, fallback_role_counts)
                for node_id, node_data in raw_nodes.items()
                if isinstance(node_data, dict)
            },
            role_counts=dict(data.get("role_counts", {})),
            rules=dict(data.get("rules", {})),
            ui_state=dict(data.get("ui_state", {})),
        )


class TreeStorage(Protocol):
    def load_tree(self, tree_id: str) -> StoredTreeRecord | None:
        ...

    def save_tree(self, tree: StoredTreeRecord) -> None:
        ...


class InMemoryTreeStorage:
    def __init__(self) -> None:
        self._trees: dict[str, StoredTreeRecord] = {}

    def load_tree(self, tree_id: str) -> StoredTreeRecord | None:
        return self._trees.get(tree_id)

    def save_tree(self, tree: StoredTreeRecord) -> None:
        self._trees[tree.tree_id] = tree


class SupabaseTreeStorage:
    def __init__(self, db_url: str) -> None:
        self.db_url = db_url

    def load_tree(self, tree_id: str) -> StoredTreeRecord | None:
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            tree_row = conn.execute(
                "select id, role_counts, rules, ui_state, current_node_id from game_trees where id = %s",
                (tree_id,),
            ).fetchone()
            if tree_row is None:
                return None

            player_rows = conn.execute(
                "select player_index, name from tree_player_configs where tree_id = %s order by player_index",
                (tree_id,),
            ).fetchall()
            node_rows = conn.execute(
                "select id, parent_node_id, branch_label, selected_target, day, phase_key, state, analysis, player_probabilities, child_node_ids from tree_nodes where tree_id = %s",
                (tree_id,),
            ).fetchall()

        db_to_app: dict[str, str] = {}
        serialized_nodes: list[dict[str, object]] = []
        for row in node_rows:
            branch_meta = _json_dict(row["analysis"]).get("branch_meta", {})
            app_node_id = str(branch_meta.get("app_node_id", row["id"]))
            db_to_app[str(row["id"])] = app_node_id
            serialized_nodes.append({
                "db_id": str(row["id"]),
                "parent_db_id": str(row["parent_node_id"]) if row["parent_node_id"] is not None else None,
                "node_id": app_node_id,
                "state": _json_dict(row["state"]),
                "analysis": _json_dict(row["analysis"]),
                "player_probabilities": _json_dict(row["player_probabilities"]),
                "child_node_ids": _json_list(row["child_node_ids"]),
            })

        nodes_by_id: dict[str, StoredNodeRecord] = {}
        for row in serialized_nodes:
            nodes_by_id[row["node_id"]] = StoredNodeRecord.deserialize(
                {
                    "node_id": row["node_id"],
                    "parent_node_id": db_to_app.get(row["parent_db_id"]) if row["parent_db_id"] else None,
                    "child_node_ids": [db_to_app.get(child_db_id, child_db_id) for child_db_id in row["child_node_ids"]],
                    "state": row["state"],
                    "analysis": row["analysis"],
                    "player_probabilities": row["player_probabilities"],
                    "branch_meta": _json_dict(row["analysis"]).get("branch_meta", {}),
                },
                dict(_json_dict(tree_row["role_counts"])) or {"villager": 1, "wolf": 1},
            )

        current_db_node_id = str(tree_row["current_node_id"]) if tree_row["current_node_id"] is not None else ""
        root_app_node_id = next((node_id for node_id, node in nodes_by_id.items() if node.parent_node_id is None), "")
        return StoredTreeRecord(
            tree_id=str(tree_row["id"]),
            current_node_id=db_to_app.get(current_db_node_id, ""),
            root_node_id=root_app_node_id,
            player_configs={str(row["player_index"]): {"index": row["player_index"], "name": row["name"]} for row in player_rows},
            nodes_by_id=nodes_by_id,
            role_counts=dict(_json_dict(tree_row["role_counts"])),
            rules=dict(_json_dict(tree_row["rules"])),
            ui_state=dict(_json_dict(tree_row["ui_state"])),
        )

    def save_tree(self, tree: StoredTreeRecord) -> None:
        tree_db_id = tree.tree_id if _looks_like_uuid(tree.tree_id) else str(uuid4())
        db_node_ids = {node_id: str(uuid4()) for node_id in tree.nodes_by_id}
        current_db_node_id = db_node_ids.get(tree.current_node_id)

        with psycopg.connect(self.db_url) as conn:
            with conn.transaction():
                conn.execute(
                    """
                    insert into game_trees (id, role_counts, rules, ui_state, current_node_id)
                    values (%s, %s, %s, %s, %s)
                    on conflict (id) do update set
                        role_counts = excluded.role_counts,
                        rules = excluded.rules,
                        ui_state = excluded.ui_state,
                        current_node_id = excluded.current_node_id,
                        updated_at = now()
                    """,
                    (
                        tree_db_id,
                        Jsonb(tree.role_counts),
                        Jsonb(tree.rules),
                        Jsonb(tree.ui_state),
                        current_db_node_id,
                    ),
                )
                conn.execute("delete from tree_player_configs where tree_id = %s", (tree_db_id,))
                conn.execute("delete from tree_nodes where tree_id = %s", (tree_db_id,))

                for player_config in tree.player_configs.values():
                    conn.execute(
                        "insert into tree_player_configs (tree_id, player_index, name) values (%s, %s, %s)",
                        (tree_db_id, int(player_config.get("index", 0)), str(player_config.get("name", "player"))),
                    )

                for node in tree.nodes_by_id.values():
                    analysis_payload = dict(node.analysis)
                    branch_meta = dict(node.branch_meta)
                    branch_meta["app_node_id"] = node.node_id
                    analysis_payload["branch_meta"] = branch_meta
                    conn.execute(
                        """
                        insert into tree_nodes (
                            id, tree_id, parent_node_id, branch_label, selected_target, day, phase_key,
                            state, analysis, player_probabilities, child_node_ids
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            db_node_ids[node.node_id],
                            tree_db_id,
                            db_node_ids.get(node.parent_node_id) if node.parent_node_id else None,
                            str(branch_meta.get("label", "")) or None,
                            branch_meta.get("selected_target"),
                            node.state.day,
                            node.state.phase_key,
                            Jsonb(serialize_node_state(node.state)),
                            Jsonb(analysis_payload),
                            Jsonb(node.player_probabilities),
                            Jsonb([db_node_ids[child_id] for child_id in node.child_node_ids if child_id in db_node_ids]),
                        ),
                    )
            conn.commit()

        tree.tree_id = tree_db_id


def build_tree_storage(runtime_config: RuntimeConfig) -> TreeStorage:
    if runtime_config.has_supabase_db:
        return SupabaseTreeStorage(runtime_config.supabase_db_url)
    return InMemoryTreeStorage()


def _looks_like_uuid(value: str) -> bool:
    parts = value.split("-")
    return len(parts) == 5


def _json_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return dict(json.loads(value))
    return {}


def _json_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [str(item) for item in json.loads(value)]
    return []
